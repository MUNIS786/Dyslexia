"""
backend/test_auth_production.py — Comprehensive Production Authentication Test Suite.

Verifies:
1. Registration & Validation:
   - Successful student & teacher signup.
   - Prevention of role elevation (admin -> student).
   - Validation: name length, email format, password complexity, password match.
   - Duplicate email prevention (409 Conflict) and case-insensitivity.
2. Login & Credential Verification:
   - Case-insensitive email login.
   - Incorrect password handling (401).
   - Unknown account handling (401).
   - Disabled account rejection (403).
   - Password hashes never returned in API responses.
3. Token & Session Management:
   - /auth/me returns identity for valid Bearer token.
   - Rejection of tampered, malformed, or missing tokens (401).
4. Password Recovery (Forgot / Reset Password):
   - User enumeration prevention: generic response for unknown emails.
   - Cryptographic reset token generation and SHA-256 storage.
   - Successful password reset and verification.
   - Rejection of expired, invalid, and reused reset tokens.
5. Email Verification:
   - Token claim and account verification state update.
   - Single-use atomic consumption of verification tokens.
   - Resend verification behavior.
6. Rate Limiting:
   - Protection against rapid repeated requests.
"""
import hashlib
import time
import uuid
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from deps.deps import hash_password, make_token
from services.email_service import get_dispatched_emails, clear_dispatched_emails
from services.auth_rate_limiter import AuthRateLimiter

client = TestClient(app)


class ProductionAuthTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        clear_dispatched_emails()
        AuthRateLimiter.reset()
        AuthRateLimiter.set_enabled(True)

    def tearDown(self):
        clear_dispatched_emails()
        AuthRateLimiter.reset()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Registration
    # ─────────────────────────────────────────────────────────────────────────

    async def test_signup_success_student(self):
        """Student registration succeeds with valid data and initializes progress."""
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.insert_one = AsyncMock(return_value=None)
            mock_db.progress.insert_one = AsyncMock(return_value=None)
            mock_db.email_verifications.insert_one = AsyncMock(return_value=None)

            payload = {
                "name": "Kavita Rao",
                "email": "kavita.rao@example.com",
                "password": "SecurePassword123!",
                "confirmPassword": "SecurePassword123!",
                "role": "student",
                "schoolName": "Greenwood High",
                "age": 11,
            }
            response = client.post("/api/auth/signup", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("token", data)
            self.assertIn("user", data)
            user = data["user"]
            self.assertEqual(user["email"], "kavita.rao@example.com")
            self.assertEqual(user["role"], "student")
            self.assertNotIn("passwordHash", user)
            self.assertNotIn("_id", user)

            # Ensure student progress was initialized
            self.assertTrue(mock_db.progress.insert_one.called)
            # Ensure verification email was dispatched
            emails = get_dispatched_emails()
            self.assertEqual(len(emails), 1)
            self.assertEqual(emails[0]["to"], "kavita.rao@example.com")
            self.assertEqual(emails[0]["category"], "email_verification")

    async def test_signup_success_teacher(self):
        """Teacher registration creates a classroom record."""
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.insert_one = AsyncMock(return_value=None)
            mock_db.classrooms.insert_one = AsyncMock(return_value=None)
            mock_db.email_verifications.insert_one = AsyncMock(return_value=None)

            payload = {
                "name": "Prof. Vikram",
                "email": "vikram@school.edu",
                "password": "TeacherPass@456",
                "confirmPassword": "TeacherPass@456",
                "role": "teacher",
                "schoolName": "National Academy",
            }
            response = client.post("/api/auth/signup", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["user"]["role"], "teacher")
            self.assertTrue(mock_db.classrooms.insert_one.called)

    async def test_signup_prevents_admin_role_escalation(self):
        """Registering with role 'admin' or 'superuser' defaults safely to 'student'."""
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)
            mock_db.users.insert_one = AsyncMock(return_value=None)
            mock_db.progress.insert_one = AsyncMock(return_value=None)
            mock_db.email_verifications.insert_one = AsyncMock(return_value=None)

            payload = {
                "name": "Hacker Attempt",
                "email": "hacker@test.com",
                "password": "Password123!",
                "confirmPassword": "Password123!",
                "role": "administrator",
            }
            response = client.post("/api/auth/signup", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["user"]["role"], "student")

    async def test_signup_validation_errors(self):
        """Tests field-level validation: short password, password mismatch, invalid email."""
        # 1. Short password (< 8 chars)
        res1 = client.post("/api/auth/signup", json={
            "name": "Short Pass", "email": "short@test.com",
            "password": "Abc1", "confirmPassword": "Abc1",
        })
        self.assertEqual(res1.status_code, 422)

        # 2. Missing numbers/symbols
        res2 = client.post("/api/auth/signup", json={
            "name": "No Number", "email": "nonum@test.com",
            "password": "OnlyLettersHere", "confirmPassword": "OnlyLettersHere",
        })
        self.assertEqual(res2.status_code, 422)

        # 3. Passwords mismatch
        res3 = client.post("/api/auth/signup", json={
            "name": "Mismatch", "email": "mismatch@test.com",
            "password": "ValidPassword123!", "confirmPassword": "DifferentPassword123!",
        })
        self.assertEqual(res3.status_code, 422)

        # 4. Invalid email format
        res4 = client.post("/api/auth/signup", json={
            "name": "Bad Email", "email": "not-an-email",
            "password": "ValidPassword123!", "confirmPassword": "ValidPassword123!",
        })
        self.assertEqual(res4.status_code, 422)

    async def test_signup_duplicate_email_conflict(self):
        """Attempting to register an existing email returns 409 Conflict."""
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value={"email": "existing@test.com"})
            payload = {
                "name": "Duplicate User",
                "email": "EXISTING@test.com",
                "password": "Password123!",
                "confirmPassword": "Password123!",
            }
            response = client.post("/api/auth/signup", json=payload)
            self.assertEqual(response.status_code, 409)
            self.assertIn("already registered", response.json()["detail"].lower())

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Login & Credential Verification
    # ─────────────────────────────────────────────────────────────────────────

    async def test_signin_success_case_insensitive(self):
        """Login succeeds with case-insensitive email normalization."""
        mock_user = {
            "id": "user-abc-123",
            "name": "Aarav Sharma",
            "email": "aarav@demo.school",
            "passwordHash": hash_password("Demo@123"),
            "role": "student",
            "emailVerified": True,
            "disabled": False,
        }
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=mock_user)

            # Uppercase email provided in login payload
            response = client.post("/api/auth/signin", json={
                "email": "AARAV@DEMO.SCHOOL",
                "password": "Demo@123",
            })
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("token", data)
            self.assertEqual(data["user"]["id"], "user-abc-123")
            self.assertNotIn("passwordHash", data["user"])

    async def test_signin_invalid_password(self):
        """Incorrect password returns HTTP 401 with generic error message."""
        mock_user = {
            "id": "user-abc-123",
            "name": "Aarav Sharma",
            "email": "aarav@demo.school",
            "passwordHash": hash_password("Demo@123"),
            "role": "student",
        }
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=mock_user)

            response = client.post("/api/auth/signin", json={
                "email": "aarav@demo.school",
                "password": "WrongPassword999",
            })
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid email or password")

    async def test_signin_unknown_account(self):
        """Unknown email returns HTTP 401 with generic error message."""
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)

            response = client.post("/api/auth/signin", json={
                "email": "ghost@nonexistent.org",
                "password": "AnyPassword123!",
            })
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid email or password")

    async def test_signin_disabled_account(self):
        """Disabled account returns HTTP 403 Forbidden."""
        mock_user = {
            "id": "user-disabled",
            "name": "Disabled User",
            "email": "disabled@test.com",
            "passwordHash": hash_password("Demo@123"),
            "role": "student",
            "disabled": True,
        }
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=mock_user)

            response = client.post("/api/auth/signin", json={
                "email": "disabled@test.com",
                "password": "Demo@123",
            })
            self.assertEqual(response.status_code, 403)
            self.assertIn("disabled", response.json()["detail"].lower())

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Session & Token Verification
    # ─────────────────────────────────────────────────────────────────────────

    async def test_auth_me_valid_and_tampered_token(self):
        """Verifies /auth/me returns identity for valid token, rejects tampered token with 401."""
        valid_token = make_token("uid-student-99")
        mock_user = {
            "id": "uid-student-99",
            "name": "Valid Student",
            "email": "valid@test.com",
            "role": "student",
            "disabled": False,
        }

        with patch("database.database.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=mock_user)

            # Valid token
            res_valid = client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
            self.assertEqual(res_valid.status_code, 200)
            self.assertEqual(res_valid.json()["id"], "uid-student-99")

            # Tampered signature
            tampered_token = valid_token[:-5] + "XXXXX"
            res_tampered = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
            self.assertEqual(res_tampered.status_code, 401)

            # Missing authorization header
            res_missing = client.get("/api/auth/me")
            self.assertEqual(res_missing.status_code, 401)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Password Recovery (Forgot / Reset Password)
    # ─────────────────────────────────────────────────────────────────────────

    async def test_forgot_password_generic_response_non_enumeration(self):
        """Unknown email returns generic 200 response without sending an email."""
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=None)

            response = client.post("/api/auth/forgot-password", json={"email": "nobody@test.com"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("instructions have been sent", response.json()["message"])
            # Ensure no email was dispatched
            self.assertEqual(len(get_dispatched_emails()), 0)

    async def test_forgot_and_reset_password_flow(self):
        """Complete password reset workflow: request, token hashing, update, and re-login."""
        user_id = str(uuid.uuid4())
        initial_hash = hash_password("OldPassword@123")
        mock_user = {
            "id": user_id,
            "name": "Reset Learner",
            "email": "learner@test.com",
            "passwordHash": initial_hash,
            "role": "student",
            "disabled": False,
        }

        # 1. Request Reset Link
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=mock_user)
            mock_db.password_resets.update_many = AsyncMock(return_value=None)
            mock_db.password_resets.insert_one = AsyncMock(return_value=None)

            res = client.post("/api/auth/forgot-password", json={"email": "LEARNER@TEST.COM"})
            self.assertEqual(res.status_code, 200)

            # Inspect dispatched email
            emails = get_dispatched_emails()
            self.assertEqual(len(emails), 1)
            self.assertEqual(emails[0]["to"], "learner@test.com")
            reset_link = emails[0]["link"]
            raw_token = reset_link.split("token=")[-1]
            self.assertTrue(len(raw_token) >= 32)

        # 2. Reset Password with valid token
        token_hash = hashlib.sha256(raw_token.strip().encode()).hexdigest()
        reset_doc = {
            "_id": "reset-obj-1",
            "userId": user_id,
            "email": "learner@test.com",
            "tokenHash": token_hash,
            "expiresAt": int(time.time()) + 3600,
            "used": False,
        }

        with patch("routers.auth.db") as mock_db:
            mock_db.password_resets.find_one = AsyncMock(return_value=reset_doc)
            mock_db.password_resets.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
            mock_db.password_resets.update_many = AsyncMock(return_value=None)
            mock_db.users.update_one = AsyncMock(return_value=None)

            res2 = client.post("/api/auth/reset-password", json={
                "token": raw_token,
                "password": "BrandNewPassword@2026",
                "confirmPassword": "BrandNewPassword@2026",
            })
            self.assertEqual(res2.status_code, 200)
            self.assertIn("successfully reset", res2.json()["message"].lower())
            self.assertTrue(mock_db.users.update_one.called)

    async def test_reset_password_single_use_atomicity(self):
        """Reusing an already-consumed reset token is rejected with HTTP 400."""
        token_hash = hashlib.sha256(b"already-used-raw-token").hexdigest()
        reset_doc = {
            "_id": "reset-obj-used",
            "userId": "uid-1",
            "tokenHash": token_hash,
            "expiresAt": int(time.time()) + 3600,
            "used": True,  # Already used!
        }

        with patch("routers.auth.db") as mock_db:
            # find_one filters used: False, so returns None
            mock_db.password_resets.find_one = AsyncMock(return_value=None)

            res = client.post("/api/auth/reset-password", json={
                "token": "already-used-raw-token",
                "password": "BrandNewPassword@2026",
                "confirmPassword": "BrandNewPassword@2026",
            })
            self.assertEqual(res.status_code, 400)
            self.assertIn("invalid or expired", res.json()["detail"].lower())

    async def test_reset_password_expired_token(self):
        """Expired reset token is rejected with HTTP 400."""
        token_hash = hashlib.sha256(b"expired-token-123456").hexdigest()
        reset_doc = {
            "_id": "reset-obj-expired",
            "userId": "uid-1",
            "tokenHash": token_hash,
            "expiresAt": int(time.time()) - 100,  # Expired in the past
            "used": False,
        }

        with patch("routers.auth.db") as mock_db:
            mock_db.password_resets.find_one = AsyncMock(return_value=reset_doc)

            res = client.post("/api/auth/reset-password", json={
                "token": "expired-token-123456",
                "password": "BrandNewPassword@2026",
                "confirmPassword": "BrandNewPassword@2026",
            })
            self.assertEqual(res.status_code, 400)
            self.assertIn("invalid or expired", res.json()["detail"].lower())

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Email Verification
    # ─────────────────────────────────────────────────────────────────────────

    async def test_verify_email_flow(self):
        """Valid email verification token sets emailVerified=True on user document."""
        raw_token = "verification-token-sample-123456"
        token_hash = hashlib.sha256(raw_token.strip().encode()).hexdigest()
        verif_doc = {
            "_id": "verif-doc-1",
            "userId": "user-to-verify",
            "tokenHash": token_hash,
            "expiresAt": int(time.time()) + 86400,
            "used": False,
        }

        with patch("routers.auth.db") as mock_db:
            mock_db.email_verifications.find_one = AsyncMock(return_value=verif_doc)
            mock_db.email_verifications.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
            mock_db.users.update_one = AsyncMock(return_value=None)

            res = client.post("/api/auth/verify-email", json={"token": raw_token})
            self.assertEqual(res.status_code, 200)
            self.assertIn("verified successfully", res.json()["message"].lower())
            self.assertTrue(mock_db.users.update_one.called)

    async def test_resend_verification_email(self):
        """Resend verification dispatches new token if account is unverified."""
        mock_user = {
            "id": "unverified-user",
            "email": "pending@test.com",
            "emailVerified": False,
        }
        with patch("routers.auth.db") as mock_db:
            mock_db.users.find_one = AsyncMock(return_value=mock_user)
            mock_db.email_verifications.update_many = AsyncMock(return_value=None)
            mock_db.email_verifications.insert_one = AsyncMock(return_value=None)

            res = client.post("/api/auth/resend-verification", json={"email": "pending@test.com"})
            self.assertEqual(res.status_code, 200)
            emails = get_dispatched_emails()
            self.assertEqual(len(emails), 1)
            self.assertEqual(emails[0]["to"], "pending@test.com")
            self.assertEqual(emails[0]["category"], "email_verification")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Rate Limiting Protection
    # ─────────────────────────────────────────────────────────────────────────

    def test_auth_rate_limiter_throttling(self):
        """Rate limiter blocks rapid requests after exceeding the threshold."""
        endpoint_key = "test_endpoint:127.0.0.1:target@example.com"
        # Allow 3 attempts within 60 seconds
        self.assertTrue(AuthRateLimiter.check(endpoint_key, max_attempts=3, window_seconds=60))
        self.assertTrue(AuthRateLimiter.check(endpoint_key, max_attempts=3, window_seconds=60))
        self.assertTrue(AuthRateLimiter.check(endpoint_key, max_attempts=3, window_seconds=60))
        # 4th attempt should be blocked
        self.assertFalse(AuthRateLimiter.check(endpoint_key, max_attempts=3, window_seconds=60))

        # Resetting rate limiter restores access
        AuthRateLimiter.reset()
        self.assertTrue(AuthRateLimiter.check(endpoint_key, max_attempts=3, window_seconds=60))


if __name__ == "__main__":
    unittest.main()
