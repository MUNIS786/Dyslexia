# DyslexAid Backend v4.0
## AI-Powered Reading Companion — School ERP + Google Classroom + Dyslexia Engine

---

## Quick Start

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Install Tesseract OCR
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-mar

# 3. Configurerun
cp .env.example .env
# Edit .env — set MONGO_URL and GEMINI_API_KEY

# 4. Run
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs
Health:   http://localhost:8000/api/health

### Demo Credentials (auto-seeded on first start)
| Role    | Email                    | Password  | Classroom |
|---------|--------------------------|-----------|-----------|
| Teacher | teacher@demo.school      | Demo@123  | DA-DEMO   |
| Student | aarav@demo.school        | Demo@123  | DA-DEMO   |
| Student | priya@demo.school        | Demo@123  | DA-DEMO   |
| Student | ravi@demo.school         | Demo@123  | DA-DEMO   |
| Student | sneha@demo.school        | Demo@123  | DA-DEMO   |

---

## New User Flow (Real-World Logic)

```
STUDENT SIGNS UP
    ↓ account created with ALL zeros (no fake data)
    ↓ onboardingComplete = false
    ↓ readingProfile = null

→ STEP 1: TAKE DYSLEXIA SCREENING TEST (/api/dyslexia-test)
    ↓ 20-question DST-aligned test (phonological, RAN, memory, etc.)
    ↓ ML model + rule-based analysis → dyslexia type + severity
    ↓ readingProfile saved to user account
    ↓ notification sent: "Screening Complete!"

→ STEP 2: AI GENERATES LEARNING PLAN (/api/ai-plan/generate)
    ↓ Gemini AI creates personalized 4-week plan
    ↓ Rule-based fallback if no internet
    ↓ notification sent: "Your AI Plan is Ready!"

→ STEP 3: DAILY TASKS GENERATED (/api/tasks)
    ↓ Each day: 3-5 tasks based on dyslexia type + current progress
    ↓ AI-generated (Gemini) or rule-based fallback
    ↓ As student completes tasks → progress updates

→ ONGOING: ADAPTIVE SYSTEM
    ↓ Every session → streak + activity logged
    ↓ Every quiz → comprehension tracked
    ↓ Every 7 days OR after 10 sessions → AI adapts plan
    ↓ If comprehension improves 15%+ → profile level updates
    ↓ Teacher sees all changes in real-time
```

---

## Complete API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/signup | Register (role: student/teacher). New users start with 0 data. |
| POST | /api/auth/signin | Login → JWT (30-day) |
| GET  | /api/auth/me | Current user + profile |
| PATCH | /api/auth/profile | Update name, languages, etc. |
| PATCH | /api/auth/settings | Font, TTS speed, bg color, font size, etc. |

### Classroom (Google Classroom-style)
| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| POST | /api/classroom/join | Student | Join with teacher's code. Teacher notified instantly. Pending assignments assigned. |
| GET  | /api/classroom/info | Both | Classroom details + student count |
| GET  | /api/classroom/students | Teacher | All students who joined |
| POST | /api/classroom/announce | Teacher | Broadcast message to all students |
| POST | /api/classroom/leave | Student | Leave classroom |

### Assignments (Full Lifecycle)
| Method | Endpoint | Who | Description |
|--------|----------|-----|-------------|
| POST | /api/assignments | Teacher | Create assignment (text auto-converted to dyslexia format) |
| POST | /api/assignments/upload-and-create | Teacher | Upload file → OCR → dyslexia-convert → assign to class |
| GET  | /api/assignments | Both | Teacher: all + submission counts. Student: own + submitted status |
| GET  | /api/assignments/{id} | Both | Teacher sees all submissions. Student sees own. |
| POST | /api/assignments/submit | Student | Submit answer. Teacher notified. Progress updated. |
| POST | /api/assignments/grade | Teacher | Grade submission. Student notified with score + feedback. |
| DELETE | /api/assignments/{id} | Teacher | Delete assignment |

### Dyslexia Screening Test (DST-Aligned)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/dyslexia-test/questions | 20 questions across 7 clinical domains |
| POST | /api/dyslexia-test/submit | Submit answers → full report: type, level, strengths, weaknesses |
| GET  | /api/dyslexia-test/history | Past screening results |

