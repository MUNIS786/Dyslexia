"""
backend/routers/v2_parent.py — V2 Parent & Guardian Portal API Router.

Endpoints:
- GET   /api/v2/parent/profile                           (Parent profile and linked learners count)
- GET   /api/v2/parent/learners                          (List active/pending linked learners)
- POST  /api/v2/parent/link/claim-code                   (Redeem 48h one-time invitation code)
- POST  /api/v2/parent/link/request                      (Initiate link request via student email/ID)
- POST  /api/v2/parent/links/{link_id}/revoke            (Revoke active relationship immediately)
- GET   /api/v2/parent/dashboard                         (Default/selected child dashboard)
- GET   /api/v2/parent/learners/{student_id}/dashboard   (Specific child dashboard)
- GET   /api/v2/parent/learners/{student_id}/activity    (Bounded chronological activity timeline)
- POST  /api/v2/parent/invitations/generate              (Student or Teacher generates invitation code)
- GET   /api/v2/parent/student/requests                  (Student reviews pending link requests)
- POST  /api/v2/parent/student/requests/{req_id}/approve (Student/Teacher approves link request)
- POST  /api/v2/parent/student/requests/{req_id}/reject  (Student/Teacher rejects link request)
- GET   /api/v2/parent/student/links                     (Student views active parent connections)
- POST  /api/v2/parent/student/links/{link_id}/revoke    (Student revokes parent connection)

Security & Governance:
- Protected by server-side authorization on every route (students blocked from parent routes, etc.).
- Governed by feature flag: V2_PARENT_PORTAL (returns 503 if disabled).
- Non-clinical, descriptive educational indicators only. Zero medical claims.
- Private AI tutor chat transcripts, raw speech audio, and teacher notes are excluded.
"""
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status

from deps.deps import get_current_user, require_teacher, require_parent
from core.config import settings
from database.database import db
from models.v2_parent import (
    ParentLinkItem,
    ParentProfileSummary,
    ClaimCodeRequest,
    LinkRequestCreate,
    InvitationCreateResponse,
    ParentDashboardResponse,
)
from services.parent.parent_service import (
    generate_invitation_code,
    claim_invitation_code,
    request_student_link,
    approve_link_request,
    reject_link_request,
    revoke_parent_link,
    verify_parent_student_access,
    get_parent_learners,
    get_parent_dashboard,
    get_parent_student_activities,
    get_parent_profile_summary,
    get_student_pending_requests,
    get_student_active_links,
)

logger = logging.getLogger("dyslexaid.routers.v2_parent")
router = APIRouter(prefix="/v2/parent", tags=["V2 Parent & Guardian Portal"])


def _check_feature_flag():
    """Ensures V2_PARENT_PORTAL feature flag is enabled."""
    if not getattr(settings, "V2_PARENT_PORTAL", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="V2 Parent & Guardian Portal is currently disabled via feature flags."
        )


class GenerateInvitationReq(BaseModel):
    studentId: Optional[str] = Field(None, description="Target student ID (optional if called by student)")


# ─── 1. Parent Profile & Linked Children ─────────────────────────────────────

@router.get("/profile", response_model=ParentProfileSummary)
async def get_profile(parent: dict = Depends(require_parent)):
    """Retrieve the authenticated parent's profile and summary counts."""
    _check_feature_flag()
    return await get_parent_profile_summary(parent)


@router.get("/learners", response_model=List[ParentLinkItem])
async def list_linked_learners(parent: dict = Depends(require_parent)):
    """List all learners linked (active and pending) to the authenticated parent."""
    _check_feature_flag()
    return await get_parent_learners(parent["id"])


# ─── 2. Linking Workflows (Parent actions) ───────────────────────────────────

@router.post("/link/claim-code", response_model=ParentLinkItem, status_code=status.HTTP_201_CREATED)
async def claim_code(
    req: ClaimCodeRequest,
    parent: dict = Depends(require_parent),
):
    """
    Parent redeems a short-lived invitation code to instantly establish an active link.
    """
    _check_feature_flag()
    return await claim_invitation_code(
        parent_user=parent,
        code=req.code,
        relationship=req.relationship or "parent",
    )


