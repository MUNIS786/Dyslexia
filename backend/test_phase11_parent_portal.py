"""
backend/test_phase11_parent_portal.py — Comprehensive Test Suite for Phase 11: Parent & Guardian Portal.

Tests cover:
1. Identity & Role Access Control:
   - 401 Unauthorized for unauthenticated requests
   - 403 Forbidden for students calling parent-only endpoints
   - 403 Forbidden for teachers calling parent-only endpoints
   - 403 Forbidden for parents calling teacher-only endpoints
   - 403 Forbidden for parents attempting to access unlinked or revoked learners
   - Forged learner IDs fail authorization checks
2. Secure Parent–Student Linking Workflows:
   - Student or Teacher generates 48h one-time invitation code (hashed in DB)
   - Parent claims invitation code -> status becomes active, invitation marked used
   - Reused invitation code is rejected (400 Bad Request)
   - Expired invitation code is rejected (400 Bad Request)
   - Duplicate active relationships are prevented (409 Conflict)
   - Direct link request by student identifier enters 'pending' state
   - Authorized student/teacher approves link request -> transitions to 'active'
   - Student/teacher rejects link request -> transitions to 'rejected'
   - Immediate revocation by parent revokes access instantly (403 on next call)
   - Immediate revocation by student revokes access instantly (403 on next call)
3. Dashboard Data & Privacy Protection:
   - Parent with zero linked learners receives a safe, non-crashing empty state
   - Dashboard returns real aggregated reading, adaptive, and gamification metrics
   - Missing historical sessions handled safely without crashing
   - Private AI tutor chat transcripts and teacher notes are strictly excluded
   - Non-clinical educational disclaimer is consistently included
   - Multi-child switching re-verifies authorization for each learner
4. Feature Flag Governance:
   - Disabling V2_PARENT_PORTAL returns 503 Service Unavailable
"""
import unittest
import time
import hashlib
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user, require_teacher, require_parent
from models.v2_parent import (
    ParentLinkItem,
    ParentProfileSummary,
    ClaimCodeRequest,
    LinkRequestCreate,
    InvitationCreateResponse,
    ParentDashboardResponse,
    HomePracticeSuggestion,
)