**Domains tested:** Letter Knowledge, Phonological Awareness, Phonological Memory, Rapid Naming, Reading Fluency, Spelling/Orthographic, Comprehension

### Daily Tasks (AI-Adaptive)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/tasks | Today's tasks (auto-generated on first call) |
| POST | /api/tasks/{id}/complete | Mark task done. Triggers progress update. |

### AI Learning Plan (Auto-Adapts)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/ai-plan/generate | Generate plan from screening + progress (needs screening first) |
| GET  | /api/ai-plan | Get current plan |
| POST | /api/ai-plan/check-adapt | Check + apply adaptation if threshold met |
| GET  | /api/ai-plan/suggestions | Latest AI adaptation suggestion |

**Adaptation triggers:** 7 days since last review OR 10 sessions completed OR ±15% comprehension change OR profile level improved

### Progress Tracking (Real-Time)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/progress | Full progress snapshot |
| POST | /api/progress/session-start | Start session (updates streak, weekly activity) |
| POST | /api/progress/session-end | End session (logs time) |
| POST | /api/progress/comprehension | Record quiz score. Auto-updates profile level if improved. |
| POST | /api/progress/scan | Log document scan |
| POST | /api/progress/word | Add mastered word |
| GET  | /api/progress/summary | Dashboard summary with levelLabel |

### Teacher Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/teacher/students | All students: progress, comprehension, submission rates, status |
| GET  | /api/teacher/student/{id} | Full drill-down: progress + plan + all submissions |
| GET  | /api/teacher/analytics | Class-wide stats: type distribution, avg comprehension, submission rate |
| POST | /api/teacher/lesson-plan | AI-generated 30-min lesson plan for a student |

### Scan & Simplify (Student: Personal Use)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/scan | Upload image/PDF → OCR text (Tesseract offline) |
| POST | /api/simplify | Simplify text → ≤12 words/sentence (AI + offline fallback) |
| POST | /api/convert-notes | Convert notes → dyslexia-friendly (offline safe) |

### Library (Student Personal Documents)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/library | All saved documents |
| POST | /api/library | Save a document |
| GET  | /api/library/{id} | Get one document |
| DELETE | /api/library/{id} | Delete |

### Chat (Gemini Flash — 24/7)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/chat | Chat with Gemini Flash. Personalised by dyslexia profile. FAQ offline fallback. |

### Notifications (Real-Time)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/notifications | List with unread count |
| GET  | /api/notifications/stream?token=JWT | SSE real-time stream |
| POST | /api/notifications/read/{id} | Mark one read |
| POST | /api/notifications/read-all | Mark all read |

---

## What Triggers What (Event Flow)

```
Student joins classroom     → Teacher gets "New Student Joined" notification
                            → Student gets all pending assignment notifications

Teacher creates assignment  → All students in classroom get notification

Student submits assignment  → Teacher gets "Assignment Submitted" notification
                            → Student comprehension score updated
                            → AI plan adaptation checked

Teacher grades submission   → Student gets "Assignment Graded" notification with score

Student completes screening → readingProfile saved
                            → "Screening Complete" notification to student
                            → AI plan auto-generated
                            → Daily tasks auto-created

Student comprehension +15%  → Profile level updated (e.g., high → moderate)
                            → "Great Progress!" notification
                            → AI plan marked for re-adaptation
                            → Teacher sees updated status

Student completes all tasks → "All Tasks Done!" celebration notification

Every 7 days (active user)  → AI checks plan adaptation
                            → If needed: new suggestions + "Plan Updated" notification
```

---

## Settings (All Adjustable per User)
```
font: OpenDyslexic | Lexend | Arial
fontSize: 14–28px
lineSpacing: 1.5–3.0
letterSpacing: em units
bgColor: #FFF8F0 (cream) | white | yellow | blue
textColor: #1A2A2A
ttsSpeed: 0.5–2.0
ttsLanguage: en-IN | hi-IN | ta-IN | mr-IN
highlightWords: true/false
showBulletPoints: true/false
autoSimplify: true/false
```
Update via: `PATCH /api/auth/settings`

---

## Offline Architecture
Every AI call follows this chain:
```
1. Gemini Flash API (primary for chat, tasks, plans)
2. Anthropic Claude API (simplification)
3. Rule-based engine (always works, zero internet)
```
OCR uses Tesseract — fully local, no internet needed.
