# DyslexAid V2 — Production-Ready Authentication Implementation Guide

**Document Version:** 2.0.0  
**Date:** October 2026  
**Repository:** [https://github.com/MUNIS786/Dyslexia.git](https://github.com/MUNIS786/Dyslexia.git)  
**Branch:** `main`  
**Status:** Implemented, Verified, and Production-Ready  

---

## 1. Executive Summary

DyslexAid V2 has transitioned from a baseline authentication system to an enterprise-grade, production-ready authentication and identity management architecture. The system connects the frontend React SPA, FastAPI backend, and MongoDB database with rigorous cryptographic verification, user enumeration prevention, brute-force rate limiting, password recovery, and email verification.

All existing DyslexAid V1/V2 features, role permissions (`student`, `teacher`, `parent`), demo accounts (`aarav@demo.school`, `teacher@demo.school`, `parent@demo.school`), learning progress, and design system tokens are preserved.

---

## 2. Implemented Workflows & Features

### 2.1 Registration Workflow (`POST /api/auth/signup`)
- **Required Fields & Validation:**
  - `name`: Minimum 2 non-whitespace characters.
  - `email`: Normalized to lowercase, stripped, and validated against standard email format (`EmailStr`).
  - `password`: Enforces minimum 8 characters, at least one letter (`[A-Za-z]`), and at least one number or special character (`[\d\W_]`).
  - `confirmPassword`: Verified server-side and client-side to strictly match `password`.
  - `role`: Restricted to `("student", "teacher", "parent")`. Any attempt to supply `admin`, `superuser`, or other roles defaults safely to `student`, preventing privilege escalation.
- **Duplicate Prevention & Concurrency:**
  - Normalizes email before database query.
  - Catches MongoDB `DuplicateKeyError` (E11000) on concurrent registration attempts and safely returns HTTP 409 Conflict with `"Email already registered"`.
- **User Record Initialization:**
  - Password hashed using `bcrypt.hashpw` with per-user salt.
  - Generates unique UUID identifier (`id`).
  - Teachers automatically receive a classroom code (`DA-XXXXXX`) and record in `db.classrooms`.
  - Students automatically receive initialized empty learning progress in `db.progress`.
  - Sensitive fields (`passwordHash`, `_id`) are never exposed in API responses.
- **Email Verification Dispatch:**
  - Generates a cryptographically random 32-byte token (`secrets.token_urlsafe(32)`).
  - Stores a SHA-256 hash in `db.email_verifications` with 24-hour expiration.
  - Dispatches verification link via `EmailService`.

### 2.2 Login Workflow (`POST /api/auth/signin` & `/api/auth/login`)
- **Case-Insensitive Email Normalization:** Normalizes input email via `.lower().strip()` before database lookup.
- **Bcrypt Verification:** Uses `bcrypt.checkpw` against stored hash.
- **Account Status Verification:**
  - Checks `user.get("disabled", False)`; if disabled, returns HTTP 403 Forbidden.
  - If `REQUIRE_EMAIL_VERIFICATION` is enabled and user is unverified, returns HTTP 403 Forbidden.
- **User Enumeration Protection:** Returns generic HTTP 401 Unauthorized (`"Invalid email or password"`) for both unknown accounts and incorrect passwords.
- **Rate Limiting:** Protects against credential-stuffing attacks with sliding-window limit (10 attempts per minute per IP and email).
- **Session Restoration & Redirect:**
  - Returns `{ "token": "<jwt>", "user": _pub(user) }`.
  - Frontend records token in `localStorage` under `dyslexaid_token`.
  - Redirects user to intended destination (`location.state?.from`) or role-based portal (`/teacher`, `/parent/dashboard`, `/student`).

### 2.3 Password Recovery Workflow
1. **Forgot Password Request (`POST /api/auth/forgot-password`):**
   - Rate-limited to 5 requests per 15 minutes per IP and email.
   - Always returns generic success response: `"If an account with that email exists, password reset instructions have been sent."` (Zero user enumeration).
   - If account exists:
     - Invalidates prior unused reset tokens.
     - Generates 32-byte cryptographically secure token.
     - Hashes token with SHA-256 before storing in `db.password_resets` with 1-hour expiration and `used: False`.
     - Dispatches reset link (`{FRONTEND_URL}/reset-password?token={token}`) via `EmailService`.
2. **Password Reset Execution (`POST /api/auth/reset-password`):**
   - Accepts raw `token`, `password`, and `confirmPassword`.
   - Validates new password strength and matching confirmation.
   - Computes SHA-256 hash and verifies against `db.password_resets`.
   - Checks expiration (`expiresAt > now`) and single-use state (`used == False`).
   - Atomically updates token record (`used: True`) using MongoDB `update_one` to prevent race conditions or token reuse.
   - Hashes new password with bcrypt and updates `users` document.
   - Invalidates any other pending reset tokens for that user.

### 2.4 Email Verification Workflow
- **Verification Endpoint (`POST /api/auth/verify-email`):**
  - Validates SHA-256 token hash against `db.email_verifications`.
  - Atomically marks token `used: True`.
  - Sets `emailVerified: True` on the user's document.
- **Resend Verification (`POST /api/auth/resend-verification`):**
  - Rate-limited endpoint allowing users to request a fresh verification link if the original expired.
- **Safe Migration for Existing Accounts:**
  - Automatic database migration in `database.py` backfills `emailVerified: True` on all existing records.
  - Seeded demo users (`aarav`, `teacher`, `parent`, etc.) are explicitly seeded with `emailVerified: True`.

### 2.5 Brute-Force Rate Limiting (`backend/services/auth_rate_limiter.py`)
- Thread-safe in-memory sliding window rate limiter.
- Configurable thresholds per endpoint and composite identifier:
  - Signin / Login: 10 attempts / 60 seconds.
  - Signup: 5 attempts / 60 seconds.
  - Forgot Password: 5 requests / 900 seconds (15 minutes).
  - Reset Password & Email Verification: 10 attempts / 60 seconds.
- Automatically releases window as time elapses.

### 2.6 Email Dispatch Infrastructure (`backend/services/email_service.py`)
- Pluggable provider system configured via environment variables:
  - `console`: Default in development and test environments. Dispatches formatted links to standard logging without exposing credentials, and records sent messages in-memory for automated test verification.
  - `smtp`: Production-ready MIME email delivery using `smtplib` with STARTTLS and authentication.
  - `mock`: Test isolation provider.

---

## 3. Frontend Architecture & User Experience

| Page / Component | Route | Description & Features |
|:---|:---|:---|
| `LoginPage` | `/login` | Email and password inputs, password visibility toggle, "Forgot password?" recovery link, submit loading indicator, automatic redirect to intended route after authentication. |
| `RegisterPage` | `/register` | Full name, email, password, confirm password, password visibility toggles, interactive password requirements checklist (8+ chars, letters, numbers/symbols, matching), role selection (`Student`, `Teacher`, `Parent`), optional school/age fields. |
| `ForgotPasswordPage` | `/forgot-password` | Clean form to request password recovery, confirmation state with clear instructions and return-to-signin navigation. |
| `ResetPasswordPage` | `/reset-password` | Extracts `?token=...`, validates new password and confirmation, submits update to backend, displays success confirmation leading back to signin. |
| `VerifyEmailPage` | `/verify-email` | Automatically verifies token from URL query parameters, displays loading/success states, and provides resend verification form if token expired. |
| `AuthContext` | Global Provider | Provides `user`, `token`, `login`, `signup`, `logout`, `updateUser`, `updateSettings`. Initializes session on application boot by calling `/api/auth/me`. |
| `client.js` | Axios Client | Global request interceptor injects `Authorization: Bearer <token>`; response interceptor clears token and redirects to `/login` on 401 (excluding public auth routes). |

---

## 4. API Reference

### `POST /api/auth/signup`
**Request Body:**
```json
{
  "name": "Aarav Sharma",
  "email": "aarav.sharma@example.com",
  "password": "Password123!",
  "confirmPassword": "Password123!",
  "role": "student",
  "schoolName": "Greenwood High",
  "age": 10
}
```
**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "e4b3c2a1-...",
    "name": "Aarav Sharma",
    "email": "aarav.sharma@example.com",
    "role": "student",
    "schoolName": "Greenwood High",
    "emailVerified": true,
    "onboardingComplete": false
  },
  "requiresVerification": false
}
```

### `POST /api/auth/signin`
**Request Body:**
```json
{
  "email": "aarav@demo.school",
  "password": "Demo@123"
}
```
**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "...",
    "name": "Aarav Sharma",
    "email": "aarav@demo.school",
    "role": "student"
  }
}
```

