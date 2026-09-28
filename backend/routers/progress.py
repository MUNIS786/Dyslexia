"""
Progress tracking — streak, session, comprehension, words, daily tasks.
Also handles adaptive profile updates: as student improves, profile updates.
"""
import datetime
import time
from typing import Optional
from fastapi import APIRouter, Header
from pydantic import BaseModel

from database.database import db, _default_progress
from deps.deps import get_current_user

router = APIRouter(tags=["progress"])


class ComprehensionReq(BaseModel):
    score: int


class ScanProgressReq(BaseModel):
    wordCount: int
    title: Optional[str] = ""


class WordReq(BaseModel):
    word: str


class SessionEndReq(BaseModel):
    durationMinutes: Optional[float] = 0


def _weekday():
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][datetime.datetime.now().weekday()]


def _today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


async def _load(uid: str) -> dict:
    prog = await db.progress.find_one({"userId": uid}, {"_id": 0})
    if not prog:
        prog = {"userId": uid, **_default_progress()}
        await db.progress.insert_one({**prog})
    return prog


async def _save(uid: str, data: dict):
    data.pop("_id", None)
    await db.progress.update_one({"userId": uid}, {"$set": data}, upsert=True)


def _update_streak(prog: dict) -> dict:
    today = _today()
    last = prog.get("lastActiveDate")
    streak = prog.get("streak", 0)
    if last == today:
        pass
    elif last:
        try:
            diff = (datetime.datetime.now() - datetime.datetime.strptime(last, "%Y-%m-%d")).days
            streak = streak + 1 if diff == 1 else 1
        except Exception:
            streak = 1
    else:
        streak = 1
    prog["streak"] = streak
    prog["lastActiveDate"] = today
    return prog


async def _maybe_adapt_profile(uid: str, prog: dict):
    """
    Adaptive profile: if comprehension has improved significantly,
    update the user's readingProfile level and trigger plan re-adaptation.
    """
    scores = prog.get("comprehensionScores", [])
    if len(scores) < 5:
        return  # not enough data yet

    recent_avg = round(sum(scores[-5:]) / 5)
    user = await db.users.find_one({"id": uid}, {"_id": 0, "readingProfile": 1})
    if not user:
        return
    rp = user.get("readingProfile")
    if not rp:
        return

    current_level = rp.get("level", "moderate")
    new_level = current_level

    if recent_avg >= 80 and current_level in ("high", "moderate"):
        new_level = "low" if current_level == "moderate" else "moderate"
    elif recent_avg >= 65 and current_level == "high":
        new_level = "moderate"

    if new_level != current_level:
        await db.users.update_one(
            {"id": uid},
            {"$set": {
                "readingProfile.level": new_level,
                "readingProfile.lastUpdated": int(time.time()),
                "readingProfile.previousLevel": current_level,
            }}
        )
        await db.notifications.insert_one({
            "id": __import__("uuid").uuid4().__str__(),
            "userId": uid,
            "title": "Great Progress! 🎉",
            "message": f"Your reading level improved from {current_level} to {new_level}! Your plan has been updated.",
            "type": "profile_update",
            "read": False, "createdAt": int(time.time()),
        })
        # Mark plan for re-adaptation
        await db.ai_plans.update_one(
            {"userId": uid},
            {"$set": {"needsAdaptation": True, "adaptationReason": "level_improved"}},
        )


@router.get("/progress")
async def get_progress(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    prog.pop("_id", None)
    return prog


@router.post("/progress/session-start")
async def session_start(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    prog = _update_streak(prog)
    prog["sessionCount"] = (prog.get("sessionCount") or 0) + 1
    wa = prog.get("weeklyActivity") or {}
    key = _weekday()
    wa[key] = (wa.get(key) or 0) + 1
    prog["weeklyActivity"] = wa
    await _save(user["id"], prog)
    return {"streak": prog["streak"], "sessionCount": prog["sessionCount"], "weeklyActivity": prog["weeklyActivity"]}


@router.post("/progress/session-end")
async def session_end(req: SessionEndReq, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    prog["totalTimeMinutes"] = round((prog.get("totalTimeMinutes") or 0) + (req.durationMinutes or 0), 1)
    prog["hoursReading"] = round(prog["totalTimeMinutes"] / 60, 1)
    await _save(user["id"], prog)
    return {"totalTimeMinutes": prog["totalTimeMinutes"], "hoursReading": prog["hoursReading"]}


@router.post("/progress/comprehension")
async def record_comprehension(req: ComprehensionReq, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    scores = (prog.get("comprehensionScores") or [])[-9:]
    scores.append(max(0, min(100, int(req.score))))
    prog["comprehensionScores"] = scores
    prog["avgComprehension"] = round(sum(scores) / len(scores)) if scores else 0
    act = prog.get("recentActivity", [])
    act.insert(0, {"icon": "check", "text": f"Quiz completed — {req.score}%", "time": "Just now"})
    prog["recentActivity"] = act[:10]
    await _save(user["id"], prog)
    # Check if profile level should update
    await _maybe_adapt_profile(user["id"], prog)
    return {"avgComprehension": prog["avgComprehension"], "scores": scores}


@router.post("/progress/scan")
async def record_scan(req: ScanProgressReq, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    prog["docsScanned"] = (prog.get("docsScanned") or 0) + 1
    prog["wordsRead"] = (prog.get("wordsRead") or 0) + req.wordCount
    act = prog.get("recentActivity", [])
    act.insert(0, {"icon": "scan", "text": f"Scanned '{req.title or 'document'}'", "time": "Just now"})
    prog["recentActivity"] = act[:10]
    await _save(user["id"], prog)
    return {"docsScanned": prog["docsScanned"], "wordsRead": prog["wordsRead"]}


@router.post("/progress/word")
async def add_word(req: WordReq, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    words = list(set((prog.get("masteredWords") or []) + [req.word.strip().lower()]))
    prog["masteredWords"] = words
    prog["wordsMastered"] = len(words)
    act = prog.get("recentActivity", [])
    act.insert(0, {"icon": "star", "text": f"Mastered: '{req.word}'", "time": "Just now"})
    prog["recentActivity"] = act[:10]
    await _save(user["id"], prog)
    return {"wordsMastered": prog["wordsMastered"]}


@router.get("/progress/summary")
async def progress_summary(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    prog = await _load(user["id"])
    prog.pop("_id", None)
    comp = prog.get("avgComprehension", 0)
    if comp >= 80:
        level_label = "Advanced"
    elif comp >= 60:
        level_label = "Progressing"
    elif comp >= 40:
        level_label = "Developing"
    else:
        level_label = "Beginning"
    return {
        **prog,
        "levelLabel": level_label,
        "hasScreening": bool(user.get("readingProfile")),
        "hasPlan": prog.get("planGenerated", False),
        "dyslexiaType": (user.get("readingProfile") or {}).get("type", "Not screened"),
    }
