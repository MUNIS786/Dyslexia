"""
backend/routers/v2_content_authoring.py — Phase 16:
Learning Content Authoring & Quality Management API.

Endpoints:
- GET  /api/v2/content-authoring/items
- POST /api/v2/content-authoring/drafts
- GET  /api/v2/content-authoring/drafts/{content_id}
- PUT  /api/v2/content-authoring/drafts/{content_id}
- POST /api/v2/content-authoring/validate
- POST /api/v2/content-authoring/drafts/{content_id}/submit
- GET  /api/v2/content-authoring/review-queue
- POST /api/v2/content-authoring/review/{content_id}/decision
- POST /api/v2/content-authoring/items/{content_id}/publish
- POST /api/v2/content-authoring/items/{content_id}/archive
- POST /api/v2/content-authoring/items/{content_id}/revise
- GET  /api/v2/content-authoring/items/{content_id}/history
- GET  /api/v2/content-authoring/translations/{translation_group_id}

Security & Authorization:
- Strict Educator / Administrator role verification (HTTP 403 for students and parents)
- Multi-tenant boundary checks (classroom isolation)
- Separation of duties enforcement (authors cannot approve or publish their own drafts)
- Governed by V2_CONTENT_AUTHORING feature flag (HTTP 503 if disabled)
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user
from core.config import settings
from models.v2_content_authoring import (
    ContentValidationResult,
    ContentDraftCreateRequest,
    ContentDraftUpdateRequest,
    ContentReviewDecisionRequest,
    ContentItemResponse,
    ContentListResponse,
    ContentHistoryResponse,
)
from services.learning.content_authoring import (
    validate_content,
    create_content_draft,
    update_content_draft,
    submit_content_for_review,
    review_content,
    publish_content,
    archive_content,
    create_content_revision,
    list_content_items,
    get_content_item,
    get_review_queue,
    get_content_history,
    get_translation_completeness,
)

logger = logging.getLogger("dyslexaid.routers.v2_content_authoring")
router = APIRouter(prefix="/v2/content-authoring", tags=["V2 Content Authoring & Quality Management"])


def _check_feature_flag():
    """Ensures V2_CONTENT_AUTHORING feature flag is enabled."""
    if not getattr(settings, "V2_CONTENT_AUTHORING", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Content Authoring Engine is currently disabled via feature flags."
        )


def require_educator(current_user: dict = Depends(get_current_user)):
    """Enforces that the authenticated user is an authorized teacher or administrator."""
    _check_feature_flag()
    role = current_user.get("role")
    if role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Educator or Administrator authorization required for content authoring."
        )
    return current_user


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/items", response_model=ContentListResponse)
async def list_items(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by state: DRAFT, IN_REVIEW, etc."),
    language_filter: Optional[str] = Query(None, alias="language", description="Filter by language: en, hi, mr"),
    difficulty_filter: Optional[int] = Query(None, alias="difficulty", description="Filter by difficulty tier 1-5"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(require_educator),
):
    """Lists authored content items visible to the educator."""
    return await list_content_items(
        user=current_user,
        status_filter=status_filter,
        language_filter=language_filter,
        difficulty_filter=difficulty_filter,
        limit=limit,
        skip=skip,
    )


@router.post("/drafts", response_model=ContentItemResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    payload: ContentDraftCreateRequest,
    current_user: dict = Depends(require_educator),
):
    """Creates a new educational content draft."""
    try:
        return await create_content_draft(user=current_user, req=payload)
    except Exception as e:
        logger.error(f"Error creating draft: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/drafts/{content_id}", response_model=ContentItemResponse)
async def get_draft(
    content_id: str,
    current_user: dict = Depends(require_educator),
):
    """Retrieves full details of a specific authored item or draft."""
    try:
        return await get_content_item(user=current_user, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.put("/drafts/{content_id}", response_model=ContentItemResponse)
async def update_draft(
    content_id: str,
    payload: ContentDraftUpdateRequest,
    current_user: dict = Depends(require_educator),
):
    """Updates an editable content draft in DRAFT or CHANGES_REQUESTED state."""
    try:
        return await update_content_draft(user=current_user, content_id=content_id, req=payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/validate", response_model=ContentValidationResult)
async def validate_draft(
    payload: Dict[str, Any],
    current_user: dict = Depends(require_educator),
):
    """Performs deterministic server-side quality and multilingual validation on a draft."""
    return validate_content(payload)


@router.post("/drafts/{content_id}/submit", response_model=ContentItemResponse)
async def submit_for_review(
    content_id: str,
    current_user: dict = Depends(require_educator),
):
    """Submits a validated draft for peer or administrator review."""
    try:
        return await submit_content_for_review(user=current_user, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get("/review-queue", response_model=ContentListResponse)
async def get_queue(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(require_educator),
):
    """Retrieves all content items awaiting peer review."""
    return await get_review_queue(user=current_user, limit=limit, skip=skip)


@router.post("/review/{content_id}/decision", response_model=ContentItemResponse)
async def review_decision(
    content_id: str,
    payload: ContentReviewDecisionRequest,
    current_user: dict = Depends(require_educator),
):
    """
    Submits a review decision (APPROVE, REQUEST_CHANGES, REJECT).
    Enforces separation of duties (authors cannot review their own content).
    """
    try:
        return await review_content(user=current_user, content_id=content_id, req=payload)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/items/{content_id}/publish", response_model=ContentItemResponse)
async def publish_item(
    content_id: str,
    current_user: dict = Depends(require_educator),
):
    """Publishes approved content into the active catalog for Phase 15 student discovery."""
    try:
        return await publish_content(user=current_user, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/items/{content_id}/archive", response_model=ContentItemResponse)
async def archive_item(
    content_id: str,
    current_user: dict = Depends(require_educator),
):
    """Archives published content, withdrawing it from student discovery while preserving history."""
    try:
        return await archive_content(user=current_user, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/items/{content_id}/revise", response_model=ContentItemResponse)
async def revise_item(
    content_id: str,
    current_user: dict = Depends(require_educator),
):
    """Creates a new draft version of a published or archived content item."""
    try:
        return await create_content_revision(user=current_user, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.get("/items/{content_id}/history", response_model=ContentHistoryResponse)
async def get_history(
    content_id: str,
    current_user: dict = Depends(require_educator),
):
    """Retrieves immutable audit timeline and version history for a content item."""
    try:
        return await get_content_history(user=current_user, content_id=content_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))


@router.get("/translations/{translation_group_id}")
async def get_translations(
    translation_group_id: str,
    current_user: dict = Depends(require_educator),
):
    """Retrieves multilingual translation completeness across en, hi, and mr."""
    return await get_translation_completeness(translation_group_id)
