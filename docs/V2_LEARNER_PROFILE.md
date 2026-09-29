# DyslexAid V2 Learner Intelligence Profile Architecture & Specification

**Phase:** Phase 2 — Learner Intelligence Profile (Complete)  
**Safety Notice:** DyslexAid is an educational support platform. All indicators, levels, and profiles represent educational accommodations and do not constitute a medical, psychological, or clinical diagnosis.

---

## 1. System Overview & Purpose

The **Learner Intelligence Profile** transforms raw screening assessments and ongoing reading telemetry into a dynamic, multidimensional cognitive and educational representation of the learner.

The platform architecture follows this pipeline:
```
Screening Results
      ↓
Domain Analysis (12 Cognitive & Reading Domains)
      ↓
Domain Normalization (0–100 Educational Scale)
      ↓
Learner Profile Synthesis
      ↓
Strength Detection (Top 2–3 Superpowers)
      ↓
Areas to Practice (Positive Growth Guidance with Activity Matches)
      ↓
Learning Level (Deterministic Levels 1–5: Foundation → Advanced)
      ↓
Learning Preferences & Assistive Ergonomics
      ↓
Personalized Goals (Checklist & Additions)
      ↓
Student & Teacher Views (Role-Separated Presentation)
```

---

## 2. Profile Data Model

The canonical V2 Learner Profile document is persisted in the `learner_profiles` MongoDB collection and projected through the REST API with the following structure:

```json
{
  "learner": {
    "id": "uuid-v4-user-id",
    "name": "Aarav Sharma",
    "preferred_language": "en-IN"
  },
  "learning_level": {
    "level": 3,
    "name": "Progressing",
    "description": "Making steady progress in reading fluency, vocabulary, and paragraph comprehension.",
    "calculated_at": 1727548000,
    "inputs": {
      "composite_score": 64.5,
      "domains_evaluated": 12,
      "reading_wpm": 60.0,
      "comprehension_metric": 68
    }
  },
  "domain_scores": {
    "phonological_awareness": 72.0,
    "phonological_memory": 65.0,
    "rapid_naming": 58.0,
    "reading_fluency": 55.0,
    "orthographic_spelling": 62.0,
    "reading_comprehension": 80.0,
    "visual_processing": 90.0,
    "visual_attention": 68.0,
    "language_processing": 75.0,
    "working_memory": 65.0,
    "letter_reversal": 70.0,
    "processing_speed": 60.0
  },
  "domain_interpretations": {
    "phonological_awareness": {
      "score": 72.0,
      "label": "Progressing",
      "friendly_name": "Sound & Word Practice",
      "technical_name": "Phonological Awareness",
      "description": "Making steady growth with continuing practice."
    }
  },
  "strengths": [
    {
      "domain": "visual_processing",
      "score": 90.0,
      "label": "Strong",
      "friendly_name": "Visual Pattern Finding",
      "description": "You have strong visual superpowers to spot shapes and patterns!"
    },
    {
      "domain": "reading_comprehension",
      "score": 80.0,
      "label": "Strength",
      "friendly_name": "Story & Text Understanding",
      "description": "You are showing good understanding of what you read."
    }
  ],
  "areas_for_practice": [
    {
      "domain": "reading_fluency",
      "score": 55.0,
      "priority": "medium",
      "friendly_name": "Smooth Reading Flow",
      "description": "Short guided reading activities can help you build smoother reading.",
      "suggested_activity_type": "guided_reading"
    },
    {
      "domain": "rapid_naming",
      "score": 58.0,
      "priority": "medium",
      "friendly_name": "Quick Naming",
      "description": "Speed-naming drills can help words pop into your mind faster.",
      "suggested_activity_type": "rapid_naming_drills"
    }
  ],
  "cognitive_indicators": {
    "working_memory": "standard",
    "visual_processing": "strong",
    "auditory_processing": "standard",
    "processing_speed": "typical"
  },
  "reading_metrics": {
    "reading_level": "intermediate",
    "comprehension_level": 68,
    "vocabulary_level": "standard",
    "avg_words_per_minute": 60.0,
    "words_mastered": 4
  },
  "preferences": {
    "learning_modes": ["Reading", "Visual", "Interactive"],
    "font": "OpenDyslexic",
    "font_size": 18,
    "line_spacing": 2.0,
    "letter_spacing": 0.12,
    "bg_color": "#FFF8F0",
    "text_color": "#1A2A2A",
    "tts_speed": 0.85,
    "tts_language": "en-IN",
    "highlight_words": true,
    "syllable_split": true,
    "auto_simplify": true
  },
  "goals": [
    {
      "id": "goal-1",
      "title": "Complete today's reading practice",
      "completed": false
    },
    {
      "id": "goal-2",
      "title": "Master 5 new vocabulary words",
      "completed": true
    }
  ],
  "confidence": {
    "overall": 0.78,
    "screening": 0.92,
    "performance": 0.51,
    "screening_questions_answered": 20,
    "scored_domains_count": 12
  },
  "metadata": {
    "profile_version": 2,
    "generated_at": 1727548000,
    "updated_at": 1727548000,
    "source": "screening",
    "screening_completed": true
  },
  "disclaimer": "Educational Screening Indicator: This profile summarizes educational screening observations and reading preferences to guide assistive accommodations. It does not constitute a medical, psychological, or clinical diagnosis."
}
```

