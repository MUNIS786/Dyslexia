# DyslexAid 📚✨
### AI-Powered Assistive Reading Companion & Classroom Learning Platform

DyslexAid is an intelligent assistive platform engineered to empower neurodivergent learners—specifically children and adults with dyslexia—through clinical screening, adaptive personalized learning plans, assistive reading tools, and seamless teacher-student classroom workflows.

---

## Table of Contents
1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Tesseract OCR Setup](#tesseract-ocr-setup)
7. [Backend Setup & Installation](#backend-setup--installation)
8. [Frontend Setup & Installation](#frontend-setup--installation)
9. [Database Configuration (MongoDB)](#database-configuration-mongodb)
10. [Environment Variables](#environment-variables)
11. [Running the Application](#running-the-application)
12. [Demo Accounts](#demo-accounts)
13. [Architecture & Event Flow](#architecture--event-flow)
14. [Current Limitations](#current-limitations)
15. [License](#license)

---

## Overview

DyslexAid addresses the everyday reading, writing, and comprehension challenges faced by dyslexic learners. Rather than treating dyslexia with a one-size-fits-all approach, DyslexAid diagnoses specific dyslexia subtypes (phonological, surface, rapid naming, or double deficit) via standardized clinical screening, trains offline machine learning models for low-latency scoring, generates personalized 4-week learning interventions via Google Gemini AI, and provides teachers with real-time classroom analytics.

---

## Key Features

### 🧠 1. Clinical Dyslexia Screening Test (DST-Aligned)
- 20-question multidimensional test assessing 7 clinical domains:
  - Letter Knowledge & Mirroring
  - Phonological Awareness
  - Phonological Memory
  - Rapid Automatized Naming (RAN)
  - Reading Fluency & Hesitation
  - Orthographic Spelling & Irregular Words
  - Reading Comprehension
- Immediate diagnosis of dyslexia subtype and severity level (*Mild*, *Moderate*, *Severe*).

### 🤖 2. Offline Machine Learning Diagnostics
- Pre-trained Scikit-Learn pipelines (`dyslexia_type_model.pkl` and `dyslexia_level_model.pkl`) run locally without requiring external cloud API calls or internet connectivity.

### 📅 3. Adaptive AI Learning Plans & Daily Tasks
- Generates 4-week structured learning modules tailored to the student's exact diagnosis.
- Auto-adaptation engine evaluates student progress every 7 days or 10 completed sessions:
  - Re-calibrates difficulty if comprehension improves by ≥15%.
  - Generates 3–5 daily adaptive reading exercises.

### 🔍 4. Document Scanning & Text Simplification (OCR)
- Upload textbook pages, worksheets, or PDFs.
- Optical Character Recognition (OCR) powered by local Tesseract engine.
- AI & rule-based text simplifier: breaks complex sentences into short, dyslexia-friendly clauses (≤12 words/sentence) with simplified vocabulary.

### 🏫 5. Google Classroom-Style School ERP
- **Classroom Codes**: Simple alphanumeric codes for students to join classes.
- **Assignment Lifecycle**: Teachers create assignments (with automatic dyslexia-formatting and OCR import), students submit answers, and teachers review and grade submissions.
- **Teacher Dashboard**: Real-time student progress tracking, comprehension trends, and one-click AI lesson plan generation.

### 💬 6. Assistive AI Chat Companion
- 24/7 empathetic conversational companion powered by Google Gemini Flash.
- Personalized to each student's name, dyslexia profile, and preferred language.
- Deterministic offline FAQ fallback if internet or API key is unavailable.

### 🎨 7. Neurodivergent-Optimized Accessibility
- Specialized typography: **OpenDyslexic**, **Lexend**, and Arial.
- Custom visual ergonomics: Cream (`#FFF8F0`), pastel yellow, and soft blue tint overlays to mitigate visual stress (Meares-Irlen syndrome).
- Adjustable letter-spacing, line-height, text-to-speech (TTS) playback speed, and word-by-word visual guides.

---

## Technology Stack

### Frontend
- **Framework**: React 18 (Vite)
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **Icons**: Lucide React
- **Notifications**: React Hot Toast
- **HTTP Client**: Axios with centralized request/response interceptors

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn (ASGI)
- **Database**: MongoDB with `motor` (async driver)
- **Authentication**: JWT (JSON Web Tokens) with `bcrypt` password hashing
- **Data Validation**: Pydantic v2

### Machine Learning & OCR
- **ML Framework**: Scikit-Learn, Joblib, NumPy
- **OCR Engine**: Tesseract OCR via `pytesseract`
- **PDF & Image Processing**: Pillow, `pdf2image`, `pypdf`, PyPDF2

### AI Integration
- **Google Gemini**: Gemini 2.0 Flash / 3.5 Flash for chat, personalized lesson plans, and text simplification
- **Anthropic Claude**: Optional secondary provider
- **Offline Rule Engine**: Deterministic fallback ensuring complete offline continuity

---

## Project Structure

```
Dyslexia/
├── backend/
│   ├── ai_model/                 # Pre-trained ML models & training pipeline
│   │   ├── dyslexia_level_model.pkl
│   │   ├── dyslexia_type_model.pkl
│   │   ├── model_info.json
│   │   └── train_model.py
│   ├── data/                     # Offline reference dictionaries (e.g. simple words)
│   ├── database/                 # Async MongoDB connection & schema setup
│   ├── deps/                     # JWT authentication & route dependencies
│   ├── routers/                  # FastAPI routers (auth, classroom, assignments, test, etc.)
│   ├── services/                 # Business logic (AI service, OCR, personalization, analyzer)
│   ├── uploads/                  # Temporary document upload directory (.gitkeep)
│   ├── .env.example              # Backend environment template
│   ├── main.py                   # FastAPI application entrypoint
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                  # Axios client & centralized API handlers
│   │   ├── components/           # Reusable UI & accessibility components
│   │   ├── context/              # Authentication & theme context providers
│   │   ├── pages/                # Student, Teacher, and Auth views
│   │   ├── App.jsx               # Main application routing
│   │   └── main.jsx              # React DOM mounting
│   ├── .env.example              # Frontend environment template
│   ├── package.json              # Frontend npm dependencies & scripts
│   ├── tailwind.config.js        # Accessibility theme configuration
│   └── vite.config.js            # Vite configuration & backend proxy
├── ml/                           # ML models documentation & training scripts
│   ├── model_info.json
│   ├── README.md
│   └── train_model.py
├── docs/                         # Extended documentation
│   ├── ARCHITECTURE.md           # System architecture & data flow
│   └── AI_ASSISTANT_FIX_REPORT.md# Root cause analysis & fix report
├── .env.example                  # Root environment variable template
├── .gitignore                    # Git ignore specifications
├── package.json                  # Root npm workspace shortcuts
├── requirements.txt              # Root pip requirements pointer
└── README.md                     # Project documentation
```

---

## Prerequisites

Ensure the following tools are installed:
- **Node.js** (v18.x or later) & **npm**
- **Python** (v3.10 or v3.11 recommended)
- **MongoDB** (Local Community Server running on `localhost:27017` or MongoDB Atlas URI)
- **Tesseract OCR** (for document image scanning)
- **Git**

---

## Tesseract OCR Setup

Tesseract OCR is required for the document scanning feature.

### Windows
1. Download the installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install to the default directory: `C:\Program Files\Tesseract-OCR`.
3. Add `C:\Program Files\Tesseract-OCR` to your Windows System `PATH`.

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-mar
```

### macOS
```bash
brew install tesseract
```

---

## Backend Setup & Installation

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create the backend `.env` configuration:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in your values (see [Environment Variables](#environment-variables)).

---

## Frontend Setup & Installation

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install npm dependencies:
   ```bash
   npm install
   ```

3. Configure frontend environment (optional):
   ```bash
   cp .env.example .env
   ```

---

## Database Configuration (MongoDB)

DyslexAid utilizes MongoDB for persistent user profiles, classroom rosters, screening histories, and assignments.

- **Local MongoDB**: Start your MongoDB service via MongoDB Compass or terminal:
  ```bash
  mongod --dbpath <path-to-data-directory>
  ```
  Default connection string: `mongodb://localhost:27017`
- **MongoDB Atlas (Cloud)**:
  Provide your connection string in `backend/.env`:
  ```env
  MONGO_URL=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
  ```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default / Example |
|---|---|---|
| `MONGO_URL` | MongoDB connection URI | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `dyslexaid` |
| `JWT_SECRET` | Secret key used to sign session JWTs | `dyslexaid-change-this-in-production` |
| `GEMINI_API_KEY` | Google Gemini API key for AI chat and lesson planning | *Optional for offline use* |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional secondary AI provider) | *Optional* |
| `PORT` | Backend server port | `8000` |
| `CORS_ORIGINS` | Comma-separated allowed origins (`*` for development) | `*` |
| `GEMINI_MODEL` | Gemini model identifier | `gemini-2.0-flash` |
| `CHAT_OFFLINE_MODE` | Force offline FAQ fallback for chat | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE` | API base URL proxied by Vite | `http://localhost:8000/api` |

---

## Running the Application

### 1. Start the Backend Server
From the `backend/` directory:
```bash
uvicorn main:app --reload --port 8000
```
- API Docs (Swagger): `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`

### 2. Start the Frontend Development Server
From the `frontend/` directory:
```bash
npm run dev
```
- Open your browser at: `http://localhost:3000`

---

## Demo Accounts

On initial backend startup with an empty database, demo accounts are automatically seeded:

| Role | Email | Password | Classroom Code |
|---|---|---|---|
| **Teacher** | `teacher@demo.school` | `Demo@123` | `DA-DEMO` |
| **Student** | `aarav@demo.school` | `Demo@123` | `DA-DEMO` |
| **Student** | `priya@demo.school` | `Demo@123` | `DA-DEMO` |
| **Student** | `ravi@demo.school` | `Demo@123` | `DA-DEMO` |
| **Student** | `sneha@demo.school` | `Demo@123` | `DA-DEMO` |

---

## Architecture & Event Flow

```
Student Signs Up (zeroed baseline)
       │
       ▼
1. Complete Screening Test (/api/dyslexia-test)
       │  └─ Scikit-Learn model classifies type & severity
       ▼
2. AI Learning Plan Generated (/api/ai-plan/generate)
       │  └─ Gemini builds 4-week tailored intervention
       ▼
3. Daily Tasks Assigned (/api/tasks)
       │  └─ 3-5 daily micro-reading exercises
       ▼
4. Continuous Progress & Adaptation Loop
       ├─ Streak & time tracked on every session
       ├─ Comprehension assessed on every quiz
       └─ Auto-adaptation triggered every 7 days or +15% improvement
```

---

## Current Limitations

1. **OCR Dependencies**: Document text extraction relies on the Tesseract OCR system binary installed on the host machine. If Tesseract is not installed, OCR scanning endpoints will return an error.
2. **AI Dynamic Capabilities vs. Offline Mode**:
   - Conversational AI chat, AI-adapted 4-week plans, and contextual lesson plans utilize the Google Gemini API and require internet connectivity and a valid `GEMINI_API_KEY`.
   - When offline or when no API key is provided, the platform automatically engages deterministic rule-based engines and offline FAQ fallbacks.
3. **Camera & Microphone Access**: Web-based speech synthesis and document capture depend on modern HTML5 browser API permissions (MediaDevices / Web Speech API).
4. **Single-Region TTS**: Web Speech API voice quality and regional accent support vary depending on the client operating system and browser voices installed.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
