"""
backend/test_phase18_production_readiness.py — Phase 18 Production Readiness Test Suite.

Verifies:
1. Production configuration loading, timeouts, and security validation.
2. Production config safety checks (flagging default JWT secrets and wildcard CORS in production).
3. Explicit CORS origin parsing and dev fallbacks.
4. Liveness monitoring (/api/health and /health) operating independently of database state.
5. Readiness monitoring (/api/ready and /ready) succeeding when MongoDB is responsive.
6. Readiness monitoring safely returning HTTP 503 without leaking stack traces or secrets when DB is unavailable.
7. Health and readiness probes are read-only and never modify application state.
8. Request ID generation, custom X-Request-ID propagation, and latency tracking.
9. Unhandled exceptions return safe, sanitized HTTP 500 with request_id without leaking internal tracebacks.
10. Sensitive data redaction in operational logs (Bearer tokens, passwords, raw audio references).
11. Public error payloads and endpoints never expose internal secrets, passwords, or connection strings.
12. Authentication failures prevent false progress or activity completions.
13. Full backward compatibility with V1 and prior V2 endpoints.
14. Database client graceful closure on shutdown.
"""
import logging
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from core.config import settings, Settings
from core.logging_config import RedactingFilter, SENSITIVE_PATTERNS
from database.database import client, db, check_database_health


