"""
AI Learning Plan — auto-generated from screening results, adapts with usage.

Flow:
1. Student completes dyslexia screening test
2. POST /ai-plan/generate — creates initial plan using screening + progress data
3. Plan updates automatically as student uses the app (via progress webhooks)
4. GET /ai-plan — fetch current plan
5. POST /ai-plan/check-adapt — trigger adaptation check (called by frontend periodically)
"""
import time
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from database.database import db
from deps.deps import get_current_user
from services.ai_service import generate_ai_plan, generate_progress_suggestion

router = APIRouter(prefix="/ai-plan", tags=["ai-plan"])

# Minimum progress change to trigger plan adaptation
ADAPT_THRESHOLDS = {
    "comprehension_jump": 15,     # ±15% change in avg comprehension
    "sessions_for_review": 10,    # After every 10 sessions
    "days_for_review": 7,         # At least weekly
}


@router.post("/generate")
async def generate_plan(authorization: Optional[str] = Header(None)):
    """Generate or regenerate AI plan from current screening + progress data."""
    user = await get_current_user(authorization)

    reading_profile = user.get("readingProfile")
    if not reading_profile:
        raise HTTPException(400, "Please complete the dyslexia screening test first.")

    # Load current progress
    progress = await db.progress.find_one({"userId": user["id"]}, {"_id": 0}) or {}

    # Try AI generation
    plan_data = await generate_ai_plan(reading_profile, progress, user)

    now = int(time.time())
    if plan_data:
        plan_doc = {
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "dyslexiaType": reading_profile.get("type"),
            "level": reading_profile.get("level"),
            "summary": plan_data.get("summary", ""),
            "plan": plan_data.get("plan", []),
            "weeklyGoals": plan_data.get("weeklyGoals", []),
            "accommodations": plan_data.get("accommodations", []),
            "parentTips": plan_data.get("parentTips", []),
            "teacherTips": plan_data.get("teacherTips", []),
            "adaptations": 0,
            "baselineComprehension": progress.get("avgComprehension", 0),
            "baselineSessions": progress.get("sessionCount", 0),
            "source": "ai",
            "createdAt": now,
            "updatedAt": now,
        }
    else:
        # Fallback rule-based plan
        plan_doc = _rule_based_plan(user, reading_profile, progress, now)

    # Upsert plan
    await db.ai_plans.update_one(
        {"userId": user["id"]},
        {"$set": plan_doc},
        upsert=True,
    )

    # Update progress to mark plan generated
    await db.progress.update_one(
        {"userId": user["id"]},
        {"$set": {"planGenerated": True}},
        upsert=True,
    )

    # Notify student
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "title": "Your AI Plan is Ready!",
        "message": f"We created a personalized 4-week plan for you based on your {reading_profile.get('type', 'dyslexia profile')}.",
        "type": "plan_ready",
        "read": False,
        "createdAt": now,
    })

    plan_doc.pop("_id", None)
    return plan_doc


@router.get("")
async def get_plan(authorization: Optional[str] = Header(None)):
    """Get current AI learning plan."""
    user = await get_current_user(authorization)
    plan = await db.ai_plans.find_one({"userId": user["id"]}, {"_id": 0})
    if not plan:
        # Return a starter prompt to complete screening
        return {
            "hasPlan": False,
            "message": "Complete the dyslexia screening test to get your personalized AI learning plan.",
        }
    plan["hasPlan"] = True
    return plan


