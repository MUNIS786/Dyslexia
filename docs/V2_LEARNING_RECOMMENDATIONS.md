# DyslexAid V2 — Phase 14: Personalized Learning Recommendations & Study Plan Engine

## 1. Objective

Phase 14 delivers a deterministic, explainable **Personalized Learning Recommendation Engine and Study Plan** for DyslexAid V2. It directly answers:

> **"What should this learner practice next, and why?"**

By synthesizing multi-domain signals generated across Phases 2–13, Phase 14 generates actionable, prioritized next practice steps and bounded daily study plans tailored to three core personas:
1. **Student:** Receives encouraging, child-friendly recommendations (e.g. practicing tricky words, reading calibrated stories, or trying read-aloud practice), an accessible daily study plan, and optional AI Tutor integration.
2. **Teacher:** Views the learner's recommended focus, underlying pedagogical rationale, and supporting longitudinal evidence within Teacher Analytics.
3. **Parent / Guardian:** Sees encouraging suggestions for at-home shared reading, recommended daily reading minutes, target focus words, and evidence-based encouragement tips.

---

## 2. Architecture & File Structure

Phase 14 strictly follows the established DyslexAid modular architectural conventions:

```text
backend/
  core/
    config.py                           # Feature flag: V2_LEARNING_RECOMMENDATIONS (default: True)
  models/
    v2_learning_recommendations.py     # Pydantic v2 data models & response contracts
    __init__.py                         # Model re-exports
  services/
    learning/
      learning_recommendations.py      # Recommendation engine, ranking, study plan generator
  routers/
    v2_learning_recommendations.py     # Role-guarded API router (/api/v2/learning-recommendations)
  test_phase14_learning_recommendations.py # 22 deterministic unit/integration tests

frontend/
  src/
    api/v2/
      client.js                         # recommendationsV2API client
    components/
      recommendations/
        RecommendationCard.jsx          # Priority cards with category badge, reason, & launch CTA
        StudyPlan.jsx                   # Daily study plan with progress bar & horizon toggle
        RecommendationReason.jsx        # Child-friendly 'Why?' explanation component
        RecommendationEmptyState.jsx    # Encouraging 'Getting to Know You' state
        TeacherRecommendedFocusCard.jsx # Teacher analytics pedagogical focus component
        ParentSuggestedPracticeCard.jsx # Parent portal at-home reading suggestions component
        index.js                        # Barrel export
    pages/
      student/
        LearningRecommendationsPage.jsx # Dedicated student route (/student/recommendations)
    i18n/
      locales/en.js                     # English translations
      locales/hi.js                     # Hindi translations
      locales/mr.js                     # Marathi translations
    App.jsx                             # Route registration & screening exception
```

---

## 3. Data Sources & Signal Collection

Phase 14 does **not** create a second adaptive-learning system. Phase 3 remains the authoritative source for the learner's adaptive tier and progression. Phase 14 consumes real evidence collected across:

1. **Phase 2 (Learner Intelligence Profile):**
   - Baseline learning level (1–5) and level designation (`Foundation` through `Fluent`).
   - Profile strengths and prioritized practice areas.
2. **Phase 3 (Adaptive Learning Engine):**
   - Authoritative active difficulty tier (1–5).
   - Consecutive passes and consecutive failures.
   - Rolling comprehension score history.
3. **Phase 4 (Reading Coach):**
   - Recent passage reading performance and words attempted.
   - Specific difficult words recorded during reading sessions.
4. **Phase 5 (Speech & Reading Analysis):**
   - Oral reading word accuracy and presence of speech practice records.
5. **Phase 8 (Intervention Effectiveness):**
   - Active pedagogical support strategies and effectiveness response.
6. **Phase 9 (Gamification & Engagement):**
   - Active streak and daily consistency habits.
7. **Phase 13 (Learning Insights):**
   - Longitudinal progress trends in reading accuracy, reading speed, practice consistency, and speech accuracy (`improving`, `stable`, `needs_attention`, `insufficient_data`).

---

