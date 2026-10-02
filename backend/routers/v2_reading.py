"""
backend/routers/v2_reading.py — V2 Adaptive Reading Coach API.

Endpoints:
- GET  /api/v2/reading/recommendation       (Get best adaptive reading passage based on Phase 3 state)
- GET  /api/v2/reading/passages             (Browse/filter catalog of passages by tier/domain/language)
- GET  /api/v2/reading/passages/{passage_id}(Get details for a specific reading passage)
- POST /api/v2/reading/session/start        (Initialize a reading session)
- POST /api/v2/reading/session/complete     (Submit telemetry, server-side grading, adapt tier)
- GET  /api/v2/reading/sessions             (Learner reading session history)
- GET  /api/v2/reading/stats                (Aggregated reading statistics and trends)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user, require_teacher
from core.config import settings
from database.database import db
from models.v2_reading import (
    ReadingSessionStartRequest,
    ReadingSessionCompleteRequest,
    ReadingRecommendationResponse,
    ReadingStatsResponse,
)
from models.v2_speech_analysis import (
    SpeechAnalysisRequest,
    SpeechAnalysisResponse,
)
from services.learning.reading_service import (
    get_passages,
    get_passage_by_id,
    start_reading_session,
    complete_reading_session,
    get_learner_sessions,
    get_learner_reading_stats,
)
from services.learning.reading_recommender import recommend_reading_passage
from services.learning.speech_analysis import (
    analyze_speech_reading,
    get_speech_analysis_for_session,
)

logger = logging.getLogger("dyslexaid.routers.v2_reading")
router = APIRouter(prefix="/v2/reading", tags=["V2 Adaptive Reading Coach"])


def _check_feature_flag():
    if not settings.V2_READING_COACH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Adaptive Reading Coach is currently disabled via feature flags."
        )


@router.get("/recommendation", response_model=ReadingRecommendationResponse)
async def get_reading_recommendation(
    language: Optional[str] = Query(None, description="Optional target language ('en', 'mr', 'hi')"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve the optimal reading passage recommendation for the authenticated learner.
    Determined deterministically from the learner's active ZPD tier, language, and learning state.
    """
    _check_feature_flag()
    learner_id = current_user.get("id")
    pref_lang = (language or current_user.get("preferredLanguage") or "en").strip().lower()
    if pref_lang.startswith("mr"):
        pref_lang = "mr"
    elif pref_lang.startswith("hi"):
        pref_lang = "hi"
    else:
        pref_lang = "en"

    try:
        rec = await recommend_reading_passage(learner_id=learner_id, preferred_language=pref_lang)
        return rec
    except Exception as e:
        logger.error(f"Error recommending reading passage for user {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reading recommendation."
        )