@router.post("/check-adapt")
async def check_and_adapt(authorization: Optional[str] = Header(None)):
    """
    Check if plan needs adaptation based on progress.
    Call this from frontend periodically (e.g., after each session).
    Returns adapted plan or 'no_change' status.
    """
    user = await get_current_user(authorization)
    plan = await db.ai_plans.find_one({"userId": user["id"]}, {"_id": 0})
    if not plan:
        return {"adapted": False, "reason": "no_plan"}

    progress = await db.progress.find_one({"userId": user["id"]}, {"_id": 0}) or {}
    now = int(time.time())

    # Check if adaptation is needed
    should_adapt, reason = _check_adaptation_needed(plan, progress, now)
    if not should_adapt:
        return {"adapted": False, "reason": reason}

    # Generate suggestion
    suggestion = await generate_progress_suggestion(progress, plan, user)
    if not suggestion:
        return {"adapted": False, "reason": "ai_unavailable"}

    # Apply suggestion to plan
    adaptations = (plan.get("adaptations") or 0) + 1
    update = {
        "latestSuggestion": suggestion,
        "adaptations": adaptations,
        "lastAdaptedAt": now,
        "updatedAt": now,
    }
    await db.ai_plans.update_one({"userId": user["id"]}, {"$set": update})

    # Update progress counter
    await db.progress.update_one(
        {"userId": user["id"]},
        {"$inc": {"aiPlanAdaptations": 1}}
    )

    # Notify student
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "title": "Your Plan Was Updated!",
        "message": suggestion.get("encouragement", "Keep up the great work! Your plan has been updated."),
        "type": "plan_adapted",
        "read": False,
        "createdAt": now,
    })

    return {
        "adapted": True,
        "reason": reason,
        "suggestion": suggestion,
        "adaptations": adaptations,
    }


@router.get("/suggestions")
async def get_suggestions(authorization: Optional[str] = Header(None)):
    """Get latest AI suggestion for the student."""
    user = await get_current_user(authorization)
    plan = await db.ai_plans.find_one({"userId": user["id"]}, {"_id": 0, "latestSuggestion": 1})
    if not plan or not plan.get("latestSuggestion"):
        return {"suggestion": None}
    return {"suggestion": plan["latestSuggestion"]}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _check_adaptation_needed(plan: dict, progress: dict, now: int) -> tuple[bool, str]:
    last_adapted = plan.get("lastAdaptedAt") or plan.get("createdAt", 0)
    days_since = (now - last_adapted) / 86400

    # Weekly review
    if days_since >= ADAPT_THRESHOLDS["days_for_review"]:
        return True, "weekly_review"

    # Session milestone
    baseline_sessions = plan.get("baselineSessions", 0)
    current_sessions = progress.get("sessionCount", 0)
    if (current_sessions - baseline_sessions) >= ADAPT_THRESHOLDS["sessions_for_review"]:
        return True, "session_milestone"

    # Comprehension change
    baseline_comp = plan.get("baselineComprehension", 0)
    current_comp = progress.get("avgComprehension", 0)
    if abs(current_comp - baseline_comp) >= ADAPT_THRESHOLDS["comprehension_jump"]:
        return True, "comprehension_change"

    return False, "no_change_needed"


