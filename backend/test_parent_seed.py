"""
backend/test_parent_seed.py — Comprehensive Unit & Integration Tests for Idempotent Parent Demo Seeding.

Verifies:
1. Fresh database: teacher, students, parent, and parent-student link are created.
2. Partial existing database: a missing parent is added even when other demo users exist.
3. Existing parent: re-running the seed does not reset password or overwrite profile fields.
4. Existing parent link: re-running does not duplicate relationships.
5. Revoked link: seeding does not silently reactivate it.
6. Missing intended student: no invalid or dangling relationship is created.
7. Conflicting parent account role: handled safely without destructive updates.
8. Repeated seed execution: results remain completely stable and idempotent.
"""
import copy
import time
import unittest
from unittest.mock import patch

from database.database import (
    _seed_demo_data,
    seed_demo_data,
    hash_password,
    _default_settings,
)
from deps.deps import verify_password


class MockCollection:
    """In-memory asynchronous collection mock mimicking Motor collections."""

    def __init__(self, name="mock_collection"):
        self.name = name
        self.docs = []

    def _match(self, doc, query):
        for k, v in query.items():
            if k == "$or":
                matched_or = False
                for sub_q in v:
                    if self._match(doc, sub_q):
                        matched_or = True
                        break
                if not matched_or:
                    return False
            elif "." in k:
                # Basic nested field check
                parts = k.split(".")
                curr = doc
                for p in parts:
                    if isinstance(curr, dict) and p in curr:
                        curr = curr[p]
                    else:
                        curr = None
                        break
                if curr != v:
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if self._match(d, query):
                res = copy.deepcopy(d)
                if projection and "_id" in projection and projection["_id"] == 0:
                    res.pop("_id", None)
                return res
        return None

    async def insert_one(self, doc):
        stored = copy.deepcopy(doc)
        if "_id" not in stored:
            stored["_id"] = str(len(self.docs) + 1)
        self.docs.append(stored)
        return type("InsertResult", (), {"inserted_id": stored["_id"]})()

    async def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._match(d, query):
                if "$set" in update:
                    for sk, sv in update["$set"].items():
                        if "." in sk:
                            parts = sk.split(".")
                            curr = d
                            for p in parts[:-1]:
                                curr = curr.setdefault(p, {})
                            curr[parts[-1]] = sv
                        else:
                            d[sk] = sv
                return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1})()

        if upsert:
            new_doc = copy.deepcopy(query)
            if "$set" in update:
                new_doc.update(copy.deepcopy(update["$set"]))
            await self.insert_one(new_doc)
            return type("UpdateResult", (), {"matched_count": 0, "upserted_id": new_doc.get("_id")})()

        return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0})()

    async def count_documents(self, query):
        count = 0
        for d in self.docs:
            if self._match(d, query):
                count += 1
        return count


class MockDB:
    """Mock MongoDB database containing all collections used by _seed_demo_data."""

    def __init__(self):
        self.users = MockCollection("users")
        self.classrooms = MockCollection("classrooms")
        self.progress = MockCollection("progress")
        self.libraries = MockCollection("libraries")
        self.screening_results = MockCollection("screening_results")
        self.prediction_history = MockCollection("prediction_history")
        self.assignments = MockCollection("assignments")
        self.submissions = MockCollection("submissions")
        self.notifications = MockCollection("notifications")
        self.teacher_notes = MockCollection("teacher_notes")
        self.parent_links = MockCollection("parent_links")


