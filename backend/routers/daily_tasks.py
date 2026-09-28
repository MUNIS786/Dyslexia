"""
Daily Tasks — AI-generated tasks created after screening, updated based on progress.
New user → screening done → AI generates first task set → tasks update weekly.
"""
import time
import uuid
import datetime
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from database.database import db
from deps.deps import get_current_user
from services.ai_service import generate_daily_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


@router.get("")
async def get_today_tasks(authorization: Optional[str] = Header(None)):
    """Get today's tasks. Auto-generate if none exist for today."""
    user = await get_current_user(authorization)
    today = _today()

    # Fetch today's tasks
    tasks = await db.daily_tasks.find(
        {"userId": user["id"], "date": today}, {"_id": 0}
    ).to_list(20)

    if not tasks:
        # Auto-generate tasks if student has a profile
        rp = user.get("readingProfile")
        if rp and rp.get("type"):
            tasks = await _generate_and_save_tasks(user, today)
        else:
            # No screening done yet — return prompt to take screening
            return {
                "date": today,
                "tasks": [],
                "message": "Complete your dyslexia screening to get personalized daily tasks!",
                "hasScreening": False,
            }

    completed = sum(1 for t in tasks if t.get("completed"))
    return {
        "date": today,
        "tasks": tasks,
        "total": len(tasks),
        "completed": completed,
        "hasScreening": True,
    }


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, authorization: Optional[str] = Header(None)):
    """Mark a task as done. Updates progress counters."""
    user = await get_current_user(authorization)
    now = int(time.time())
    res = await db.daily_tasks.update_one(
        {"id": task_id, "userId": user["id"]},
        {"$set": {"completed": True, "completedAt": now}}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Task not found")

    # Increment progress counter
    await db.progress.update_one(
        {"userId": user["id"]},
        {"$inc": {"tasksCompleted": 1}},
        upsert=True,
    )

    # Check if all tasks done — notify
    today = _today()
    tasks = await db.daily_tasks.find(
        {"userId": user["id"], "date": today}, {"_id": 0}
    ).to_list(20)
    all_done = all(t.get("completed") for t in tasks)
    if all_done and tasks:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()), "userId": user["id"],
            "title": "🎉 All Tasks Done!",
            "message": f"You completed all {len(tasks)} tasks for today. Keep up the great work!",
            "type": "tasks_complete", "read": False, "createdAt": now,
        })

    return {"completed": True, "allDone": all_done}


async def _generate_and_save_tasks(user: dict, date: str) -> list:
    """Generate tasks from AI or rule-based fallback, save, return list."""
    rp = user.get("readingProfile") or {}
    prog = await db.progress.find_one({"userId": user["id"]}, {"_id": 0}) or {}
    d_type = rp.get("type", "")
    level = rp.get("level", "moderate")
    comp = prog.get("avgComprehension", 0)

    # Try AI generation
    ai_tasks = await generate_daily_tasks(d_type, level, comp, user)

    tasks = ai_tasks if ai_tasks else _rule_tasks(d_type, level, comp)

    now = int(time.time())
    docs = []
    for i, t in enumerate(tasks):
        doc = {
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "date": date,
            "order": i + 1,
            "title": t.get("title", ""),
            "description": t.get("description", ""),
            "type": t.get("type", "reading"),  # reading | phonics | vocabulary | quiz | exercise
            "durationMinutes": t.get("durationMinutes", 10),
            "completed": False,
            "createdAt": now,
        }
        docs.append(doc)

    if docs:
        await db.daily_tasks.insert_many(docs)
        await db.progress.update_one(
            {"userId": user["id"]},
            {"$inc": {"tasksAssigned": len(docs)}},
            upsert=True,
        )

    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]


def _rule_tasks(d_type: str, level: str, comp: int) -> list:
    """Rule-based tasks by dyslexia type and current level."""
    base = [
        {"title": "📖 Read Today's Document", "description": "Scan or open any document. Use TTS to listen while reading.", "type": "reading", "durationMinutes": 10},
        {"title": "⭐ Learn 3 New Words", "description": "Find 3 words you didn't know and add them to your mastered list.", "type": "vocabulary", "durationMinutes": 5},
        {"title": "✅ Answer 5 Questions", "description": "Complete the comprehension quiz after reading your document.", "type": "quiz", "durationMinutes": 5},
    ]
    if "Phonological" in d_type or "Double" in d_type:
        base.insert(1, {"title": "🔤 Phonics Drill", "description": "Practice sounding out 5 new words: blend the sounds slowly.", "type": "phonics", "durationMinutes": 5})
    if "Surface" in d_type:
        base.insert(1, {"title": "👁️ Sight Word Practice", "description": "Practise reading these sight words: was, said, they, where, because.", "type": "phonics", "durationMinutes": 5})
    if "RAN" in d_type or "Double" in d_type:
        base.append({"title": "⚡ Speed Naming", "description": "Name the letters b, d, p, q, n as fast as you can. Repeat 3 times.", "type": "exercise", "durationMinutes": 3})
    if comp >= 70:
        base.append({"title": "📝 Write a Summary", "description": "Write 3 sentences about what you read today in your own words.", "type": "exercise", "durationMinutes": 8})
    return base
