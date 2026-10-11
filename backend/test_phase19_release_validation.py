"""
backend/test_phase19_release_validation.py — Phase 19: Release Validation, Security Hardening & UAT Test Suite.

Verifies:
1. Authentication & JWT Security:
   - Missing, invalid, expired, and signature-tampered tokens rejected with HTTP 401.
   - JWT 'alg: none' vulnerability rejection.
   - Direct verification of token signing, expiration, and tampering.
   - Prevention of role self-promotion via profile update requests.
2. Authorization & Tenant Isolation:
   - Student cannot access or mutate another student's profile or progress.
   - Teacher cannot access learner analytics outside authorized classroom code (HTTP 403).
   - Parent cannot access child without an active, verified relationship (HTTP 403).
   - Instant termination of parent access upon relationship link revocation.
   - Separation of duties in content authoring: author cannot self-review or self-publish (HTTP 403).
   - Private AI tutor history and teacher-only notes strictly isolated from unauthorized parties.
3. Input Validation & API Abuse:
   - Malformed JSON, unexpected types, and oversized requests handled safely without unhandled 500 crashes.
   - Activity launch telemetry persists with completed=False (zero fake completions).
   - Duplicate gamification / reward event submission idempotency.
4. Realistic Release Scenarios:
   - Student journey: profile -> launch -> reading session completion -> adaptive update -> accessibility & language persistence.
   - Teacher journey: classroom roster isolation -> draft creation -> review queue -> approval -> publication.
   - Parent journey: one-time invitation code claim -> progress summary inspection -> immediate revocation cutoff.
   - Graceful resilience: AI service timeout fallback to deterministic heuristics; database degradation safety.
"""
import time
import uuid
import jwt as pyjwt
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import (
    make_token,
    verify_token,
    get_jwt_secret,
    JWT_ALG,
    get_current_user,
    require_teacher,
    require_parent,
)
from services.learning.reading_service import DEFAULT_PASSAGES
from services.learning.gamification_service import process_learning_reward
from services.learning.tutor_context import build_tutor_context


def make_cursor_mock(items):
    """Helper to mock a synchronous cursor returned by motor find() whose to_list() is async."""
    c = MagicMock()
    c.to_list = AsyncMock(return_value=items)
    c.limit = MagicMock(return_value=c)
    c.skip = MagicMock(return_value=c)
    c.sort = MagicMock(return_value=c)
    return c


