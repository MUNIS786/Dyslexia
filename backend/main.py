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

# NOTE: load_dotenv() above MUST stay before these router imports —
# routers/chat.py -> services/ai_service.py reads GEMINI_API_KEY at
# import time. Importing routers before load_dotenv() would leave the
# key empty and force every chat request to fail with a clear 500 error.
from routers import auth, scan, simplify, screening, library, progress
from routers import chat, teacher, classroom, assignments, notifications
from routers import ai_plan, dyslexia_test, daily_tasks
from routers import version, v2_learner
from database.database import init_db

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
    await init_db()
    yield


app = FastAPI(
    title="DyslexAid API", version="4.1.0",
    description="AI-powered adaptive reading companion for dyslexic students in India",
    lifespan=lifespan,
)

# In main.py — do this FIRST, before any routes
ALLOWED_ORIGINS = [
    "http://localhost:3000",    # React / Vite dev
    "http://localhost:5173",    # Vite default port
    "https://yourdomain.com",   # production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # NEVER use "*" with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V1 Routers
for mod in [auth, scan, simplify, screening, library, progress, chat,
            teacher, classroom, assignments, notifications, ai_plan,
            dyslexia_test, daily_tasks]:
    app.include_router(mod.router, prefix="/api")

# V2 Routers & System Info
app.include_router(version.router, prefix="/api")
app.include_router(v2_learner.router, prefix="/api")


@app.get("/api/")
async def root():
    return {"status": "ok", "version": "4.0.0", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "dyslexaid"}


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