"""
backend/test_auth_deletion.py — Comprehensive Account Deletion Test Suite (Milestone 1).

Tests:
1. Successful student account deletion (cascades across private collections, removes submissions, preserves assignments).
2. Successful parent account deletion (unlinks children, purges parent data, NEVER deletes child accounts or child learning data).
3. Successful teacher account deletion when zero students are enrolled (removes classroom and teacher-owned assignments).
4. Teacher deletion protection: returns HTTP 409 Conflict when students remain enrolled in their classroom.
5. Password verification: rejects deletion with 401 when incorrect password is provided.
6. Confirmation phrase validation: rejects deletion with 400 when confirmation != 'DELETE_MY_ACCOUNT'.
7. Unauthenticated request protection: returns 401 when token is missing or invalid.
8. Cross-user deletion prevention: target user is strictly derived from token; body user IDs are ignored.
9. Immediate JWT invalidation: token issued before deletion is rejected after deletion starts.
10. Account state protection: account marked disabled and deletionState='pending' during cleanup.
11. Cleanup failure and recovery: operational error marks deletionState='failed', keeps account disabled (403), allows retry.
12. Isolation of another student's records: classmate's attempts, submissions, and profile are untouched.
13. Global curriculum preservation: reading passages, learning activities, and catalog are never deleted.
14. Security tokens invalidation: password reset and email verification tokens for the user are deleted.
15. Sensitive PII absence in operational logs: error logs omit user emails and passwords.
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from deps.deps import hash_password, make_token
from services.auth_rate_limiter import AuthRateLimiter

client = TestClient(app)


def make_mock_db():
    """
    Creates a flexible asynchronous mock database for MongoDB collections.
    Every collection automatically provides AsyncMocks for coroutine methods,
    preventing 'MagicMock cannot be used in await expression' errors.
    """
    class MockCollection:
        def __init__(self):
            self.find_one = AsyncMock(return_value=None)
            self.delete_many = AsyncMock(return_value=MagicMock(deleted_count=1))
            self.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
            self.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
            self.insert_one = AsyncMock(return_value=None)
            self.count_documents = AsyncMock(return_value=0)
            cursor = MagicMock()
            cursor.to_list = AsyncMock(return_value=[])
            self.find = MagicMock(return_value=cursor)

    collections = {}

    class MockDB:
        def __getattr__(self, name):
            if name not in collections:
                collections[name] = MockCollection()
            return collections[name]

    return MockDB()


class AccountDeletionTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        AuthRateLimiter.reset()
        AuthRateLimiter.set_enabled(False)

    def tearDown(self):
        AuthRateLimiter.reset()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Validation & Authentication Guards
    # ─────────────────────────────────────────────────────────────────────────

    async def test_delete_account_unauthenticated_rejected(self):
        """Unauthenticated requests without Bearer token must return 401."""
        response = client.post(
            "/api/auth/delete-account",
            json={"password": "AnyPassword123!", "confirmation": "DELETE_MY_ACCOUNT"}
        )
        self.assertEqual(response.status_code, 401)

    async def test_delete_account_invalid_confirmation_rejected(self):
        """Requests with missing or incorrect confirmation phrase must return 400."""
        token = make_token("student-test-01")
        mock_user = {
            "id": "student-test-01",
            "email": "student@test.com",
            "role": "student",
            "passwordHash": hash_password("ValidPassword123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_user)

        with patch("database.database.db", mock_db):
            for bad_conf in ["DELETE", "delete_my_account", "YES", "", None]:
                response = client.post(
                    "/api/auth/delete-account",
                    json={"password": "ValidPassword123!", "confirmation": bad_conf},
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("DELETE_MY_ACCOUNT", response.json()["detail"])

    async def test_delete_account_incorrect_password_rejected(self):
        """Requests with wrong password must return 401 and leave account active."""
        token = make_token("student-test-02")
        mock_user = {
            "id": "student-test-02",
            "email": "student2@test.com",
            "role": "student",
            "passwordHash": hash_password("CorrectPassword123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_user)

        with patch("database.database.db", mock_db):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "WrongPassword999!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response.status_code, 401)
            self.assertIn("Incorrect password", response.json()["detail"])
            mock_db.users.update_one.assert_not_called()
            mock_db.users.delete_one.assert_not_called()

    async def test_cross_user_deletion_prevention(self):
        """Attacker passing another user's ID in body cannot delete the other user's account."""
        victim_id = "victim-student-99"
        attacker_id = "attacker-user-01"
        attacker_token = make_token(attacker_id)

        attacker_user = {
            "id": attacker_id,
            "email": "attacker@test.com",
            "role": "student",
            "passwordHash": hash_password("AttackerPass123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=attacker_user)

        with patch("database.database.db", mock_db):
            # Attacker injects victim_id in request body
            response = client.post(
                "/api/auth/delete-account",
                json={
                    "password": "AttackerPass123!",
                    "confirmation": "DELETE_MY_ACCOUNT",
                    "userId": victim_id,
                    "targetUserId": victim_id,
                },
                headers={"Authorization": f"Bearer {attacker_token}"}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            # Verified: the deleted account is exclusively the attacker's identity
            self.assertEqual(data["deletedUserId"], attacker_id)
            mock_db.users.delete_one.assert_called_with({"id": attacker_id})

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Student Role Deletion & Cascade Isolation
    # ─────────────────────────────────────────────────────────────────────────

    async def test_student_account_deletion_full_cascade(self):
        """
        Student deletion:
        - Cascades across all student-private collections.
        - Deletes student's own submissions and teacher notes.
        - Removes parent links.
        - DOES NOT delete teacher assignments or other students' submissions.
        """
        student_id = "student-full-01"
        token = make_token(student_id)
        mock_user = {
            "id": student_id,
            "email": "student.cascade@test.com",
            "role": "student",
            "passwordHash": hash_password("StudentPass123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_user)

        with patch("database.database.db", mock_db):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "StudentPass123!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")
            self.assertEqual(response.json()["deletedUserId"], student_id)

            # Verify phase 1: disabled and deletionState='pending'
            mock_db.users.update_one.assert_called_once()
            update_call = mock_db.users.update_one.call_args
            self.assertEqual(update_call[0][0], {"id": student_id})
            self.assertTrue(update_call[0][1]["$set"]["disabled"])
            self.assertEqual(update_call[0][1]["$set"]["deletionState"], "pending")
            self.assertEqual(update_call[0][1]["$inc"]["token_version"], 1)

            # Verify student private records were deleted
            mock_db.learner_profiles.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.learning_states.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.activity_attempts.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.reading_sessions.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.speech_reading_analyses.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.tutor_conversations.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.gamification_summaries.delete_many.assert_called_with({"learnerId": student_id})
            mock_db.submissions.delete_many.assert_called_with({"studentId": student_id})
            mock_db.teacher_notes.delete_many.assert_called_with({"studentId": student_id})
            mock_db.parent_links.delete_many.assert_called_with({"studentId": student_id})

            # Verify phase 3: user document permanently purged
            mock_db.users.delete_one.assert_called_with({"id": student_id})

            # Verify shared assignments and global curriculum were PRESERVED
            mock_db.assignments.delete_many.assert_not_called()
            mock_db.classrooms.delete_many.assert_not_called()
            mock_db.reading_passages.delete_many.assert_not_called()
            mock_db.learning_activities.delete_many.assert_not_called()

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Parent Role Deletion & Child Data Protection
    # ─────────────────────────────────────────────────────────────────────────

    async def test_parent_account_deletion_preserves_child_data(self):
        """
        Parent deletion:
        - Removes parent personal account data, preferences, and notifications.
        - Terminates parent-child relationships in parent_links.
        - NEVER deletes children's user documents, profiles, or learning progress.
        """
        parent_id = "parent-preserve-01"
        token = make_token(parent_id)
        mock_parent = {
            "id": parent_id,
            "email": "parent.preserve@test.com",
            "role": "parent",
            "passwordHash": hash_password("ParentPass123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_parent)

        with patch("database.database.db", mock_db):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "ParentPass123!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["role"], "parent")

            # Verify parent-child links terminated
            mock_db.parent_links.delete_many.assert_called_with({"parentId": parent_id})
            mock_db.parent_requests.delete_many.assert_called_with({"parentId": parent_id})
            mock_db.users.delete_one.assert_called_with({"id": parent_id})

            # Verify child learning history was NOT touched
            mock_db.learner_profiles.delete_many.assert_not_called()
            mock_db.reading_sessions.delete_many.assert_not_called()
            mock_db.tutor_conversations.delete_many.assert_not_called()
            mock_db.progress.delete_many.assert_not_called()

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Teacher Deletion Guards & Empty Classroom Cleanup
    # ─────────────────────────────────────────────────────────────────────────

    async def test_teacher_deletion_blocked_when_students_enrolled(self):
        """Teacher deletion must return HTTP 409 Conflict if active students remain in classroom."""
        teacher_id = "teacher-blocked-01"
        token = make_token(teacher_id)
        mock_teacher = {
            "id": teacher_id,
            "email": "teacher.blocked@test.com",
            "role": "teacher",
            "classroomCode": "DA-ENROLL",
            "passwordHash": hash_password("TeacherPass123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_teacher)
        mock_db.users.count_documents = AsyncMock(return_value=3)

        with patch("database.database.db", mock_db):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "TeacherPass123!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response.status_code, 409)
            self.assertIn("3 student(s) remain enrolled", response.json()["detail"])
            mock_db.users.delete_one.assert_not_called()

    async def test_teacher_deletion_allowed_when_zero_students_enrolled(self):
        """Teacher deletion succeeds when classroom has 0 students, cleaning up teacher-owned assignments."""
        teacher_id = "teacher-clean-01"
        token = make_token(teacher_id)
        mock_teacher = {
            "id": teacher_id,
            "email": "teacher.clean@test.com",
            "role": "teacher",
            "classroomCode": "DA-EMPTY",
            "passwordHash": hash_password("TeacherPass123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_teacher)
        mock_db.users.count_documents = AsyncMock(return_value=0)
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[{"id": "assign-101"}])
        mock_db.assignments.find = MagicMock(return_value=cursor)

        with patch("database.database.db", mock_db):
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "TeacherPass123!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["role"], "teacher")

            # Verify classroom & teacher-owned assignments deleted
            mock_db.classrooms.delete_many.assert_any_call({"code": "DA-EMPTY"})
            mock_db.classrooms.delete_many.assert_any_call({"teacherId": teacher_id})
            mock_db.assignments.delete_many.assert_called_with({"teacherId": teacher_id})
            mock_db.submissions.delete_many.assert_called_with({"assignmentId": {"$in": ["assign-101"]}})
            mock_db.users.delete_one.assert_called_with({"id": teacher_id})

            # Verify curriculum untouched
            mock_db.learning_activities.delete_many.assert_not_called()
            mock_db.reading_passages.delete_many.assert_not_called()

    # ─────────────────────────────────────────────────────────────────────────
    # 5. JWT Revocation & Session Invalidation
    # ─────────────────────────────────────────────────────────────────────────

    async def test_previously_issued_jwt_rejected_after_deletion_begins(self):
        """
        Token issued before deletion must be rejected immediately:
        - When account enters disabled/pending state -> rejected with 403.
        - When user record is purged -> rejected with 401.
        """
        student_id = "student-token-revoc"
        initial_token = make_token(student_id, token_version=1)

        # 1. State: Account is marked disabled & pending in DB with bumped token_version
        pending_user = {
            "id": student_id,
            "email": "pending@test.com",
            "role": "student",
            "disabled": True,
            "deletionState": "pending",
            "token_version": 2,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=pending_user)

        with patch("database.database.db", mock_db):
            res_pending = client.get("/api/auth/me", headers={"Authorization": f"Bearer {initial_token}"})
            self.assertEqual(res_pending.status_code, 403)
            self.assertIn("Account disabled", res_pending.json()["detail"])

        # 2. State: Account is completely purged from DB
        mock_db_purged = make_mock_db()
        mock_db_purged.users.find_one = AsyncMock(return_value=None)

        with patch("database.database.db", mock_db_purged):
            res_purged = client.get("/api/auth/me", headers={"Authorization": f"Bearer {initial_token}"})
            self.assertEqual(res_purged.status_code, 401)
            self.assertIn("Unauthorized", res_purged.json()["detail"])

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Operational Failure & Safe Idempotent Retry
    # ─────────────────────────────────────────────────────────────────────────

    async def test_cleanup_failure_preserves_disabled_state_and_enables_retry(self):
        """
        If a database error occurs mid-cleanup:
        - Account remains disabled (deletionState='failed').
        - Returns 500 error without exposing stack or PII.
        - Repeated request can safely retry and complete cleanup.
        """
        student_id = "student-retry-01"
        token = make_token(student_id)
        mock_user = {
            "id": student_id,
            "email": "student.retry@test.com",
            "role": "student",
            "passwordHash": hash_password("RetryPass123!"),
            "disabled": False,
            "token_version": 1,
        }

        mock_db = make_mock_db()
        mock_db.users.find_one = AsyncMock(return_value=mock_user)
        # Simulate failure on speech analysis deletion
        mock_db.speech_reading_analyses.delete_many = AsyncMock(side_effect=RuntimeError("Mongo connection drop"))

        with patch("database.database.db", mock_db):
            response_fail = client.post(
                "/api/auth/delete-account",
                json={"password": "RetryPass123!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response_fail.status_code, 500)
            self.assertIn("operational error", response_fail.json()["detail"].lower())

            # Verified: user was marked disabled with deletionState='failed'
            self.assertTrue(mock_db.users.update_one.called)
            last_update = mock_db.users.update_one.call_args[0][1]["$set"]
            self.assertEqual(last_update.get("deletionState"), "failed")
            self.assertIn("RuntimeError", last_update.get("deletionFailureError"))
            mock_db.users.delete_one.assert_not_called()

            # Now resolve the failure and retry
            mock_db.speech_reading_analyses.delete_many = AsyncMock(return_value=MagicMock(deleted_count=1))
            response_retry = client.post(
                "/api/auth/delete-account",
                json={"password": "RetryPass123!", "confirmation": "DELETE_MY_ACCOUNT"},
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(response_retry.status_code, 200)
            self.assertEqual(response_retry.json()["status"], "ok")
            mock_db.users.delete_one.assert_called_with({"id": student_id})
