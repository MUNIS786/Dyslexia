"""
Teacher dashboard — students list with full progress, class analytics,
lesson plan generation. Teacher does NOT have scan/library/plan routes.
"""
import time
from typing import Optional
from fastapi import APIRouter, Header
from pydantic import BaseModel

from database.database import db
from deps.deps import require_teacher
from services.ai_service import generate_lesson_plan

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/students")
async def get_students(authorization: Optional[str] = Header(None)):
    """Full student roster with live progress + assignment completion."""
    teacher = await require_teacher(authorization)
    code = teacher.get("classroomCode")
    if not code:
        return []

    students = await db.users.find(
        {"role": "student", "classroomJoined": code},
        {"_id": 0, "passwordHash": 0}
    ).sort("createdAt", -1).to_list(500)

    # All assignments for this classroom
    all_assignments = await db.assignments.find(
        {"classroomCode": code}, {"_id": 0, "id": 1}
    ).to_list(200)
    total_assignments = len(all_assignments)
    assignment_ids = [a["id"] for a in all_assignments]

    out = []
    for s in students:
        prog = await db.progress.find_one({"userId": s["id"]}, {"_id": 0}) or {}
        rp = s.get("readingProfile") or {}
        comp = prog.get("avgComprehension", 0)
        streak = prog.get("streak", 0)
        sessions = prog.get("sessionCount", 0)

        # Count submissions for this student
        submitted_count = await db.submissions.count_documents(
            {"studentId": s["id"], "assignmentId": {"$in": assignment_ids}}
        ) if assignment_ids else 0

        # Determine status
        if not rp.get("type"):
            status = "not_screened"
        elif comp < 40 or sessions == 0:
            status = "needs_attention"
        elif comp < 65:
            status = "progressing"
        else:
            status = "on_track"

        last_active = "Never"
        if prog.get("recentActivity"):
            last_active = prog["recentActivity"][0].get("time", "Recently")

        out.append({
            "id": s["id"], "name": s["name"], "email": s["email"],
            "language": (s.get("languages") or ["english"])[0].title(),
            "profile": rp.get("type", "Not screened"),
            "profileLevel": rp.get("level", ""),
            "profileScore": rp.get("score", 0),
            "status": status, "streak": streak,
            "comprehension": comp,
            "sessions": sessions,
            "docsScanned": prog.get("docsScanned", 0),
            "wordsRead": prog.get("wordsRead", 0),
            "wordsMastered": prog.get("wordsMastered", 0),
            "planGenerated": prog.get("planGenerated", False),
            "screeningDone": bool(rp.get("type")),
            "assignmentsSubmitted": submitted_count,
            "assignmentsTotal": total_assignments,
            "submissionRate": round((submitted_count / total_assignments) * 100) if total_assignments else 0,
            "lastActive": last_active,
            "weeklyActivity": prog.get("weeklyActivity", {}),
            "comprehensionScores": prog.get("comprehensionScores", [])[-5:],
            "joinedAt": s.get("createdAt", 0),
        })
    return out


@router.get("/student/{student_id}")
async def get_student_detail(student_id: str, authorization: Optional[str] = Header(None)):
    """Full drill-down for one student."""
    teacher = await require_teacher(authorization)
    student = await db.users.find_one(
        {"id": student_id, "classroomJoined": teacher.get("classroomCode")},
        {"_id": 0, "passwordHash": 0}
    )
    if not student:
        from fastapi import HTTPException
        raise HTTPException(404, "Student not found in your classroom")

    prog = await db.progress.find_one({"userId": student_id}, {"_id": 0}) or {}
    plan = await db.ai_plans.find_one({"userId": student_id}, {"_id": 0})

    # Get all submissions
    submissions = await db.submissions.find(
        {"studentId": student_id}, {"_id": 0}
    ).sort("submittedAt", -1).to_list(50)

    # Attach assignment titles
    for sub in submissions:
        a = await db.assignments.find_one({"id": sub["assignmentId"]}, {"_id": 0, "title": 1})
        sub["assignmentTitle"] = (a or {}).get("title", "Unknown")

    return {
        "student": student,
        "progress": prog,
        "plan": plan,
        "submissions": submissions,
    }


@router.get("/analytics")
async def class_analytics(authorization: Optional[str] = Header(None)):
    """Aggregate stats for the whole class."""
    teacher = await require_teacher(authorization)
    code = teacher.get("classroomCode")
    if not code:
        return {}

    students = await db.users.find(
        {"role": "student", "classroomJoined": code},
        {"_id": 0, "id": 1, "readingProfile": 1}
    ).to_list(500)

    comp_scores, type_dist, level_dist = [], {}, {}
    screened = needs_attention = on_track = 0

    for s in students:
        rp = s.get("readingProfile") or {}
        prog = await db.progress.find_one({"userId": s["id"]}, {"_id": 0}) or {}
        comp = prog.get("avgComprehension", 0)
        if comp > 0:
            comp_scores.append(comp)
        if rp.get("type"):
            screened += 1
            t = rp["type"]
            type_dist[t] = type_dist.get(t, 0) + 1
            l = rp.get("level", "low")
            level_dist[l] = level_dist.get(l, 0) + 1
        if comp < 40:
            needs_attention += 1
        elif comp >= 65:
            on_track += 1

    total = len(students)
    assignments = await db.assignments.count_documents({"classroomCode": code})
    submissions = await db.submissions.count_documents({
        "assignmentId": {"$in": [
            a["id"] async for a in db.assignments.find({"classroomCode": code}, {"_id": 0, "id": 1})
        ]}
    }) if assignments else 0

    return {
        "studentCount": total,
        "screenedCount": screened,
        "avgComprehension": round(sum(comp_scores) / len(comp_scores)) if comp_scores else 0,
        "needsAttention": needs_attention,
        "onTrack": on_track,
        "dyslexiaTypeDistribution": type_dist,
        "severityDistribution": level_dist,
        "assignmentsCreated": assignments,
        "submissionsReceived": submissions,
        "submissionRate": round((submissions / (assignments * total)) * 100) if assignments and total else 0,
    }


class LessonPlanReq(BaseModel):
    studentName: Optional[str] = "Student"
    profile: Optional[str] = "Sound-First"
    subject: Optional[str] = "Reading"
    language: Optional[str] = "English"


@router.post("/lesson-plan")
async def lesson_plan(req: LessonPlanReq, authorization: Optional[str] = Header(None)):
    await require_teacher(authorization)
    plan = await generate_lesson_plan(
        req.studentName or "Student", req.profile or "Sound-First",
        req.subject or "Reading", req.language or "English",
    )
    return {"plan": plan}
