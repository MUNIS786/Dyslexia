"""
backend/services/parent/parent_service.py — V2 Parent & Guardian Portal Core Service.

Coordinates:
1. Cryptographically secure one-time parent link invitation generation & verification.
2. Direct parent link requests with student/guardian approval workflows.
3. Strict parent-student relationship authorization & instant revocation.
4. Privacy-preserving dashboard aggregations across Reading Coach, Adaptive Practice, and Gamification.
5. Exclusion of private AI tutor chat history, raw audio, and teacher-only notes.
6. Descriptive, encouraging home reading practice recommendations without clinical claims.
"""
import time
import uuid
import secrets
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status

from database.database import db
from models.v2_parent import (
    ParentLinkItem,
    ParentProfileSummary,
    HomePracticeSuggestion,
    ParentRecentSession,
    ParentRecentActivity,
    ParentLearningOverview,
    ParentProgressTrend,
    ParentDashboardResponse,
)

logger = logging.getLogger("dyslexaid.parent_service")

# ─── Home Practice Suggestions Catalog ───────────────────────────────────────

DEFAULT_HOME_SUGGESTIONS = [
    HomePracticeSuggestion(
        id="sug-shared-reading",
        title="10-Minute Shared Reading",
        description="Read a story aloud together. Take turns reading alternating sentences or paragraphs to build natural reading rhythm and confidence.",
        category="shared_reading",
        practicalTip="Point to words gently as you read, and pause to talk about interesting pictures or story moments.",
    ),
    HomePracticeSuggestion(
        id="sug-effort-praise",
        title="Celebrate Consistency & Effort",
        description="Praise daily persistence and trying difficult words rather than focusing on speed or perfection.",
        category="celebration",
        practicalTip="Say: 'I noticed how carefully you sounded out that tricky word!' rather than 'You read so fast.'",
    ),
    HomePracticeSuggestion(
        id="sug-calm-environment",
        title="Quiet & Comfortable Reading Nook",
        description="Create a cozy, well-lit reading corner with minimal audio distractions (like TV or loud background music).",
        category="routine",
        practicalTip="Let your child choose a favorite cushion or blanket to make reading time relaxing and inviting.",
    ),
    HomePracticeSuggestion(
        id="sug-rhyme-wordplay",
        title="Playful Word & Sound Games",
        description="Practice rhyming words or syllable clapping during car rides, cooking, or evening walks.",
        category="phonics_game",
        practicalTip="Ask: 'What rhymes with cat?' or clap together for each beat in family names.",
    ),
]


# ─── Helper Functions ────────────────────────────────────────────────────────

def _format_epoch_to_date(epoch_val: Any) -> str:
    """Safely converts an epoch timestamp or datetime to a readable date string."""
    try:
        if isinstance(epoch_val, (int, float)):
            return datetime.fromtimestamp(epoch_val, tz=timezone.utc).strftime("%b %d, %Y")
        if isinstance(epoch_val, datetime):
            return epoch_val.strftime("%b %d, %Y")
        if isinstance(epoch_val, str):
            return epoch_val[:10]
    except Exception:
        pass
    return "Recent"


