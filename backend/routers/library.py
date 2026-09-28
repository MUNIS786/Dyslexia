"""Document library CRUD."""
import uuid
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from database.database import db
from deps.deps import get_current_user

router = APIRouter(tags=["library"])


class DocSaveReq(BaseModel):
    title: str
    language: Optional[str] = "english"
    original: str
    simplified: Optional[str] = ""
    bullet_points: Optional[list] = []
    highlights: Optional[list] = []
    source: Optional[str] = "scan"   # scan | notes | assignment


@router.get("/library")
async def list_library(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    docs = await db.libraries.find(
        {"userId": user["id"]}, {"_id": 0}
    ).sort("createdAt", -1).to_list(500)
    return docs


@router.post("/library")
async def save_doc(req: DocSaveReq, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = {
        "id": "doc-" + str(uuid.uuid4())[:8],
        "userId": user["id"],
        "title": req.title or "Untitled",
        "language": req.language or "english",
        "wordCount": len((req.simplified or req.original).split()),
        "original": req.original,
        "simplified": req.simplified or "",
        "bullet_points": req.bullet_points or [],
        "highlights": req.highlights or [],
        "source": req.source or "scan",
        "createdAt": int(time.time()),
    }
    await db.libraries.insert_one({**doc})
    return doc


@router.get("/library/{doc_id}")
async def get_doc(doc_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    doc = await db.libraries.find_one({"id": doc_id, "userId": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.delete("/library/{doc_id}")
async def delete_doc(doc_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.libraries.delete_one({"id": doc_id, "userId": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Document not found")
    return {"deleted": doc_id}