@router.post("/link/request", response_model=ParentLinkItem, status_code=status.HTTP_201_CREATED)
async def request_link(
    req: LinkRequestCreate,
    parent: dict = Depends(require_parent),
):
    """
    Parent submits a link request using the student's email or student ID.
    Enters 'pending' state until approved by the student or teacher.
    """
    _check_feature_flag()
    return await request_student_link(
        parent_user=parent,
        student_identifier=req.studentIdentifier,
        relationship=req.relationship or "parent",
    )


@router.post("/links/{link_id}/revoke")
async def revoke_link_as_parent(
    link_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Immediately revokes an active parent-student relationship.
    Callable by the parent or the linked student.
    """
    _check_feature_flag()
    return await revoke_parent_link(revoker_user=current_user, link_id=link_id)


# ─── 3. Parent Dashboard & Activity Timeline ─────────────────────────────────

@router.get("/dashboard", response_model=ParentDashboardResponse)
async def get_dashboard_default(
    student_id: Optional[str] = Query(None, description="Optional specific student ID"),
    parent: dict = Depends(require_parent),
):
    """
    Retrieve parent dashboard metrics, reading sessions, adaptive tasks, and home suggestions.
    """
    _check_feature_flag()
    return await get_parent_dashboard(parent_user=parent, student_id=student_id)


@router.get("/learners/{student_id}/dashboard", response_model=ParentDashboardResponse)
async def get_dashboard_for_learner(
    student_id: str,
    parent: dict = Depends(require_parent),
):
    """
    Retrieve parent dashboard for a specific authorized learner.
    Enforces active verified relationship check.
    """
    _check_feature_flag()
    return await get_parent_dashboard(parent_user=parent, student_id=student_id)


@router.get("/learners/{student_id}/activity")
async def get_learner_activity(
    student_id: str,
    limit: int = Query(15, ge=1, le=50, description="Max activities to return"),
    parent: dict = Depends(require_parent),
):
    """
    Retrieve bounded chronological activity timeline for an authorized learner.
    Strictly excludes private AI tutor conversations and teacher-only notes.
    """
    _check_feature_flag()
    return await get_parent_student_activities(parent_user=parent, student_id=student_id, limit=limit)


# ─── 4. Student & Teacher Invitation & Approval Workflows ─────────────────────

@router.post("/invitations/generate", response_model=InvitationCreateResponse)
async def create_invitation_code(
    req: GenerateInvitationReq,
    current_user: dict = Depends(get_current_user),
):
    """
    Generates a secure 48h one-time invitation code.
    Callable by the student themselves or a teacher for an enrolled student.
    """
    _check_feature_flag()
    user_role = current_user.get("role")
    user_id = current_user.get("id")

    if user_role == "student":
        target_student_id = user_id
    elif user_role == "teacher":
        if not req.studentId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="studentId is required when generated by a teacher."
            )
        # Verify student is in this teacher's classroom
        teacher_code = current_user.get("classroomCode")
        student = await db.users.find_one({"id": req.studentId, "classroomJoined": teacher_code}, {"_id": 0})
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in your assigned classroom."
            )
        target_student_id = req.studentId
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students or teachers can generate parent invitation codes."
        )

    result = await generate_invitation_code(
        student_id=target_student_id,
        creator_id=user_id,
        creator_role=user_role,
    )
    return InvitationCreateResponse(**result)


@router.get("/student/requests")
async def get_my_link_requests(current_user: dict = Depends(get_current_user)):
    """
    Student view: list incoming parent link requests waiting for approval.
    """
    _check_feature_flag()
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their incoming link requests."
        )
    return await get_student_pending_requests(current_user["id"])


@router.post("/student/requests/{request_id}/approve", response_model=ParentLinkItem)
async def approve_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Student or assigned teacher approves a pending parent link request.
    """
    _check_feature_flag()
    return await approve_link_request(approver_user=current_user, request_id=request_id)


@router.post("/student/requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Student or assigned teacher rejects a pending parent link request.
    """
    _check_feature_flag()
    return await reject_link_request(approver_user=current_user, request_id=request_id)


@router.get("/student/links")
async def get_my_active_parent_links(current_user: dict = Depends(get_current_user)):
    """
    Student view: list active parent connections linked to their account.
    """
    _check_feature_flag()
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their active parent connections."
        )
    return await get_student_active_links(current_user["id"])


@router.post("/student/links/{link_id}/revoke")
async def revoke_link_as_student(
    link_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Student view: immediately revokes an active parent connection.
    """
    _check_feature_flag()
    return await revoke_parent_link(revoker_user=current_user, link_id=link_id)
