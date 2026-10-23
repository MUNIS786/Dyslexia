"""Shared dependencies — JWT auth, password hashing."""
import os
import time
import bcrypt
import jwt as pyjwt
from fastapi import Header, HTTPException, status, Depends
from typing import Optional, Any, Union
from core.config import settings

JWT_ALG = "HS256"
JWT_EXP_DAYS = 30


def get_jwt_secret() -> str:
    return getattr(settings, "JWT_SECRET", os.environ.get("JWT_SECRET", "dyslexaid-dev-secret-change-in-prod"))


JWT_SECRET = get_jwt_secret()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id: str, token_version: int = 1) -> str:
    payload = {
        "sub": user_id,
        "token_version": token_version,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 24 * JWT_EXP_DAYS,
    }
    return pyjwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALG)


def verify_token_payload(token: str) -> Optional[dict]:
    try:
        payload = pyjwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALG])
        return payload
    except Exception:
        return None


def verify_token(token: str) -> Optional[str]:
    payload = verify_token_payload(token)
    return payload["sub"] if payload and "sub" in payload else None


async def get_current_user_optional(authorization: Optional[str] = Header(None)):
    """Returns user doc or None; never raises."""
    from database.database import db
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    payload = verify_token_payload(token)
    if not payload or not payload.get("sub"):
        return None
    uid = payload["sub"]
    user = await db.users.find_one({"id": uid}, {"_id": 0, "passwordHash": 0})
    if not user:
        return None
    user["_token_version"] = payload.get("token_version", 1)
    return user


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Returns user doc or raises 401/403."""
    user = await get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if user.get("disabled", False) or user.get("deletionState") in ("pending", "deleted"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token_v = user.get("_token_version", 1)
    db_token_v = user.get("token_version", 1)
    if db_token_v > token_v:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")
    return user


async def require_teacher(user: Any = Depends(get_current_user)):
    if isinstance(user, str) or user is None:
        user = await get_current_user(user)
    if not isinstance(user, dict) or user.get("role") != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required")
    return user


async def require_parent(user: Any = Depends(get_current_user)):
    if isinstance(user, str) or user is None:
        user = await get_current_user(user)
    if not isinstance(user, dict) or user.get("role") != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent role required")
    return user
