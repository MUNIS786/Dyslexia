"""
backend/test_phase12_accessibility.py — Comprehensive Test Suite for Phase 12: Accessibility & Personalization.

Tests cover:
1. Authentication & Authorization:
   - 401 Unauthorized for unauthenticated GET/PUT/PATCH/POST requests
   - User ownership: each user retrieves and modifies only their own preferences
2. Preference Retrieval & Defaults:
   - Authenticated user with no saved preferences gets safe canonical defaults
   - Response envelope contains non-clinical educational disclaimer
3. Valid Updates & Persistence:
   - PUT replaces all preferences with valid parameters
   - PATCH partially updates specified fields while keeping other fields intact
   - Synced legacy keys update in users.settings for V1 backward-compatibility
4. Schema Validation:
   - Invalid font size (<12 or >36) rejected with 422
   - Invalid line spacing (<1.2 or >3.5) rejected with 422
   - Invalid contentWidth rejected with 422
   - Invalid tintOverlay rejected with 422
   - Invalid rulerColor rejected with 422
5. Reset to Defaults:
   - POST /reset restores factory default settings
6. Feature Flag Governance:
   - When V2_ACCESSIBILITY_PREFERENCES is False, all endpoints return 503 Service Unavailable
"""
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings
from deps.deps import get_current_user
from models.v2_accessibility import (
    V2AccessibilityPreferences,
    AccessibilityPreferencesPatch,
    AccessibilityPreferencesResponse,
)


