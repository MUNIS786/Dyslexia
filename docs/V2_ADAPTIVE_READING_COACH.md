# DyslexAid V2 Adaptive Reading Coach Specification

**Platform:** DyslexAid V2 Adaptive Reading Coach  
**Release Horizon:** Phase 4 Implementation  
**Standard:** Continuous Closed-Loop Accessible Reading Practice & ZPD Adaptation  
**Safety Framing:** Strictly Educational & Assistive Practice Accommodations (Non-Clinical)

---

## 1. Architectural Overview

The DyslexAid Adaptive Reading Coach constitutes the primary reading-practice experience for learners with dyslexia and reading challenges. It closes the feedback loop between the student's **Learner Intelligence Profile (Phase 2)** and the **Adaptive Learning Engine (Phase 3)** by presenting calibrated reading passages, assistive ergonomics, interactive difficult-word support, and comprehension checks.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   V2 Adaptive Reading Coach Lifecycle                  │
└────────────────────────────────────────────────────────────────────────┘
                                 │
     ┌───────────────────────────┴───────────────────────────┐
     ▼                                                       ▼
1. Learner Profile & State                             2. Adaptive Passage Recommender
   • Current ZPD Tier (1-5)                              • Best-Fit Tier Calibration
   • Rolling Comprehension Trend                         • Unread Passage Prioritization
   • Priority Practice Areas                             • Child-Friendly Explainable Reason
     │                                                       │
     └───────────────────────────┬───────────────────────────┘
                                 │
                                 ▼
                    3. Accessible Reading Experience
                       • Reading Ergonomics (Font, Spacing, Width, Tint)
                       • Display Modes (Standard, Focus, Guided, Listen)
                       • Clickable Word Support (Phonics, Syllables, TTS)
                                 │
                                 ▼
                    4. Comprehension Quiz Player
                       • Step-by-Step Questions (1 at a time)
                       • Large Readable Touch Targets
                       • Instant Encouraging Feedback
                                 │
                                 ▼
                    5. Server-Side Performance Engine
                       • Comprehension Score = (correct / total) * 100
                       • Completion Rate & Gentle Pacing Metric
                       • Overall Score (60% comp + 25% comp rate + 15% pacing)
                                 │
                                 ▼
                    6. Phase 3 Adaptive Engine Integration
                       • Persist `reading_sessions`
                       • Update `reading_comprehension` & `reading_fluency`
                       • Trigger ZPD Upward / Downward Adaptation
                       • Level Up / Down Reflection in Next Reading
```

---

## 2. Reading Data Models

### 2.1 Reading Sessions Collection (`db.reading_sessions`)
Persists telemetry and educational results for each reading attempt.

```python
class ReadingSession(BaseModel):
    sessionId: str
    learnerId: str
    activityId: Optional[str] = None
    passageId: str
    domain: str = "reading_comprehension"
    difficulty: int = 1
    startedAt: int
    completedAt: Optional[int] = None
    readingMode: str = "standard"  # standard | focus | guided | listen
    language: str = "en"
    wordsPresented: int = 0
    wordsRead: int = 0
    wordsCompleted: int = 0
    durationSeconds: int = 0
    comprehensionQuestions: int = 0
    comprehensionCorrect: int = 0
    comprehensionAccuracy: float = 0.0
    hintsUsed: int = 0
    replaysUsed: int = 0
    difficultWords: List[str] = []
    practicedWords: List[str] = []
    readingScore: float = 0.0
    comprehensionScore: float = 0.0
    overallScore: float = 0.0
    completed: bool = False
    skipped: bool = False
    adaptation: Optional[Dict[str, Any]] = None
    createdAt: int
    updatedAt: int
