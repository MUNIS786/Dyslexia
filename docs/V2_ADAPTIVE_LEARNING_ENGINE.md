# DyslexAid V2 Adaptive Learning Engine Specification

**Platform:** DyslexAid V2 Adaptive Learning Engine  
**Release Horizon:** Phase 3 Implementation  
**Standard:** Continuous Closed-Loop Adaptation within the Zone of Proximal Development (ZPD)  
**Safety Framing:** Strictly Educational & Non-Clinical Pedagogical Scaffolding

---

## 1. Architectural Overview

The DyslexAid Adaptive Learning Engine transforms student interaction telemetry into a continuous, real-time feedback loop. Rather than delivering static or one-size-fits-all exercises, the engine calibrates micro-task difficulty, pacing, and visual scaffolding according to the learner's individual **Zone of Proximal Development (ZPD)**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      V2 Continuous Adaptive Loop                       │
└────────────────────────────────────────────────────────────────────────┘
                                 │
     ┌───────────────────────────┴───────────────────────────┐
     ▼                                                       ▼
1. Learner Profile & State                             2. Activity Recommender
   • Current ZPD Tier (1-5)                              • 80% Priority Growth Areas
   • Rolling Comprehension Trend                         • 20% Strength Reinforcement
   • Priority Practice Areas                             • Child-Friendly Rationale
     │                                                       │
     └───────────────────────────┬───────────────────────────┘
                                 │
                                 ▼
                    3. Interactive Micro-Task Player
                       • Web Speech Audio Prompts
                       • Latency & Hesitation Tracking
                       • Hint Request Monitoring
                                 │
                                 ▼
                    4. Adaptive Decision Engine
                       • Check Upward / Downward Thresholds
                       • Update Difficulty Tier (1-5)
                       • Live Profile Recalibration
```

---

## 2. Educational Difficulty Tiers (1 to 5)

Content difficulty is partitioned into 5 deterministic educational tiers. Each tier governs sentence length, vocabulary complexity, scaffolding intensity, allowed hints, and time limits:

| Tier | Tier Name | Description | Max Sentence Length | Vocabulary Level | Scaffolding Level | Allowed Hints | Time Multiplier |
|---|---|---|---|---|---|---|---|
| **1** | **Foundation** | Single sounds, simple CVC words, high visual guidance. | 6 words | simple_cvc | Maximum | 3 | 1.5x |
| **2** | **Developing** | Consonant blends, high-frequency sight words. | 9 words | consonant_blends | High | 2 | 1.25x |
| **3** | **Progressing** | Multi-syllable phonemes, compound words, standard syntax. | 13 words | multi_syllabic | Standard | 2 | 1.0x |
| **4** | **Independent** | Complex spelling patterns, irregular words, paragraph reading. | 18 words | complex_orthographic | Light | 1 | 0.9x |
| **5** | **Advanced** | Academic vocabulary, multi-paragraph context, inferential reasoning. | 24 words | academic | Minimal | 1 | 0.8x |

---

## 3. Mathematical Adaptation & Progression Rules

The engine implements deterministic progression heuristics to maintain the student in their optimal Zone of Proximal Development (challenging enough to stimulate growth, accessible enough to prevent anxiety).

### Upward Progression (Advancing Difficulty Tier)
Advancing to the next tier ($Tier_{new} = \min(5, Tier_{old} + 1)$) occurs when either:
1. **Consecutive Mastery:** The student completes **3 consecutive activities** with scores $\ge 80.0\%$.
2. **Comprehension Delta:** The rolling average of the last 3 sessions improves by $\ge +15.0\%$ over baseline and reaches $\ge 80.0\%$.

### Downward Adaptation (Scaffolding & Confidence Reinforcement)
Easing difficulty to reinforce foundations ($Tier_{new} = \max(1, Tier_{old} - 1)$) occurs when either:
1. **Consecutive Struggle:** The student experiences **2 consecutive activities** with scores $< 50.0\%$.
2. **Comprehension Drop:** The rolling average drops by $\ge 15.0\%$ below earlier performance, with recent average $< 50.0\%$.

### ZPD Maintenance
When scores fall between $50.0\%$ and $79.9\%$, the student is operating in their productive growth zone. The engine maintains the current tier, reinforcing skills with varied micro-task formats.

---

## 4. Activity Recommendation Strategy

The recommender executes an 80/20 balanced pedagogical strategy:
- **80% Growth Areas:** Activities selected from the student's highest-priority `areasForPractice` (e.g. phonological awareness, rapid naming, letter reversal, or sight-word spelling).
- **20% Strength Reinforcement:** Activities selected from detected `strengths` (e.g. visual processing pattern finding) to foster self-efficacy and prevent frustration.
- **Explainable Rationale:** Every recommended task displays a motivating, transparent reason for why it was chosen (e.g., *"Why recommended: Focuses on Sound & Word Practice, an area where guided practice will help you connect letters to sounds."*).

---

## 5. Live Profile Recalibration

When an activity attempt is submitted, `recalibrate_from_activity` executes an asynchronous update on the student's `learner_profiles` document:
- **Exponential Moving Average:** Domain scores are updated via $S_{updated} = 0.80 \times S_{old} + 0.20 \times S_{attempt}$.
- **Dynamic Re-sorting:** Strengths and practice areas are re-evaluated if updated domain scores cross educational interpretation boundaries.
- **Progress Sync:** Updates `progress.comprehensionScores`, `progress.tasksCompleted`, and daily streak.

---

## 6. REST API Specification

All endpoints are prefixed with `/api/v2/learning` and guarded by `V2_ADAPTIVE_ENGINE`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/learning/activities` | Query catalog micro-tasks filtered by `domain` and/or `tier` (1–5). |
| `GET` | `/api/v2/learning/recommendations` | Retrieve ZPD-calibrated daily activities with explainable rationale. |
| `POST` | `/api/v2/learning/attempt` | Submit attempt telemetry (`scorePercent`, `durationSeconds`, `hesitationCount`, `hintsRequested`). Evaluates ZPD rules and returns adaptation result. |
| `GET` | `/api/v2/learning/state` | Returns active difficulty tier, streak, rolling comprehension scores, and tier calibration. |
| `GET` | `/api/v2/learning/tier-info` | Returns definitions and UI parameters for all 5 tiers. |

---

## 7. Frontend Architecture

### Core Feature Components (`frontend/src/features/learning/`)
1. **`AdaptiveTaskCarousel.jsx`**: Renders tailored challenge cards with domain icons, tier badges, duration estimates, and explainable rationale callouts.
2. **`InteractiveTaskPlayer.jsx`**: Accessible modal player supporting audio/phoneme prompts, speed naming sprint grids, letter reversal checks, hint requests, hesitation tracking, and celebration modals.
3. **`TierProgressionCard.jsx`**: Visual 5-step progression track, active tier badge, day streak counter, and tasks-completed counter.
4. **`AdaptiveEmptyState.jsx`**: Guidance prompt for learners who have not completed their screening assessment.

### Student Experience Integration
- Dedicated page: `/student/adaptive-learning` (`AdaptiveLearningPage.jsx`).
- Direct navigation in `Layout.jsx` sidebar (`🎯 Adaptive Practice`).
- Quick Spotlight banner embedded on `StudentHome.jsx` linking directly to adaptive tasks.

---

## 8. Educational Safety Requirement

DyslexAid is an educational support platform. All adaptive progression metrics, tier calibrations, and domain scores represent **assistive learning accommodations and instructional pacing**, NOT medical or clinical diagnoses of dyslexia severity.
