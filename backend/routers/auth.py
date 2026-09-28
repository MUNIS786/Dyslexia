"""Auth — signup, signin, profile, settings. New users start with zero data."""
import time
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field

from database.database import db, _default_progress, _default_settings
from deps.deps import hash_password, verify_password, make_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupReq(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "student"
    schoolName: Optional[str] = ""
    age: Optional[int] = None
    languages: Optional[List[str]] = ["english"]


class SigninReq(BaseModel):
    email: EmailStr
    password: str


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
    return {k: v for k, v in u.items() if k not in ("passwordHash", "_id")}


@router.post("/signup")
async def signup(req: SignupReq):
    email = req.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered")

    uid = str(uuid.uuid4())
    role = req.role if req.role in ("student", "teacher") else "student"
    classroom_code = f"DA-{uid[:6].upper()}" if role == "teacher" else None
    now = int(time.time())

    user = {
        "id": uid, "name": req.name.strip(), "email": email,
        "passwordHash": hash_password(req.password), "role": role,
        "classroomCode": classroom_code, "schoolName": req.schoolName or "",
        "readingProfile": None, "onboardingComplete": False,
        "languages": req.languages or ["english"],
        "classroomJoined": None,  # student must explicitly join
        "age": req.age,
        "settings": _default_settings(),
        "isDemo": False, "createdAt": now,
    }
    await db.users.insert_one({**user})

    # Teacher gets a classroom record immediately
    if role == "teacher":
        await db.classrooms.insert_one({
            "code": classroom_code, "teacherId": uid,
            "teacherName": req.name.strip(),
            "schoolName": req.schoolName or "",
            "subject": "", "createdAt": now,
        })

    # Initialize empty progress for student
    if role == "student":
        await db.progress.insert_one({"userId": uid, **_default_progress()})

    token = make_token(uid)
    return {"token": token, "user": _pub(user)}


@router.post("/signin")
async def signin(req: SigninReq):
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user["passwordHash"]):
        raise HTTPException(401, "Invalid email or password")
    token = make_token(user["id"])
    return {"token": token, "user": _pub(user)}


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