---

## 3. Domain Normalization & Educational Interpretation

### 3.1. Normalization from Screening Impairment Scale to Educational Proficiency Scale
In the underlying screening battery, tests measure error counts and latencies, producing an impairment metric (0% = error-free, 100% = high error/impairment rate).

The V2 Learner Intelligence Profile normalizes all cognitive domains into an **Educational Scale (0–100)** where higher scores indicate greater relative ability and comfort:
$$\text{Educational Score} = \text{clamp}(100 - \text{Raw Impairment}, 0, 100)$$

### 3.2. Educational Interpretation Thresholds
These thresholds represent non-clinical, educational indicators:

| Score Range | Educational Label | Meaning & Scaffolding Recommendation |
|---|---|---|
| **90–100** | **Strong** | Mastery and high confidence; learner can rely on this strength. |
| **75–89** | **Strength** | Solid capability and positive independence. |
| **60–74** | **Progressing** | Steady growth with continuing practice and positive reinforcement. |
| **40–59** | **Developing** | Foundational understanding; benefits from guided scaffolding. |
| **0–39** | **Needs Practice** | Target for structured practice and multi-sensory accommodations. |

---

## 4. Strength Detection

- **Data-Driven:** Extracted automatically from the highest normalized domain scores ($\ge 60\%$).
- **Child-Friendly Framing:** Uses encouraging language (e.g. *"You have strong visual superpowers to spot shapes and patterns!"*).
- **Cognitive Load Protection:** Limited to the top 2–3 primary strengths so students celebrate their wins without feeling overwhelmed.

---

## 5. Areas to Practice

- **Positive Growth Language:** Never referred to as "Weaknesses" or clinical deficits. Labeled strictly as **"Areas to Practice"**.
- **Actionable Micro-Intervention Match:** Every area includes an educational `suggested_activity_type` (e.g., `phoneme_blending`, `guided_reading`, `word_pattern_builder`, `rapid_naming_drills`).
- **Priority Tiering:**
  - High Priority: Educational score $< 40$
  - Medium Priority: Educational score $40–59$
  - Low / Gentle Practice: Educational score $60–74$

---

## 6. Learning Level Calculation

The educational learning level is a **deterministic, explainable calculation** (Levels 1 to 5) computed across core reading pillars:
- Phonological Awareness (20%)
- Reading Comprehension (20%)
- Reading Fluency (15%)
- Orthographic / Spelling (15%)
- Working Memory (15%)
- Visual Processing (15%)

$$\text{Composite} = \frac{\sum w_i \cdot s_i}{\sum w_i}$$

| Level | Name | Composite Score | Educational Description |
|---|---|---|---|
| **1** | **Foundation** | $0–39$ | Starting your reading journey with foundational letter sounds and basic word shapes. |
| **2** | **Developing** | $40–54$ | Growing your sound blending and word recognition with regular guided practice. |
| **3** | **Progressing** | $55–69$ | Making steady progress in reading fluency, vocabulary, and paragraph comprehension. |
| **4** | **Independent** | $70–84$ | Reading with strong independence, confident decoding, and solid comprehension. |
| **5** | **Advanced** | $85–100$ | Demonstrating high reading automaticity, rich vocabulary, and deep contextual insight. |

