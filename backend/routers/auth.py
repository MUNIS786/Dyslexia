"""
Auth — Production-ready signup, signin, password recovery, email verification, profile, and settings.
Connects frontend, backend, database (MongoDB), and role-based access control.
"""
import hashlib
import re
import secrets
import time
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, Request, status
from pydantic import BaseModel, EmailStr, Field, model_validator
from pymongo.errors import DuplicateKeyError

from core.config import settings
from database.database import db, _default_progress, _default_settings
from deps.deps import hash_password, verify_password, make_token, get_current_user
from services.email_service import EmailService
from services.auth_rate_limiter import enforce_rate_limit
from services.account_deletion_service import execute_account_deletion

router = APIRouter(prefix="/auth", tags=["auth"])


def _validate_password_strength(pw: str) -> None:
    if len(pw) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", pw):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"[\d\W_]", pw):
        raise ValueError("Password must contain at least one number or special character.")


class SignupReq(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)
    confirmPassword: Optional[str] = None
    role: str = "student"
    schoolName: Optional[str] = ""
    age: Optional[int] = None
    languages: Optional[List[str]] = ["english"]

    @model_validator(mode="after")
    def validate_signup(self):
        if not self.name.strip():
            raise ValueError("Full name cannot be empty.")
        _validate_password_strength(self.password)
        if self.confirmPassword is not None and self.confirmPassword != self.password:
            raise ValueError("Passwords do not match.")
        return self


class SigninReq(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordReq(BaseModel):
    email: EmailStr


class ResetPasswordReq(BaseModel):
    token: str = Field(min_length=16)
    password: str = Field(min_length=8)
    confirmPassword: Optional[str] = None

    @model_validator(mode="after")
    def validate_reset(self):
        _validate_password_strength(self.password)
        if self.confirmPassword is not None and self.confirmPassword != self.password:
            raise ValueError("Passwords do not match.")
        return self


class VerifyEmailReq(BaseModel):
    token: str = Field(min_length=16)


class ResendVerificationReq(BaseModel):
    email: EmailStr


class DeleteAccountReq(BaseModel):
    password: str = Field(..., min_length=1, description="Current password for identity reauthentication")
    confirmation: Optional[str] = Field(None, description="Must be exactly 'DELETE_MY_ACCOUNT'")


class ProfilePatch(BaseModel):
    readingProfile: Optional[dict] = None
    onboardingComplete: Optional[bool] = None
    languages: Optional[List[str]] = None
    schoolName: Optional[str] = None
    age: Optional[int] = None


class SettingsPatch(BaseModel):
    font: Optional[str] = None
    fontSize: Optional[int] = None
    lineSpacing: Optional[float] = None
    letterSpacing: Optional[float] = None
    bgColor: Optional[str] = None
    textColor: Optional[str] = None
    ttsSpeed: Optional[float] = None
    ttsLanguage: Optional[str] = None
    highlightWords: Optional[bool] = None
    showBulletPoints: Optional[bool] = None
    autoSimplify: Optional[bool] = None


def _pub(u: dict) -> dict:
    """Sanitize user record to never expose password hashes or database internal IDs."""
    sensitive_keys = ("passwordHash", "_id", "resetTokenHash", "verificationTokenHash")
    return {k: v for k, v in u.items() if k not in sensitive_keys}


@router.post("/signup")
async def signup(req: SignupReq, request: Request):
    # Enforce registration rate limit (5 signups per minute per IP)
    enforce_rate_limit(request, endpoint="signup", max_attempts=5, window_seconds=60)

    email = req.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    uid = str(uuid.uuid4())
    # Explicit role validation: only student, teacher, or parent allowed; never admin
    role = req.role if req.role in ("student", "teacher", "parent") else "student"
    classroom_code = f"DA-{uid[:6].upper()}" if role == "teacher" else None
    now = int(time.time())

    # In production with verification required, new non-demo users start unverified
    email_verified = False if settings.REQUIRE_EMAIL_VERIFICATION else True

    user = {
        "id": uid,
        "name": req.name.strip(),
        "email": email,
        "passwordHash": hash_password(req.password),
        "role": role,
        "classroomCode": classroom_code,
        "schoolName": (req.schoolName or "").strip(),
        "readingProfile": None,
        "onboardingComplete": False,
        "languages": req.languages or ["english"],
        "classroomJoined": None,  # student must explicitly join
        "age": req.age,
        "settings": _default_settings(),
        "emailVerified": email_verified,
        "disabled": False,
        "token_version": 1,
        "deletionState": None,
        "isDemo": False,
        "createdAt": now,
    }

    try:
        await db.users.insert_one({**user})
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Teacher gets a classroom record immediately
    if role == "teacher":
        await db.classrooms.insert_one({
            "code": classroom_code,
            "teacherId": uid,
            "teacherName": req.name.strip(),
            "schoolName": (req.schoolName or "").strip(),
            "subject": "",
            "createdAt": now,
        })

    # Initialize empty progress for student
    if role == "student":
        await db.progress.insert_one({"userId": uid, **_default_progress()})

    # Generate and send email verification token
    raw_verif_token = secrets.token_urlsafe(32)
    verif_hash = hashlib.sha256(raw_verif_token.encode()).hexdigest()
    await db.email_verifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": uid,
        "email": email,
        "tokenHash": verif_hash,
        "expiresAt": now + 86400,  # 24 hours
        "used": False,
        "createdAt": now,
    })
    EmailService.send_verification_email(email, raw_verif_token)

    token = make_token(uid, user.get("token_version", 1))
    return {
        "token": token,
        "user": _pub(user),
        "requiresVerification": not email_verified,
    }


