"""
Screening route — legacy endpoint for quick screening.
For full medically-aligned test, use /dyslexia-test/submit.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from services.screening_analyzer import analyze_screening
from database.database import db
from deps.deps import get_current_user_optional

router = APIRouter(tags=["screening"])


class ScreeningAnswer(BaseModel):
    question_type: str
    correct: Optional[bool] = True
    slow_response: Optional[bool] = False


class ScreeningReq(BaseModel):
    answers: List[ScreeningAnswer]
    method: Optional[str] = "combined"


@router.post("/screening")
async def screening(req: ScreeningReq, authorization: Optional[str] = Header(None)):
    """Quick screening — for full DST-aligned test use /dyslexia-test/submit."""
    if not req.answers:
        raise HTTPException(400, "No answers provided")

    result = analyze_screening([a.model_dump() for a in req.answers], req.method or "combined")

    user = await get_current_user_optional(authorization)
    if user:
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"readingProfile": {
                "type": result["type"],
                "level": result["level"],
                "score": result["score"],
                "recommendation": result["recommendation"],
            }}},
        )
    return result