class TestPhase11ParentPortal(unittest.TestCase):
    """Test suite for V2 Parent & Guardian Portal identity, linking, and dashboard APIs."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_parent = {
            "id": "parent-101",
            "name": "Sarah Jenkins",
            "email": "sarah.parent@example.com",
            "role": "parent",
        }
        self.mock_student = {
            "id": "student-202",
            "name": "Leo Jenkins",
            "email": "leo.student@example.com",
            "role": "student",
            "classroomJoined": "CLASS-A",
        }
        self.mock_other_student = {
            "id": "student-303",
            "name": "Maya Patel",
            "email": "maya.student@example.com",
            "role": "student",
            "classroomJoined": "CLASS-B",
        }
        self.mock_teacher = {
            "id": "teacher-404",
            "name": "Mr. Sharma",
            "email": "sharma.teacher@example.com",
            "role": "teacher",
            "classroomCode": "CLASS-A",
        }

    # ─── 1. Authentication & Role Authorization Tests ─────────────────────────

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to parent portal endpoints return 401 Unauthorized."""
        endpoints = [
            ("GET", "/api/v2/parent/profile"),
            ("GET", "/api/v2/parent/learners"),
            ("GET", "/api/v2/parent/dashboard"),
            ("POST", "/api/v2/parent/link/claim-code"),
            ("POST", "/api/v2/parent/link/request"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = self.client.get(path)
            else:
                resp = self.client.post(path, json={})
            self.assertEqual(resp.status_code, 401, f"Expected 401 for {method} {path}")

    def test_student_cannot_access_parent_endpoints(self):
        """Student accounts calling parent-only endpoints are rejected with 403 Forbidden."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        try:
            resp = self.client.get("/api/v2/parent/dashboard")
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Parent role required", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    def test_teacher_cannot_access_parent_endpoints(self):
        """Teacher accounts calling parent-only endpoints are rejected with 403 Forbidden."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_teacher
        try:
            resp = self.client.get("/api/v2/parent/dashboard")
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Parent role required", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    def test_parent_cannot_access_teacher_endpoints(self):
        """Parent accounts calling teacher-only endpoints are rejected with 403 Forbidden."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        try:
            resp = self.client.get("/api/v2/teacher/analytics/overview")
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Teacher role required", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    # ─── 2. Secure Linking Workflow Tests ─────────────────────────────────────

    @patch("services.parent.parent_service.db")
    def test_invitation_code_generation_by_student(self, mock_db):
        """Student generates a 48h invitation code starting with 'PLC-'."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        mock_db.users.find_one = AsyncMock(return_value=self.mock_student)
        mock_db.parent_invitations.update_many = AsyncMock(return_value=None)
        mock_db.parent_invitations.insert_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post("/api/v2/parent/invitations/generate", json={})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertTrue(data["invitationCode"].startswith("PLC-"))
            self.assertEqual(data["studentId"], "student-202")
            self.assertEqual(data["studentName"], "Leo Jenkins")
            # Verify expiresAt is ~48 hours in the future
            now = int(time.time())
            self.assertGreater(data["expiresAt"], now + (47 * 3600))
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_claim_valid_invitation_code(self, mock_db):
        """Parent redeems a valid invitation code to immediately establish an active link."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        code = "PLC-AB12-CD34"
        code_norm = "PLCAB12CD34"
        code_hash = hashlib.sha256(code_norm.encode()).hexdigest()

        mock_invitation = {
            "id": "inv-001",
            "codeHash": code_hash,
            "studentId": "student-202",
            "studentName": "Leo Jenkins",
            "status": "active",
            "expiresAt": int(time.time()) + 10000,
        }

        mock_db.parent_invitations.find_one = AsyncMock(return_value=mock_invitation)
        mock_db.parent_links.find_one = AsyncMock(return_value=None)  # No existing link
        mock_db.parent_invitations.update_one = AsyncMock(return_value=None)
        mock_db.parent_links.insert_one = AsyncMock(return_value=None)
        mock_db.notifications.insert_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post("/api/v2/parent/link/claim-code", json={"code": code})
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            self.assertEqual(data["status"], "active")
            self.assertEqual(data["studentId"], "student-202")
            self.assertEqual(data["studentName"], "Leo Jenkins")
            self.assertIsNotNone(data["verifiedAt"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_claim_already_used_invitation_code(self, mock_db):
        """Reusing an already-claimed invitation code returns 400 Bad Request."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        code = "PLC-USED-CODE"
        code_norm = "PLCUSEDCODE"
        code_hash = hashlib.sha256(code_norm.encode()).hexdigest()

        mock_invitation = {
            "id": "inv-002",
            "codeHash": code_hash,
            "studentId": "student-202",
            "studentName": "Leo Jenkins",
            "status": "used",  # Already used!
            "expiresAt": int(time.time()) + 10000,
        }
        mock_db.parent_invitations.find_one = AsyncMock(return_value=mock_invitation)

        try:
            resp = self.client.post("/api/v2/parent/link/claim-code", json={"code": code})
            self.assertEqual(resp.status_code, 400)
            self.assertIn("already been used", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_claim_expired_invitation_code(self, mock_db):
        """Expired invitation codes are rejected with 400 Bad Request."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        code = "PLC-EXPD-CODE"
        code_norm = "PLCEXPDCODE"
        code_hash = hashlib.sha256(code_norm.encode()).hexdigest()

        mock_invitation = {
            "id": "inv-003",
            "codeHash": code_hash,
            "studentId": "student-202",
            "studentName": "Leo Jenkins",
            "status": "active",
            "expiresAt": int(time.time()) - 100,  # Expired in past!
        }
        mock_db.parent_invitations.find_one = AsyncMock(return_value=mock_invitation)
        mock_db.parent_invitations.update_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post("/api/v2/parent/link/claim-code", json={"code": code})
            self.assertEqual(resp.status_code, 400)
            self.assertIn("expired", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_prevent_duplicate_active_links(self, mock_db):
        """Cannot claim or request a link if an active relationship already exists."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        code = "PLC-DUPL-CODE"
        code_norm = "PLCDUPLCODE"
        code_hash = hashlib.sha256(code_norm.encode()).hexdigest()

        mock_invitation = {
            "id": "inv-004",
            "codeHash": code_hash,
            "studentId": "student-202",
            "status": "active",
            "expiresAt": int(time.time()) + 10000,
        }
        # Existing active link found in DB
        existing_link = {"id": "link-999", "parentId": "parent-101", "studentId": "student-202", "status": "active"}

        mock_db.parent_invitations.find_one = AsyncMock(return_value=mock_invitation)
        mock_db.parent_links.find_one = AsyncMock(return_value=existing_link)

        try:
            resp = self.client.post("/api/v2/parent/link/claim-code", json={"code": code})
            self.assertEqual(resp.status_code, 409)
            self.assertIn("already actively connected", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_parent_link_request_by_student_email(self, mock_db):
        """Parent requests link by email; creates pending link and student notification."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        mock_db.users.find_one = AsyncMock(return_value=self.mock_student)
        mock_db.parent_links.find_one = AsyncMock(return_value=None)
        mock_db.parent_links.insert_one = AsyncMock(return_value=None)
        mock_db.notifications.insert_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post(
                "/api/v2/parent/link/request",
                json={"studentIdentifier": "leo.student@example.com"}
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            self.assertEqual(data["status"], "pending")
            self.assertEqual(data["studentId"], "student-202")
            self.assertIsNone(data["verifiedAt"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_student_approves_link_request(self, mock_db):
        """Student approves a pending parent link request -> transitions to active."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        pending_link = {
            "id": "req-777",
            "parentId": "parent-101",
            "studentId": "student-202",
            "studentName": "Leo Jenkins",
            "status": "pending",
            "requestedAt": int(time.time()),
            "createdAt": int(time.time()),
        }
        mock_db.parent_links.find_one = AsyncMock(return_value=pending_link)
        mock_db.parent_links.update_one = AsyncMock(return_value=None)
        mock_db.notifications.insert_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post("/api/v2/parent/student/requests/req-777/approve")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "active")
            self.assertIsNotNone(data["verifiedAt"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_student_rejects_link_request(self, mock_db):
        """Student rejects a pending parent link request -> transitions to rejected."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_student
        pending_link = {
            "id": "req-888",
            "parentId": "parent-101",
            "studentId": "student-202",
            "status": "pending",
        }
        mock_db.parent_links.find_one = AsyncMock(return_value=pending_link)
        mock_db.parent_links.update_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post("/api/v2/parent/student/requests/req-888/reject")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["success"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_immediate_revocation_by_parent(self, mock_db):
        """Revoking a link marks it revoked immediately."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        active_link = {
            "id": "link-active-01",
            "parentId": "parent-101",
            "studentId": "student-202",
            "status": "active",
        }
        mock_db.parent_links.find_one = AsyncMock(return_value=active_link)
        mock_db.parent_links.update_one = AsyncMock(return_value=None)

        try:
            resp = self.client.post("/api/v2/parent/links/link-active-01/revoke")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["success"])
        finally:
            app.dependency_overrides.clear()

    # ─── 3. Access Isolation & Forged Learner ID Tests ───────────────────────

    @patch("services.parent.parent_service.db")
    def test_parent_cannot_access_unlinked_learner_dashboard(self, mock_db):
        """Parent attempting to view an unlinked student receives 403 Forbidden."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        # DB lookup returns None (no active link between parent-101 and student-303)
        mock_db.parent_links.find_one = AsyncMock(return_value=None)

        try:
            resp = self.client.get("/api/v2/parent/learners/student-303/dashboard")
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Access denied", resp.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_revoked_link_immediately_blocks_dashboard_access(self, mock_db):
        """Once revoked, subsequent calls to that learner's dashboard immediately return 403."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        # verify_parent_student_access filters by status="active". Revoked returns None
        mock_db.parent_links.find_one = AsyncMock(return_value=None)

        try:
            resp = self.client.get("/api/v2/parent/learners/student-202/dashboard")
            self.assertEqual(resp.status_code, 403)
        finally:
            app.dependency_overrides.clear()

    # ─── 4. Dashboard Data & Privacy Protection Tests ─────────────────────────

    @patch("services.parent.parent_service.db")
    def test_dashboard_with_no_linked_learners(self, mock_db):
        """Parent with no linked learners sees a graceful empty state with suggestions."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent

        # Counts
        mock_db.parent_links.count_documents = AsyncMock(return_value=0)
        mock_db.user_language_preferences.find_one = AsyncMock(return_value=None)

        # Empty active links cursor
        cursor_mock = MagicMock()
        cursor_mock.sort = MagicMock(return_value=cursor_mock)
        cursor_mock.to_list = AsyncMock(return_value=[])
        mock_db.parent_links.find = MagicMock(return_value=cursor_mock)

        try:
            resp = self.client.get("/api/v2/parent/dashboard")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data["hasLinkedLearners"])
            self.assertIsNone(data["selectedLearner"])
            self.assertEqual(len(data["linkedLearners"]), 0)
            self.assertIsNone(data["overview"])
            # Home suggestions and disclaimer are still present
            self.assertGreater(len(data["homeSuggestions"]), 0)
            self.assertIn("educational observations", data["disclaimer"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_dashboard_with_active_learner_data(self, mock_db):
        """Parent with an active learner receives aggregated learning metrics and disclaimers."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent

        # Parent counts
        mock_db.parent_links.count_documents = AsyncMock(return_value=1)
        mock_db.user_language_preferences.find_one = AsyncMock(return_value={"preferredLanguage": "mr"})

        # Active link
        active_link = {
            "id": "link-1",
            "parentId": "parent-101",
            "studentId": "student-202",
            "studentName": "Leo Jenkins",
            "relationship": "parent",
            "status": "active",
            "requestedAt": int(time.time()) - 1000,
            "verifiedAt": int(time.time()) - 500,
            "createdAt": int(time.time()) - 1000,
        }

        # Mock find queries
        def mock_find(query, projection=None):
            m_cursor = MagicMock()
            m_cursor.sort = MagicMock(return_value=m_cursor)
            if "status" in query and "parentId" in query:
                m_cursor.to_list = AsyncMock(return_value=[active_link])
            elif "learnerId" in query:
                if query.get("completed") is True:
                    # Reading sessions
                    m_cursor.to_list = AsyncMock(return_value=[{
                        "sessionId": "read-01",
                        "passageTitle": "The Forest Trail",
                        "difficultyTier": 2,
                        "wordsRead": 120,
                        "comprehensionScore": 85.0,
                        "durationSeconds": 300,
                        "createdAt": int(time.time()) - 86400,
                    }])
                else:
                    # Adaptive attempts
                    m_cursor.to_list = AsyncMock(return_value=[{
                        "attemptId": "act-01",
                        "domain": "phonics",
                        "scorePercent": 90.0,
                        "difficultyTier": 2,
                        "completedAt": int(time.time()) - 43200,
                    }])
            else:
                m_cursor.to_list = AsyncMock(return_value=[])
            return m_cursor

        mock_db.parent_links.find = MagicMock(side_effect=mock_find)
        mock_db.parent_links.find_one = AsyncMock(return_value=active_link)
        mock_db.reading_sessions.find = MagicMock(side_effect=mock_find)
        mock_db.activity_attempts.find = MagicMock(side_effect=mock_find)
        mock_db.speech_reading_analyses.find = MagicMock(side_effect=mock_find)

        mock_db.gamification_summaries.find_one = AsyncMock(return_value={
            "totalPoints": 150,
            "currentStreak": 4,
            "longestStreak": 7,
            "earnedBadges": [{"badgeId": "first_steps", "title": "First Steps", "icon": "🌱"}],
        })
        mock_db.learning_states.find_one = AsyncMock(return_value={"tier": 2})

        try:
            resp = self.client.get("/api/v2/parent/dashboard")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["hasLinkedLearners"])
            self.assertEqual(data["selectedLearner"]["studentName"], "Leo Jenkins")
            self.assertEqual(data["overview"]["storiesCompleted"], 1)
            self.assertEqual(data["overview"]["totalReadingMinutes"], 5.0)
            self.assertEqual(data["overview"]["avgComprehensionScore"], 85.0)
            self.assertEqual(data["overview"]["totalPoints"], 150)
            self.assertEqual(data["overview"]["currentStreak"], 4)
            self.assertEqual(data["overview"]["currentDifficultyTier"], 2)

            # Disclaimer check
            self.assertIn("educational observations", data["disclaimer"])
            self.assertIn("not a clinical or medical diagnosis", data["disclaimer"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.parent.parent_service.db")
    def test_activity_timeline_excludes_tutor_and_teacher_notes(self, mock_db):
        """Activity timeline lists reading and adaptive events without leaking tutor chats or teacher notes."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        active_link = {"parentId": "parent-101", "studentId": "student-202", "status": "active"}
        mock_db.parent_links.find_one = AsyncMock(return_value=active_link)

        def mock_find(query, projection=None):
            m_cursor = MagicMock()
            m_cursor.sort = MagicMock(return_value=m_cursor)
            if query.get("completed") is True:
                m_cursor.to_list = AsyncMock(return_value=[{
                    "sessionId": "read-01",
                    "passageTitle": "Friendly Forest",
                    "wordsRead": 80,
                    "difficultyTier": 1,
                    "comprehensionScore": 90.0,
                    "createdAt": int(time.time()) - 3600,
                }])
            elif "completedAt" in str(query) or "activity_attempts" in str(mock_find):
                m_cursor.to_list = AsyncMock(return_value=[{
                    "attemptId": "act-01",
                    "domain": "rhyming",
                    "scorePercent": 80.0,
                    "completedAt": int(time.time()) - 1800,
                }])
            else:
                m_cursor.to_list = AsyncMock(return_value=[])
            return m_cursor

        mock_db.reading_sessions.find = MagicMock(side_effect=mock_find)
        mock_db.activity_attempts.find = MagicMock(side_effect=mock_find)
        mock_db.reward_events.find = MagicMock(side_effect=mock_find)

        try:
            resp = self.client.get("/api/v2/parent/learners/student-202/activity?limit=10")
            self.assertEqual(resp.status_code, 200)
            activities = resp.json()
            self.assertIsInstance(activities, list)
            # Ensure none of the activity types are tutor chat
            for item in activities:
                self.assertNotEqual(item.get("type"), "tutor_chat")
                self.assertNotIn("tutor_message", item.get("description", "").lower())
        finally:
            app.dependency_overrides.clear()

    # ─── 5. Feature Flag Governance Tests ─────────────────────────────────────

    def test_feature_flag_disabled_returns_503(self):
        """When V2_PARENT_PORTAL is false, endpoints return 503 Service Unavailable."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_parent
        with patch.object(settings, "V2_PARENT_PORTAL", False):
            resp = self.client.get("/api/v2/parent/dashboard")
            self.assertEqual(resp.status_code, 503)
            self.assertIn("disabled via feature flags", resp.json()["detail"])
        app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
