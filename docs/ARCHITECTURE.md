# DyslexAid System Architecture

## Overview
DyslexAid is an AI-powered reading companion and assistive learning platform designed for neurodivergent individuals, specifically individuals with dyslexia. It combines a Google Classroom-style School ERP, an adaptive dyslexia screening and learning engine, and hybrid online/offline AI features.

```
                    ┌─────────────────────────────────┐
                    │      React 18 + Vite Frontend   │
                    │   (TailwindCSS, Lucide, Axios)  │
                    └───────────────┬─────────────────┘
                                    │ HTTP / SSE
                                    ▼
                    ┌─────────────────────────────────┐
                    │      FastAPI Backend (v4.0)     │
                    │      (JWT Auth, PyJWT, CORS)    │
                    └───────┬──────────────┬──────────┘
                            │              │
             ┌──────────────┴──────┐       └──────────────┬──────────────┐
             ▼                     ▼                      ▼              ▼
     ┌───────────────┐     ┌───────────────┐      ┌───────────────┐ ┌───────────────┐
     │ MongoDB Store │     │  Tesseract    │      │  Scikit-Learn │ │  Multi-Tier   │
     │  (Motor async)│     │  Local OCR    │      │  ML Classify  │ │   AI Engine   │
     └───────────────┘     └───────────────┘      └───────────────┘ └───────┬───────┘
                                                                            │
                                                ┌───────────────────────────┼───────────────────────────┐
                                                ▼                           ▼                           ▼
                                        ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
                                        │ Gemini Flash  │           │ Anthropic     │           │ Offline Rule  │
                                        │ (Chat / Plans)│           │ (Claude 3.5)  │           │ Engine        │
                                        └───────────────┘           └───────────────┘           └───────────────┘
```

## Key Modules

### 1. Backend (`/backend`)
- **FastAPI Core**: Async REST API endpoints with Pydantic validation.
- **Routers**:
  - `auth.py`: JWT-based signup, signin, user profile and dyslexia preference settings.
  - `classroom.py`: Code-based class joining, broadcasts, student roster management.
  - `assignments.py`: Full assignment lifecycle (creation, OCR file parsing, submission, grading).
  - `dyslexia_test.py`: 20-question DST-aligned clinical screening test covering 7 domains.
  - `ai_plan.py`: Personalized 4-week learning plan generation and adaptive re-evaluation.
  - `daily_tasks.py`: AI-adaptive daily task assignments.
  - `progress.py`: Comprehensive progress, streaks, comprehension quizzes, and reading speed metrics.
  - `teacher.py`: Teacher dashboard analytics, individual student drill-down, and lesson plan generator.
  - `scan.py` & `simplify.py`: Document upload, Tesseract OCR processing, and dyslexia-friendly text simplification.
  - `chat.py`: Real-time assistive chat powered by Gemini with offline fallback.
  - `notifications.py`: Server-Sent Events (SSE) stream and inbox management.
- **Database (`backend/database`)**: MongoDB persistence using `motor` async driver.

### 2. Machine Learning Engine (`backend/ai_model` & `ml/`)
- **Type Classifier** (`dyslexia_type_model.pkl`): Multi-label model predicting dyslexia subtypes (Phonological, Surface, Rapid Naming, Double Deficit).
- **Severity Predictor** (`dyslexia_level_model.pkl`): Estimates dyslexia severity level (Mild, Moderate, Severe).
- **Training Pipeline** (`train_model.py`): Synthetic + clinical scoring pipeline for offline inference without requiring external cloud API calls.

### 3. Frontend (`/frontend`)
- **Vite + React 18**: Fast single-page application.
- **Tailwind CSS**: Adaptive themes, contrast adjustments, and customizable visual settings (cream backgrounds, letter spacing, font sizes).
- **Assistive Fonts**: Built-in support for OpenDyslexic, Lexend, and clean sans-serif typefaces.
- **State & Interceptors**: Axios client with JWT auto-refresh and token interceptors.
