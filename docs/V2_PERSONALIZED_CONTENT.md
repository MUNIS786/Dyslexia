# DyslexAid V2 — Phase 15: Personalized Learning Content & Activity Engine

## 1. Objective

Phase 15 delivers a deterministic, explainable **Personalized Learning Content & Activity Engine** for DyslexAid V2. It directly fulfills the core student journey:

> **"Moving seamlessly from a Phase 14 recommendation to an engaging, level-appropriate learning activity."**

By linking real student performance evidence (strengths, practice areas, tricky words, active difficulty tier, and longitudinal trends) with verified catalog passages and interactive micro-tasks, Phase 15 provides:
1. **Student Activity Experience:** Directly launches calibrated reading stories, tricky-word quests, oral read-aloud practice, comprehension checks, and skill reviews without cognitive overload.
2. **Pedagogical Integrity:** Respects Phase 3 as the sole authority for adaptive tier progression. Never fabricates completions or creates duplicate adaptive engines.
3. **Honest Multilingual Matching:** Supports English, Hindi, and Marathi with verified offline content. Never conceals language substitution when a specific tier is unavailable in the requested language.
4. **Accessible Accommodations:** Inherits Phase 12 accessibility presets (OpenDyslexic / Lexend fonts, line and word spacing, reading ruler, and high contrast) directly into activity sessions.
5. **Educator & Parent Transparency:** Provides pedagogical rationales for teachers and practical at-home practice suggestions for parents without exposing private notes or raw audio.

---

## 2. Architecture & File Structure

Phase 15 adheres to DyslexAid's modular, layered architecture:

```text
backend/
  core/
    config.py                           # Feature flag: V2_PERSONALIZED_CONTENT (default: True)
  models/
    v2_personalized_content.py          # Pydantic v2 data models & response contracts
    __init__.py                         # Model re-exports
  services/
    learning/
      personalized_content.py           # Content selection, ZPD calibration, language matching
  routers/
    v2_personalized_content.py          # Role-guarded API router (/api/v2/personalized-content)
  test_phase15_personalized_content.py  # 22 deterministic unit and integration tests

frontend/
  src/
    api/v2/
      client.js                         # personalizedContentV2API client
    components/
      content/
        ActivityRecommendationCard.jsx  # Activity card with tier, duration, reason, & launch action
        ActivityReason.jsx              # Child-friendly 'Why this was chosen' explanation
        ContentAvailabilityState.jsx    # Transparent language fallback notice
        index.js                        # Barrel export
    pages/
      student/
        PersonalizedActivityPage.jsx    # Student activity hub route (/student/activity)
    i18n/
      locales/en.js                     # English translations
      locales/hi.js                     # Hindi translations
      locales/mr.js                     # Marathi translations
    App.jsx                             # Route registration & screening exception
    components/shared/Layout.jsx        # Navigation link in STUDENT_NAV
```

---

## 3. Supported Activity Types

Phase 15 connects to existing activity mechanisms in the repository across six controlled educational categories:

| Activity Type | Educational Focus | Underlying Source | Action URL Destination |
| :--- | :--- | :--- | :--- |
| **`GUIDED_READING`** | Core story reading with TTS, syllable cues, and word definitions | `reading_service.py` (`DEFAULT_PASSAGES`) | `/student/reading-coach?passageId=...` |
| **`DIFFICULT_WORD_PRACTICE`** | Orthographic spelling, letter scramble, and targeted tricky words | `activity_recommender.py` (`act-spell-*`) | `/student/adaptive-learning?activityId=...` |
| **`READING_COMPREHENSION`** | Bite-sized story recall and inferential detective questions | `activity_recommender.py` (`act-comp-*`) | `/student/adaptive-learning?activityId=...` |
| **`VOCABULARY_PRACTICE`** | Pre-teaching key vocabulary definitions and phonetic breakdowns | `reading_service.py` (Passage vocabulary) | `/student/reading-coach?passageId=...&view=vocabulary` |
| **`ORAL_READING_SPEECH`** | Read-aloud fluency practice with client-side speech recognition | Phase 5 Speech Analysis + Reading Coach | `/student/reading-coach?passageId=...&mode=oral` |
| **`SKILL_REVIEW`** | Spaced repetition of foundational phoneme and rhyme blends | `activity_recommender.py` (`act-phon-*`) | `/student/adaptive-learning?activityId=...` |

---

## 4. Content Selection & Eligibility Rules