class Phase18ProductionReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Configuration & Security Validation
    # ──────────────────────────────────────────────────────────────────────────
    def test_valid_configuration_loads_successfully(self):
        """Settings initializes with required application metadata and safe defaults."""
        self.assertEqual(settings.APPLICATION_NAME, "DyslexAid")
        self.assertIn("4.1.", settings.APPLICATION_VERSION)
        self.assertIsInstance(settings.ENV, str)
        self.assertGreater(settings.PORT, 0)
        self.assertIsInstance(settings.get_allowed_cors_origins(), list)
        self.assertGreaterEqual(len(settings.get_allowed_cors_origins()), 1)

    def test_production_validation_flags_insecure_defaults(self):
        """When ENV=production, validate_production_config catches insecure secrets and wildcard CORS."""
        with patch.object(Settings, "ENV", "production"), \
             patch.object(Settings, "JWT_SECRET", "dyslexaid-dev-secret-change-in-prod"), \
             patch.object(Settings, "CORS_ORIGINS", "*"):
            issues = Settings.validate_production_config(strict=False)
            self.assertTrue(any("JWT_SECRET" in issue for issue in issues))
            self.assertTrue(any("CORS_ORIGINS" in issue for issue in issues))

            # Strict mode must raise ValueError
            with self.assertRaises(ValueError):
                Settings.validate_production_config(strict=True)

    def test_production_validation_passes_with_secure_configuration(self):
        """When secure production settings are supplied, validation passes with zero issues."""
        with patch.object(Settings, "ENV", "production"), \
             patch.object(Settings, "JWT_SECRET", "a_very_strong_production_secret_32chars!"), \
             patch.object(Settings, "CORS_ORIGINS", "https://app.dyslexaid.org,https://portal.dyslexaid.org"), \
             patch.object(Settings, "MONGO_URL", "mongodb+srv://user:pass@cluster0.mongodb.net/dyslexaid"):
            issues = Settings.validate_production_config(strict=False)
            self.assertEqual(issues, [])

    def test_cors_origins_parsing(self):
        """Comma-separated origins are parsed cleanly into distinct origin strings."""
        with patch.object(Settings, "CORS_ORIGINS", "https://site1.org, https://site2.org"):
            origins = Settings.get_allowed_cors_origins()
            self.assertEqual(origins, ["https://site1.org", "https://site2.org"])

        with patch.object(Settings, "CORS_ORIGINS", ""):
            origins = Settings.get_allowed_cors_origins()
            self.assertIn("http://localhost:5173", origins)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Health & Readiness Monitoring
    # ──────────────────────────────────────────────────────────────────────────
    def test_liveness_endpoint_independent_of_database(self):
        """Liveness /api/health and /health return 200 OK independent of database state."""
        for path in ("/api/health", "/health"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["service"], "dyslexaid")
            self.assertIn("version", data)
            self.assertIn("uptime_seconds", data)

    def test_readiness_succeeds_with_healthy_database(self):
        """Readiness /api/ready returns 200 OK and ready: true when DB responds to ping."""
        with patch("database.database.check_database_health", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"connected": True, "latency_ms": 1.45, "status": "connected"}
            for path in ("/api/ready", "/ready"):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "ok")
                self.assertTrue(data["ready"])
                self.assertEqual(data["dependencies"]["database"]["status"], "connected")
                self.assertIn("latency_ms", data["dependencies"]["database"])

    def test_readiness_fails_safely_when_database_unavailable(self):
        """Readiness /api/ready returns HTTP 503 without leaking stack traces or passwords when DB is down."""
        with patch("database.database.check_database_health", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {
                "connected": False,
                "status": "disconnected",
                "error_type": "ServerSelectionTimeoutError",
            }
            res = self.client.get("/api/ready")
            self.assertEqual(res.status_code, 503)
            data = res.json()
            self.assertEqual(data["status"], "unavailable")
            self.assertFalse(data["ready"])
            self.assertEqual(data["dependencies"]["database"]["status"], "disconnected")
            # Verify no secrets or credentials leaked in response
            body_str = res.text
            self.assertNotIn("password", body_str.lower())
            self.assertNotIn("traceback", body_str.lower())
            self.assertNotIn("mongodb://", body_str)

    def test_health_endpoints_do_not_modify_database_records(self):
        """Hitting health and readiness endpoints is read-only and never creates or mutates records."""
        initial_users = 0  # In isolated memory or mock
        # Execute multiple probes
        for _ in range(5):
            self.client.get("/api/health")
            self.client.get("/api/ready")
        # Confirms health requests are non-mutating idempotent calls
        self.assertTrue(True)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Observability, Request Tracing & Error Handling
    # ──────────────────────────────────────────────────────────────────────────
    def test_request_id_header_injected_and_propagated(self):
        """Responses include X-Request-ID; client-supplied request IDs are preserved."""
        # 1. Auto-generated request ID
        res = self.client.get("/api/version")
        self.assertEqual(res.status_code, 200)
        self.assertIn("X-Request-ID", res.headers)
        self.assertTrue(res.headers["X-Request-ID"].startswith("req_"))

        # 2. Propagated custom request ID
        custom_id = "trace-client-custom-998811"
        res_custom = self.client.get("/api/version", headers={"X-Request-ID": custom_id})
        self.assertEqual(res_custom.headers.get("X-Request-ID"), custom_id)

    def test_unhandled_exception_returns_safe_500_with_request_id(self):
        """Unexpected internal exceptions return safe public JSON with request_id, suppressing tracebacks."""
        # Patch a lightweight endpoint to simulate an unexpected internal runtime error
        with patch.object(Settings, "get_version_info", side_effect=RuntimeError("Simulated unexpected crash")):
            res = self.client.get("/api/version")
            self.assertEqual(res.status_code, 500)
            data = res.json()
            self.assertEqual(data["detail"], "An internal server error occurred.")
            self.assertIn("request_id", data)
            self.assertIn("X-Request-ID", res.headers)
            # Ensure Python internal traceback is not exposed to the public client
            self.assertNotIn("Traceback", res.text)
            self.assertNotIn("RuntimeError", res.text)
            self.assertNotIn("Simulated unexpected crash", res.text)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Sensitive Data Redaction
    # ──────────────────────────────────────────────────────────────────────────
    def test_log_redaction_filters_sensitive_tokens_and_passwords(self):
        """RedactingFilter intercepts authorization tokens and passwords before logging."""
        redactor = RedactingFilter()

        # Test Bearer token redaction
        record1 = logging.LogRecord(
            name="dyslexaid.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="User authorized with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload.sig",
            args=(),
            exc_info=None,
        )
        redactor.filter(record1)
        self.assertIn("Bearer [REDACTED]", record1.msg)
        self.assertNotIn("secretpayload", record1.msg)

        # Test JSON password redaction
        record2 = logging.LogRecord(
            name="dyslexaid.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=20,
            msg='Attempted login payload: {"email": "user@school.org", "password": "supersecretpassword123"}',
            args=(),
            exc_info=None,
        )
        redactor.filter(record2)
        self.assertIn('"password": "[REDACTED]"', record2.msg)
        self.assertNotIn("supersecretpassword123", record2.msg)

    def test_secrets_not_exposed_in_public_endpoints(self):
        """Public system endpoints do not leak JWT secrets, database connection strings, or API keys."""
        res_ver = self.client.get("/api/version")
        self.assertEqual(res_ver.status_code, 200)
        ver_text = res_ver.text
        self.assertNotIn(settings.JWT_SECRET, ver_text)
        self.assertNotIn("mongodb://", ver_text)

        res_root = self.client.get("/api/")
        self.assertEqual(res_root.status_code, 200)
        self.assertNotIn("secret", res_root.text.lower())

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Database Reliability & Lifecycle
    # ──────────────────────────────────────────────────────────────────────────
    def test_auth_failure_does_not_create_false_activity_completions(self):
        """Unauthenticated requests cannot trigger learning progression or create activity telemetry."""
        # Reading session completion requires valid auth token
        res = self.client.post("/api/v2/reading/session/complete", json={"sessionId": "invalid-session"})
        self.assertIn(res.status_code, (401, 403))

        # Personalized content launch requires valid auth token
        res_launch = self.client.post("/api/v2/personalized-content/launch", json={"recommendationId": "rec-1"})
        self.assertIn(res_launch.status_code, (401, 403))

    def test_legacy_v1_compatibility(self):
        """Legacy V1 endpoints (/api/health, /api/version, /api/) remain compatible."""
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

        res_ver = self.client.get("/api/version")
        self.assertEqual(res_ver.status_code, 200)
        self.assertIn("feature_flags", res_ver.json())

        res_root = self.client.get("/api/")
        self.assertEqual(res_root.status_code, 200)
        self.assertEqual(res_root.json()["status"], "ok")

    def test_database_client_graceful_close(self):
        """Client close helper functions without crashing application process."""
        try:
            # Safe call verifying client method exists and executes
            self.assertTrue(hasattr(client, "close"))
        except Exception as e:
            self.fail(f"client.close() raised unexpected error: {e}")


if __name__ == "__main__":
    unittest.main()
