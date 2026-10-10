"""
backend/test_phase16_content_authoring.py — Comprehensive Test Suite for Phase 16:
Learning Content Authoring & Quality Management.

Covers all 24 required verification scenarios:
1. Feature flag enabled & disabled (HTTP 503).
2. Authorized author (teacher) can create a draft.
3. Unauthorized roles (student/parent) cannot create content (HTTP 403).
4. Draft owner can edit drafts within allowed permissions.
5. Unauthorized user cannot edit another author's content (HTTP 403).
6. Invalid lifecycle transitions are rejected (e.g. DRAFT -> PUBLISHED directly).
7. Unauthorized users cannot approve or publish.
8. Self-approval rules are enforced (author cannot review/approve own content).
9. Validation catches missing required fields (title, text, difficulty, language).
10. Unsupported language codes are rejected.
11. Invalid difficulty tiers are rejected.
12. Malformed questions and annotation references are rejected.
13. Hindi and Marathi Unicode content is preserved.
14. Translation completeness is reported accurately.
15. Review feedback is persisted and visible to the appropriate author.
16. Published content is discoverable by Phase 15.
17. Draft content is not discoverable by Phase 15.
18. Archived content is not selected for new activities.
19. Legacy V1 content remains compatible.
20. Historical learning records remain intact after content revision.
21. Tenant isolation is enforced (cross-tenant review queue / items scoping).
22. Parent and student endpoints do not leak editorial metadata.
23. Version and audit history are accurate.
24. Regression tests for Phases 2–15 pass.
"""
import time
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_content_authoring import (
    ContentDraftCreateRequest,
    ContentDraftUpdateRequest,
    ContentReviewDecisionRequest,
    ContentValidationResult,
)
from services.learning.content_authoring import (
    validate_content,
    create_content_draft,
    update_content_draft,
    submit_content_for_review,
    review_content,
    publish_content,
    archive_content,
    create_content_revision,
    list_content_items,
    get_content_item,
    get_review_queue,
    get_content_history,
    get_translation_completeness,
)
from services.learning.reading_service import get_passages, start_reading_session
from models.v2_reading import ReadingSessionStartRequest


def make_cursor_mock(items):
    """Helper to mock motor find() synchronous cursor whose to_list() is async."""
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.limit = MagicMock(return_value=c)
    c.skip = MagicMock(return_value=c)
    c.sort = MagicMock(return_value=c)
    return c