## 4. Controlled Recommendation Categories

To ensure pedagogical clarity and prevent recommendation sprawl, recommendations are strictly categorized into 6 controlled types:

| Category | Educational Intent | Typical Action | Estimated Duration |
| :--- | :--- | :--- | :--- |
| **`READING_PRACTICE`** | Core story reading calibrated to active adaptive tier | `/student/reading-coach?passageId=...` | 10 mins |
| **`DIFFICULT_WORD_PRACTICE`** | Targeted syllable and phoneme practice on tricky words | `/student/adaptive-learning` | 5 mins |
| **`SPEECH_PRACTICE`** | Oral read-aloud practice to activate voice-print pathways | `/student/reading-coach` | 5 mins |
| **`REVIEW`** | Low-stress spaced repetition of mastered foundational patterns | `/student/adaptive-learning` | 5 mins |
| **`STRETCH`** | Optional higher-tier challenge when learner shows mastery | `/student/reading-coach?passageId=...` | 15 mins |
| **`CONSISTENCY`** | Quick 5-minute habit builder when practice has dipped | `/student/reading-coach` | 5 mins |

---

## 5. Eligibility & Safety Rules

Before a candidate recommendation is approved, it is validated against strict pedagogical constraints:
- **Adaptive Level Eligibility:** Activities and passages must match the learner's active ZPD tier. Advanced material that conflicts with the adaptive level is rejected.
- **Stretch Eligibility:** A `STRETCH` challenge is eligible **only if** `consecutive_passes >= 2`, `current_tier < 5`, and `readingAccuracy >= 80%`.
- **Repetition Suppression:** Passages read in the learner's immediate previous sessions are de-duplicated.
- **Language Compatibility:** Passages and tasks must conform to the learner's active locale/language.

---

## 6. Transparent Ranking & Scoring Formula

Candidate activities are ranked using a deterministic, explainable scoring formula:

$$\text{Score} = \text{Need} + \text{Recency} + \text{Adaptive Suitability} + \text{Practice Gap} + \text{Effectiveness}$$

- **Need (0–35 pts):** High when specific tricky words exist ($\ge 3$ words $\to 35$ pts), when speech data is missing, or when reading consistency needs reinforcement.
- **Recency (0–20 pts):** Rewards variety; candidates already completed today are down-weighted to prioritize uncompleted goals.
- **Adaptive Suitability (0–25 pts):** Max points for precise alignment with the learner's active ZPD tier.
- **Practice Gap (0–15 pts):** Directly targets identified improvement areas from Phase 2 and Phase 13.
- **Effectiveness (0–10 pts):** Incorporates high-performing pedagogical strategies from Phase 8.

---

## 7. Child-Friendly Explanations & Confidence

Every recommendation is paired with an encouraging, non-clinical explanation:
- **Child-Friendly 'Why?':** Clear, relatable phrasing such as:
  - *"Your recent reading shows lower accuracy on words like 'sprout' and 'through'. A quick practice round will build confidence."*
  - *"Your reading comprehension is improving! Keep up the momentum with 'The Forest River' at Level 2."*
- **Non-Clinical Confidence Rating:**
  - `high`: Multiple corroborating data points across sessions.
  - `medium`: Steady single-window signal.
  - `low`: Limited recent activity.
  - `insufficient_data`: New learner with no or 1 session.
  *(Represents evidence sufficiency, NOT medical or diagnostic certainty).*

---

## 8. Personalized Study Plan & Completion Tracking

- **Planning Horizons:** Supports `today` (default daily plan) and `7d` (weekly pacing).
- **Daily Plan Limit:** Bounded strictly to **2 to 4 activities per day** to prevent learner cognitive overload. Total estimated workload is typically 15–25 minutes.
- **Real Completion Tracking:** Does not manufacture completion. Verifies whether matching session records exist in `reading_sessions`, `activity_attempts`, or `speech_reading_analyses` for the current calendar day.
- **Idempotent Refresh:** `POST /api/v2/learning-recommendations/student/refresh` recalculates recommendations deterministically without creating duplicate entries.