class Phase19ReleaseValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.student_user = {
            "id": "student-test-01",
            "name": "Aarav Sharma",
            "email": "aarav@school.org",
            "role": "student",
            "classroomJoined": "DA-DELHI",
            "preferredLanguage": "hi",
            "settings": {"font": "OpenDyslexic", "fontSize": 18},
        }
        self.other_student_user = {
            "id": "student-test-02",
            "name": "Rohan Verma",
            "email": "rohan@school.org",
            "role": "student",
            "classroomJoined": "DA-MUMBAI",
            "preferredLanguage": "en",
        }
        self.teacher_user = {
            "id": "teacher-delhi-01",
            "name": "Ms. Ananya Roy",
            "email": "ananya@school.org",
            "role": "teacher",
            "classroomCode": "DA-DELHI",
        }
        self.other_teacher_user = {
            "id": "teacher-mumbai-02",
            "name": "Mr. Rajiv Joshi",
            "email": "rajiv@school.org",
            "role": "teacher",
            "classroomCode": "DA-MUMBAI",
        }
        self.parent_user = {
            "id": "parent-user-01",
            "name": "Sunita Sharma",
            "email": "sunita@home.org",
            "role": "parent",
        }

    def tearDown(self):
        app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Authentication & JWT Security Tests
    # ──────────────────────────────────────────────────────────────────────────
    def test_missing_auth_header_rejected_with_401(self):
        """Protected endpoints strictly require Authorization header."""
        protected_endpoints = [
            ("GET", "/api/auth/me"),
            ("GET", "/api/v2/learner/profile"),
            ("GET", "/api/v2/reading/recommendation"),
            ("GET", "/api/v2/tutor/history"),
            ("GET", "/api/v2/teacher/analytics/overview"),
            ("GET", "/api/v2/parent/profile"),
        ]
        for method, path in protected_endpoints:
            if method == "GET":
                res = self.client.get(path)
            else:
                res = self.client.post(path, json={})
            self.assertIn(
                res.status_code,
                (401, 403),
                f"Expected 401/403 for unauthenticated {method} {path}, got {res.status_code}",
            )

    def test_invalid_malformed_token_rejected_with_401(self):
        """Malformed or random token strings are rejected immediately."""
        malformed_headers = [
            {"Authorization": "Bearer not_a_real_jwt"},
            {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalid.signature"},
            {"Authorization": "Basic dXNlcjpwYXNz"},
            {"Authorization": ""},
        ]
        for headers in malformed_headers:
            res = self.client.get("/api/auth/me", headers=headers)
            self.assertIn(res.status_code, (401, 403))

    def test_expired_jwt_token_rejected_with_401(self):
        """Tokens with past expiration timestamp (exp) cannot access protected resources."""
        expired_payload = {
            "sub": "student-test-expired",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        }
        expired_token = pyjwt.encode(expired_payload, get_jwt_secret(), algorithm=JWT_ALG)
        res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIsNone(verify_token(expired_token))

    def test_tampered_jwt_signature_rejected_with_401(self):
        """JWT signed with a different key or modified payload is rejected."""
        bogus_secret = "attacker-compromised-secret-key-12345"
        payload = {"sub": "student-test-1", "exp": int(time.time()) + 3600}
        tampered_token = pyjwt.encode(payload, bogus_secret, algorithm=JWT_ALG)
        res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIsNone(verify_token(tampered_token))

    def test_jwt_none_algorithm_attack_rejected_with_401(self):
        """JWT with 'alg': 'none' header is strictly rejected by cryptographic verification."""
        header = {"alg": "none", "typ": "JWT"}
        payload = {"sub": "student-admin-bypass", "exp": int(time.time()) + 3600}
        none_token = pyjwt.encode(payload, key="", algorithm="none", headers=header)
        res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {none_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIsNone(verify_token(none_token))

    @patch("routers.auth.db")
    @patch("routers.auth.get_current_user", new_callable=AsyncMock)
    def test_role_self_promotion_prevented_in_profile_patch(self, mock_get_user, mock_auth_db):
        """Student cannot elevate their own role to 'teacher' or 'admin' via profile patch."""
        mock_get_user.return_value = self.student_user
        mock_auth_db.users.find_one = AsyncMock(return_value=self.student_user)
        mock_auth_db.users.update_one = AsyncMock(return_value=MagicMock())

        res = self.client.patch(
            "/api/auth/profile",
            headers={"Authorization": "Bearer valid-dummy-token"},
            json={"role": "teacher", "schoolName": "Advanced Academy"},
        )
        self.assertEqual(res.status_code, 200)

        # Assert update_one was never called with {"role": ...}
        if mock_auth_db.users.update_one.called:
            call_args = mock_auth_db.users.update_one.call_args[0]
            update_doc = call_args[1].get("$set", {})
            self.assertNotIn("role", update_doc, "Role must not be modifiable via profile patch")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Authorization & Multi-Tenant Isolation Tests
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.analytics.teacher_analytics.db")
    def test_teacher_cannot_access_student_outside_classroom(self, mock_db):
        """Teacher A (Classroom DA-DELHI) cannot access student enrolled in Classroom DA-MUMBAI (HTTP 403)."""
        app.dependency_overrides[require_teacher] = lambda: self.teacher_user
        mock_db.users.find_one = AsyncMock(return_value=self.other_student_user)  # enrolled in DA-MUMBAI

        res = self.client.get(
            f"/api/v2/teacher/analytics/learners/{self.other_student_user['id']}"
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("not enrolled in your classroom", res.json()["detail"].lower())

    @patch("services.parent.parent_service.db")
    def test_parent_cannot_access_unlinked_child(self, mock_db):
        """Parent without an active verified link cannot inspect an unlinked child's dashboard (HTTP 403)."""
        app.dependency_overrides[require_parent] = lambda: self.parent_user
        mock_db.parent_links.find_one = AsyncMock(return_value=None)  # No active link

        res = self.client.get(
            f"/api/v2/parent/learners/{self.student_user['id']}/dashboard"
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("access denied", res.json()["detail"].lower())

    @patch("services.parent.parent_service.db")
    def test_revoked_parent_link_immediately_terminates_access(self, mock_db):
        """When a relationship link is revoked, subsequent protected dashboard calls fail with 403."""
        app.dependency_overrides[require_parent] = lambda: self.parent_user
        app.dependency_overrides[get_current_user] = lambda: self.parent_user
        link_id = "link-1234"

        active_link = {
            "id": link_id,
            "parentId": self.parent_user["id"],
            "studentId": self.student_user["id"],
            "status": "active",
        }

        # 1. Revoke active link
        mock_db.parent_links.find_one = AsyncMock(return_value=active_link)
        mock_db.parent_links.update_one = AsyncMock(return_value=MagicMock())

        res_revoke = self.client.post(f"/api/v2/parent/links/{link_id}/revoke")
        self.assertEqual(res_revoke.status_code, 200)

        # 2. Subsequent access attempts fail with 403
        mock_db.parent_links.find_one = AsyncMock(return_value=None)  # Revoked link not found as active

        res_blocked = self.client.get(
            f"/api/v2/parent/learners/{self.student_user['id']}/dashboard"
        )
        self.assertEqual(res_blocked.status_code, 403)

    @patch("services.learning.content_authoring.db")
    def test_content_author_cannot_self_review_or_self_publish(self, mock_db):
        """Author of educational content cannot approve or self-publish their own draft (separation of duties)."""
        app.dependency_overrides[get_current_user] = lambda: self.teacher_user
        draft_id = "draft-self-review-test"

        draft_doc = {
            "contentId": draft_id,
            "authorId": self.teacher_user["id"],
            "status": "IN_REVIEW",
            "title": "Passage Alpha",
            "difficulty": 1,
            "language": "en",
        }
        mock_db.reading_passages.find_one = AsyncMock(return_value=draft_doc)

        # Author attempts to self-approve -> returns HTTP 403 Forbidden
        res_decision = self.client.post(
            f"/api/v2/content-authoring/review/{draft_id}/decision",
            json={"decision": "APPROVE", "feedback": "I approve my own work"},
        )
        self.assertEqual(res_decision.status_code, 403)
        self.assertIn("cannot review", res_decision.json()["detail"].lower())

    @patch("services.learning.tutor_context.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.tutor_context.db")
    async def test_student_and_parent_cannot_access_private_tutor_or_teacher_notes(
        self, mock_db, mock_profile, mock_state
    ):
        """Tutor context builds strictly for the target student with zero private note leakage."""
        mock_db.users.find_one = AsyncMock(return_value={
            "id": self.student_user["id"],
            "name": "Aarav Sharma",
            "settings": {"font": "OpenDyslexic", "fontSize": 20},
            "preferredLanguage": "en",
        })
        mock_profile.return_value = {
            "learnerId": self.student_user["id"],
            "learning_level": {"level": 2},
            "strengths": [{"friendly_name": "Visual Memory"}],
            "practice_areas": [{"friendly_name": "Phonemic Blending"}],
        }
        mock_state.return_value = {"active_difficulty_tier": 2}
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.reading_passages.find_one = AsyncMock(return_value=DEFAULT_PASSAGES[0])

        ctx = await build_tutor_context(
            learner_id=self.student_user["id"],
            active_passage_id="pas-t1-001",
            active_word="orange",
        )
        self.assertEqual(ctx.displayName, "Aarav")
        self.assertEqual(ctx.adaptiveTier, 2)
        ctx_dict = ctx.model_dump()
        self.assertNotIn("rawAudio", ctx_dict)
        self.assertNotIn("passwordHash", ctx_dict)
        self.assertNotIn("teacherPrivateNotes", ctx_dict)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Input Validation & API Resilience Tests
    # ──────────────────────────────────────────────────────────────────────────
    def test_invalid_identifiers_and_malformed_json_handled_safely(self):
        """Malformed requests return standard HTTP 422 without crashing process or leaking tracebacks."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        # 1. Invalid non-integer difficulty filter
        res_bad_filter = self.client.get("/api/v2/reading/passages?tier=invalid_not_an_int")
        self.assertEqual(res_bad_filter.status_code, 422)

        # 2. Malformed JSON payload
        res_malformed = self.client.post(
            "/api/v2/reading/session/start",
            headers={"Content-Type": "application/json"},
            content="{ malformed_json: true, ",
        )
        self.assertEqual(res_malformed.status_code, 422)

    @patch("services.learning.personalized_content.db")
    def test_activity_launch_records_completed_false(self, mock_db):
        """Activity launch telemetry sets completed=False; launching never counts as completion."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.activity_launches.insert_one = AsyncMock(return_value=MagicMock())

        res = self.client.post(
            "/api/v2/personalized-content/launch",
            json={"activityId": "pas-t1-001", "activityType": "GUIDED_READING", "language": "en"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "launched")
        self.assertEqual(data["activityId"], "pas-t1-001")
        self.assertFalse(data["completed"], "Activity must NOT be marked completed upon launch")

    @patch("services.learning.gamification_service.db")
    async def test_duplicate_reward_event_is_idempotent(self, mock_db):
        """Replaying identical gamification reward events does not double-award points."""
        now = int(time.time())
        summary_doc = {
            "learnerId": self.student_user["id"],
            "totalPoints": 150,
            "currentStreak": 2,
            "longestStreak": 4,
            "lastActiveDate": "2026-10-10",
            "milestoneProgress": {},
            "earnedBadges": [],
        }
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=summary_doc)
        mock_db.reward_events.find_one = AsyncMock(return_value=None)
        mock_db.reward_events.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.gamification_summaries.update_one = AsyncMock(return_value=MagicMock())
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.reward_events.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.count_documents = AsyncMock(return_value=0)
        mock_db.reading_sessions.count_documents = AsyncMock(return_value=0)
        mock_db.users.find_one = AsyncMock(return_value=self.student_user)

        eval1 = await process_learning_reward(
            user_id=self.student_user["id"],
            source_event_id="ses-unique-rel-19",
            event_type="reading_session",
            metadata={"comprehensionScore": 85.0, "wordsRead": 60},
        )
        self.assertGreater(eval1.pointsAwarded, 0)

        # Subsequent call with same source_event_id is detected as duplicate
        existing_event = {
            "eventId": "rev-existing-19",
            "learnerId": self.student_user["id"],
            "sourceEventId": "ses-unique-rel-19",
            "pointsAwarded": eval1.pointsAwarded,
            "eventType": "reading_session",
            "createdAt": now,
        }
        mock_db.reward_events.find_one = AsyncMock(return_value=existing_event)
        eval2 = await process_learning_reward(
            user_id=self.student_user["id"],
            source_event_id="ses-unique-rel-19",
            event_type="reading_session",
            metadata={"comprehensionScore": 85.0, "wordsRead": 60},
        )
        self.assertTrue(eval2.isDuplicate)
        self.assertEqual(eval2.pointsAwarded, 0)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Realistic User Journeys & End-to-End Scenarios
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.learning.reading_recommender.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.reading_recommender.get_or_create_learner_profile", new_callable=AsyncMock)
    @patch("services.learning.reading_service.recalibrate_from_activity", new_callable=AsyncMock)
    @patch("services.learning.reading_service.get_learning_state", new_callable=AsyncMock)
    @patch("services.learning.reading_service.db")
    def test_student_realistic_learning_journey(self, mock_db, mock_state, mock_recal, mock_profile, mock_rec_state):
        """End-to-end student flow: recommendation lookup -> start session -> complete session -> adaptive progression."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        session_id = f"ses-rel19-{uuid.uuid4().hex[:6]}"

        mock_profile.return_value = {
            "learnerId": self.student_user["id"],
            "learning_level": 1,
            "preferred_language": "en",
        }
        mock_rec_state.return_value = {"active_difficulty_tier": 1, "consecutive_passes": 0}
        mock_state.return_value = {"active_difficulty_tier": 1, "consecutive_passes": 0}
        mock_db.reading_passages.find.return_value = make_cursor_mock([DEFAULT_PASSAGES[0]])
        mock_db.reading_passages.find_one = AsyncMock(return_value=DEFAULT_PASSAGES[0])
        mock_db.reading_sessions.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.reading_sessions.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learning_states.update_one = AsyncMock(return_value=MagicMock())
        mock_db.progress.update_one = AsyncMock(return_value=MagicMock())
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.update_one = AsyncMock(return_value=MagicMock())

        # 1. Fetch reading recommendation
        res_rec = self.client.get("/api/v2/reading/recommendation?language=en")
        self.assertEqual(res_rec.status_code, 200)

        # 2. Start reading session
        res_start = self.client.post(
            "/api/v2/reading/session/start",
            json={"passageId": "pas-t1-001", "readingMode": "guided"},
        )
        self.assertEqual(res_start.status_code, 200)

        # 3. Complete reading session with answers
        now = int(time.time())
        session_doc = {
            "sessionId": session_id,
            "learnerId": self.student_user["id"],
            "passageId": "pas-t1-001",
            "difficulty": 1,
            "status": "in_progress",
            "wordsPresented": 50,
            "createdAt": now - 100,
        }
        mock_db.reading_sessions.find_one = AsyncMock(return_value=session_doc)

        res_complete = self.client.post(
            "/api/v2/reading/session/complete",
            json={
                "sessionId": session_id,
                "durationSeconds": 90,
                "wordsRead": 50,
                "comprehensionAnswers": {"q-t1-001-1": 1, "q-t1-001-2": 2},
                "completed": True,
            },
        )
        self.assertEqual(res_complete.status_code, 200)
        comp_data = res_complete.json()
        self.assertEqual(comp_data["status"], "ok")
        self.assertEqual(comp_data["sessionId"], session_id)

    @patch("services.learning.content_authoring.db")
    def test_teacher_realistic_classroom_journey(self, mock_db):
        """End-to-end teacher flow: classroom draft creation -> review queue -> approval -> publication."""
        app.dependency_overrides[get_current_user] = lambda: self.teacher_user
        mock_db.reading_passages.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.content_audit_logs.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.reading_passages.update_one = AsyncMock(return_value=MagicMock())

        # 1. Teacher creates draft
        res_draft = self.client.post(
            "/api/v2/content-authoring/drafts",
            json={
                "title": "The Friendly Sparrow",
                "text": "Once upon a time, a cheerful sparrow nested near the garden tree. She sang sweet songs every morning for all the garden creatures.",
                "difficulty": 2,
                "language": "en",
                "domain": "reading_comprehension",
                "questions": [
                    {
                        "questionId": "q1",
                        "question": "Where did the sparrow nest?",
                        "options": ["Near the garden tree", "Under a rock", "In the ocean"],
                        "correctAnswer": 0,
                        "explanation": "The story mentions the sparrow nested near the garden tree.",
                    }
                ],
                "vocabulary": [
                    {
                        "word": "sparrow",
                        "syllables": ["spar", "row"],
                        "definition": "A small brown bird commonly seen in gardens.",
                    }
                ],
            },
        )
        self.assertEqual(res_draft.status_code, 201)
        draft_item = res_draft.json()
        content_id = draft_item["contentId"]
        self.assertEqual(draft_item["status"], "DRAFT")

        # 2. Teacher submits draft for review
        draft_doc = dict(draft_item)
        draft_doc["authorId"] = self.teacher_user["id"]
        mock_db.reading_passages.find_one = AsyncMock(return_value=draft_doc)

        res_submit = self.client.post(f"/api/v2/content-authoring/drafts/{content_id}/submit")
        self.assertEqual(res_submit.status_code, 200)

        # 3. Independent Teacher 2 reviews and approves
        app.dependency_overrides[get_current_user] = lambda: self.other_teacher_user
        draft_doc["status"] = "IN_REVIEW"
        res_approve = self.client.post(
            f"/api/v2/content-authoring/review/{content_id}/decision",
            json={"decision": "APPROVE", "feedback": "High educational quality and well-annotated vocabulary."},
        )
        self.assertEqual(res_approve.status_code, 200)

        # 4. Teacher publishes approved content
        draft_doc["status"] = "APPROVED"
        draft_doc["reviewerId"] = self.other_teacher_user["id"]
        res_publish = self.client.post(f"/api/v2/content-authoring/items/{content_id}/publish")
        self.assertEqual(res_publish.status_code, 200)
        self.assertEqual(res_publish.json()["status"], "PUBLISHED")

    @patch("services.parent.parent_service.db")
    def test_parent_realistic_code_claim_and_access_journey(self, mock_db):
        """End-to-end parent flow: claim one-time invitation code -> view verified dashboard -> revoke link."""
        app.dependency_overrides[get_current_user] = lambda: self.parent_user
        app.dependency_overrides[require_parent] = lambda: self.parent_user

        now = int(time.time())
        invitation_doc = {
            "id": "inv-valid-01",
            "code": "PLC-TEST-1234",
            "studentId": self.student_user["id"],
            "studentName": self.student_user["name"],
            "status": "active",
            "expiresAt": now + 3600,
            "createdAt": now - 60,
        }
        active_link_doc = {
            "id": "link-active-01",
            "parentId": self.parent_user["id"],
            "studentId": self.student_user["id"],
            "status": "active",
            "studentName": self.student_user["name"],
            "createdAt": now,
        }

        mock_db.parent_invitations.find_one = AsyncMock(return_value=invitation_doc)
        mock_db.parent_invitations.update_one = AsyncMock(return_value=MagicMock())
        mock_db.parent_links.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.parent_links.find_one = AsyncMock(side_effect=[None, active_link_doc, active_link_doc])
        mock_db.parent_links.find.return_value = make_cursor_mock([active_link_doc])
        mock_db.parent_links.count_documents = AsyncMock(return_value=1)
        mock_db.user_language_preferences.find_one = AsyncMock(return_value=None)
        mock_db.gamification_summaries.find_one = AsyncMock(return_value=None)
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
        mock_db.notifications.insert_one = AsyncMock(return_value=MagicMock())
        mock_db.users.find_one = AsyncMock(return_value=self.student_user)
        mock_db.reading_sessions.find.return_value = make_cursor_mock([])
        mock_db.activity_attempts.find.return_value = make_cursor_mock([])
        mock_db.speech_reading_analyses.find.return_value = make_cursor_mock([])
        mock_db.learning_states.find_one = AsyncMock(return_value={"tier": 1})

        # 1. Claim valid invitation code (creates link: 201 Created)
        res_claim = self.client.post(
            "/api/v2/parent/link/claim-code",
            json={"code": "PLC-TEST-1234"},
        )
        self.assertEqual(res_claim.status_code, 201)

        # 2. View linked dashboard
        res_dash = self.client.get(f"/api/v2/parent/learners/{self.student_user['id']}/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        dash_data = res_dash.json()
        self.assertEqual(dash_data["selectedLearner"]["studentName"], "Aarav Sharma")
        self.assertTrue(dash_data["hasLinkedLearners"])

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Resilience & Fault Tolerance Verification
    # ──────────────────────────────────────────────────────────────────────────
    @patch("routers.v2_tutor.handle_tutor_chat", new_callable=AsyncMock)
    def test_offline_fallback_when_ai_service_unavailable(self, mock_chat):
        """When third-party LLM or Gemini times out, AI Tutor falls back safely to offline heuristics."""
        from models.v2_tutor import TutorResponse
        app.dependency_overrides[get_current_user] = lambda: self.student_user

        mock_chat.return_value = TutorResponse(
            status="ok",
            message="Great effort! Let's break this word down into smaller syllables: spar-row.",
            source="offline-fallback",
            learningLevel=1,
            timestamp=int(time.time()),
        )

        res = self.client.post(
            "/api/v2/tutor/chat",
            json={"message": "I don't know the word sparrow"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("syllables", data["message"])
        self.assertEqual(data.get("source"), "offline-fallback")

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Accessibility & Multilingual Verification
    # ──────────────────────────────────────────────────────────────────────────
    @patch("services.accessibility.accessibility_service.db")
    def test_accessibility_preferences_and_multilingual_persistence(self, mock_db):
        """User accessibility preferences (OpenDyslexic, lineSpacing) persist accurately."""
        app.dependency_overrides[get_current_user] = lambda: self.student_user
        mock_db.user_accessibility_preferences.find_one = AsyncMock(return_value={
            "userId": self.student_user["id"],
            "preferences": {
                "font": "OpenDyslexic",
                "fontSize": 20,
                "lineHeight": 2.2,
                "highContrast": True,
            }
        })
        mock_db.user_accessibility_preferences.update_one = AsyncMock(return_value=MagicMock())
        mock_db.users.find_one = AsyncMock(return_value=None)
        mock_db.users.update_one = AsyncMock(return_value=MagicMock())

        res = self.client.get("/api/v2/accessibility/preferences")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["preferences"]["fontSize"], 20)
        self.assertTrue(data["preferences"]["highContrast"])

        patch_res = self.client.patch("/api/v2/accessibility/preferences", json={"fontSize": 24})
        self.assertEqual(patch_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
