"""
backend/routers/health.py — Health and Readiness Monitoring Endpoints.

Provides:
- GET /health (and /api/health): Liveness probe confirming FastAPI process is active.
- GET /ready (and /api/ready): Readiness probe verifying MongoDB connectivity with timeout.
"""
import time
from fastapi import APIRouter, Response, status
from core.config import settings
import database.database as db_module

router = APIRouter(tags=["Health & Monitoring"])

_PROCESS_START_TIME = time.time()


@router.get("/health")
async def liveness():
    """
    Liveness probe.
    Confirms the application process is running and serving traffic.
    Does not depend on external services or databases.
    """
    uptime = round(time.time() - _PROCESS_START_TIME, 2)
    return {
        "status": "ok",
        "service": settings.APPLICATION_NAME.lower(),
        "version": settings.APPLICATION_VERSION,
        "environment": settings.ENV,
        "uptime_seconds": uptime,
    }


@router.get("/ready")
async def readiness(response: Response):
    """
    Readiness probe.
    Verifies that required operational dependencies (MongoDB) are reachable and healthy.
    Returns HTTP 200 when ready, HTTP 503 when dependencies are unreachable or timed out.
    Safe diagnostic payload: zero credentials, secrets, or internal connection strings.
    """
    db_health = await db_module.check_database_health(timeout_seconds=2.0)

    if db_health.get("connected"):
        return {
            "status": "ok",
            "ready": True,
            "service": settings.APPLICATION_NAME.lower(),
            "version": settings.APPLICATION_VERSION,
            "environment": settings.ENV,
            "dependencies": {
                "database": {
                    "status": "connected",
                    "latency_ms": db_health.get("latency_ms", 0.0),
                }
            },
        }
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "ready": False,
            "service": settings.APPLICATION_NAME.lower(),
            "version": settings.APPLICATION_VERSION,
            "environment": settings.ENV,
            "dependencies": {
                "database": {
                    "status": "disconnected",
                    "error_type": db_health.get("error_type", "UnknownError"),
                }
            },
        }