---

## 9. Privacy, Security & Data Governance

- **Zero Raw Audio Exposure:** Speech analysis signals are derived strictly via client-side Web Speech API; zero audio blobs or recordings are stored or transmitted.
- **Zero AI Tutor Transcript Exposure:** Multi-turn conversational transcripts remain strictly shielded from recommendation endpoints.
- **Zero Teacher-Private Note Exposure:** Private educator notes and IEP flags remain strictly isolated in Teacher Analytics.
- **Tenant Isolation:** Enforced on every database query using authenticated user credentials.

---

## 10. APIs

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v2/learning-recommendations/student` | Student (`get_current_user`) | Returns student recommendations and daily study plan |
| `POST` | `/api/v2/learning-recommendations/student/refresh` | Student (`get_current_user`) | Refreshes recommendations with latest progress telemetry |
| `GET` | `/api/v2/learning-recommendations/teacher/{learner_id}` | Teacher (`require_teacher`) | Returns teacher pedagogical focus and evidence summary |
| `GET` | `/api/v2/learning-recommendations/parent/{learner_id}` | Parent (`require_parent`) | Returns parent at-home reading suggestions and tips |

---

## 11. Multilingual & Accessibility Support

- **Multilingual (Phase 10):** Full localization across English (`en`), Hindi (`hi`), and Marathi (`mr`).
- **Accessibility (Phase 12):** Semantic buttons, visible focus indicators, responsive card layouts, no horizontal scrolling, and full compatibility with OpenDyslexic typography, variable line/letter spacing, high contrast mode, and visual stress tinting.

---

## 12. Verification & Test Suite

### Backend Test Suite (`test_phase14_learning_recommendations.py`)
- **22 Unit & Integration Tests:**
  1. `test_new_learner_no_data_state`: Validates empty state and beginner starter activities.
  2. `test_insufficient_data_state`: Validates 1-session history handling.
  3. `test_reading_practice_recommendation`: Validates tier-calibrated story selection.
  4. `test_difficult_words_recommendation`: Validates extraction of tricky vocabulary words.
  5. `test_speech_practice_recommendation`: Validates oral reading practice recommendation.
  6. `test_stretch_challenge_eligibility`: Validates eligibility on consecutive passes.
  7. `test_stretch_challenge_ineligibility`: Validates suppression when criteria are unmet.
  8. `test_recommendation_ranking_priority`: Validates deterministic priority ordering.
  9. `test_recommendation_explanations`: Validates child-friendly 'Why?' rationales.
  10. `test_daily_plan_bounded_limit`: Validates study plan limit of 2-4 activities.
  11. `test_completion_tracking_real_records`: Validates real session completion reflection.
  12. `test_recommendation_refresh_endpoint`: Validates idempotent refresh behavior.
  13. `test_student_authentication_required`: Validates 401 on unauthenticated access.
  14. `test_student_tenant_isolation`: Validates student isolation to own ID.
  15. `test_teacher_authorized_learner_access`: Validates teacher access for enrolled student.
  16. `test_teacher_unauthorized_learner_access`: Validates 403 on non-enrolled student.
  17. `test_parent_authorized_child_access`: Validates parent access for linked child.
  18. `test_parent_unauthorized_child_access`: Validates 403 on unlinked child.
  19. `test_privacy_zero_tutor_transcripts`: Validates zero chat transcripts in responses.
  20. `test_privacy_zero_raw_audio`: Validates zero raw audio in responses.
  21. `test_feature_flag_disabled_returns_503`: Validates 503 behavior when disabled.
  22. `test_invalid_period_parameter_returns_422`: Validates query parameter validation.

**Results:**
- **Phase 14 Tests:** **22 / 22 Passed**
- **Full Backend Suite:** **313 / 313 Passed** (0 failures, 0 regressions)
- **Frontend ESLint:** `npm run lint` exited 0 (0 errors, 0 warnings).
- **Frontend Build:** `npm run build` succeeded cleanly in 3.23s.