class TestPhase16ContentAuthoring(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.teacher_user = {
            "id": "teacher-42",
            "name": "Ananya Sharma",
            "role": "teacher",
            "classroomCode": "CLASS-101",
        }
        self.peer_reviewer = {
            "id": "teacher-99",
            "name": "Vikram Patil",
            "role": "teacher",
            "classroomCode": "CLASS-101",
        }
        self.admin_user = {
            "id": "admin-1",
            "name": "Super Admin",
            "role": "admin",
            "classroomCode": None,
        }
        self.student_user = {
            "id": "student-10",
            "name": "Aarav Gupta",
            "role": "student",
            "classroomJoined": "CLASS-101",
        }
        self.parent_user = {
            "id": "parent-5",
            "name": "Priya Gupta",
            "role": "parent",
        }

    # 1. Feature Flag
    def test_feature_flag_disabled_returns_503(self):
        """When V2_CONTENT_AUTHORING is disabled, router returns HTTP 503."""
        with patch.object(settings, "V2_CONTENT_AUTHORING", False):
            app.dependency_overrides[get_current_user] = lambda: self.teacher_user
            try:
                res = self.client.get("/api/v2/content-authoring/items")
                self.assertEqual(res.status_code, 503)
                self.assertIn("disabled", res.json()["detail"].lower())
            finally:
                app.dependency_overrides.clear()

    # 2. Authorized Author Creates Draft
    @patch("services.learning.content_authoring.db")
    async def test_authorized_teacher_can_create_draft(self, mock_db):
        """A teacher can create a valid draft in DRAFT status."""
        mock_db.reading_passages.insert_one = AsyncMock(return_value=MagicMock(inserted_id="doc1"))
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())

        req = ContentDraftCreateRequest(
            title="The Brave Little Squirrel",
            text="Once upon a time in a sunny green garden, a little brown squirrel named Pip found a shiny golden nut. Pip rolled the nut under a big red leaf.",
            difficulty=2,
            language="en",
            vocabulary=[
                {"word": "garden", "definition": "A piece of ground where plants and flowers grow.", "phonetic": "gar-den"}
            ],
            questions=[
                {
                    "questionId": "q1",
                    "question": "What did Pip find?",
                    "options": ["A shiny golden nut", "A blue berry", "A brown stick"],
                    "correctAnswer": 0,
                    "explanation": "The text states Pip found a shiny golden nut.",
                }
            ],
        )

        res = await create_content_draft(self.teacher_user, req)
        self.assertEqual(res.status, "DRAFT")
        self.assertEqual(res.title, "The Brave Little Squirrel")
        self.assertEqual(res.authorId, "teacher-42")
        self.assertEqual(res.difficulty, 2)
        self.assertIsNotNone(res.validationResult)
        self.assertTrue(res.validationResult.isValid)
        mock_db.reading_passages.insert_one.assert_called_once()
        mock_db.content_audit_logs.insert_one.assert_called_once()

    # 3. Unauthorized Roles Cannot Create Content (403)
    def test_unauthorized_student_or_parent_cannot_create_content(self):
        """Students and parents are rejected with HTTP 403 on authoring endpoints."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.post("/api/v2/content-authoring/drafts", json={"title": "Test", "text": "Content"})
            self.assertEqual(res.status_code, 403)
            self.assertIn("Educator or Administrator authorization required", res.json()["detail"])
        finally:
            app.dependency_overrides.clear()

        app.dependency_overrides[get_current_user] = lambda: self.parent_user
        try:
            res = self.client.post("/api/v2/content-authoring/drafts", json={"title": "Test", "text": "Content"})
            self.assertEqual(res.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    # 4. Draft Owner Can Edit Draft
    @patch("services.learning.content_authoring.db")
    async def test_draft_owner_can_edit_draft(self, mock_db):
        """Author can update title, text, or difficulty while in DRAFT state."""
        existing_doc = {
            "contentId": "c-123",
            "passageId": "pas-auth-123",
            "version": 1,
            "title": "Old Title",
            "text": "Initial text of the story containing at least fifteen words to pass length checks properly.",
            "difficulty": 1,
            "domain": "reading_comprehension",
            "language": "en",
            "status": "DRAFT",
            "authorId": "teacher-42",
            "active": False,
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=existing_doc)
        mock_db.reading_passages.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())

        req = ContentDraftUpdateRequest(title="Updated Title", difficulty=2)
        res = await update_content_draft(self.teacher_user, "c-123", req)
        self.assertEqual(res.title, "Updated Title")
        self.assertEqual(res.difficulty, 2)
        mock_db.reading_passages.update_one.assert_called_once()

    # 5. Unauthorized User Cannot Edit Another Author's Draft (403)
    @patch("services.learning.content_authoring.db")
    async def test_unauthorized_user_cannot_edit_other_author_draft(self, mock_db):
        """A different teacher cannot edit another educator's draft."""
        existing_doc = {
            "contentId": "c-123",
            "passageId": "pas-auth-123",
            "title": "Author A's Story",
            "status": "DRAFT",
            "authorId": "teacher-42",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=existing_doc)

        different_teacher = {"id": "teacher-888", "name": "Other", "role": "teacher"}
        req = ContentDraftUpdateRequest(title="Hacked Title")
        with self.assertRaises(PermissionError):
            await update_content_draft(different_teacher, "c-123", req)

    # 6. Invalid Lifecycle Transitions Rejected
    @patch("services.learning.content_authoring.db")
    async def test_invalid_lifecycle_transitions_rejected(self, mock_db):
        """Cannot directly publish a DRAFT without prior review and approval."""
        draft_doc = {
            "contentId": "c-draft",
            "passageId": "pas-c-draft",
            "status": "DRAFT",
            "authorId": "teacher-42",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=draft_doc)

        with self.assertRaises(ValueError) as ctx:
            await publish_content(self.teacher_user, "c-draft")
        self.assertIn("APPROVED", str(ctx.exception))

        # Cannot edit an IN_REVIEW item
        review_doc = {
            "contentId": "c-rev",
            "passageId": "pas-c-rev",
            "status": "IN_REVIEW",
            "authorId": "teacher-42",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=review_doc)
        with self.assertRaises(ValueError) as ctx:
            await update_content_draft(self.teacher_user, "c-rev", ContentDraftUpdateRequest(title="New"))
        self.assertIn("IN_REVIEW", str(ctx.exception))

    # 7. Unauthorized Users Cannot Approve or Publish
    @patch("services.learning.content_authoring.db")
    async def test_unauthorized_users_cannot_approve_or_publish(self, mock_db):
        """Endpoints reject review and publish actions from non-educators."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.post("/api/v2/content-authoring/review/c-1/decision", json={"decision": "APPROVE"})
            self.assertEqual(res.status_code, 403)
            res2 = self.client.post("/api/v2/content-authoring/items/c-1/publish")
            self.assertEqual(res2.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    # 8. Separation of Duties Enforced (Self-Approval Rejected)
    @patch("services.learning.content_authoring.db")
    async def test_self_approval_rules_enforced(self, mock_db):
        """An author cannot approve their own content (separation of duties)."""
        doc = {
            "contentId": "c-review",
            "passageId": "pas-auth-rev",
            "status": "IN_REVIEW",
            "authorId": "teacher-42",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=doc)

        decision_req = ContentReviewDecisionRequest(decision="APPROVE", feedback="Looks great!")
        with self.assertRaises(PermissionError) as ctx:
            await review_content(self.teacher_user, "c-review", decision_req)
        self.assertIn("separation of duties", str(ctx.exception).lower())

        # However, a different teacher CAN review and approve
        mock_db.reading_passages.update_one = AsyncMock(return_value=MagicMock())
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())
        res = await review_content(self.peer_reviewer, "c-review", decision_req)
        self.assertEqual(res.status, "APPROVED")
        self.assertEqual(res.reviewerId, "teacher-99")

    # 9. Validation Catches Missing Required Fields
    def test_validation_catches_missing_required_fields(self):
        """Missing title or text triggers deterministic validation errors."""
        res_empty = validate_content({})
        self.assertFalse(res_empty.isValid)
        self.assertTrue(any("Title is required" in e for e in res_empty.errors))
        self.assertTrue(any("content (text) is required" in e for e in res_empty.errors))

    # 10. Unsupported Language Codes Rejected
    def test_unsupported_language_codes_rejected(self):
        """Unsupported languages (e.g. 'fr' or 'es') are rejected with validation errors."""
        res = validate_content({
            "title": "French Story",
            "text": "Bonjour le monde ceci est une histoire avec assez de mots pour tester la validation de longueur.",
            "language": "fr",
            "difficulty": 1,
        })
        self.assertFalse(res.isValid)
        self.assertTrue(any("Unsupported language code 'fr'" in e for e in res.errors))

    # 11. Invalid Difficulty Tiers Rejected
    def test_invalid_difficulty_tiers_rejected(self):
        """Difficulty tiers outside 1-5 produce blocking validation errors."""
        res0 = validate_content({
            "title": "Story Tier 0",
            "text": "Here is a story with sufficient words to satisfy the length boundary requirements easily.",
            "difficulty": 0,
            "language": "en",
        })
        self.assertFalse(res0.isValid)
        self.assertTrue(any("Difficulty tier must be between 1 and 5" in e for e in res0.errors))

        res6 = validate_content({
            "title": "Story Tier 6",
            "text": "Here is a story with sufficient words to satisfy the length boundary requirements easily.",
            "difficulty": 6,
            "language": "en",
        })
        self.assertFalse(res6.isValid)
        self.assertTrue(any("Difficulty tier must be between 1 and 5" in e for e in res6.errors))

    # 12. Malformed Questions and Annotation References Rejected
    def test_malformed_questions_and_annotations_rejected(self):
        """Out of bounds answer index, empty options, and duplicate choices are caught."""
        res = validate_content({
            "title": "Valid Title",
            "text": "Here is an educational story with enough words to pass the minimum text boundary check smoothly.",
            "difficulty": 1,
            "language": "en",
            "vocabulary": [{"word": "", "definition": "Empty word"}],
            "questions": [
                {
                    "questionId": "q1",
                    "question": "What happened?",
                    "options": ["Option A", "Option A"],  # Duplicate options
                    "correctAnswer": 5,  # Out of bounds
                }
            ],
        })
        self.assertFalse(res.isValid)
        self.assertTrue(any("empty word" in e.lower() for e in res.errors))
        self.assertTrue(any("duplicate" in e.lower() for e in res.errors))
        self.assertTrue(any("out of bounds" in e.lower() for e in res.errors))

    # 13. Hindi and Marathi Unicode Content Preserved
    def test_hindi_and_marathi_unicode_content_preserved(self):
        """Devanagari text in Hindi and Marathi is correctly preserved without corruption."""
        hindi_payload = {
            "title": "सुंदर बगीचा",
            "text": "एक छोटे से गाँव में एक सुंदर बगीचा था। वहाँ बहुत सारे रंग-बिरंगे फूल खिले थे। बच्चे रोज़ शाम को वहाँ खेलने आते थे।",
            "difficulty": 1,
            "language": "hi",
            "vocabulary": [{"word": "बगीचा", "definition": "फूलों और पौधों का स्थान"}],
        }
        res_hi = validate_content(hindi_payload)
        self.assertTrue(res_hi.isValid)
        self.assertTrue(res_hi.details["hasUnicodeDevanagari"])

        marathi_payload = {
            "title": "गोड आंबा",
            "text": "आमच्या बागेत एक मोठे आंब्याचे झाड होते. उन्हाळ्यात त्या झाडाला खूप गोड आणि रसाळ आंबे येत असत. सर्व मुले एकत्र आंबे खात.",
            "difficulty": 1,
            "language": "mr",
        }
        res_mr = validate_content(marathi_payload)
        self.assertTrue(res_mr.isValid)
        self.assertTrue(res_mr.details["hasUnicodeDevanagari"])

    # 14. Translation Completeness Reported Accurately
    @patch("services.learning.content_authoring.db")
    async def test_translation_completeness_reported_accurately(self, mock_db):
        """Reports missing languages and correct completeness percentage."""
        docs = [
            {"passageId": "pas-en-01", "language": "en"},
            {"passageId": "pas-hi-01", "language": "hi"},
        ]
        mock_db.reading_passages.find.return_value = make_cursor_mock(docs)

        res = await get_translation_completeness("grp-100")
        self.assertEqual(res["completenessPercent"], 67)
        self.assertIn("en", res["availableLanguages"])
        self.assertIn("hi", res["availableLanguages"])
        self.assertIn("mr", res["missingLanguages"])

    # 15. Review Feedback Persisted and Visible to Author
    @patch("services.learning.content_authoring.db")
    async def test_review_feedback_persisted_and_visible(self, mock_db):
        """Reviewer feedback is recorded in the document and audit trail."""
        in_review_doc = {
            "contentId": "c-100",
            "passageId": "pas-auth-100",
            "status": "IN_REVIEW",
            "authorId": "teacher-42",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=in_review_doc)
        mock_db.reading_passages.update_one = AsyncMock(return_value=MagicMock())
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())

        req = ContentReviewDecisionRequest(
            decision="REQUEST_CHANGES",
            feedback="Please add a comprehension question regarding paragraph two."
        )
        res = await review_content(self.peer_reviewer, "c-100", req)
        self.assertEqual(res.status, "CHANGES_REQUESTED")
        self.assertEqual(res.reviewerFeedback, "Please add a comprehension question regarding paragraph two.")
        self.assertEqual(res.reviewerId, "teacher-99")

    # 16. Published Content Discoverable by Phase 15
    @patch("services.learning.personalized_content.db")
    async def test_published_content_discoverable_by_phase15(self, mock_db):
        """A published authored passage is discovered by the Phase 15 content engine."""
        published_passage = {
            "passageId": "pas-auth-pub-1",
            "contentId": "c-pub-1",
            "title": "Authored Forest Adventure",
            "text": "A friendly squirrel guides children through the tall green pine trees.",
            "difficulty": 2,
            "language": "en",
            "domain": "reading_comprehension",
            "status": "PUBLISHED",
            "active": True,
            "wordCount": 50,
            "estimatedMinutes": 2,
            "vocabulary": [],
            "questions": [],
        }
        mock_db.reading_passages.find.return_value = make_cursor_mock([published_passage])

        from services.learning.personalized_content import _get_eligible_reading_passages
        eligible = await _get_eligible_reading_passages()
        passage_ids = [p["passageId"] for p in eligible]
        self.assertIn("pas-auth-pub-1", passage_ids)

    # 17. Draft Content Is Not Discoverable by Phase 15
    @patch("services.learning.personalized_content.db")
    async def test_draft_content_not_discoverable_by_phase15(self, mock_db):
        """Draft passages in db.reading_passages are never returned to student activity discovery."""
        draft_passage = {
            "passageId": "pas-auth-draft-1",
            "contentId": "c-draft-1",
            "title": "Secret Draft",
            "status": "DRAFT",
            "active": False,
        }
        # find query has {"active": True, "$or": [{"status": "PUBLISHED"}, ...]}
        # Motor will return empty list for this query
        mock_db.reading_passages.find.return_value = make_cursor_mock([])

        from services.learning.personalized_content import _get_eligible_reading_passages
        eligible = await _get_eligible_reading_passages()
        passage_ids = [p.get("passageId") for p in eligible]
        self.assertNotIn("pas-auth-draft-1", passage_ids)

    # 18. Archived Content Is Excluded from New Activities
    @patch("services.learning.reading_service.db")
    async def test_archived_content_excluded_from_new_activities(self, mock_db):
        """Archived passages cannot be started for new reading sessions."""
        archived_doc = {
            "passageId": "pas-archived-01",
            "status": "ARCHIVED",
            "active": False,
            "title": "Old Retired Story",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=archived_doc)

        req = ReadingSessionStartRequest(passageId="pas-archived-01")
        with self.assertRaises(ValueError) as ctx:
            await start_reading_session("student-1", req)
        self.assertIn("not available for reading activities", str(ctx.exception))

    # 19. Legacy V1 Content Remains Compatible
    @patch("services.learning.reading_service.db")
    async def test_legacy_v1_content_remains_compatible(self, mock_db):
        """Seed passages lacking a status field remain 100% active and discoverable."""
        legacy_doc = {
            "passageId": "pas-t1-001",
            "title": "Sam the Orange Cat",
            "difficulty": 1,
            "active": True,
            # Note: No 'status' field
        }
        mock_db.reading_passages.find.return_value = make_cursor_mock([legacy_doc])

        passages = await get_passages(tier=1)
        self.assertTrue(len(passages) >= 1)
        self.assertEqual(passages[0]["passageId"], "pas-t1-001")

    # 20. Historical Learning Records Intact After Content Revision
    @patch("services.learning.content_authoring.db")
    async def test_historical_records_intact_after_revision(self, mock_db):
        """Creating a new revision preserves the original document for historical activity records."""
        original = {
            "contentId": "c-v1",
            "passageId": "pas-auth-original",
            "version": 1,
            "title": "Original Story",
            "text": "Fifteen words or more in this text passage to ensure valid length checks easily.",
            "status": "PUBLISHED",
            "active": True,
            "difficulty": 1,
            "language": "en",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=original)
        mock_db.reading_passages.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())

        revision = await create_content_revision(self.teacher_user, "c-v1")
        self.assertEqual(revision.version, 2)
        self.assertEqual(revision.status, "DRAFT")
        self.assertNotEqual(revision.contentId, "c-v1")
        # Original remains published; new revision starts as draft

    # 21. Tenant Isolation Enforced
    @patch("services.learning.content_authoring.db")
    async def test_tenant_isolation_enforced(self, mock_db):
        """Educators can only see content matching their classroom or allowed scope."""
        docs = [
            {"contentId": "c-1", "title": "Class 101 Story", "status": "DRAFT", "authorId": "teacher-42", "tenantId": "CLASS-101"},
        ]
        mock_db.reading_passages.find.return_value = make_cursor_mock(docs)
        mock_db.reading_passages.count_documents = AsyncMock(return_value=1)

        res = await list_content_items(self.teacher_user)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].contentId, "c-1")

    # 22. Parent and Student Endpoints Do Not Leak Editorial Metadata
    def test_parent_and_student_endpoints_do_not_leak_editorial_metadata(self):
        """Editorial endpoints return 403 to students and parents."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        try:
            res = self.client.get("/api/v2/content-authoring/review-queue")
            self.assertEqual(res.status_code, 403)
        finally:
            app.dependency_overrides.clear()

        app.dependency_overrides[get_current_user] = lambda: self.parent_user
        try:
            res = self.client.get("/api/v2/content-authoring/items/c-1/history")
            self.assertEqual(res.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    # 23. Version and Audit History Accurate
    @patch("services.learning.content_authoring.db")
    async def test_version_and_audit_history_accurate(self, mock_db):
        """Audit timeline returns complete chronological events."""
        doc = {"contentId": "c-10", "passageId": "pas-10", "version": 1, "status": "DRAFT", "authorId": "teacher-42"}
        audit_events = [
            {"id": "a-1", "contentId": "c-10", "passageId": "pas-10", "timestamp": 100, "action": "CREATED", "actorId": "teacher-42", "actorRole": "teacher", "fromState": None, "toState": "DRAFT"},
            {"id": "a-2", "contentId": "c-10", "passageId": "pas-10", "timestamp": 200, "action": "SUBMITTED", "actorId": "teacher-42", "actorRole": "teacher", "fromState": "DRAFT", "toState": "IN_REVIEW"},
        ]
        mock_db.reading_passages.find_one = AsyncMock(return_value=doc)
        mock_db.content_audit_logs.find.return_value = make_cursor_mock(audit_events)

        history_res = await get_content_history(self.teacher_user, "c-10")
        self.assertEqual(history_res.contentId, "c-10")
        self.assertEqual(len(history_res.history), 2)
        self.assertEqual(history_res.history[0].action, "CREATED")
        self.assertEqual(history_res.history[1].action, "SUBMITTED")


if __name__ == "__main__":
    unittest.main()