```

**Indexes:**
- `sessionId` (unique)
- `learnerId`
- `createdAt`
- `(learnerId, createdAt: -1)`
- `(learnerId, activityId)`

### 2.2 Reading Passages Collection (`db.reading_passages`)
Reusable educational passage representation with embedded vocabulary definitions and comprehension questions.

**Fields:**
- `passageId`: Unique identifier (e.g. `pas-t1-001`)
- `title`: Child-friendly title
- `text`: Educational passage text
- `difficulty`: Difficulty tier (1=Foundation to 5=Mastery)
- `domain`: Educational domain (default `reading_comprehension`)
- `estimatedMinutes`: Estimated reading time (1–10 mins)
- `wordCount`: Total word count
- `language`: Language code (`en`)
- `gradeBand`: Target educational level (e.g. `Grade 1`, `Grade 3-4`)
- `topics`: Subject tags (e.g. `nature`, `science`, `animals`)
- `questions`: List of `ReadingQuestion`
- `vocabulary`: List of `ReadingVocabularyWord`
- `accessibility`: Typography & layout presets
- `active`: Boolean availability flag

---

## 3. Seed Passage Catalog (Tiers 1–5)

The platform provides a deterministic local library of original educational passages spanning all 5 difficulty tiers without requiring external LLM APIs:

| Tier | Title | Word Count | Grade Band | Phonics / Focus |
|---|---|---|---|---|
| **Tier 1 (Foundation)** | *Sam the Orange Cat* | 60 | Grade 1 | CVC words, short vowels, sight words |
| **Tier 1 (Foundation)** | *The Little Red Hen* | 62 | Grade 1 | Consonant blends, simple syntax, nature |
| **Tier 2 (Supported)** | *Leo the Brave Pond Frog* | 94 | Grade 2 | Compound words, multi-sentence narrative, courage |
| **Tier 2 (Supported)** | *Asha's Paper Kite* | 85 | Grade 2 | Descriptive language, family crafts, action verbs |
| **Tier 3 (Standard)** | *The River Otters of the Western Ghats* | 97 | Grade 3-4 | Multi-paragraph, ecology, bioindicators |
| **Tier 3 (Standard)** | *Maya and the Solar Oven* | 110 | Grade 3-4 | Applied science, renewable clean energy, experiments |
| **Tier 4 (Advanced)** | *The Secrets of Firefly Bioluminescence* | 154 | Grade 5-6 | Compound-complex sentences, biological enzymes, biomimicry |
| **Tier 5 (Mastery)** | *Architectural Marvels: The Stepwells of India* | 166 | Grade 7-8 | Academic vocabulary, subterranean hydrology, historical synthesis |

Each passage includes:
1. **Comprehension Questions:** Covering `main_idea`, `detail`, `sequence`, `vocabulary_in_context`, and `simple_inference`.
2. **Predefined Vocabulary:** Child-friendly definitions, phonetic guides, syllable breakdowns, and contextual example sentences.

---

## 4. Adaptive Passage Recommender

Located in `backend/services/learning/reading_recommender.py`:
- **Input:** Learner profile, learning state, active ZPD difficulty tier, domain performance, recent sessions.
- **Selection Heuristic:**
  1. Filters catalog by student's active tier (1–5).
  2. Prioritizes unread passages over recently completed passages to prevent immediate repetition.
  3. Sorts by word count / complexity based on rolling accuracy:
     - Consecutive passes ($\ge 1$): slightly longer passage for gentle challenge.
     - Consecutive struggles ($\ge 1$): slightly shorter passage for supportive scaffolding.
  4. Generates an explainable, encouraging child-facing reason (e.g. *"You've been reading with great comprehension! 'The Little Red Hen' is calibrated at Level 1 to help you build mastery and prepare for higher levels."*).
- **Fallback:** Gracefully serves Level 1/2 foundation passages to unscreened or fresh learners.

---

## 5. Accessibility & Ergonomics System

Built specifically for learners with dyslexia and visual tracking sensitivities:
- **Typography:** OpenDyslexic (weighted baselines to prevent letter flipping), Lexend (reduced visual crowding), Arial (clean sans fallback).
- **Controls:**
  - Font Size: 16px to 32px
  - Line Spacing: 1.4x to 2.6x
  - Letter Spacing: 0.05em to 0.20em
  - Reading Width: Narrow (540px), Normal (720px), Wide (900px)
  - Color Tinting: Warm Cream (`#FFF8F0`), Clean White (`#FFFFFF`), Soft Sky (`#F0F9FF`), Gentle Beige (`#F5F5DC`)
- **Display Modes:**
  1. **Standard Mode:** Classic paragraph reading.
  2. **Focus Mode:** Chunks text into single sentences/paragraphs with stepper buttons (`Part 1 of 8`) to eliminate visual crowding.
  3. **Guided Reading Mode:** Highlights the active sentence with warm contrast while gently dimming surrounding lines.
  4. **Listen Mode:** Reads passage aloud via browser SpeechSynthesis with real-time audio playback controls.

---

## 6. Word Support (Vocabulary Interaction)

- Learners can click/tap any word in a passage.
- Predefined vocabulary items feature a subtle dotted underline indicator.
- Clicking opens the **Difficult Words Modal**:
  - Word title and phonetic respelling
  - Syllable separation pills (e.g. `bio · lu · mi · nes · cence`)
  - Simple, non-technical definition
  - Real-world example sentence
  - Audio pronunciation button (synthesizes speech locally)