---

## 7. Profile Evidence Confidence

The confidence engine calculates a mathematical reliability index ($0.0 \dots 1.0$) based on concrete evidence volume:
1. **Screening Confidence ($C_{\text{screening}}$):** Evaluates completed questions vs. the full battery ($N/20$) and the proportion of domains tested ($D/10$).
2. **Performance Confidence ($C_{\text{perf}}$):** Reflects telemetry volume: completed reading sessions, words read, and task attempts.
3. **Overall Confidence:**
   $$C_{\text{overall}} = 0.7 \cdot C_{\text{screening}} + 0.3 \cdot C_{\text{perf}}$$
4. **Empty State:** If the student has not completed screening, confidence remains strictly $0.0$ (never fabricated).

---

## 8. Screening Integration Architecture

Integration between V1 screening and V2 profile synthesis occurs safely at the service layer:
```
Student submits answers to POST /api/dyslexia-test/submit
              ↓
analyze_screening(answers) scores battery (V1 algorithm unchanged)
              ↓
screening_results document inserted (Immutable historical attempt)
              ↓
users.readingProfile updated (V1 compatibility maintained)
              ↓
progress.screeningCompleted set to True
              ↓
recalibrate_from_screening(user_id, result) runs asynchronously
              ↓
V2 learner_profiles document synthesized & stored
              ↓
V1 submission returns result JSON without delay or disruption
```

---

## 9. API Specifications

### `GET /api/v2/learner/profile`
- **Access:** Student (self) via JWT Bearer token.
- **Description:** Returns the sanitized, frontend-friendly learner intelligence profile.
- **Unscreened Response:** Returns 200 OK with `screening_completed: false` and empty scores so frontend displays empty state without error.

### `PATCH /api/v2/learner/profile`
- **Access:** Student (self).
- **Permitted Fields:** `current_goals`, `preferred_language`, `preferred_learning_modes`, `accessibility_preferences`.
- **Security Constraint:** System-generated domain scores, learning levels, and confidence ratings are strictly immutable by students.

### `GET /api/v2/learner/state`
- **Access:** Student (self).
- **Description:** Returns active learning state, streak, and difficulty tier.

### `GET /api/v2/learner/student/{id}/profile`
- **Access:** Teacher only (`require_teacher` dependency).
- **Authorization Check:** Verifies that the requested student is enrolled in the teacher's active classroom (`classroomJoined == teacher.classroomCode`). Unauthorized access returns `404 Not Found` or `403 Forbidden`.

---

## 10. Frontend Components (`frontend/src/features/learner/`)

- `LearnerProfileHeader`: Child-friendly greeting, language chips, refresh trigger.
- `LearningLevelCard`: Stepped 5-level progression tracker with explainability metrics.
- `StrengthsCard`: Identified superpower cards with positive reinforcement descriptions.
- `PracticeAreasCard`: Constructive growth areas with activity type chips.
- `DomainScoreChart`: 12-domain interactive map with friendly/technical name toggle and educational color coding.
- `LearningPreferencesCard`: Interactive mode selector (Reading, Listening, Visual, Interactive).
- `AccessibilityPreferencesCard`: Direct controls for dyslexia-friendly fonts, text size, background tint, and TTS speed.
- `LearningGoalsCard`: Interactive reading goals checklist with addition capability.
- `ProfileConfidenceCard`: Calibration metrics and data source transparency.
- `LearnerDisclaimer`: Prominent non-clinical educational indicator notice.
- `LearnerEmptyState`: Welcoming empty state with `[Complete Learning Check]` button navigating to screening.
- `LearnerProfileSkeleton`: Accessible pulse loading skeleton.
- `LearnerErrorState`: Friendly error state with retry button.

---

## 11. Security, Privacy & Data Governance

1. **Role-Based Access Control (RBAC):** Students can only read and update their own profile (`user["id"]`). Teachers can only access profiles of students enrolled in their assigned classroom code.
2. **Sanitized Output:** MongoDB internal identifiers (`_id`, `passwordHash`) are stripped before responding.
3. **Data Loss Prevention:** Backward-compatible synchronization preserves existing `users.settings` and `users.readingProfile` documents.
4. **Educational Disclaimer Enforced:** Explicitly stated on all profile APIs, student profile cards, and teacher drilldown views.
