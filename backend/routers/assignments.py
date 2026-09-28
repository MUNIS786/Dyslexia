"""
Assignments — Google Classroom-style.
Teacher: create (with optional dyslexia-converted text), track submissions per student.
Student: see assignments, submit, get grade & feedback back.
"""
import uuid
import time
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel

from database.database import db
from deps.deps import get_current_user, require_teacher
from services.ai_service import simplify_with_ai
from services.offline_simplifier import simplify_offline
from services.ocr_service import ocr_image, preprocess_image
import os
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/assignments", tags=["assignments"])


class CreateReq(BaseModel):
    title: str
    description: Optional[str] = ""
    originalText: Optional[str] = ""
    language: Optional[str] = "english"
    dueInDays: Optional[int] = 7
    maxScore: Optional[int] = 100


class GradeReq(BaseModel):
    submissionId: str
    score: int
    feedback: Optional[str] = ""


class SubmitReq(BaseModel):
    assignmentId: str
    score: Optional[int] = 0
    answers: Optional[list] = []
    comment: Optional[str] = ""
    timeSpentMinutes: Optional[float] = 0


# ── Teacher: create assignment ────────────────────────────────────────────────
@router.post("")
async def create_assignment(req: CreateReq, authorization: Optional[str] = Header(None)):
    teacher = await require_teacher(authorization)
    code = teacher.get("classroomCode")
    if not code:
        raise HTTPException(400, "Teacher has no classroom")

    now = int(time.time())
    aid = str(uuid.uuid4())

    # Auto-convert text to dyslexia-friendly format
    original = req.originalText or ""
    simplified_data = None
    if original.strip():
        simplified_data, _ = await simplify_with_ai(original, req.language or "english")
        if not simplified_data:
            simplified_data = simplify_offline(original)

    doc = {
        "id": aid, "classroomCode": code,
        "teacherId": teacher["id"], "teacherName": teacher["name"],
        "title": req.title, "description": req.description or "",
        "originalText": original,
        "simplifiedText": (simplified_data or {}).get("text", ""),
        "bulletPoints": (simplified_data or {}).get("bullet_points", []),
        "highlights": (simplified_data or {}).get("highlights", []),
        "language": req.language or "english",
        "maxScore": req.maxScore or 100,
        "createdAt": now, "dueDate": now + 86400 * (req.dueInDays or 7),
    }
    await db.assignments.insert_one({**doc})

    # Notify all students in classroom
    students = await db.users.find(
        {"role": "student", "classroomJoined": code}, {"_id": 0, "id": 1}
    ).to_list(500)
    if students:
        notifs = [{
            "id": str(uuid.uuid4()), "userId": s["id"],
            "title": "New Assignment",
            "message": f"{teacher['name']} assigned: {req.title}",
            "type": "assignment", "assignmentId": aid,
            "read": False, "createdAt": now,
        } for s in students]
        await db.notifications.insert_many(notifs)

    return doc


@router.post("/upload-and-create")
async def upload_and_create(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    language: str = Form("english"),
    dueInDays: int = Form(7),
    authorization: Optional[str] = Header(None),
):
    """Teacher uploads a document → OCR + dyslexia-convert → create assignment."""
    teacher = await require_teacher(authorization)
    code = teacher.get("classroomCode")
    if not code:
        raise HTTPException(400, "No classroom")

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    path = str(UPLOAD_DIR / f"assign_{uuid.uuid4().hex}{ext}")
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    extracted = ""
    try:
        is_pdf = ext == ".pdf"
        if is_pdf:
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                extracted = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
            except Exception:
                pass
        if not extracted:
            clean = preprocess_image(path)
            extracted = ocr_image(clean, lang=language)
            if clean != path:
                try: os.remove(clean)
                except: pass
    finally:
        try: os.remove(path)
        except: pass

    if not extracted:
        raise HTTPException(400, "Could not extract text from file")

    simplified_data, _ = await simplify_with_ai(extracted, language)
    if not simplified_data:
        simplified_data = simplify_offline(extracted)

    now = int(time.time())
    aid = str(uuid.uuid4())
    doc = {
        "id": aid, "classroomCode": code,
        "teacherId": teacher["id"], "teacherName": teacher["name"],
        "title": title, "description": description,
        "originalText": extracted,
        "simplifiedText": simplified_data.get("text", ""),
        "bulletPoints": simplified_data.get("bullet_points", []),
        "highlights": simplified_data.get("highlights", []),
        "language": language, "maxScore": 100,
        "createdAt": now, "dueDate": now + 86400 * dueInDays,
    }
    await db.assignments.insert_one({**doc})

    students = await db.users.find(
        {"role": "student", "classroomJoined": code}, {"_id": 0, "id": 1}
    ).to_list(500)
    if students:
        notifs = [{
            "id": str(uuid.uuid4()), "userId": s["id"],
            "title": "New Assignment",
            "message": f"{teacher['name']} assigned: {title}",
            "type": "assignment", "assignmentId": aid,
            "read": False, "createdAt": now,
        } for s in students]
        await db.notifications.insert_many(notifs)

    return doc