- Telemetry records `difficultWords` and `practicedWords` for progress analysis.

---

## 7. Comprehension Quiz Player

- Presented immediately upon completing passage reading.
- One question displayed at a time with large touch-friendly buttons.
- Clear, immediate feedback:
  - Correct: celebratory message (*"You got it! 🌟"*) with full educational explanation.
  - Incorrect: gentle, non-punitive encouragement (*"Nice try! Let's check this part again: ..."*).
- Questions cannot be answered more than once, and answers are never revealed prior to student selection.

---

## 8. Reading Performance Engine

Implemented in `backend/services/learning/reading_performance.py`:

$$ComprehensionScore = \frac{CorrectQuestions}{TotalQuestions} \times 100$$
$$CompletionRate = \min\left(100, \frac{WordsRead}{WordsPresented} \times 100\right)$$
$$OverallScore = 0.60 \times ComprehensionScore + 0.25 \times CompletionRate + 0.15 \times TimeEfficiency + PracticeBonus - HintPenalty$$

**Safety Protections:**
- Zero-question protection: returns 100.0% if total questions is 0, preventing division-by-zero.
- Skipped sessions receive a fixed low score (20.0%) and do not artificially boost streaks.
- Slower, careful reading is never penalized; pacing scores reward deliberate attention.
- Server-side grading: student submitted answers are graded exclusively on the server against passage question definitions.

---

## 9. Phase 3 Adaptive Engine Integration

Completing a reading session immediately triggers the Phase 3 progression loop:
1. Calculates objective session metrics.
2. Synchronizes consecutive passes and failures:
   - High score ($\ge 80\%$ overall & $\ge 70\%$ comprehension) increments consecutive passes.
   - Low score ($< 50\%$ overall) increments consecutive failures.
3. Evaluates ZPD Adaptation:
   - **3 consecutive passes:** triggers tier advance ($Tier_{new} = Tier_{old} + 1$).
   - **2 consecutive failures:** triggers supportive scaffolding ($Tier_{new} = Tier_{old} - 1$).
4. Updates `learner_profiles` domain scores:
   - `reading_comprehension` updated with comprehension accuracy.
   - `reading_fluency` updated with reading engagement score.
5. Next recommendation automatically reflects the adapted tier!

---

## 10. REST API Reference

All endpoints are hosted under `/api/v2/reading` and guarded by `V2_READING_COACH`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/reading/recommendation` | Returns optimal reading passage recommendation for the authenticated student. |
| `GET` | `/api/v2/reading/passages` | Lists passages with optional `tier`, `domain`, and `language` filters. |
| `GET` | `/api/v2/reading/passages/{id}` | Fetches full passage details including questions and vocabulary. |
| `POST` | `/api/v2/reading/session/start` | Creates a new reading session record. |
| `POST` | `/api/v2/reading/session/complete` | Submits telemetry; grades answers; triggers Phase 3 adaptation. |
| `GET` | `/api/v2/reading/sessions` | Retrieves learner's reading session history. |
| `GET` | `/api/v2/reading/stats` | Returns aggregated reading stats (words read, total minutes, accuracy, trend). |

---

## 11. Security & Authorization

- **Student Isolation:** Students can only start, complete, view, and read their own sessions. Any attempt by a student to pass `student_id` for another learner is rejected with `403 Forbidden`.
- **Teacher Verification:** Teachers may view reading statistics and session history only for students enrolled in their active classroom (`classroomJoined == teacher.classroomCode`).
- **Server-Side Grading:** Clients cannot submit calculated scores; scores are computed strictly by the server.

---

## 12. Feature Flag

The feature flag `V2_READING_COACH` is defined in `backend/core/config.py`:
- When disabled (`false`), all `/api/v2/reading/*` endpoints return `503 Service Unavailable`.
- When enabled (`true`), the complete reading coach pipeline is active.
- Overridable via the environment variable `V2_READING_COACH`.

---

## 13. Safety & Educational Disclaimers

DyslexAid is an educational assistive tool designed to make reading joyful, accessible, and confidence-building.
- It does **NOT** provide medical, psychological, or clinical diagnoses of dyslexia or reading disorders.
- It does **NOT** measure intelligence (IQ) or clinical deficit severity.
- Browser text-to-speech (TTS) usage is recognized as an assistive reading modality, not an indicator of reading inability.
- All progression feedback uses non-stigmatizing, growth-mindset language.
