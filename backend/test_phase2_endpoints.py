"""
backend/test_phase2_endpoints.py — Integration and Security Tests for Phase 2 Endpoints.
Verifies FastAPI routing, authorization, security boundaries, and patch validation.
"""
import sys
import os
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from deps.deps import get_current_user, require_teacher

client = TestClient(app)


class TestPhase2Endpoints(unittest.TestCase):

    def test_student_profile_endpoint_authenticated(self):
        """Test GET /api/v2/learner/profile returns clean structure for student."""
        mock_student = {
            "id": "student-123",
            "name": "Test Student",
            "email": "student@test.com",
            "role": "student",
            "languages": ["english"],
            "readingProfile": {
                "type": "Phonological Dyslexia",
                "level": "moderate",
                "score": 50,
                "confidence": 75,
                "domainScores": {"phonological_processing": 60, "reading_fluency": 50},
                "screenedAt": 1727548000,
            },
        }

        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_student

        with patch("services.learning.learner_profile_service.db") as mock_db:
            # Mock find_one for learner_profiles (None) so it synthesizes from user
            mock_db.learner_profiles.find_one = AsyncMock(return_value=None)
            mock_db.users.find_one = AsyncMock(return_value=mock_student)
            mock_db.progress.find_one = AsyncMock(return_value={"sessionCount": 5, "streak": 3})
            mock_db.screening_results.find_one = AsyncMock(return_value=None)
            mock_db.learner_profiles.update_one = AsyncMock(return_value=None)

            response = client.get("/api/v2/learner/profile")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            prof = data["profile"]
            self.assertEqual(prof["learner"]["id"], "student-123")
            self.assertIn("learning_level", prof)
            self.assertIn("domain_scores", prof)
            self.assertIn("strengths", prof)
            self.assertIn("areas_for_practice", prof)
            self.assertIn("disclaimer", prof)

        app.dependency_overrides.clear()

    def test_student_profile_patch_endpoint(self):
        """Test PATCH /api/v2/learner/profile allows updating goals and preferences."""
        mock_student = {
            "id": "student-123",
            "name": "Test Student",
            "role": "student",
        }
        app.dependency_overrides[get_current_user] = lambda: mock_student

        with patch("services.learning.learner_profile_service.db") as mock_db:
            mock_db.learner_profiles.update_one = AsyncMock(return_value=None)
            mock_db.users.update_one = AsyncMock(return_value=None)
            mock_db.users.find_one = AsyncMock(return_value=mock_student)
            mock_db.progress.find_one = AsyncMock(return_value={})
            mock_db.screening_results.find_one = AsyncMock(return_value=None)

            # Return synthetic profile on get_or_create
            fake_profile = {
                "learnerId": "student-123",
                "displayName": "Test Student",
                "preferredLanguage": "en-IN",
                "currentGoals": [{"id": "g-1", "title": "Read chapter 1", "completed": True}],
                "preferredLearningModes": ["Visual"],
                "accessibilityPreferences": {"font": "OpenDyslexic", "font_size": 20},
                "lastUpdated": 1727548000,
            }
            mock_db.learner_profiles.find_one = AsyncMock(return_value=fake_profile)

            patch_payload = {
                "preferred_language": "en-IN",
                "preferred_learning_modes": ["Visual"],
                "current_goals": [{"id": "g-1", "title": "Read chapter 1", "completed": True}],
                "accessibility_preferences": {"font": "OpenDyslexic", "font_size": 20},
            }

            response = client.patch("/api/v2/learner/profile", json=patch_payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")

        app.dependency_overrides.clear()

    def test_teacher_access_authorized_student(self):
        """Test authorized teacher can access student enrolled in their classroom."""
        mock_teacher = {
            "id": "teacher-456",
            "name": "Teacher Anjali",
            "role": "teacher",
            "classroomCode": "CLASS-101",
        }
        mock_student = {
            "id": "student-789",
            "name": "Aarav",
            "classroomJoined": "CLASS-101",
            "role": "student",
        }

        app.dependency_overrides[require_teacher] = lambda: mock_teacher

        with patch("routers.v2_learner.db") as mock_router_db, \
             patch("services.learning.learner_profile_service.db") as mock_srv_db:
            # Student matches teacher's classroom
            mock_router_db.users.find_one = AsyncMock(return_value=mock_student)
            mock_srv_db.users.find_one = AsyncMock(return_value=mock_student)
            mock_srv_db.progress.find_one = AsyncMock(return_value={})
            mock_srv_db.learner_profiles.update_one = AsyncMock(return_value=None)
            mock_srv_db.learner_profiles.find_one = AsyncMock(return_value={
                "learnerId": "student-789",
                "displayName": "Aarav",
                "screeningCompleted": True,
                "learningLevel": {"level": 2, "name": "Developing"},
                "domainScores": {"reading_fluency": 50.0},
                "metadata": {"screening_completed": True},
            })

            response = client.get("/api/v2/learner/student/student-789/profile")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["student_name"], "Aarav")

        app.dependency_overrides.clear()

    def test_teacher_access_unauthorized_student(self):
        """Security: Teacher cannot access a student from another classroom."""
        mock_teacher = {
            "id": "teacher-456",
            "name": "Teacher Anjali",
            "role": "teacher",
            "classroomCode": "CLASS-101",
        }
        app.dependency_overrides[require_teacher] = lambda: mock_teacher

        with patch("routers.v2_learner.db") as mock_router_db:
            # Student is NOT in CLASS-101, so query returns None
            mock_router_db.users.find_one = AsyncMock(return_value=None)

            response = client.get("/api/v2/learner/student/other-student-999/profile")
            self.assertEqual(response.status_code, 404)
            self.assertIn("not found in your assigned classroom", response.json()["detail"].lower())

        app.dependency_overrides.clear()

    def test_non_teacher_forbidden_on_teacher_endpoint(self):
        """Security: Student role cannot access teacher student-detail endpoint."""
        response = client.get("/api/v2/learner/student/some-student/profile")
        # Without authorization header, require_teacher raises 401
        self.assertIn(response.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
