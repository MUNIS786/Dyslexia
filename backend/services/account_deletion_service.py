"""
backend/services/account_deletion_service.py — Recoverable, role-aware account deletion saga.

Adheres strictly to DyslexAid V2 Privacy & Child Data Architecture:
1. Idempotent multi-phase deletion sequence.
2. Immediate disabled / deletion-pending state to block active sessions.
3. Persistent token invalidation by incrementing user token_version.
4. Strict role isolation:
   - Student: wipes all student-private records (20+ collections) and student submissions,
     terminating parent links, while preserving teacher assignments, classrooms, and global curriculum.
   - Parent: unlinks from children, purges parent data; NEVER deletes child accounts or learning records.
   - Teacher: BLOCKS deletion with HTTP 409 if active students remain enrolled.
     When empty, cleans up classroom and teacher-owned assignments.
5. Permanent removal of personal account data from db.users upon completion.
6. Safe operational error recording and retry support.
"""
import time
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

import database.database as db_module
from deps.deps import verify_password

logger = logging.getLogger("dyslexaid.account_deletion")


async def execute_account_deletion(user_id: str, password: str, confirmation: str) -> Dict[str, Any]:
    """
    Executes a recoverable, role-aware account deletion saga.

    1. Validates explicit confirmation string 'DELETE_MY_ACCOUNT'.
    2. Fetches user document from DB to retrieve passwordHash, role, and current state.
    3. Re-authenticates caller with password.
    4. Enforces teacher deletion guard: blocks with HTTP 409 if active students remain enrolled.
    5. Transitions account to `disabled: True, deletionState: 'pending'` and increments `token_version`.
       At this instant, all active JWTs are invalidated and rejected by auth guards.
    6. Executes role-specific cascading cleanup across all dependent MongoDB collections.
    7. Permanently removes personal user document from db.users upon completion.
    8. Returns safe confirmation metadata without personal data.
    """
    db = db_module.db

    if not confirmation or confirmation != "DELETE_MY_ACCOUNT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase must be exactly 'DELETE_MY_ACCOUNT'."
        )

    # 1. Fetch user record directly from database
    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found."
        )

    # 2. Re-authenticate password
    if not verify_password(password, user_doc.get("passwordHash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Account deletion requires valid password reauthentication."
        )

    role = user_doc.get("role", "student")

    # 3. Role-specific pre-deletion safety guards
    if role == "teacher":
        classroom_code = user_doc.get("classroomCode")
        if classroom_code:
            enrolled_count = await db.users.count_documents({
                "role": "student",
                "classroomJoined": classroom_code,
            })
            if enrolled_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot delete teacher account while {enrolled_count} student(s) remain enrolled "
                        f"in classroom '{classroom_code}'. Students must leave or be transferred before deleting this account."
                    )
                )

    # 4. Immediate Session Termination & Deletion-Pending State (Phase 1 Tombstone)
    now = int(time.time())
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "disabled": True,
                "deletionState": "pending",
                "deletionRequestedAt": now,
                "deletionFailureError": None,
            },
            "$inc": {"token_version": 1}
        }
    )

    # 5. Execute Cascading Cleanup Saga (Phase 2)
    try:
        if role == "student":
            await _cleanup_student_records(user_id, db)
        elif role == "parent":
            await _cleanup_parent_records(user_id, db)
        elif role == "teacher":
            await _cleanup_teacher_records(user_id, user_doc.get("classroomCode"), db)
        else:
            await _cleanup_generic_user_records(user_id, db)
    except Exception as exc:
        # Record operational failure without logging personal PII
        logger.error(
            "Operational failure during account deletion cleanup for user_id=%s, role=%s: %s",
            user_id, role, type(exc).__name__
        )
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "deletionState": "failed",
                    "deletionFailedAt": int(time.time()),
                    "deletionFailureError": str(type(exc).__name__),
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An operational error occurred during data cleanup. Account remains disabled. Please retry or contact support."
        )

    # 6. Final Purge (Phase 3) — Permanent removal of identifying account record
    await db.users.delete_one({"id": user_id})
    logger.info("Account deletion completed successfully for user_id=%s, role=%s", user_id, role)

    return {
        "status": "ok",
        "message": "Account and all associated personal data have been permanently deleted.",
        "deletedUserId": user_id,
        "role": role,
        "deletedAt": now,
    }