@router.get("/passages")
async def list_passages(
    tier: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty tier (1-5)"),
    domain: Optional[str] = Query(None, description="Filter by educational domain"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    current_user: dict = Depends(get_current_user),
):
    """
    List available reading passages from the catalog, optionally filtered by tier, domain, or language.
    """
    _check_feature_flag()
    try:
        passages = await get_passages(tier=tier, domain=domain, language=language)
        return {
            "status": "ok",
            "count": len(passages),
            "passages": passages,
        }
    except Exception as e:
        logger.error(f"Error listing passages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reading passages."
        )


@router.get("/passages/{passage_id}")
async def get_passage(
    passage_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve full details of a specific reading passage by ID, including questions and vocabulary.
    """
    _check_feature_flag()
    passage = await get_passage_by_id(passage_id)
    if not passage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passage '{passage_id}' not found."
        )
    return {"status": "ok", "passage": passage}


@router.post("/session/start")
async def start_session(
    req: ReadingSessionStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Initiate a reading coach session for the authenticated learner.
    """
    _check_feature_flag()
    learner_id = current_user.get("id")
    try:
        result = await start_reading_session(learner_id=learner_id, req=req)
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error starting reading session for user {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start reading session."
        )


@router.post("/session/complete")
async def complete_session(
    req: ReadingSessionCompleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit completed reading session telemetry.
    The server validates ownership, grades comprehension answers, calculates objective performance,
    updates the session, and triggers Phase 3 adaptive ZPD progression.
    """
    _check_feature_flag()
    learner_id = current_user.get("id")
    try:
        result = await complete_reading_session(learner_id=learner_id, req=req)
        return result
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error completing reading session {req.sessionId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process completed reading session."
        )


@router.get("/sessions")
async def get_sessions(
    student_id: Optional[str] = Query(None, description="Optional student ID for teacher inquiry"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve reading session history.
    Students may only view their own sessions.
    Teachers may view sessions for students enrolled in their classroom.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    role = current_user.get("role", "student")

    target_learner_id = user_id
    if student_id and student_id != user_id:
        if role != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not authorized to view other students' reading sessions."
            )
        # Verify teacher authorization
        teacher_code = current_user.get("classroomCode")
        student = await db.users.find_one(
            {"id": student_id, "classroomJoined": teacher_code},
            {"_id": 0}
        )
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in your assigned classroom."
            )
        target_learner_id = student_id

    try:
        sessions = await get_learner_sessions(learner_id=target_learner_id, limit=limit, skip=skip)
        return {
            "status": "ok",
            "learnerId": target_learner_id,
            "count": len(sessions),
            "sessions": sessions,
        }
    except Exception as e:
        logger.error(f"Error fetching reading sessions for {target_learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reading sessions."
        )


@router.get("/stats", response_model=ReadingStatsResponse)
async def get_reading_stats(
    student_id: Optional[str] = Query(None, description="Optional student ID for teacher inquiry"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve aggregated reading progress statistics for the learner.
    Includes words read, total minutes, average comprehension accuracy, and trend analysis.
    """
    _check_feature_flag()
    user_id = current_user.get("id")
    role = current_user.get("role", "student")

    target_learner_id = user_id
    if student_id and student_id != user_id:
        if role != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot view stats for other learners."
            )
        teacher_code = current_user.get("classroomCode")
        student = await db.users.find_one(
            {"id": student_id, "classroomJoined": teacher_code},
            {"_id": 0}
        )
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in your assigned classroom."
            )
        target_learner_id = student_id

    try:
        stats = await get_learner_reading_stats(learner_id=target_learner_id)
        return stats
    except Exception as e:
        logger.error(f"Error computing reading stats for {target_learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute reading statistics."
        )


# ─── Speech & Reading Analysis Endpoints ─────────────────────────────────────

def _check_speech_feature_flag():
    if not settings.V2_SPEECH_ANALYSIS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Speech & Reading Analysis is currently disabled via feature flags."
        )


@router.post("/speech/analyze", response_model=SpeechAnalysisResponse)
async def analyze_speech(
    req: SpeechAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Submits a speech reading transcript for authoritative server-side alignment and analysis.
    Computes word accuracy, coverage, WPM, pauses, and educational practice score.
    Strictly derives educational metrics; NO raw audio is stored.
    """
    _check_feature_flag()
    _check_speech_feature_flag()

    learner_id = current_user.get("id")
    try:
        result = await analyze_speech_reading(learner_id=learner_id, req=req)
        return result
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error analyzing speech for user {learner_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete speech reading analysis."
        )


@router.get("/speech/sessions/{session_id}")
async def get_speech_analysis(
    session_id: str,
    student_id: Optional[str] = Query(None, description="Optional student ID for teacher query"),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the speech reading analysis record for a specific reading session.
    Students may only view their own analysis.
    Teachers may view analyses for students in their assigned classroom.
    """
    _check_feature_flag()
    _check_speech_feature_flag()

    user_id = current_user.get("id")
    role = current_user.get("role", "student")

    target_learner_id = user_id
    is_teacher = False

    if student_id and student_id != user_id:
        if role != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot access speech analyses for other learners."
            )
        teacher_code = current_user.get("classroomCode")
        student = await db.users.find_one(
            {"id": student_id, "classroomJoined": teacher_code},
            {"_id": 0}
        )
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in your assigned classroom."
            )
        target_learner_id = student_id
        is_teacher = True

    try:
        analysis = await get_speech_analysis_for_session(
            session_id=session_id,
            learner_id=target_learner_id,
            is_teacher=is_teacher,
        )
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Speech analysis for session '{session_id}' not found."
            )
        return {"status": "ok", "analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving speech analysis for {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve speech reading analysis."
        )

