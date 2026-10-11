"""DyslexAid FastAPI Backend v4.0 — production-ready"""
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ─── Logging ────────────────────────────────────────────────────────────────
# Configure once, here, before any router/service module is imported, so
# every logger in the app (dyslexaid.ai_service, dyslexaid.routers.chat, etc.)
# actually prints instead of relying on default WARNING-only root config.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dyslexaid.main")

from core.config import settings
from core.logging_config import setup_logging, RequestObservabilityMiddleware

setup_logging(settings.LOG_LEVEL)

# NOTE: load_dotenv() above MUST stay before these router imports —
# routers/chat.py -> services/ai_service.py reads GEMINI_API_KEY at
# import time. Importing routers before load_dotenv() would leave the
# key empty and force every chat request to fail with a clear 500 error.
from routers import auth, scan, simplify, screening, library, progress
from routers import chat, teacher, classroom, assignments, notifications
from routers import ai_plan, dyslexia_test, daily_tasks
from routers import version, health, v2_learner, v2_learning, v2_reading, v2_tutor, v2_teacher_analytics, v2_intervention, v2_gamification, v2_multilingual, v2_parent, v2_accessibility, v2_learning_insights, v2_learning_recommendations, v2_personalized_content, v2_content_authoring
from database.database import init_db, client

if not os.environ.get("GEMINI_API_KEY", "").strip():
    logger.warning(
        "GEMINI_API_KEY is not set (.env missing the key, or .env not found "
        "at %s). The AI Assistant will return HTTP errors until this is set.",
        ROOT_DIR / ".env",
    )
else:
    logger.info("GEMINI_API_KEY loaded successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate production configuration if running in production mode
    if settings.ENV == "production":
        issues = settings.validate_production_config(strict=False)
        if issues:
            logger.warning("Production configuration warnings: %s", issues)
    try:
        await init_db()
    except Exception as exc:
        logger.warning("Database init failed during startup: %s", exc)
    yield
    # Graceful shutdown: close MongoDB connection pool
    try:
        client.close()
        logger.info("MongoDB client closed cleanly.")
    except Exception as exc:
        logger.warning("Error closing MongoDB client: %s", exc)


app = FastAPI(
    title="DyslexAid API", version=settings.APPLICATION_VERSION,
    description="AI-powered adaptive reading companion for dyslexic students in India",
    lifespan=lifespan,
)

# Observability middleware: request IDs, latency tracking, and unhandled exception safety
app.add_middleware(RequestObservabilityMiddleware, logger=logger)

# Explicit CORS Origins
ALLOWED_ORIGINS = settings.get_allowed_cors_origins()
allow_cred = "*" not in ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=allow_cred,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health & Monitoring Endpoints (available at /api/health, /api/ready, and root /health, /ready)
app.include_router(health.router, prefix="/api")
app.include_router(health.router, prefix="")

# V1 Routers
for mod in [auth, scan, simplify, screening, library, progress, chat,
            teacher, classroom, assignments, notifications, ai_plan,
            dyslexia_test, daily_tasks]:
    app.include_router(mod.router, prefix="/api")

# V2 Routers & System Info
app.include_router(version.router, prefix="/api")
app.include_router(v2_learner.router, prefix="/api")
app.include_router(v2_learning.router, prefix="/api")
app.include_router(v2_reading.router, prefix="/api")
app.include_router(v2_tutor.router, prefix="/api")
app.include_router(v2_teacher_analytics.router, prefix="/api")
app.include_router(v2_intervention.router, prefix="/api")
app.include_router(v2_gamification.router, prefix="/api")
app.include_router(v2_multilingual.router, prefix="/api")
app.include_router(v2_parent.router, prefix="/api")
app.include_router(v2_accessibility.router, prefix="/api")
app.include_router(v2_learning_insights.router, prefix="/api")
app.include_router(v2_learning_recommendations.router, prefix="/api")
app.include_router(v2_personalized_content.router, prefix="/api")
app.include_router(v2_content_authoring.router, prefix="/api")


@app.get("/api/")
async def root():
    return {"status": "ok", "version": settings.APPLICATION_VERSION, "docs": "/docs"}


# ─── Dev server entrypoint ──────────────────────────────────────────────────
# Only used when you run `python main.py` directly. If you instead launch
# with the `uvicorn main:app --reload ...` CLI, apply the same
# --reload-dir / --reload-exclude flags there instead (see chat below).
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        # Only watch your actual source folders — NOT venv/site-packages.
        # Add/remove folder names here to match your project layout.
        reload_dirs=[
            str(ROOT_DIR / "routers"),
            str(ROOT_DIR / "services"),
            str(ROOT_DIR / "deps"),
            str(ROOT_DIR / "database"),
        ],
        reload_excludes=[
            "venv/*",
            ".venv/*",
            "**/site-packages/**",
            "**/__pycache__/**",
        ],
    )