@router.post("/signin")
@router.post("/login")
async def signin(req: SigninReq, request: Request):
    email = req.email.lower().strip()
    # Rate limit by IP and normalized email: 10 attempts per minute
    enforce_rate_limit(request, endpoint="signin", identifier=email, max_attempts=10, window_seconds=60)

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user.get("passwordHash", "")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if user.get("disabled", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account has been disabled. Please contact support.")

    if settings.REQUIRE_EMAIL_VERIFICATION and not user.get("emailVerified", False):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Please verify your email address before signing in. Check your inbox for the verification link.",
        )

    token = make_token(user["id"], user.get("token_version", 1))
    return {"token": token, "user": _pub(user)}


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordReq, request: Request):
    email = req.email.lower().strip()
    # Rate limit: 5 requests per 15 minutes per IP/email
    enforce_rate_limit(request, endpoint="forgot_password", identifier=email, max_attempts=5, window_seconds=900)

    # Generic response message returned unconditionally to prevent user enumeration
    generic_success = {
        "status": "ok",
        "message": "If an account with that email exists, password reset instructions have been sent.",
    }

    user = await db.users.find_one({"email": email})
    if not user:
        return generic_success

    now = int(time.time())
    # Invalidate existing unused tokens for this user
    await db.password_resets.update_many(
        {"userId": user["id"], "used": False},
        {"$set": {"used": True, "invalidatedAt": now}},
    )

    # Generate single-use, cryptographically random 32-byte token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    await db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "email": email,
        "tokenHash": token_hash,
        "expiresAt": now + 3600,  # 1-hour expiry
        "used": False,
        "createdAt": now,
    })

    EmailService.send_password_reset_email(email, raw_token)
    return generic_success