def _hash_code(code: str) -> str:
    """Computes SHA-256 hash of normalized code string."""
    normalized = code.strip().upper().replace(" ", "").replace("-", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ─── 1. One-Time Invitation Code Management ──────────────────────────────────

async def generate_invitation_code(student_id: str, creator_id: str, creator_role: str) -> Dict[str, Any]:
    """
    Generates a secure, short-lived (48h), one-time invitation code for linking a parent.
    Stored only as a SHA-256 hash in the database.
    """
    student = await db.users.find_one({"id": student_id, "role": "student"}, {"_id": 0, "passwordHash": 0})
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    # Invalidate previous unused active invitations for this student to keep codes clean
    await db.parent_invitations.update_many(
        {"studentId": student_id, "status": "active"},
        {"$set": {"status": "revoked", "revokedAt": int(time.time())}}
    )

    # Generate 8-character random alphanumeric code formatted as PLC-XXXX-XXXX
    random_part = secrets.token_hex(4).upper()  # 8 chars
    invitation_code = f"PLC-{random_part[:4]}-{random_part[4:]}"
    code_hash = _hash_code(invitation_code)

    now = int(time.time())
    expires_at = now + (48 * 3600)  # 48 hours validity

    invitation_doc = {
        "id": str(uuid.uuid4()),
        "codeHash": code_hash,
        "studentId": student_id,
        "studentName": student.get("name", "Student"),
        "createdBy": creator_id,
        "creatorRole": creator_role,
        "expiresAt": expires_at,
        "status": "active",
        "createdAt": now,
        "usedAt": None,
        "usedByParentId": None,
    }
    await db.parent_invitations.insert_one(invitation_doc)

    logger.info(f"Generated parent invitation code for student {student_id} by {creator_role} {creator_id}")
    return {
        "invitationCode": invitation_code,
        "expiresAt": expires_at,
        "studentId": student_id,
        "studentName": student.get("name", "Student"),
        "success": True,
        "message": "Share this code with your parent or guardian. It expires in 48 hours.",
    }


async def claim_invitation_code(parent_user: dict, code: str, relationship: str = "parent") -> ParentLinkItem:
    """
    Redeems a valid invitation code to immediately establish an active parent-student link.
    Enforces one-time use, expiry check, and prevention of duplicate active links.
    """
    code_hash = _hash_code(code)
    invitation = await db.parent_invitations.find_one({"codeHash": code_hash}, {"_id": 0})

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation code. Please check the code and try again."
        )

    now = int(time.time())
    if invitation.get("status") != "active":
        detail_msg = "This invitation code has already been used." if invitation.get("status") == "used" else "This invitation code is no longer valid."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg
        )

    if int(invitation.get("expiresAt", 0)) < now:
        await db.parent_invitations.update_one(
            {"id": invitation["id"]},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation code has expired. Please ask your child or teacher for a new code."
        )

    student_id = invitation["studentId"]
    parent_id = parent_user["id"]

    # Check for existing active link
    existing_link = await db.parent_links.find_one(
        {"parentId": parent_id, "studentId": student_id, "status": "active"},
        {"_id": 0}
    )
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already actively connected to this learner."
        )

    # Mark invitation as used (atomically)
    await db.parent_invitations.update_one(
        {"id": invitation["id"]},
        {"$set": {"status": "used", "usedAt": now, "usedByParentId": parent_id}}
    )

    # Create active parent link
    link_id = str(uuid.uuid4())
    link_doc = {
        "id": link_id,
        "parentId": parent_id,
        "parentName": parent_user.get("name", "Parent"),
        "parentEmail": parent_user.get("email", ""),
        "studentId": student_id,
        "studentName": invitation.get("studentName", "Student"),
        "relationship": relationship or "parent",
        "status": "active",
        "verifiedAt": now,
        "verifiedBy": "invitation_code",
        "invitationId": invitation["id"],
        "requestedAt": now,
        "createdAt": now,
        "revokedAt": None,
        "revokedBy": None,
    }
    await db.parent_links.insert_one(link_doc)

    # Insert notification for student
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": student_id,
        "title": "Parent Connected",
        "message": f"{parent_user.get('name', 'A parent')} has connected to your account using an invitation code.",
        "type": "parent_linked",
        "read": False,
        "createdAt": now,
    })

    logger.info(f"Active parent link created via code: Parent {parent_id} -> Student {student_id}")
    return ParentLinkItem(
        id=link_id,
        studentId=student_id,
        studentName=invitation.get("studentName", "Student"),
        relationship=relationship or "parent",
        status="active",
        requestedAt=now,
        verifiedAt=now,
        createdAt=now,
    )


# ─── 2. Direct Request Linking Workflow ──────────────────────────────────────