class TestPhase12Accessibility(unittest.TestCase):
    """Test suite for Phase 12 accessibility and personalization API."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_user = {
            "id": "student-101",
            "name": "Aarav Sharma",
            "email": "aarav@school.edu",
            "role": "student",
        }
        self.mock_user_b = {
            "id": "student-202",
            "name": "Diya Patel",
            "email": "diya@school.edu",
            "role": "student",
        }
        app.dependency_overrides = {}

    def tearDown(self):
        app.dependency_overrides = {}

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests must return 401 Unauthorized."""
        res_get = self.client.get("/api/v2/accessibility/preferences")
        self.assertEqual(res_get.status_code, 401)

        res_put = self.client.put("/api/v2/accessibility/preferences", json={})
        self.assertEqual(res_put.status_code, 401)

        res_patch = self.client.patch("/api/v2/accessibility/preferences", json={})
        self.assertEqual(res_patch.status_code, 401)

        res_reset = self.client.post("/api/v2/accessibility/preferences/reset")
        self.assertEqual(res_reset.status_code, 401)

    @patch("services.accessibility.accessibility_service.db")
    def test_get_preferences_returns_defaults_when_empty(self, mock_db):
        """When user has no preferences recorded, canonical defaults are returned."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        mock_db.user_accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value={"id": "student-101", "settings": None})

        try:
            res = self.client.get("/api/v2/accessibility/preferences")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("preferences", data)
            self.assertIn("disclaimer", data)
            self.assertIn("not constitute a medical", data["disclaimer"])

            prefs = data["preferences"]
            self.assertEqual(prefs["font"], "OpenDyslexic")
            self.assertEqual(prefs["fontSize"], 18)
            self.assertEqual(prefs["lineSpacing"], 2.0)
            self.assertEqual(prefs["contentWidth"], "standard")
            self.assertFalse(prefs["highContrast"])
            self.assertFalse(prefs["reducedMotion"])
            self.assertFalse(prefs["readingRuler"])
        finally:
            app.dependency_overrides.clear()

    @patch("services.accessibility.accessibility_service.db")
    def test_put_preferences_success(self, mock_db):
        """PUT replaces all preferences with valid parameters and syncs legacy keys."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        mock_db.user_accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value={"id": "student-101"})
        mock_db.user_accessibility_preferences.update_one = AsyncMock(return_value=None)
        mock_db.users.update_one = AsyncMock(return_value=None)

        payload = {
            "font": "Lexend",
            "fontSize": 24,
            "lineSpacing": 2.4,
            "letterSpacing": 0.12,
            "wordSpacing": 0.1,
            "contentWidth": "narrow",
            "bgColor": "#FFFFFF",
            "textColor": "#000000",
            "highContrast": True,
            "reducedMotion": True,
            "readingRuler": True,
            "rulerSize": 80,
            "rulerColor": "cyan",
            "tintOverlay": "peach",
            "ttsSpeed": 1.0,
            "ttsLanguage": "en-IN",
            "highlightWords": True,
            "showBulletPoints": True,
            "autoSimplify": True,
        }

        try:
            res = self.client.put("/api/v2/accessibility/preferences", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            prefs = data["preferences"]
            self.assertEqual(prefs["font"], "Lexend")
            self.assertEqual(prefs["fontSize"], 24)
            self.assertEqual(prefs["lineSpacing"], 2.4)
            self.assertEqual(prefs["contentWidth"], "narrow")
            self.assertTrue(prefs["highContrast"])
            self.assertTrue(prefs["reducedMotion"])
            self.assertTrue(prefs["readingRuler"])
            self.assertEqual(prefs["rulerSize"], 80)
            self.assertEqual(prefs["rulerColor"], "cyan")
            self.assertEqual(prefs["tintOverlay"], "peach")

            # Verify database updates called
            mock_db.user_accessibility_preferences.update_one.assert_called_once()
            mock_db.users.update_one.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @patch("services.accessibility.accessibility_service.db")
    def test_patch_preferences_partial_update(self, mock_db):
        """PATCH updates only targeted fields and leaves existing ones intact."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        mock_db.user_accessibility_preferences.find_one = AsyncMock(return_value={
            "userId": "student-101",
            "preferences": {
                "font": "OpenDyslexic",
                "fontSize": 18,
                "lineSpacing": 2.0,
                "letterSpacing": 0.08,
                "wordSpacing": 0.05,
                "contentWidth": "standard",
                "bgColor": "#FFF8F0",
                "textColor": "#1A2A2A",
                "highContrast": False,
                "reducedMotion": False,
                "readingRuler": False,
                "rulerSize": 60,
                "rulerColor": "amber",
                "tintOverlay": "none",
                "ttsSpeed": 0.85,
                "ttsLanguage": "en-IN",
                "highlightWords": True,
                "showBulletPoints": True,
                "autoSimplify": True,
            }
        })
        mock_db.user_accessibility_preferences.update_one = AsyncMock(return_value=None)
        mock_db.users.update_one = AsyncMock(return_value=None)

        patch_payload = {
            "fontSize": 22,
            "highContrast": True,
            "tintOverlay": "mint",
        }

        try:
            res = self.client.patch("/api/v2/accessibility/preferences", json=patch_payload)
            self.assertEqual(res.status_code, 200)
            prefs = res.json()["preferences"]
            # Updated fields
            self.assertEqual(prefs["fontSize"], 22)
            self.assertTrue(prefs["highContrast"])
            self.assertEqual(prefs["tintOverlay"], "mint")
            # Preserved fields
            self.assertEqual(prefs["font"], "OpenDyslexic")
            self.assertEqual(prefs["lineSpacing"], 2.0)
            self.assertEqual(prefs["contentWidth"], "standard")
        finally:
            app.dependency_overrides.clear()

    def test_invalid_preference_values_rejected(self):
        """Out-of-range or unrecognized values must be rejected with 422."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user

        try:
            # Invalid fontSize too large
            res1 = self.client.patch("/api/v2/accessibility/preferences", json={"fontSize": 99})
            self.assertEqual(res1.status_code, 422)

            # Invalid fontSize too small
            res2 = self.client.patch("/api/v2/accessibility/preferences", json={"fontSize": 5})
            self.assertEqual(res2.status_code, 422)

            # Invalid lineSpacing
            res3 = self.client.patch("/api/v2/accessibility/preferences", json={"lineSpacing": 5.0})
            self.assertEqual(res3.status_code, 422)

            # Invalid contentWidth
            res4 = self.client.patch("/api/v2/accessibility/preferences", json={"contentWidth": "ultra-wide"})
            self.assertEqual(res4.status_code, 422)

            # Invalid tintOverlay
            res5 = self.client.patch("/api/v2/accessibility/preferences", json={"tintOverlay": "neon-purple"})
            self.assertEqual(res5.status_code, 422)

            # Invalid rulerColor
            res6 = self.client.patch("/api/v2/accessibility/preferences", json={"rulerColor": "magenta"})
            self.assertEqual(res6.status_code, 422)

            # Invalid rulerSize too small
            res7 = self.client.patch("/api/v2/accessibility/preferences", json={"rulerSize": 10})
            self.assertEqual(res7.status_code, 422)

            # Invalid ttsSpeed too fast
            res8 = self.client.patch("/api/v2/accessibility/preferences", json={"ttsSpeed": 4.5})
            self.assertEqual(res8.status_code, 422)

            # Invalid letterSpacing too large
            res9 = self.client.patch("/api/v2/accessibility/preferences", json={"letterSpacing": 1.2})
            self.assertEqual(res9.status_code, 422)
        finally:
            app.dependency_overrides.clear()

    @patch("services.accessibility.accessibility_service.db")
    def test_legacy_user_settings_fallback(self, mock_db):
        """When user has legacy users.settings, it falls back and adopts those preferences."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        mock_db.user_accessibility_preferences.find_one = AsyncMock(return_value=None)
        mock_db.users.find_one = AsyncMock(return_value={
            "id": "student-101",
            "settings": {
                "font": "Lexend",
                "fontSize": 26,
                "lineSpacing": 2.2,
                "letterSpacing": 0.15,
                "bgColor": "#FFFFFF",
                "textColor": "#000000",
                "ttsSpeed": 0.9,
            }
        })

        try:
            res = self.client.get("/api/v2/accessibility/preferences")
            self.assertEqual(res.status_code, 200)
            prefs = res.json()["preferences"]
            self.assertEqual(prefs["font"], "Lexend")
            self.assertEqual(prefs["fontSize"], 26)
            self.assertEqual(prefs["lineSpacing"], 2.2)
            self.assertEqual(prefs["letterSpacing"], 0.15)
        finally:
            app.dependency_overrides.clear()

    @patch("services.accessibility.accessibility_service.db")
    def test_reset_preferences_to_defaults(self, mock_db):
        """POST /reset restores factory default settings."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        mock_db.user_accessibility_preferences.update_one = AsyncMock(return_value=None)
        mock_db.users.update_one = AsyncMock(return_value=None)

        try:
            res = self.client.post("/api/v2/accessibility/preferences/reset")
            self.assertEqual(res.status_code, 200)
            prefs = res.json()["preferences"]
            self.assertEqual(prefs["font"], "OpenDyslexic")
            self.assertEqual(prefs["fontSize"], 18)
            self.assertEqual(prefs["lineSpacing"], 2.0)
            self.assertFalse(prefs["highContrast"])
            self.assertFalse(prefs["readingRuler"])
            self.assertEqual(prefs["tintOverlay"], "none")
        finally:
            app.dependency_overrides.clear()

    @patch("services.accessibility.accessibility_service.db")
    def test_user_isolation(self, mock_db):
        """User A cannot see User B's preferences."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user_b

        async def fake_find_one(filter_query):
            if filter_query.get("userId") == "student-202":
                return {
                    "userId": "student-202",
                    "preferences": {
                        "font": "Lexend",
                        "fontSize": 20,
                        "lineSpacing": 1.8,
                        "letterSpacing": 0.05,
                        "wordSpacing": 0.05,
                        "contentWidth": "standard",
                        "bgColor": "#FFF8F0",
                        "textColor": "#1A2A2A",
                        "highContrast": False,
                        "reducedMotion": False,
                        "readingRuler": False,
                        "rulerSize": 60,
                        "rulerColor": "amber",
                        "tintOverlay": "none",
                        "ttsSpeed": 1.0,
                        "ttsLanguage": "en-IN",
                        "highlightWords": True,
                        "showBulletPoints": True,
                        "autoSimplify": True,
                    }
                }
            return None

        mock_db.user_accessibility_preferences.find_one = AsyncMock(side_effect=fake_find_one)
        try:
            res = self.client.get("/api/v2/accessibility/preferences")
            self.assertEqual(res.status_code, 200)
            prefs = res.json()["preferences"]
            self.assertEqual(prefs["font"], "Lexend")
            self.assertEqual(prefs["fontSize"], 20)
        finally:
            app.dependency_overrides.clear()

    def test_feature_flag_disabled_returns_503(self):
        """When V2_ACCESSIBILITY_PREFERENCES is disabled, endpoints return 503."""
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        try:
            with patch.object(settings, "V2_ACCESSIBILITY_PREFERENCES", False):
                res_get = self.client.get("/api/v2/accessibility/preferences")
                self.assertEqual(res_get.status_code, 503)

                res_put = self.client.put("/api/v2/accessibility/preferences", json={})
                self.assertEqual(res_put.status_code, 503)

                res_patch = self.client.patch("/api/v2/accessibility/preferences", json={})
                self.assertEqual(res_patch.status_code, 503)

                res_reset = self.client.post("/api/v2/accessibility/preferences/reset")
                self.assertEqual(res_reset.status_code, 503)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