# ── List (teacher sees all + submission counts; student sees own status) ──────
@router.get("")
async def list_assignments(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    now = int(time.time())

    if user["role"] == "teacher":
        code = user.get("classroomCode")
        assignments = await db.assignments.find(
            {"classroomCode": code}, {"_id": 0}
        ).sort("createdAt", -1).to_list(500)
        for a in assignments:
            a["submissionCount"] = await db.submissions.count_documents({"assignmentId": a["id"]})
            a["studentCount"] = await db.users.count_documents({"role": "student", "classroomJoined": code})
            a["overdue"] = a.get("dueDate", 0) < now
        return assignments

    code = user.get("classroomJoined")
    if not code:
        return []
    assignments = await db.assignments.find(
        {"classroomCode": code}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    for a in assignments:
        sub = await db.submissions.find_one(
            {"assignmentId": a["id"], "studentId": user["id"]}, {"_id": 0}
        )
        a["submitted"] = bool(sub)
        a["mySubmission"] = sub
        a["overdue"] = a.get("dueDate", 0) < now and not bool(sub)
    return assignments


@router.get("/{aid}")
async def get_assignment(aid: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    a = await db.assignments.find_one({"id": aid}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Not found")
    if user["role"] == "teacher":
        subs = await db.submissions.find({"assignmentId": aid}, {"_id": 0}).to_list(500)
        # Attach student profile info to each submission
        for sub in subs:
            student = await db.users.find_one(
                {"id": sub["studentId"]}, {"_id": 0, "name": 1, "readingProfile": 1}
            ) or {}
            sub["studentProfile"] = student.get("readingProfile")
        a["submissions"] = subs
        a["totalStudents"] = await db.users.count_documents(
            {"role": "student", "classroomJoined": a["classroomCode"]}
        )
    else:
        sub = await db.submissions.find_one(
            {"assignmentId": aid, "studentId": user["id"]}, {"_id": 0}
        )
        a["mySubmission"] = sub
    return a


@router.post("/submit")
async def submit_assignment(req: SubmitReq, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if user["role"] != "student":
        raise HTTPException(403, "Only students can submit")

    a = await db.assignments.find_one({"id": req.assignmentId})
    if not a:
        raise HTTPException(404, "Assignment not found")

    now = int(time.time())
    sub = {
        "id": str(uuid.uuid4()),
        "assignmentId": req.assignmentId,
        "studentId": user["id"], "studentName": user["name"],
        "score": int(req.score or 0),
        "answers": req.answers or [],
        "comment": req.comment or "",
        "timeSpentMinutes": req.timeSpentMinutes or 0,
        "graded": False, "teacherFeedback": "",
        "submittedAt": now,
    }
    await db.submissions.update_one(
        {"assignmentId": req.assignmentId, "studentId": user["id"]},
        {"$set": sub}, upsert=True,
    )

    # Update student progress
    await db.progress.update_one(
        {"userId": user["id"]},
        {"$inc": {"tasksCompleted": 1}},
        upsert=True,
    )

    # Record comprehension score
    if req.score and req.score > 0:
        from routers.progress import _load, _save
        prog = await _load(user["id"])
        scores = (prog.get("comprehensionScores") or [])[-9:]
        scores.append(max(0, min(100, req.score)))
        prog["comprehensionScores"] = scores
        prog["avgComprehension"] = round(sum(scores) / len(scores))
        act = prog.get("recentActivity", [])
        act.insert(0, {"icon": "check", "text": f"Submitted '{a['title']}' — {req.score}%", "time": "Just now"})
        prog["recentActivity"] = act[:10]
        await _save(user["id"], prog)

    # Notify teacher
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "userId": a["teacherId"],
        "title": "Assignment Submitted",
        "message": f"{user['name']} submitted '{a['title']}' — {sub['score']}%",
        "type": "submission", "assignmentId": req.assignmentId,
        "studentId": user["id"], "studentName": user["name"],
        "read": False, "createdAt": now,
    })
    return sub


@router.post("/grade")
async def grade_submission(req: GradeReq, authorization: Optional[str] = Header(None)):
    """Teacher grades a submission and sends feedback to student."""
    teacher = await require_teacher(authorization)
    sub = await db.submissions.find_one({"id": req.submissionId}, {"_id": 0})
    if not sub:
        raise HTTPException(404, "Submission not found")

    now = int(time.time())
    await db.submissions.update_one(
        {"id": req.submissionId},
        {"$set": {"score": req.score, "teacherFeedback": req.feedback or "", "graded": True, "gradedAt": now}}
    )

    # Notify student of grade
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "userId": sub["studentId"],
        "title": "Assignment Graded",
        "message": f"You got {req.score}% on your assignment. {req.feedback or ''}".strip(),
        "type": "grade", "assignmentId": sub["assignmentId"],
        "read": False, "createdAt": now,
    })
    return {"graded": True, "score": req.score}


@router.delete("/{aid}")
async def delete_assignment(aid: str, authorization: Optional[str] = Header(None)):
    teacher = await require_teacher(authorization)
    a = await db.assignments.find_one({"id": aid})
    if not a or a["teacherId"] != teacher["id"]:
        raise HTTPException(404, "Not found")
    await db.assignments.delete_one({"id": aid})
    await db.submissions.delete_many({"assignmentId": aid})
    return {"deleted": aid}