class TestParentDemoSeeding(unittest.IsolatedAsyncioTestCase):
    """Test suite verifying idempotent demo parent account and relationship seeding."""

    def setUp(self):
        self.mock_db = MockDB()

    async def test_fresh_database_seed(self):
        """On a fresh database, teacher, students, parent, and parent-student link are seeded."""
        with patch("database.database.db", self.mock_db):
            await seed_demo_data()

        # 1. Verify Parent Account
        parent = await self.mock_db.users.find_one({"email": "parent@demo.school"})
        self.assertIsNotNone(parent, "parent@demo.school must be created")
        self.assertEqual(parent["name"], "Meera Sharma")
        self.assertEqual(parent["role"], "parent")
        self.assertTrue(parent["isDemo"])
        self.assertTrue(parent["onboardingComplete"])
        self.assertTrue(verify_password("Demo@123", parent["passwordHash"]))

        # 2. Verify Student Account
        student = await self.mock_db.users.find_one({"email": "aarav@demo.school"})
        self.assertIsNotNone(student, "aarav@demo.school must be created")
        self.assertEqual(student["role"], "student")

        # 3. Verify Initial Parent-Student Link
        link = await self.mock_db.parent_links.find_one({
            "parentId": parent["id"],
            "studentId": student["id"]
        })
        self.assertIsNotNone(link, "Active link between Meera and Aarav must be seeded")
        self.assertEqual(link["relationship"], "Mother")
        self.assertEqual(link["status"], "active")
        self.assertEqual(link["verifiedBy"], "invitation_code")
        self.assertIsNone(link["revokedAt"])

    async def test_partial_existing_database_adds_missing_parent(self):
        """When teacher and students already exist, missing parent is created and linked."""
        teacher_doc = {
            "id": "t-1",
            "email": "teacher@demo.school",
            "name": "Mrs. Anjali Sharma",
            "role": "teacher",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        }
        aarav_doc = {
            "id": "s-1",
            "email": "aarav@demo.school",
            "name": "Aarav Sharma",
            "role": "student",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        }
        await self.mock_db.users.insert_one(teacher_doc)
        await self.mock_db.users.insert_one(aarav_doc)

        with patch("database.database.db", self.mock_db):
            await _seed_demo_data()

        # Parent should now exist
        parent = await self.mock_db.users.find_one({"email": "parent@demo.school"})
        self.assertIsNotNone(parent)
        self.assertEqual(parent["role"], "parent")

        # Link should be established to existing Aarav
        link = await self.mock_db.parent_links.find_one({
            "parentId": parent["id"],
            "studentId": "s-1"
        })
        self.assertIsNotNone(link)
        self.assertEqual(link["status"], "active")
        self.assertEqual(link["relationship"], "Mother")

        # Teacher and student must remain intact
        teacher_after = await self.mock_db.users.find_one({"email": "teacher@demo.school"})
        self.assertEqual(teacher_after["id"], "t-1")

    async def test_existing_parent_preserves_password_and_fields(self):
        """Re-running seed must NOT overwrite existing parent password or attributes."""
        custom_hash = hash_password("MyCustomPassword999!")
        existing_parent = {
            "id": "parent-custom-id",
            "email": "parent@demo.school",
            "name": "Meera Custom Sharma",
            "role": "parent",
            "passwordHash": custom_hash,
            "customAttribute": "preserved",
            "isDemo": True,
        }
        await self.mock_db.users.insert_one(existing_parent)

        with patch("database.database.db", self.mock_db):
            await _seed_demo_data()

        parent_after = await self.mock_db.users.find_one({"email": "parent@demo.school"})
        self.assertEqual(parent_after["id"], "parent-custom-id")
        self.assertEqual(parent_after["passwordHash"], custom_hash, "Password hash must not be overwritten")
        self.assertEqual(parent_after["name"], "Meera Custom Sharma")
        self.assertEqual(parent_after["customAttribute"], "preserved")

    async def test_existing_parent_link_not_duplicated(self):
        """Re-running seed must not create duplicate parent links."""
        parent_id = "parent-001"
        student_id = "student-001"
        await self.mock_db.users.insert_one({
            "id": parent_id,
            "email": "parent@demo.school",
            "name": "Meera Sharma",
            "role": "parent",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        })
        await self.mock_db.users.insert_one({
            "id": student_id,
            "email": "aarav@demo.school",
            "name": "Aarav Sharma",
            "role": "student",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        })
        await self.mock_db.parent_links.insert_one({
            "id": "link-original-id",
            "parentId": parent_id,
            "studentId": student_id,
            "relationship": "Mother",
            "status": "active",
        })

        with patch("database.database.db", self.mock_db):
            await _seed_demo_data()

        links_count = await self.mock_db.parent_links.count_documents({
            "parentId": parent_id,
            "studentId": student_id,
        })
        self.assertEqual(links_count, 1, "Duplicate link must not be created")
        link = await self.mock_db.parent_links.find_one({"parentId": parent_id, "studentId": student_id})
        self.assertEqual(link["id"], "link-original-id")

    async def test_revoked_link_not_silently_reactivated(self):
        """Seeding must NOT silently reactivate or modify an existing revoked link."""
        parent_id = "parent-001"
        student_id = "student-001"
        revoked_timestamp = 1700000000
        await self.mock_db.users.insert_one({
            "id": parent_id,
            "email": "parent@demo.school",
            "role": "parent",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        })
        await self.mock_db.users.insert_one({
            "id": student_id,
            "email": "aarav@demo.school",
            "role": "student",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        })
        await self.mock_db.parent_links.insert_one({
            "id": "revoked-link-id",
            "parentId": parent_id,
            "studentId": student_id,
            "relationship": "Mother",
            "status": "revoked",
            "revokedAt": revoked_timestamp,
            "revokedBy": parent_id,
        })

        with patch("database.database.db", self.mock_db):
            await _seed_demo_data()

        link = await self.mock_db.parent_links.find_one({"parentId": parent_id, "studentId": student_id})
        self.assertEqual(link["status"], "revoked", "Revoked link must remain revoked")
        self.assertEqual(link["revokedAt"], revoked_timestamp)

    async def test_missing_intended_student_skips_link(self):
        """If aarav@demo.school does not exist, no dangling link is created."""
        parent_id = "parent-001"
        await self.mock_db.users.insert_one({
            "id": parent_id,
            "email": "parent@demo.school",
            "role": "parent",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        })
        # aarav@demo.school is NOT present in mock_db

        with patch("database.database.db", self.mock_db):
            # We mock demo_students as empty in this specific check to test absence of aarav
            with patch("database.database.db.users.find_one") as mock_find_one:
                async def side_effect(query):
                    if query.get("email") == "parent@demo.school":
                        return {"id": parent_id, "role": "parent", "email": "parent@demo.school", "name": "Meera Sharma"}
                    if query.get("email") == "aarav@demo.school":
                        return None
                    return None
                mock_find_one.side_effect = side_effect
                await _seed_demo_data()

        links_count = await self.mock_db.parent_links.count_documents({})
        self.assertEqual(links_count, 0, "No link should be created when student is missing")

    async def test_conflicting_parent_account_role_handled_safely(self):
        """If parent@demo.school exists with a non-parent role, it is not modified or linked."""
        conflicting_user = {
            "id": "conflicting-001",
            "email": "parent@demo.school",
            "name": "Conflicting Role User",
            "role": "student",  # conflicting role
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        }
        await self.mock_db.users.insert_one(conflicting_user)
        await self.mock_db.users.insert_one({
            "id": "aarav-001",
            "email": "aarav@demo.school",
            "role": "student",
            "isDemo": True,
            "passwordHash": hash_password("Demo@123"),
        })

        with patch("database.database.db", self.mock_db):
            await _seed_demo_data()

        user_after = await self.mock_db.users.find_one({"email": "parent@demo.school"})
        self.assertEqual(user_after["role"], "student", "Conflicting role must not be changed destructively")
        links_count = await self.mock_db.parent_links.count_documents({})
        self.assertEqual(links_count, 0, "No parent link should be established for non-parent account")

    async def test_repeated_seed_execution_is_stable(self):
        """Running _seed_demo_data multiple times yields identical, stable state."""
        with patch("database.database.db", self.mock_db):
            await _seed_demo_data()
            count_users_1 = await self.mock_db.users.count_documents({})
            count_links_1 = await self.mock_db.parent_links.count_documents({})

            await _seed_demo_data()
            count_users_2 = await self.mock_db.users.count_documents({})
            count_links_2 = await self.mock_db.parent_links.count_documents({})

            await _seed_demo_data()
            count_users_3 = await self.mock_db.users.count_documents({})
            count_links_3 = await self.mock_db.parent_links.count_documents({})

        self.assertEqual(count_users_1, count_users_2)
        self.assertEqual(count_users_2, count_users_3)
        self.assertEqual(count_links_1, count_links_2)
        self.assertEqual(count_links_2, count_links_3)
        self.assertEqual(count_links_1, 1)


if __name__ == "__main__":
    unittest.main()
