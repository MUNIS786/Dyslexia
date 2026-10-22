# DyslexAid V2 — Authentication Architecture Audit & Remediation Plan

**Document Version:** 1.0.0  
**Date:** October 2026  
**Repository:** [https://github.com/MUNIS786/Dyslexia.git](https://github.com/MUNIS786/Dyslexia.git)  
**Branch:** `main`  
**Application:** DyslexAid V2 — Dyslexia-Friendly Universal Accessible Learning Platform  

---

## 1. Executive Summary & Scope

This audit evaluates the end-to-end authentication and session management architecture of DyslexAid V2. DyslexAid is an assistive learning platform serving neurodivergent students, educators, and parents. Authentication must be robust, reliable, cryptographically secure, and accessible, ensuring strict tenant and role isolation without breaking existing V1/V2 features, learning progress, or demo accounts.

### Scope of Audit
- **Backend Components:** FastAPI endpoints (`backend/routers/auth.py`), JWT and cryptography utilities (`backend/deps/deps.py`), configuration (`backend/core/config.py`), database indexes and seeding (`backend/database/database.py`).
- **Frontend Components:** React application router and route guards (`frontend/src/App.jsx`), authentication context (`frontend/src/context/AuthContext.jsx`), API client and interceptors (`frontend/src/api/client.js`), public authentication pages (`frontend/src/pages/auth/AuthPages.jsx`).
- **Session & Security:** Bearer token handling, JWT lifecycle, password hashing parameters, role isolation, brute-force mitigation, and password recovery workflows.

---

## 2. Inventory of Files Involved

| File Path | Role / Purpose | Current Status |
|:---|:---|:---|
| `backend/routers/auth.py` | FastAPI authentication router (`/auth/signup`, `/auth/signin`, `/auth/me`, `/auth/profile`, `/auth/settings`, `/auth/signout`) | Functional baseline; lacks password reset, email verification, confirm-password validation, and rate limiting. |
| `backend/deps/deps.py` | JWT generation/verification (`HS256`, 30-day expiry), bcrypt hashing, `get_current_user`, `require_teacher`, `require_parent` | Secure hashing (`bcrypt`); hardcoded dev fallback secret in non-production; lacks token revocation. |
| `backend/database/database.py` | MongoDB connection, indexes, demo account seeding (`aarav`, `teacher`, `parent@demo.school`) | Unique email and ID indexes created; missing indexes for password reset and email verification tokens. |
| `backend/core/config.py` | Centralized settings, JWT settings, CORS origin configuration, production validation | Contains `validate_production_config` enforcing non-default `JWT_SECRET` in production mode. |
| `frontend/src/context/AuthContext.jsx` | React context providing `user`, `token`, `login`, `logout`, `updateUser`, `updateSettings`, session restoration on boot | Functional; handles token persistence in `localStorage`; lacks explicit `signup` method and password-reset state helpers. |
| `frontend/src/api/client.js` | Axios client with `Authorization: Bearer <token>` injection and 401 response redirect | Functional; clears token and redirects on 401; lacks endpoints for forgot password, reset password, and email verification. |
| `frontend/src/pages/auth/AuthPages.jsx` | `AuthShell`, `LoginPage`, `RegisterPage` components | Well-styled with accessible tokens; missing `confirmPassword` field, password strength meter, forgot-password link and forms. |
| `frontend/src/App.jsx` | Route registration, `ProtectedRoute` with role validation and student screening redirection | Protects `/student/*`, `/teacher/*`, `/parent/*`; missing routes for `/forgot-password`, `/reset-password`, `/verify-email`. |

---

## 3. Current Architecture & Mechanism Analysis

### 3.1 Session Mechanism: Bearer Token in `localStorage`
- **Current Flow:** Upon successful login or registration, the backend returns `{ "token": "<jwt>", "user": {...} }`. The frontend stores the token under `localStorage.getItem('dyslexaid_token')` and sends it in the `Authorization: Bearer <token>` header for subsequent requests.
- **Why Bearer Token is Maintained:**
  - The local development environment operates on split origins (Frontend: Vite on `http://localhost:5173`; Backend: FastAPI on `http://localhost:8000`).
  - Production deployments may use separate static CDN/storage for the SPA and containerized microservices for the API.
  - Browser third-party cookie restrictions (SameSite=None, Safari ITP, partitioned storage) often disrupt cross-origin cookies in educational and school Chromebook environments.
  - **Verdict:** Maintain the Bearer token contract for complete compatibility with the current frontend SPA, mobile/offline clients, and existing automated tests, while strengthening backend token verification, expiration, and rate limiting.

### 3.2 Role-Based Access Control (RBAC)
- **Roles Supported:** `student`, `teacher`, `parent`.
- **Registration Security:**
  - `SignupReq` validates role against `("student", "teacher", "parent")`. If any other role (e.g. `admin`, `superuser`) is supplied, it defaults safely to `student`.
  - Self-elevation to `admin` is prevented at the schema level.
- **Route Guards & Backend Authorization:**
  - Frontend `ProtectedRoute` redirects unauthorized roles (e.g., student accessing `/teacher` is redirected to `/student`).
  - Backend endpoints strictly check roles independently using FastAPI dependencies (`require_teacher`, `require_parent`, `get_current_user`).

### 3.3 Seeded & Demo Accounts
- Seeded accounts:
  - Teacher: `teacher@demo.school` / `Demo@123`
  - Students: `aarav@demo.school`, `priya@demo.school`, `ravi@demo.school`, `sneha@demo.school` / `Demo@123`
  - Parent: `parent@demo.school` / `Demo@123`
- Database seeding in `backend/database/database.py` is idempotent and safe against race conditions.

---

## 4. Deficiencies, Vulnerabilities & Gaps Identified

### 4.1 Missing Password Confirmation & Weak Password Policy
- `SignupReq` requires `password: str = Field(min_length=6)`.
- Frontend `RegisterPage` only requires `password` with no `confirmPassword` field, creating risks of user lockout due to typos during registration.
- No server-side complexity or character diversity requirement is enforced.

### 4.2 Complete Lack of Password Recovery (Forgot / Reset Password)
- No `Forgot password?` link on the `LoginPage`.
- No backend endpoints for `/auth/forgot-password` or `/auth/reset-password`.
- If a real user forgets their password, they have no recovery mechanism other than manual database intervention.

### 4.3 Missing Account Verification (Email Verification)
- Accounts are immediately active upon registration.
- No tokenized verification mechanism or email verification flow exists.
- In educational environments, unverified emails allow spam registrations.

### 4.4 Lack of Rate Limiting on Authentication Endpoints
- `/auth/signin`, `/auth/signup`, and `/auth/login` have no request rate limiting or brute-force throttling.
- An attacker can execute automated dictionary or credential stuffing attacks against student or teacher accounts.

### 4.5 Email Case Normalization & Database Collations
- While `auth.py` normalizes emails with `.lower().strip()`, MongoDB index on `users.email` is default binary collation without case-insensitive collation (`collation={'locale': 'en', 'strength': 2}`).
- In addition, new collections `password_resets` and `email_verifications` require indexed expiration times (TTL indexes) to automatically purge expired tokens.

---

## 5. Remediation & Implementation Plan

### Phase 2: Registration Hardening
1. Add `confirmPassword` to `SignupReq` with validator ensuring `password == confirmPassword`.
2. Strengthen password policy: minimum 8 characters, requiring at least one letter and one number or special character.
3. Update `RegisterPage`:
   - Add `confirmPassword` input field with real-time match validation.
   - Add password visibility toggle for both password fields.
   - Add password strength and requirements checklist.
   - Add field-level error messages and submit button disabled state during loading.

### Phase 3: Login Hardening
1. Add case-insensitive email normalization on all login endpoints.
2. Ensure generic, safe error message: `"Invalid email or password"`.
3. Support redirect to intended destination (read `location.state?.from`).
4. Add "Forgot password?" link on `LoginPage`.

### Phase 4: Session Security & Rate Limiting
1. Implement in-memory sliding-window rate limiter for auth endpoints (`/auth/signin`, `/auth/signup`, `/auth/forgot-password`).
2. Add security headers and token integrity checks.
3. Expose `signup` method in `AuthContext` to streamline session initialization post-registration.

### Phase 5: Complete Password Recovery Flow
1. Backend `/auth/forgot-password`:
   - Accepts email, returns generic success response to prevent user enumeration.
   - Generates cryptographically secure token (`secrets.token_urlsafe(32)`).
   - Stores SHA-256 hash of token in `db.password_resets` with 1-hour expiration and `used: False`.
   - Supports pluggable email dispatch (console/logger in dev/test, SMTP in production).
2. Backend `/auth/reset-password`:
   - Validates token hash, checks expiration and `used: False`.
   - Hashes new password with bcrypt and updates `users` collection.
   - Marks token `used: True` and invalidates any other active reset tokens for that user.
3. Frontend:
   - Create and export `ForgotPasswordPage` (`/forgot-password`).
   - Create and export `ResetPasswordPage` (`/reset-password?token=...`).
   - Add routes in `App.jsx`.

### Phase 6: Email Verification Flow
1. Add `emailVerified` flag on user records (seeded demo users default to `True`).
2. Backend `/auth/verify-email` and `/auth/resend-verification`.
3. Single-use verification tokens stored with 24-hour expiration.
4. Frontend `VerifyEmailPage` (`/verify-email?token=...`).

### Phase 7 & 8: Design System Integration
1. Apply DyslexAid indigo/slate styling, OpenDyslexic font support, and accessible form controls.
2. Keyboard navigation (`Tab`, `Enter`, `Space`) on all interactive buttons.
3. ARIA labels and alerts.

### Phase 9: Automated Testing
1. Add `backend/test_auth_production.py` covering all new authentication endpoints, edge cases, rate limiting, and failure modes.
2. Verify full backend regression suite (`pytest backend/ -v --tb=short`).
3. Verify frontend lint (`npm run lint`) and production build (`npm run build`).
4. Run `python scripts/verify_release.py`.