def _rule_based_plan(user: dict, profile: dict, progress: dict, now: int) -> dict:
    d_type = profile.get("type", "Unknown")
    level = profile.get("level", "moderate")

    plans = {
        "Phonological Dyslexia": [
            {"week": 1, "focus": "Sound Foundations", "activities": ["Complete letter-sound matching exercises daily", "Use TTS at 0.75x speed for all reading", "Scan 1 document per day using DyslexAid"], "goal": "Scan 5 documents, complete 3 phonics sessions"},
            {"week": 2, "focus": "Phoneme Practice", "activities": ["Phoneme blending: combine 3 sounds into words daily", "Highlight and learn 3 new words per day", "Listen to simplified text before reading it"], "goal": "Master 15 new words, reach 55% comprehension"},
            {"week": 3, "focus": "Reading Fluency", "activities": ["Re-read the same passage 3 times for fluency", "Complete comprehension quiz after each document", "Use bullet-points mode for all class notes"], "goal": "Reach 65% avg comprehension"},
            {"week": 4, "focus": "Independence Building", "activities": ["Read one document independently (with TTS if needed)", "Review mastered words list", "Complete progress review with teacher"], "goal": "70% comprehension, 20+ words mastered"},
        ],
        "Surface Dyslexia": [
            {"week": 1, "focus": "Sight Word Building", "activities": ["Practice 10 irregular sight words daily (was, said, they, where)", "Use visual word cards with DyslexAid highlights", "Scan 1 document per day"], "goal": "Learn 30 sight words"},
            {"week": 2, "focus": "Word Pattern Recognition", "activities": ["Group words by visual pattern (-ight, -tion, -ough)", "Spot the correctly-spelled word exercises", "Read simplified texts with highlighted keywords"], "goal": "Recognise 5 word families"},
            {"week": 3, "focus": "Spelling Practice", "activities": ["Daily 5-minute spelling drill", "Use look-cover-write-check method", "Complete comprehension quizzes"], "goal": "Spell 20 irregular words correctly"},
            {"week": 4, "focus": "Fluent Reading", "activities": ["Read full passages with minimal support", "Compare comprehension before/after simplification", "Review progress with teacher"], "goal": "70% comprehension, independent word reading"},
        ],
        "Double Deficit": [
            {"week": 1, "focus": "Baseline & Support", "activities": ["Use ALL DyslexAid supports: TTS, simplification, highlights", "Limit reading sessions to 10 minutes", "Seek specialist assessment at dyslexiaindia.org.in"], "goal": "Complete specialist referral, scan 3 documents"},
            {"week": 2, "focus": "Multi-Modal Reading", "activities": ["Always use audio + text together", "Use 0.75x TTS speed", "Take breaks every 10 minutes"], "goal": "Complete 5 reading sessions with audio"},
            {"week": 3, "focus": "Structured Practice", "activities": ["Follow prescribed specialist activities", "Use DyslexAid for all class reading", "Track mood and energy before/after sessions"], "goal": "Consistent daily use, 50% comprehension"},
            {"week": 4, "focus": "Review & Adjust", "activities": ["Review with specialist and teacher", "Adjust plan based on specialist feedback", "Celebrate progress made"], "goal": "Plan adjustment based on specialist input"},
        ],
    }
    plan_weeks = plans.get(d_type, [
        {"week": 1, "focus": "Getting Started", "activities": ["Scan 1 document daily", "Use TTS for all reading", "Explore app features"], "goal": "Complete 5 reading sessions"},
        {"week": 2, "focus": "Building Habit", "activities": ["Read daily for 15 minutes", "Learn 5 new words per day", "Complete comprehension quizzes"], "goal": "7-day reading streak"},
        {"week": 3, "focus": "Improving Comprehension", "activities": ["Re-read difficult passages", "Use bullet point summaries", "Track comprehension scores"], "goal": "60% average comprehension"},
        {"week": 4, "focus": "Review & Progress", "activities": ["Review mastered words", "Share progress with teacher", "Set next month goals"], "goal": "65% comprehension, 20 words mastered"},
    ])

    return {
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "dyslexiaType": d_type,
        "level": level,
        "summary": f"Personalized plan for {d_type}. Level: {level}. Focus on consistent daily reading with DyslexAid's adaptive tools.",
        "plan": plan_weeks,
        "weeklyGoals": ["Read daily for 15 minutes", "Learn 5 new words", "Complete comprehension quiz"],
        "accommodations": ["Use OpenDyslexic font always", "TTS for all reading", "Extended time on all tests", "Cream background to reduce visual stress"],
        "parentTips": ["Read together for 10 minutes daily", "Praise effort, not outcome", "Contact teacher if struggling"],
        "teacherTips": ["Allow audio recordings of lessons", "Provide simplified notes", "Use DyslexAid for class assignments"],
        "adaptations": 0,
        "baselineComprehension": progress.get("avgComprehension", 0),
        "baselineSessions": progress.get("sessionCount", 0),
        "source": "rule_based",
        "createdAt": now,
        "updatedAt": now,
    }