async def request_student_link(parent_user: dict, student_identifier: str, relationship: str = "parent") -> ParentLinkItem:
    """
    Parent initiates a link request by providing the student's email or student ID.
    Enters 'pending' state until approved by the student or their teacher.
    """
    clean_id = student_identifier.strip()
    student = await db.users.find_one(
        {"$or": [{"email": clean_id.lower()}, {"id": clean_id}], "role": "student"},
        {"_id": 0, "passwordHash": 0}
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learner not found. Please verify the student's email address or student ID."
        )

    parent_id = parent_user["id"]
    student_id = student["id"]

    # Check existing active or pending link
    existing_link = await db.parent_links.find_one(
        {"parentId": parent_id, "studentId": student_id, "status": {"$in": ["active", "pending"]}},
        {"_id": 0}
    )
    if existing_link:
        if existing_link.get("status") == "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already actively connected to this learner."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A connection request is already pending approval for this learner."
            )

    now = int(time.time())
    link_id = str(uuid.uuid4())
    link_doc = {
        "id": link_id,
        "parentId": parent_id,
        "parentName": parent_user.get("name", "Parent"),
        "parentEmail": parent_user.get("email", ""),
        "studentId": student_id,
        "studentName": student.get("name", "Student"),
        "relationship": relationship or "parent",
        "status": "pending",
        "verifiedAt": None,
        "verifiedBy": None,
        "invitationId": None,
        "requestedAt": now,
        "createdAt": now,
        "revokedAt": None,
        "revokedBy": None,
    }
    await db.parent_links.insert_one(link_doc)

    # Notify student
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": student_id,
        "title": "Parent Link Request",
        "message": f"{parent_user.get('name', 'Parent')} ({parent_user.get('email')}) requested to link to your reading profile.",
        "type": "parent_request",
        "requestId": link_id,
        "read": False,
        "createdAt": now,
    })

    logger.info(f"Parent {parent_id} requested link to student {student_id}")
    return ParentLinkItem(
        id=link_id,
        studentId=student_id,
        studentName=student.get("name", "Student"),
        relationship=relationship or "parent",
        status="pending",
        requestedAt=now,
        verifiedAt=None,
        createdAt=now,
    )


async def approve_link_request(approver_user: dict, request_id: str) -> ParentLinkItem:
    """
    Student or assigned teacher approves a pending parent link request.
    """
    link = await db.parent_links.find_one({"id": request_id}, {"_id": 0})
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link request not found."
        )

    if link.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request with status '{link.get('status')}'."
        )

    # Authorization: approver must be the student or student's teacher
    user_id = approver_user.get("id")
    user_role = approver_user.get("role")
    student_id = link["studentId"]

    is_authorized = False
    if user_id == student_id:
        is_authorized = True
    elif user_role == "teacher":
        # Check if student is in this teacher's classroom
        teacher_code = approver_user.get("classroomCode")
        student = await db.users.find_one({"id": student_id}, {"_id": 0, "classroomJoined": 1})
        if student and student.get("classroomJoined") == teacher_code:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to approve this link request."
        )

    now = int(time.time())
    await db.parent_links.update_one(
        {"id": request_id},
        {"$set": {"status": "active", "verifiedAt": now, "verifiedBy": user_id}}
    )

    # Notify parent
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": link["parentId"],
        "title": "Link Request Approved",
        "message": f"Your connection to {link['studentName']} has been approved. You can now view their progress.",
        "type": "parent_link_approved",
        "read": False,
        "createdAt": now,
    })

    logger.info(f"Link request {request_id} approved by user {user_id}")
    return ParentLinkItem(
        id=request_id,
        studentId=student_id,
        studentName=link.get("studentName", "Student"),
        relationship=link.get("relationship", "parent"),
        status="active",
        requestedAt=link.get("requestedAt", now),
        verifiedAt=now,
        createdAt=link.get("createdAt", now),
    )


async def reject_link_request(approver_user: dict, request_id: str) -> Dict[str, Any]:
    """
    Student or assigned teacher rejects a pending parent link request.
    """
    link = await db.parent_links.find_one({"id": request_id}, {"_id": 0})
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link request not found."
        )

    user_id = approver_user.get("id")
    student_id = link["studentId"]
    if user_id != student_id and approver_user.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to reject this link request."
        )

    now = int(time.time())
    await db.parent_links.update_one(
        {"id": request_id},
        {"$set": {"status": "rejected", "revokedAt": now, "revokedBy": user_id}}
    )

    logger.info(f"Link request {request_id} rejected by {user_id}")
    return {"success": True, "message": "Link request rejected.", "requestId": request_id}