Content selection is deterministic and explainable:
1. **Adaptive Tier Authority:** The learner's active tier (1–5) in Phase 3 dictates the difficulty of selected activities.
2. **Stretch Eligibility:** Stretch challenges (`STRETCH` -> `GUIDED_READING` at tier + 1) are presented only when consecutive passes $\ge 2$ and tier $< 5$.
3. **De-duplication & Variety:** Candidates recently attempted or completed are down-weighted to promote variety.
4. **Real Completion Verification:** An activity is marked `completed: true` **only** if matching records exist in `db.reading_sessions` (`completed=True`), `db.activity_attempts` (`completed=True`), or `db.speech_reading_analyses`. Launching an activity never marks it complete.
5. **Idempotent Retrieval:** Repeated requests or page re-renders do not generate synthetic attempts or alter the student's learning history.

---

## 5. Multilingual Matching & Honest Fallbacks

The content engine respects the student's selected language (`en`, `mr`, `hi`):
- **Exact Matches:**
  - Marathi: Level 1 (`pas-mr-t1-001`), Level 2 (`pas-mr-t2-001`).
  - Hindi: Level 1 (`pas-hi-t1-001`).
  - English: Levels 1–5 (`pas-t1-001` through `pas-t5-001`) and all micro-tasks.
- **Honest Fallback Protocol:**
  - If a student requests Marathi at Level 4, the engine does **not** fake a Marathi story.
  - Returns `availabilityStatus: "LANGUAGE_FALLBACK_OFFERED"`, sets `language: "en"`, and supplies `languageFallbackMessage`:
    *"A Level 4 story is not currently available in Marathi (मराठी). Showing an English story at Level 4 with interactive vocabulary and audio support."*
  - The student can see the original language options and switch anytime.

---

## 6. API Endpoints

All endpoints are hosted under `/api/v2/personalized-content`:

### Student Endpoints
* `GET /api/v2/personalized-content/next?language=...&activity_type=...`
  * Returns immediate next best activity for authenticated student with level info and accessibility config.
* `GET /api/v2/personalized-content/activities?language=...&tier=...&category=...&limit=...`
  * Lists diverse personalized activities matching the student's tier and language.
* `GET /api/v2/personalized-content/recommendation/{recommendation_id}?language=...`
  * Retrieves content specifically linked to a Phase 14 recommendation item.
* `POST /api/v2/personalized-content/launch`
  * Logs activity launch telemetry event in `db.activity_launches`. Returns `status: "launched"`, `completed: false`.

### Educator & Family Endpoints
* `GET /api/v2/personalized-content/teacher/{learner_id}`
  * Enforces teacher classroom enrollment authorization. Returns pedagogical justification and supporting signals.
* `GET /api/v2/personalized-content/parent/{learner_id}`
  * Enforces verified parent-child link authorization. Returns at-home practice suggestions and focus words.

---

## 7. Security, Privacy & Data Governance

* **Tenant Isolation:** Student endpoints derive identity exclusively from the JWT session (`current_user.id`). Arbitrary query parameter overrides are ignored.
* **Role-Based Authorization:** Teacher and Parent endpoints verify classroom enrollment and active parent links via `verify_teacher_student_access` and `verify_parent_student_access` (HTTP 403 on unauthorized access).
* **Zero Raw Audio Exposure:** Speech practice relies on client-side Web Speech recognition; no raw audio blobs are saved or transmitted.
* **Zero Tutor Transcript Exposure:** Private AI tutor multi-turn conversations are excluded from content payloads.
* **Zero Private Teacher Notes Exposure:** Teacher observation notes remain strictly private.
* **Non-Clinical Guarantee:** Clear disclaimers communicate that recommendations and activity selections support educational practice, not clinical or medical diagnosis.

---

## 8. Verification & Test Results

### Backend Test Execution
* **Target Test Suite (`backend/test_phase15_personalized_content.py`):** **22 / 22 Passed** in 3.87s.
* **Full Regression Suite (`pytest backend/ -q`):** **335 / 335 Passed** in 4.35s (100% pass rate).

### Frontend Code Quality & Build
* **ESLint (`npm run lint`):** **0 errors, 0 warnings** with `--max-warnings 0`.
* **Vite Production Build (`npm run build`):** **Success** in 9.00s.

---

## 9. Known Limitations

* Non-English passage content in the offline seed library is currently limited to Marathi (Levels 1–2) and Hindi (Level 1). For higher tiers in these languages, the engine transparently offers verified English passages with full assistive scaffolding.
* Micro-learning tasks (phoneme blending, letter reversal, and spelling puzzles) currently target English phonetic structures.