@router.post("/reset-password")
async def reset_password(req: ResetPasswordReq, request: Request):
    enforce_rate_limit(request, endpoint="reset_password", max_attempts=10, window_seconds=60)

    token_hash = hashlib.sha256(req.token.strip().encode()).hexdigest()
    now = int(time.time())

    reset_record = await db.password_resets.find_one({"tokenHash": token_hash, "used": False})
    if not reset_record or reset_record.get("expiresAt", 0) < now:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired password reset link. Please request a new link.",
        )

    # Atomic consumption check: ensure token cannot be re-used concurrently
    res = await db.password_resets.update_one(
        {"_id": reset_record["_id"], "used": False},
        {"$set": {"used": True, "usedAt": now}},
    )
    if res.modified_count == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Password reset link has already been used.",
        )

    # Hash new password with bcrypt and update user record
    new_hash = hash_password(req.password)
    await db.users.update_one(
        {"id": reset_record["userId"]},
        {"$set": {"passwordHash": new_hash, "updatedAt": now}},
    )

    # Invalidate any other remaining reset tokens for this user
    await db.password_resets.update_many(
        {"userId": reset_record["userId"], "used": False},
        {"$set": {"used": True, "invalidatedAt": now}},
    )

    return {
        "status": "ok",
        "message": "Your password has been successfully reset. You can now sign in with your new password.",
    }


@router.post("/verify-email")
async def verify_email(req: VerifyEmailReq, request: Request):
    enforce_rate_limit(request, endpoint="verify_email", max_attempts=10, window_seconds=60)

    token_hash = hashlib.sha256(req.token.strip().encode()).hexdigest()
    now = int(time.time())

    verif_record = await db.email_verifications.find_one({"tokenHash": token_hash, "used": False})
    if not verif_record or verif_record.get("expiresAt", 0) < now:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired email verification link. Please request a new verification email.",
        )

    # Atomic single-use consumption
    res = await db.email_verifications.update_one(
        {"_id": verif_record["_id"], "used": False},
        {"$set": {"used": True, "verifiedAt": now}},
    )
    if res.modified_count == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Email verification link has already been used.",
        )

    await db.users.update_one(
        {"id": verif_record["userId"]},
        {"$set": {"emailVerified": True, "updatedAt": now}},
    )

    return {
        "status": "ok",
        "message": "Your email address has been verified successfully. You may now continue using DyslexAid.",
    }


@router.post("/resend-verification")
async def resend_verification(req: ResendVerificationReq, request: Request):
    email = req.email.lower().strip()
    enforce_rate_limit(request, endpoint="resend_verification", identifier=email, max_attempts=5, window_seconds=900)

    generic_response = {
        "status": "ok",
        "message": "If the account exists and is pending verification, a new link has been sent.",
    }

    user = await db.users.find_one({"email": email})
    if not user or user.get("emailVerified", False):
        return generic_response

    now = int(time.time())
    await db.email_verifications.update_many(
        {"userId": user["id"], "used": False},
        {"$set": {"used": True, "invalidatedAt": now}},
    )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    await db.email_verifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "email": email,
        "tokenHash": token_hash,
        "expiresAt": now + 86400,
        "used": False,
        "createdAt": now,
    })

    EmailService.send_verification_email(email, raw_token)
    return generic_response


@router.get("/me")
async def me(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    return user


@router.patch("/profile")
async def update_profile(patch: ProfilePatch, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    update = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
    if update:
        await db.users.update_one({"id": user["id"]}, {"$set": update})
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "passwordHash": 0})


@router.patch("/settings")
async def update_settings(patch: SettingsPatch, authorization: Optional[str] = Header(None)):
    """Update accessibility settings (font, TTS speed, colors, etc.)"""
    user = await get_current_user(authorization)
    update = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
    if update:
        set_doc = {f"settings.{k}": v for k, v in update.items()}
        await db.users.update_one({"id": user["id"]}, {"$set": set_doc})
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "passwordHash": 0})


@router.post("/signout")
async def signout():
    return {"status": "signed out"}


@router.post("/delete-account")
async def delete_account(
    req: DeleteAccountReq,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Permanently deletes the authenticated user's account and all associated personal data.
    Requires current password for identity reauthentication and confirmation phrase 'DELETE_MY_ACCOUNT'.
    Target user is strictly derived from the authenticated identity.
    """
    enforce_rate_limit(request, endpoint="delete_account", max_attempts=5, window_seconds=60)
    user = await get_current_user(authorization)
    result = await execute_account_deletion(
        user_id=user["id"],
        password=req.password,
        confirmation=req.confirmation,
    )
    return result