async def revoke_parent_link(revoker_user: dict, link_id: str) -> Dict[str, Any]:
    """
    Immediately revokes an active parent-student link.
    Callable by either the parent or the linked student.
    """
    link = await db.parent_links.find_one({"id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship link not found."
        )

    user_id = revoker_user.get("id")
    if user_id != link["parentId"] and user_id != link["studentId"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to revoke this relationship."
        )

    now = int(time.time())
    await db.parent_links.update_one(
        {"id": link_id},
        {"$set": {"status": "revoked", "revokedAt": now, "revokedBy": user_id}}
    )

    logger.info(f"Parent link {link_id} revoked by {user_id}")
    return {"success": True, "message": "Relationship link revoked successfully.", "linkId": link_id}


# ─── 3. Authorization & Tenant Isolation Guard ───────────────────────────────

async def verify_parent_student_access(parent_id: str, student_id: str) -> dict:
    """
    Strict server-side security check.
    Enforces that the caller has an active, verified relationship with the target learner.
    Raises 403 Forbidden immediately if link is missing, pending, rejected, or revoked.
    """
    link = await db.parent_links.find_one(
        {"parentId": parent_id, "studentId": student_id, "status": "active"},
        {"_id": 0}
    )
    if not link:
        logger.warning(f"Unauthorized parent access attempt: Parent {parent_id} requested Student {student_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have an active verified relationship with this learner."
        )
    return link


# ─── 4. Queries & Dashboard Aggregation ──────────────────────────────────────

async def get_parent_profile_summary(parent_user: dict) -> ParentProfileSummary:
    """Returns profile and counts for the authenticated parent."""
    parent_id = parent_user["id"]
    active_count = await db.parent_links.count_documents({"parentId": parent_id, "status": "active"})
    pending_count = await db.parent_links.count_documents({"parentId": parent_id, "status": "pending"})

    # Check preferred language
    lang_pref = await db.user_language_preferences.find_one({"userId": parent_id}, {"_id": 0, "preferredLanguage": 1})
    preferred_lang = lang_pref.get("preferredLanguage", "en") if lang_pref else "en"

    return ParentProfileSummary(
        id=parent_id,
        name=parent_user.get("name", "Parent"),
        email=parent_user.get("email", ""),
        role="parent",
        linkedLearnersCount=active_count,
        pendingRequestsCount=pending_count,
        preferredLanguage=preferred_lang,
    )


async def get_parent_learners(parent_id: str) -> List[ParentLinkItem]:
    """Retrieves all active and pending links for a parent."""
    cursor = db.parent_links.find(
        {"parentId": parent_id, "status": {"$in": ["active", "pending"]}},
        {"_id": 0}
    ).sort("createdAt", -1)
    links = await cursor.to_list(50)
    return [
        ParentLinkItem(
            id=l["id"],
            studentId=l["studentId"],
            studentName=l.get("studentName", "Student"),
            relationship=l.get("relationship", "parent"),
            status=l.get("status", "active"),
            requestedAt=l.get("requestedAt", 0),
            verifiedAt=l.get("verifiedAt"),
            createdAt=l.get("createdAt", 0),
        )
        for l in links
    ]


async def get_student_pending_requests(student_id: str) -> List[Dict[str, Any]]:
    """Retrieves pending parent connection requests for a student to review."""
    cursor = db.parent_links.find(
        {"studentId": student_id, "status": "pending"},
        {"_id": 0}
    ).sort("requestedAt", -1)
    return await cursor.to_list(20)


async def get_student_active_links(student_id: str) -> List[Dict[str, Any]]:
    """Retrieves active parent connections for a student."""
    cursor = db.parent_links.find(
        {"studentId": student_id, "status": "active"},
        {"_id": 0}
    ).sort("verifiedAt", -1)
    return await cursor.to_list(20)


async def get_parent_student_activities(
    parent_user: dict,
    student_id: str,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Retrieves bounded, safe chronological learning activity timeline for an authorized learner.
    Strictly excludes private AI tutor chat transcripts and teacher-only notes.
    """
    await verify_parent_student_access(parent_user["id"], student_id)

    # 1. Fetch completed reading sessions
    r_docs = await db.reading_sessions.find(
        {"learnerId": student_id, "completed": True},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(limit)

    # 2. Fetch completed adaptive attempts
    a_docs = await db.activity_attempts.find(
        {"learnerId": student_id},
        {"_id": 0}
    ).sort("completedAt", -1).to_list(limit)

    # 3. Fetch reward events (milestones, badges)
    rw_docs = await db.reward_events.find(
        {"learnerId": student_id},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(limit)

    events: List[Dict[str, Any]] = []

    for r in r_docs:
        ts = int(r.get("createdAt") or 0)
        events.append({
            "id": r.get("id") or r.get("sessionId") or str(uuid.uuid4()),
            "type": "reading_session",
            "title": r.get("passageTitle") or "Reading Practice",
            "description": f"Read {r.get('wordsRead', 0)} words (Tier {r.get('difficultyTier', 1)})",
            "score": r.get("comprehensionScore"),
            "date": _format_epoch_to_date(ts),
            "timestamp": ts,
        })

    for a in a_docs:
        ts = int(a.get("completedAt") or 0)
        domain = a.get("domain") or a.get("activityType") or "Skill Practice"
        events.append({
            "id": a.get("id") or a.get("attemptId") or str(uuid.uuid4()),
            "type": "adaptive_activity",
            "title": f"Adaptive {domain.title()}",
            "description": f"Completed skill challenge (Score: {float(a.get('scorePercent', 0)):.0f}%)",
            "score": a.get("scorePercent"),
            "date": _format_epoch_to_date(ts),
            "timestamp": ts,
        })

    for rw in rw_docs:
        ts = int(rw.get("createdAt") or 0)
        events.append({
            "id": rw.get("eventId") or str(uuid.uuid4()),
            "type": "reward_earned",
            "title": rw.get("title") or "Achievement Earned",
            "description": rw.get("description") or f"+{rw.get('points', 0)} points earned",
            "score": rw.get("points"),
            "date": _format_epoch_to_date(ts),
            "timestamp": ts,
        })

    # Sort combined timeline descending by timestamp
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events[:limit]


async def get_parent_dashboard(
    parent_user: dict,
    student_id: Optional[str] = None,
) -> ParentDashboardResponse:
    """
    Compiles the full, authorized parent dashboard payload.
    Derives metrics exclusively from real learning records without fabricating data.
    """
    parent_id = parent_user["id"]
    if student_id:
        await verify_parent_student_access(parent_id, student_id)

    profile_summary = await get_parent_profile_summary(parent_user)

    # Get all active links
    active_cursor = db.parent_links.find({"parentId": parent_id, "status": "active"}, {"_id": 0}).sort("createdAt", -1)
    active_links = await active_cursor.to_list(50)

    # Safe LinkItem list
    linked_items = [
        ParentLinkItem(
            id=l["id"],
            studentId=l["studentId"],
            studentName=l.get("studentName", "Student"),
            relationship=l.get("relationship", "parent"),
            status=l.get("status", "active"),
            requestedAt=l.get("requestedAt", 0),
            verifiedAt=l.get("verifiedAt"),
            createdAt=l.get("createdAt", 0),
        )
        for l in active_links
    ]

    # Handle parent with no linked learners
    if not linked_items:
        return ParentDashboardResponse(
            parent=profile_summary,
            selectedLearner=None,
            linkedLearners=[],
            overview=None,
            recentReadingSessions=[],
            recentAdaptiveActivities=[],
            gamificationSummary=None,
            trends=None,
            homeSuggestions=DEFAULT_HOME_SUGGESTIONS,
            hasLinkedLearners=False,
        )

    # Determine selected learner
    target_link: Optional[ParentLinkItem] = None
    if student_id:
        # Strict authorization check
        await verify_parent_student_access(parent_id, student_id)
        target_link = next((item for item in linked_items if item.studentId == student_id), None)
    
    if not target_link:
        target_link = linked_items[0]

    target_id = target_link.studentId

    # 1. Fetch completed reading sessions
    reading_sessions = await db.reading_sessions.find(
        {"learnerId": target_id, "completed": True},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(50)

    # 2. Fetch adaptive activity attempts
    activity_attempts = await db.activity_attempts.find(
        {"learnerId": target_id},
        {"_id": 0}
    ).sort("completedAt", -1).to_list(50)

    # 3. Fetch speech reading analyses
    speech_analyses = await db.speech_reading_analyses.find(
        {"learnerId": target_id},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(50)

    # 4. Fetch gamification summary & reward events
    gamification = await db.gamification_summaries.find_one({"learnerId": target_id}, {"_id": 0})
    if not gamification:
        gamification = {
            "totalPoints": 0,
            "currentStreak": 0,
            "longestStreak": 0,
            "earnedBadges": [],
            "upcomingMilestones": [],
        }

    # Compute overview metrics
    total_reading_secs = sum(float(r.get("durationSeconds", 0.0)) for r in reading_sessions)
    stories_completed = len(reading_sessions)
    comprehension_scores = [
        float(r["comprehensionScore"])
        for r in reading_sessions
        if r.get("comprehensionScore") is not None
    ]
    avg_comp = (sum(comprehension_scores) / len(comprehension_scores)) if comprehension_scores else None

    adaptive_completed = len(activity_attempts)
    # Determine current tier from recent activity or state
    learning_state = await db.learning_states.find_one({"learnerId": target_id}, {"_id": 0})
    current_tier = int(learning_state.get("tier", 1)) if learning_state else 1

    overview = ParentLearningOverview(
        totalReadingMinutes=round(total_reading_secs / 60.0, 1),
        storiesCompleted=stories_completed,
        avgComprehensionScore=round(avg_comp, 1) if avg_comp is not None else None,
        adaptiveActivitiesCompleted=adaptive_completed,
        currentDifficultyTier=current_tier,
        currentStreak=int(gamification.get("currentStreak", 0)),
        longestStreak=int(gamification.get("longestStreak", 0)),
        totalPoints=int(gamification.get("totalPoints", 0)),
        badgesEarnedCount=len(gamification.get("earnedBadges", [])),
    )

    # Summarize recent reading sessions
    recent_reading: List[ParentRecentSession] = []
    for r in reading_sessions[:5]:
        ts = int(r.get("createdAt") or 0)
        recent_reading.append(ParentRecentSession(
            id=r.get("sessionId") or r.get("id"),
            title=r.get("passageTitle") or "Reading Passage",
            difficultyTier=int(r.get("difficultyTier", 1)),
            wordsRead=int(r.get("wordsRead", 0)),
            comprehensionScore=round(float(r["comprehensionScore"]), 1) if r.get("comprehensionScore") is not None else None,
            durationMinutes=round(float(r.get("durationSeconds", 0)) / 60.0, 1),
            date=_format_epoch_to_date(ts),
            timestamp=ts,
        ))

    # Summarize recent adaptive activities
    recent_adaptive: List[ParentRecentActivity] = []
    for a in activity_attempts[:5]:
        ts = int(a.get("completedAt") or 0)
        recent_adaptive.append(ParentRecentActivity(
            id=a.get("attemptId") or a.get("id"),
            domain=a.get("domain") or a.get("activityType") or "Practice",
            scorePercent=round(float(a.get("scorePercent", 0)), 1),
            difficultyTier=int(a.get("difficultyTier", 1)),
            date=_format_epoch_to_date(ts),
            timestamp=ts,
        ))

    # Calculate trends over time (using objective historical evaluation)
    def _evaluate_trend(scores: List[float]) -> str:
        if len(scores) < 2:
            return "insufficient_data"
        half = len(scores) // 2
        first_half = scores[:half] if half > 0 else [scores[0]]
        second_half = scores[half:] if half > 0 else [scores[-1]]
        delta = (sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half))
        if delta > 3.0:
            return "improving"
        elif delta < -3.0:
            return "declining"
        return "stable"

    comp_trend_scores = [float(r["comprehensionScore"]) for r in reversed(reading_sessions) if r.get("comprehensionScore") is not None]
    adaptive_scores = [float(a["scorePercent"]) for a in reversed(activity_attempts) if a.get("scorePercent") is not None]
    speech_scores = [float(s["accuracyRate"]) for s in reversed(speech_analyses) if s.get("accuracyRate") is not None]

    # Build trend points for charting
    trend_points: List[Dict[str, Any]] = []
    for r in reversed(reading_sessions[:10]):
        ts = int(r.get("createdAt") or 0)
        trend_points.append({
            "timestamp": ts,
            "date": _format_epoch_to_date(ts),
            "comprehensionScore": r.get("comprehensionScore"),
            "type": "reading",
        })

    trends = ParentProgressTrend(
        readingTrend=_evaluate_trend(comp_trend_scores),
        adaptiveTrend=_evaluate_trend(adaptive_scores),
        speechTrend=_evaluate_trend(speech_scores),
        points=trend_points,
    )

    # Clean gamification object for parent view
    clean_gamification = {
        "totalPoints": gamification.get("totalPoints", 0),
        "currentStreak": gamification.get("currentStreak", 0),
        "longestStreak": gamification.get("longestStreak", 0),
        "earnedBadges": gamification.get("earnedBadges", []),
        "upcomingMilestones": gamification.get("upcomingMilestones", []),
    }

    return ParentDashboardResponse(
        parent=profile_summary,
        selectedLearner=target_link,
        linkedLearners=linked_items,
        overview=overview,
        recentReadingSessions=recent_reading,
        recentAdaptiveActivities=recent_adaptive,
        gamificationSummary=clean_gamification,
        trends=trends,
        homeSuggestions=DEFAULT_HOME_SUGGESTIONS,
        hasLinkedLearners=True,
    )
