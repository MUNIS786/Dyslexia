"""Notifications — polling + SSE stream for real-time updates."""
import asyncio
import time
import json
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from database.database import db
from deps.deps import get_current_user, verify_token

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(authorization: Optional[str] = Header(None), limit: int = 30):
    user = await get_current_user(authorization)
    items = await db.notifications.find(
        {"userId": user["id"]}, {"_id": 0}
    ).sort("createdAt", -1).to_list(int(limit))
    unread = await db.notifications.count_documents({"userId": user["id"], "read": False})
    return {"items": items, "unread": unread}


@router.get("/stream")
async def stream(token: str):
    """SSE stream — connect with EventSource('/api/notifications/stream?token=JWT')"""
    uid = verify_token(token)
    if not uid:
        raise HTTPException(401, "Invalid token")

    async def generator():
        last_check = int(time.time()) - 1
        try:
            while True:
                new = await db.notifications.find(
                    {"userId": uid, "createdAt": {"$gte": last_check}, "read": False},
                    {"_id": 0}
                ).sort("createdAt", -1).to_list(10)
                if new:
                    for item in new:
                        yield f"data: {json.dumps(item)}\n\n"
                last_check = int(time.time())
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/read/{notif_id}")
async def mark_read(notif_id: str, authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    res = await db.notifications.update_one(
        {"id": notif_id, "userId": user["id"]}, {"$set": {"read": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(authorization: Optional[str] = Header(None)):
    user = await get_current_user(authorization)
    await db.notifications.update_many({"userId": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}
