"""Shared dependencies — JWT auth, password hashing."""
import os
import time
import bcrypt
import jwt as pyjwt
from fastapi import Header, HTTPException, status, Depends
from typing import Optional

JWT_SECRET = os.environ.get("JWT_SECRET", "dyslexaid-dev-secret-change-in-prod")
JWT_ALG = "HS256"
JWT_EXP_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 24 * JWT_EXP_DAYS,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def verify_token(token: str) -> Optional[str]:
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload["sub"]
    except Exception:
        return None


async def get_current_user_optional(authorization: Optional[str] = Header(None)):
    """Returns user doc or None; never raises."""
    from database.database import db
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    uid = verify_token(token)
    if not uid:
        return None
    user = await db.users.find_one({"id": uid}, {"_id": 0, "passwordHash": 0})
    return user


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Returns user doc or raises 401."""
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


async def require_teacher(user: dict = Depends(get_current_user)):
    if user.get("role") != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required")
    return user


async def require_parent(user: dict = Depends(get_current_user)):
    if user.get("role") != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent role required")
    return user
