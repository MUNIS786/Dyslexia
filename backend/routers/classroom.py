"""
Classroom — Google Classroom-style.
- Teacher gets a code on signup.
- Student joins via code; teacher sees them immediately.
- Teacher can post announcements. Students see pending assignments on join.
"""
import time
import uuid
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from database.database import db
from deps.deps import get_current_user, require_teacher

router = APIRouter(prefix="/classroom", tags=["classroom"])


class JoinReq(BaseModel):
    code: str


class AnnouncementReq(BaseModel):
    message: str


@router.post("/join")
async def join(req: JoinReq, authorization: Optional[str] = Header(None)):
    """Student joins a classroom. Teacher is notified in real-time."""
    user = await get_current_user(authorization)
    if user["role"] != "student":
        raise HTTPException(403, "Only students can join classrooms")

    code = req.code.strip().upper()
    if not code:
        raise HTTPException(400, "No code provided")

    # Already in this classroom
    if user.get("classroomJoined") == code:
        classroom = await db.classrooms.find_one({"code": code}, {"_id": 0})
        return {"success": True, "alreadyJoined": True,
                "teacherName": classroom.get("teacherName", ""),
                "classroomCode": code, "schoolName": classroom.get("schoolName", "")}

    classroom = await db.classrooms.find_one({"code": code}, {"_id": 0})
    if not classroom:
        raise HTTPException(404, "Invalid classroom code. Ask your teacher for the correct code.")

    now = int(time.time())
    # Update student's classroom
    await db.users.update_one({"id": user["id"]}, {"$set": {"classroomJoined": code}})

    # Notify teacher that a new student joined
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "userId": classroom["teacherId"],
        "title": "New Student Joined",
        "message": f"{user['name']} joined your classroom.",
        "type": "student_joined",
        "studentId": user["id"],
        "studentName": user["name"],
        "read": False, "createdAt": now,
    })

    # Give student any existing open assignments as pending notifications
    open_assignments = await db.assignments.find(
        {"classroomCode": code, "dueDate": {"$gt": now}},
        {"_id": 0, "id": 1, "title": 1}
    ).to_list(20)

    if open_assignments:
        notifs = [{
            "id": str(uuid.uuid4()), "userId": user["id"],
            "title": "Assignment Waiting",
            "message": f"Complete this assignment from your teacher: {a['title']}",
            "type": "assignment", "assignmentId": a["id"],
            "read": False, "createdAt": now,
        } for a in open_assignments]
        await db.notifications.insert_many(notifs)

    return {
        "success": True,
        "teacherName": classroom.get("teacherName", ""),
        "classroomCode": code,
        "schoolName": classroom.get("schoolName", ""),
        "pendingAssignments": len(open_assignments),
    }


@router.get("/info")
async def info(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    code = user.get("classroomJoined") or user.get("classroomCode")
    if not code:
        return {"classroom": None}
    classroom = await db.classrooms.find_one({"code": code}, {"_id": 0})
    if not classroom:
        return {"classroom": None}
    count = await db.users.count_documents({"role": "student", "classroomJoined": code})
    classroom["studentCount"] = count
    return {"classroom": classroom}


@router.get("/students")
async def list_students(authorization: Optional[str] = Header(None)):
    """Teacher: list all students with basic info."""
    teacher = await require_teacher(authorization)
    code = teacher.get("classroomCode")
    if not code:
        return []
    students = await db.users.find(
        {"role": "student", "classroomJoined": code},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "readingProfile": 1,
         "onboardingComplete": 1, "languages": 1, "createdAt": 1}
    ).sort("createdAt", -1).to_list(500)
    return students


@router.post("/announce")
async def announce(req: AnnouncementReq, authorization: Optional[str] = Header(None)):
    """Teacher posts a classroom announcement to all students."""
    teacher = await require_teacher(authorization)
    code = teacher.get("classroomCode")
    if not code:
        raise HTTPException(400, "No classroom")
    now = int(time.time())
    students = await db.users.find(
        {"role": "student", "classroomJoined": code}, {"_id": 0, "id": 1}
    ).to_list(500)
    if not students:
        return {"sent": 0}
    notifs = [{
        "id": str(uuid.uuid4()), "userId": s["id"],
        "title": f"📢 {teacher['name']}",
        "message": req.message, "type": "announcement",
        "read": False, "createdAt": now,
    } for s in students]
    await db.notifications.insert_many(notifs)
    return {"sent": len(notifs)}


@router.post("/leave")
async def leave(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    if user["role"] != "student":
        raise HTTPException(403, "Only students can leave classrooms")
    await db.users.update_one({"id": user["id"]}, {"$set": {"classroomJoined": None}})
    return {"success": True}
