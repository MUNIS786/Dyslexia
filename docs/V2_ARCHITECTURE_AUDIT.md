# DyslexAid V1 Full Project Architecture Audit

**Date:** September 2026  
**Audited Target:** DyslexAid Platform v4.0  
**Repository:** [https://github.com/MUNIS786/Dyslexia.git](https://github.com/MUNIS786/Dyslexia.git)  
**Objective:** Comprehensive audit of the working V1 application to establish a rock-solid foundation for V2 evolution without breaking existing functionality.

---

## 1. Executive Summary

DyslexAid is an operational full-stack assistive learning and classroom ERP platform tailored for learners with dyslexia and educational institutions. The application consists of a FastAPI backend (Python 3.11+), an async MongoDB persistence layer (`motor`), and a single-page React 18 frontend built with Vite and Tailwind CSS. 

The application is fully operational in V1, providing:
- Standardized screening test based on Dyslexia Screening Test (DST) / NIMHANS / PhAB guidelines.
- Offline Scikit-Learn ML classification pipelines for subtype & level scoring.
- Personalized 4-week learning plans with auto-adaptation triggers.
- Daily adaptive task generation.
- Optical Character Recognition (Tesseract) and multi-level text simplification.
- Google Classroom-style assignment distribution, OCR ingestion, student submission, and teacher grading.
- Assistive multi-turn conversational AI companion powered by Google Gemini with deterministic offline FAQ fallbacks.
- Deep accessibility controls (OpenDyslexic, Lexend, letter/line spacing, color tints, TTS).

---

## 2. Current Architecture Overview

```
                               ┌────────────────────────────────────────────────────────┐
                               │                 Client Tier (React 18)                 │
                               │  Vite • Tailwind CSS • Lucide Icons • React Router v6  │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ HTTP / SSE / REST
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                Application Tier (FastAPI)              │
                               │         CORS • JWT Auth • Pydantic v2 • Uvicorn        │
                               └───────┬───────────────────┬───────────────────┬────────┘
                                       │                   │                   │
                     ┌─────────────────┴─┐       ┌─────────┴─────────┐       ┌─┴────────────────┐
                     ▼                   ▼       ▼                   ▼       ▼                  ▼
             ┌───────────────┐   ┌─────────────┐ ┌───────────────┐ ┌───────┐ ┌──────────────┐ ┌──────────────┐
             │ Motor (Async) │   │ Scikit-Learn│ │ Tesseract OCR │ │Pillow │ │ Google Gemini│ │ Offline Rule │
             │ MongoDB Driver│   │  ML Models  │ │ Local Binary  │ │ pdf2img││ Flash REST API││ Engine       │
             └───────────────┘   └─────────────┘ └───────────────┘ └───────┘ └──────────────┘ └──────────────┘
```

---

## 3. Existing Features & Capabilities

1. **Authentication & User Management:**
   - Registration and login with `role` separation (`student` vs. `teacher`).
   - JWT stateless sessions (30-day validity, HS256).
   - Zero-baseline initial onboarding: new users start with clean profiles (no mocked/fabricated data).
   - Auto-seeded demo accounts on empty database initialization (`teacher@demo.school`, `aarav@demo.school`, etc.).

2. **Clinical Screening & Diagnostics:**
   - 20-question multidimensional DST-aligned assessment covering 12 cognitive domains.
   - Dual-engine analysis: Scikit-Learn classifier (`backend/ai_model/`) and rules engine (`backend/services/screening_analyzer.py`).
   - Append-only `prediction_history` ensuring past scoring events are never overwritten.

3. **Assistive Reading & OCR:**
   - Tesseract OCR engine for scanned textbook pages, worksheets, and PDFs.
   - Text simplifier targeting sentence lengths $\le 12$ words with dyslexia-friendly vocabulary substitutions.
   - Profile-specific output styling (syllable breakdowns, visual spacing, irregular word callouts).

4. **Classroom & Teacher ERP:**
   - Alphanumeric classroom joining codes (`DA-DEMO`).
   - Teacher broadcast announcements.
   - Assignment creation with automated dyslexia-friendly reformatting.
   - Student submission and teacher grading workflows.
   - Real-time teacher analytics and automated 30-minute lesson plan generation.

5. **AI Companion & Adaptation:**
   - Multi-turn conversational chat with Gemini Flash (`gemini-2.0-flash` / `gemini-3.5-flash`).
   - Strict `AIServiceError` error surfacing with `CHAT_OFFLINE_MODE=true` toggle.
   - 4-week adaptive learning plan with automated 7-day or 10-session adaptation triggers.
   - Real-time notification streams via Server-Sent Events (SSE).

---

## 4. Existing Backend Services Inventory

| Service File | Primary Responsibilities | Dependencies | Status in V2 |
|---|---|---|---|
| `backend/services/ai_service.py` | Centralized interface for Gemini Flash, Claude fallback, multi-turn chat, prompt generation, and lesson planning. | `httpx`, `os`, `logging`, `json` | **Preserve & Extend** |
| `backend/services/screening_analyzer.py` | 12-domain cognitive assessment, difficulty-weighted scoring, profile probability estimation. | Python math/dict standard library | **Preserve & Extend** |
| `backend/services/personalization.py` | Maps dyslexia subtypes to concrete visual and textual reading accommodations. | `re` | **Preserve & Extend** |
| `backend/services/offline_simplifier.py` | Offline dictionary-based sentence shortening and vocabulary simplification. | `backend/data/simple_words.json` | **Preserve** |
| `backend/services/ocr_service.py` | Local document image and PDF OCR extraction via Tesseract. | `pytesseract`, `PIL`, `pypdf`, `pdf2image` | **Preserve** |

---

## 5. Existing API Endpoints Inventory

### Authentication (`routers/auth.py`)
- `POST /api/auth/signup` — Register new student or teacher account
- `POST /api/auth/signin` — Login and receive 30-day JWT
- `GET /api/auth/me` — Current authenticated user profile
- `PATCH /api/auth/profile` — Update name, school, preferred languages
- `PATCH /api/auth/settings` — Update accessibility preferences

### Classroom & School ERP (`routers/classroom.py` & `routers/assignments.py`)
- `POST /api/classroom/join` — Student joins classroom via code
- `GET /api/classroom/info` — Classroom summary
- `GET /api/classroom/students` — Enrolled students list (Teacher only)
- `POST /api/classroom/announce` — Broadcast announcement
- `POST /api/classroom/leave` — Student leaves classroom
- `POST /api/assignments` — Teacher creates assignment
- `POST /api/assignments/upload-and-create` — Teacher uploads file, OCRs it, and assigns
- `GET /api/assignments` — Teacher sees all; student sees own
- `GET /api/assignments/{id}` — Single assignment details
- `POST /api/assignments/submit` — Student submits assignment
- `POST /api/assignments/grade` — Teacher grades student submission
- `DELETE /api/assignments/{id}` — Delete assignment

### Screening & Clinical Testing (`routers/dyslexia_test.py` & `routers/screening.py`)
- `GET /api/dyslexia-test/questions` — 20 standardized questions with domain weights
- `POST /api/dyslexia-test/submit` — Submits assessment answers for analysis
- `GET /api/dyslexia-test/history` — Historical screening runs for the authenticated user

### Learning Plan & Adaptive Tasks (`routers/ai_plan.py` & `routers/daily_tasks.py`)
- `POST /api/ai-plan/generate` — Generate 4-week tailored intervention plan
- `GET /api/ai-plan` — Retrieve active learning plan
- `POST /api/ai-plan/check-adapt` — Evaluates adaptation conditions
- `GET /api/ai-plan/suggestions` — Latest AI adaptation suggestions
- `GET /api/tasks` — Daily micro-exercises
- `POST /api/tasks/{id}/complete` — Mark task completed

### Progress & Telemetry (`routers/progress.py`)
- `GET /api/progress` — Full progress snapshot
- `POST /api/progress/session-start` — Log session start, streak, and weekly activity
- `POST /api/progress/session-end` — Record session duration
- `POST /api/progress/comprehension` — Record quiz performance
- `POST /api/progress/scan` — Log document scanned
- `POST /api/progress/word` — Log mastered vocabulary word
- `GET /api/progress/summary` — High-level dashboard summary metrics

### OCR, Document Processing & Library (`routers/scan.py`, `routers/simplify.py`, `routers/library.py`)
- `POST /api/scan` — Upload image/PDF for OCR text extraction
- `POST /api/simplify` — Simplify text with profile accommodations
- `POST /api/convert-notes` — Offline note simplification
- `GET /api/library` — Retrieve saved personal documents
- `POST /api/library` — Save document to library
- `GET /api/library/{id}` — View saved document
- `DELETE /api/library/{id}` — Delete document

### Conversational Companion & Teacher Analytics (`routers/chat.py`, `routers/teacher.py`, `routers/notifications.py`)
- `POST /api/chat` — Conversational assistant powered by Gemini
- `GET /api/teacher/students` — Overview of all students under teacher
- `GET /api/teacher/student/{id}` — Full student drill-down
- `GET /api/teacher/analytics` — Class-wide aggregated analytics
- `POST /api/teacher/lesson-plan` — AI-generated lesson plan
- `GET /api/notifications` — List user notifications
- `GET /api/notifications/stream` — SSE real-time notification stream
- `POST /api/notifications/read/{id}` — Mark notification read
- `POST /api/notifications/read-all` — Mark all read

---

## 6. Existing MongoDB Collections & Schema Structure

| Collection | Key Indexed Fields | Purpose & Notes |
|---|---|---|
| `users` | `email` (unique), `id` (unique), `classroomCode`, `readingProfile.riskLevel`, `readingProfile.primaryProfile` | Core user identity, credentials, settings, and embedded `readingProfile`. |
| `screening_results` | `userId`, `createdAt`, `riskLevel`, `primaryProfile`, `assessmentVersion` | Individual screening attempts with domain scores, full raw results. |
| `prediction_history` | `userId`, `screeningResultId`, `assessmentVersion` | Append-only event store of ML/rule-based scoring outputs. |
| `classrooms` | `code` (unique), `teacherId` | Classroom metadata and assigned teacher. |
| `assignments` | `classroomCode`, `createdAt`, `teacherId` | Assignment instructions and OCR source materials. |
| `submissions` | `assignmentId` + `studentId` (compound unique) | Student responses, scores, and teacher feedback. |
| `progress` | `userId` (unique) | Continuous metrics: streaks, words read, hours reading, quiz scores. |
| `daily_tasks` | `userId`, `date` | Scheduled daily micro-activities. |
| `ai_plans` | `userId` (unique) | 4-week structured intervention plans. |
| `libraries` | `userId`, `createdAt` | Student-saved simplified texts. |
| `notifications` | `userId`, `createdAt` | Real-time and persistent alerts. |
| `teacher_notes` | `studentId`, `teacherId`, `classroomCode` | Qualitative notes logged by instructors. |
| `recommended_activities` | `domains`, `profileTags` | Reusable activity catalog. |
| `recommended_games` | `domains`, `profileTags` | Reusable assistive games catalog. |

---

## 7. Existing Frontend Routes

| Path | Component | Auth Role | Description |
|---|---|---|---|
| `/login` | `LoginPage` | Public | Authentication signin |
| `/register` | `RegisterPage` | Public | Role-based registration |
| `/student` | `StudentHome` | `student` | Student dashboard (tasks, streak, progress, fast actions) |
| `/student/screening` | `ScreeningTest` | `student` | 20-question interactive assessment |
| `/student/tasks` | `DailyTasks` | `student` | Daily micro-learning tasks |
| `/student/scan` | `ScanPage` | `student` | Document upload, camera scan, OCR, simplification |
| `/student/library` | `LibraryPage` | `student` | Saved documents archive |
| `/student/library/:id` | `LibraryDocPage`| `student` | Full-screen reader with TTS and custom typography |
| `/student/progress` | `ProgressPage` | `student` | Comprehension charts, streaks, mastered vocabulary |
| `/student/plan` | `PlanPage` | `student` | 4-week adaptive learning plan viewer |
| `/student/chat` | `ChatPage` | `student` | Assistive Gemini conversational assistant |
| `/student/settings` | `SettingsPage` | `student` | Typography, colors, TTS rate, spacing configuration |
| `/student/classroom`| `JoinClassroom`| `student` | Join classroom via code and view enrolled class |
| `/teacher` | `TeacherHome` | `teacher` | Teacher dashboard with class summaries |
| `/teacher/students` | `StudentsPage` | `teacher` | Class roster with risk levels and progress rates |
| `/teacher/students/:id` | `StudentDetailPage`| `teacher` | Individual student drilldown, plan history, notes |
| `/teacher/assignments` | `AssignmentsPage` | `teacher` | Assignment creation, grading, and review |
| `/teacher/scan` | `TeacherScanPage` | `teacher` | Teacher OCR text simplification for lesson creation |
| `/teacher/chat` | `ChatPage` | `teacher` | Teacher lesson planning assistant |

---

## 8. Existing AI & Machine Learning Components

1. **Scikit-Learn Classification Pipelines (`backend/ai_model/`):**
   - `dyslexia_type_model.pkl`: Multi-label classifier mapping 20 clinical features to 5 primary profiles (*No significant indicators*, *Phonological Dyslexia*, *RAN Deficit*, *Surface Dyslexia*, *Double Deficit*).
   - `dyslexia_level_model.pkl`: Classifier estimating risk severity (*low*, *moderate*, *high*).
   - `train_model.py`: Complete training and validation script with calibrated probability outputs.
   - `model_info.json`: Feature definitions and evaluation metrics.
2. **Deterministic Rules Engine (`backend/services/screening_analyzer.py`):**
   - 12-domain evaluation with confidence scoring and response-time weighting.
3. **Multi-Tier Generative AI Layer (`backend/services/ai_service.py`):**
   - Tier 1: Google Gemini Flash (`gemini-2.0-flash` / `gemini-3.5-flash`).
   - Tier 2: Anthropic Claude 3.5 Sonnet (optional fallback).
   - Tier 3: Deterministic rule-based simplification and offline FAQ answers.

---

## 9. Technical Debt & Known Bugs Identified

1. **Duplicate Model Artifacts:**
   - ML model files were duplicated across `backend/ai_model/` and `ml/`. In V2, `backend/ai_model/` must remain the runtime inference source to prevent breaking imports.
2. **Embedded Profile vs. Standalone Collection Synchronization:**
   - In V1, user reading profile data is embedded inside `users.readingProfile` and also recorded in `screening_results`. There was no dedicated `learner_profiles` collection with versioned domain snapshots and learning state tracking.
3. **Hardcoded Fallback Defaults:**
   - Several services fall back to hardcoded strings when Gemini is unreachable. V2 needs a centralized prompt and fallback manager.
4. **Lack of Dynamic Feature Flags:**
   - V1 features are either enabled or disabled solely via environment variables or hardcoded flags. V2 needs a centralized, runtime-queryable feature flag service.
5. **No Parent / Guardian Domain:**
   - V1 supports only `student` and `teacher` roles. V2 architecture must accommodate parent/guardian observations and links.

---

## 10. Components That Must NOT Be Modified Unnecessarily

> [!IMPORTANT]
> The following core modules are verified working in production and must remain intact:
> 1. `backend/deps/deps.py`: Core JWT authentication, password hashing, and user extraction.
> 2. `backend/database/database.py`: Existing `init_db()`, `_migrate_legacy_profiles()`, and demo seeding.
> 3. `backend/routers/auth.py`, `classroom.py`, `assignments.py`, `progress.py`, `dyslexia_test.py`: V1 REST contracts.
> 4. `backend/services/ai_service.py`: Tested chat, simplification, and plan generation APIs.
> 5. `frontend/src/pages/`: Existing V1 views and routes.

---

## 11. Recommended V2 Extension Points

1. **Centralized V2 Configuration (`backend/core/config.py`):**
   - Manages versioning (`/api/version`) and feature flags (`V2_LEARNER_PROFILE`, `V2_ADAPTIVE_ENGINE`, etc.).
2. **Dedicated Learner Intelligence Service (`backend/services/learning/`):**
   - `learner_profile_service.py`: Computes and serves comprehensive V2 learner profiles from existing screening and progress telemetry.
3. **V2 API Router Mount (`/api/v2`):**
   - Mounted in `backend/main.py` without modifying or interfering with existing `/api/...` endpoints.
4. **Modular Frontend Feature Structure (`frontend/src/features/` & `frontend/src/api/v2/`):**
   - Houses V2 components and hooks while keeping existing routes completely untouched.