async def _cleanup_student_records(student_id: str, db: Any) -> None:
    """
    Idempotently removes all confirmed student-private records.
    Preserves teacher assignments, classroom definitions, and global catalogs.
    """
    # 1. V2 Adaptive Learning Engine & Learner Profile
    await db.learner_profiles.delete_many({"learnerId": student_id})
    await db.learning_states.delete_many({"learnerId": student_id})
    await db.activity_attempts.delete_many({"learnerId": student_id})
    await db.adaptive_recommendations.delete_many({"learnerId": student_id})
    await db.activity_launches.delete_many({"learnerId": student_id})

    # 2. Reading Coach & Speech/Reading Analysis
    await db.reading_sessions.delete_many({"learnerId": student_id})
    await db.speech_reading_analyses.delete_many({"learnerId": student_id})

    # 3. AI Tutor Conversations
    await db.tutor_conversations.delete_many({"learnerId": student_id})

    # 4. Gamification, Streaks & Rewards
    await db.gamification_summaries.delete_many({"learnerId": student_id})
    await db.reward_events.delete_many({"learnerId": student_id})

    # 5. Core Screening, Prediction History, Daily Tasks, AI Plans, Progress
    await db.progress.delete_many({"userId": student_id})
    await db.screening_results.delete_many({"userId": student_id})
    await db.prediction_history.delete_many({"userId": student_id})
    await db.daily_tasks.delete_many({"userId": student_id})
    await db.ai_plans.delete_many({"userId": student_id})

    # 6. Personal Library & Accessibility Preferences
    await db.libraries.delete_many({"userId": student_id})
    await db.accessibility_preferences.delete_many({"learnerId": student_id})
    await db.user_accessibility_preferences.delete_many({"userId": student_id})
    await db.user_language_preferences.delete_many({"userId": student_id})

    # 7. Student Submissions & Teacher Notes for this Student
    # Note: db.assignments is teacher-owned and MUST NOT be touched.
    await db.submissions.delete_many({"studentId": student_id})
    await db.teacher_notes.delete_many({"studentId": student_id})
    await db.interventions.delete_many({"learnerId": student_id})

    # 8. Parent Links & Invitations
    await db.parent_links.delete_many({"studentId": student_id})
    await db.parent_invitations.delete_many({"studentId": student_id})
    await db.parent_requests.delete_many({"studentId": student_id})

    # 9. Notifications & Security Tokens
    await db.notifications.delete_many({"userId": student_id})
    await db.password_resets.delete_many({"userId": student_id})
    await db.email_verifications.delete_many({"userId": student_id})


async def _cleanup_parent_records(parent_id: str, db: Any) -> None:
    """
    Idempotently purges parent personal data and terminates parent-child linkages.
    CRITICAL: Never deletes children's user accounts or child learning history.
    """
    # 1. Terminate parent-child links & requests
    await db.parent_links.delete_many({"parentId": parent_id})
    await db.parent_requests.delete_many({"parentId": parent_id})

    # 2. Preferences & Notifications
    await db.user_language_preferences.delete_many({"userId": parent_id})
    await db.user_accessibility_preferences.delete_many({"userId": parent_id})
    await db.notifications.delete_many({"userId": parent_id})

    # 3. Security Tokens
    await db.password_resets.delete_many({"userId": parent_id})
    await db.email_verifications.delete_many({"userId": parent_id})


async def _cleanup_teacher_records(teacher_id: str, classroom_code: Optional[str], db: Any) -> None:
    """
    Idempotently purges teacher-owned resources once verified that zero students are enrolled.
    """
    # 1. Remove classroom definition
    if classroom_code:
        await db.classrooms.delete_many({"code": classroom_code})
    await db.classrooms.delete_many({"teacherId": teacher_id})

    # 2. Remove teacher-created assignments and any associated submissions
    assignments = await db.assignments.find({"teacherId": teacher_id}, {"id": 1}).to_list(1000)
    a_ids = [a["id"] for a in assignments if isinstance(a, dict) and "id" in a]
    if a_ids:
        await db.submissions.delete_many({"assignmentId": {"$in": a_ids}})
    await db.assignments.delete_many({"teacherId": teacher_id})

    # 3. Teacher notes and interventions created by this teacher
    await db.teacher_notes.delete_many({"teacherId": teacher_id})
    await db.interventions.delete_many({"teacherId": teacher_id})

    # 4. Content authoring logs authored by this teacher
    await db.content_audit_logs.delete_many({"authorId": teacher_id})

    # 5. Preferences & Notifications
    await db.user_language_preferences.delete_many({"userId": teacher_id})
    await db.user_accessibility_preferences.delete_many({"userId": teacher_id})
    await db.notifications.delete_many({"userId": teacher_id})

    # 6. Security Tokens
    await db.password_resets.delete_many({"userId": teacher_id})
    await db.email_verifications.delete_many({"userId": teacher_id})


async def _cleanup_generic_user_records(user_id: str, db: Any) -> None:
    """Fallback cleanup for generic user accounts."""
    await db.user_language_preferences.delete_many({"userId": user_id})
    await db.user_accessibility_preferences.delete_many({"userId": user_id})
    await db.notifications.delete_many({"userId": user_id})
    await db.password_resets.delete_many({"userId": user_id})
    await db.email_verifications.delete_many({"userId": user_id})