### `POST /api/auth/forgot-password`
**Request Body:**
```json
{
  "email": "aarav@demo.school"
}
```
**Response (200 OK):**
```json
{
  "status": "ok",
  "message": "If an account with that email exists, password reset instructions have been sent."
}
```

### `POST /api/auth/reset-password`
**Request Body:**
```json
{
  "token": "<raw_token_from_email>",
  "password": "NewSecurePassword456!",
  "confirmPassword": "NewSecurePassword456!"
}
```
**Response (200 OK):**
```json
{
  "status": "ok",
  "message": "Your password has been successfully reset. You can now sign in with your new password."
}
```

### `POST /api/auth/verify-email`
**Request Body:**
```json
{
  "token": "<raw_token_from_email>"
}
```
**Response (200 OK):**
```json
{
  "status": "ok",
  "message": "Your email address has been verified successfully. You may now continue using DyslexAid."
}
```

---

## 5. Security & Production Checklist

1. **Production Secret Generation:**
   Set a cryptographically strong secret in production `.env`:
   ```bash
   JWT_SECRET=$(openssl rand -hex 32)
   ```
2. **CORS Whitelist:**
   Ensure `CORS_ORIGINS` contains explicit domains without wildcards in production:
   ```env
   CORS_ORIGINS=https://app.dyslexaid.org,https://dyslexaid.org
   ```
3. **Email SMTP Setup:**
   Configure a production SMTP relay provider (e.g., Mailgun, SendGrid, Amazon SES):
   ```env
   EMAIL_PROVIDER=smtp
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USER=postmaster@dyslexaid.org
   SMTP_PASSWORD=your_smtp_password
   EMAIL_FROM=DyslexAid <noreply@dyslexaid.org>
   FRONTEND_URL=https://app.dyslexaid.org
   ```
4. **Enforcing Email Verification (Optional):**
   To require verification before users can log in:
   ```env
   REQUIRE_EMAIL_VERIFICATION=true
   ```

---

## 6. Verification & Automated Test Results

- **New Production Authentication Suite:** 17/17 tests passed (`backend/test_auth_production.py`).
- **Full Backend Regression Suite:** 441/441 tests passed (`pytest backend/`).
- **Frontend ESLint:** 0 errors, 0 warnings (`npm run lint`).
- **Frontend Production Build:** Built cleanly in 3.23s (`npm run build`).
- **Reproducible Release Check:** Passed with exit code 0 (`python scripts/verify_release.py`).
