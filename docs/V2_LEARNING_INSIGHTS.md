# DyslexAid V2 — Phase 13: Learning Insights & Progress Reports

## 1. Objective

Phase 13 delivers a comprehensive, child-friendly, non-clinical **Learning Insights & Progress Reports** system for DyslexAid V2. It synthesizes real longitudinal activity data generated across Phases 2–12 into actionable, encouraging progress information tailored to three distinct personas:

1. **Student ("Am I improving? What should I practice next?"):**
   - Personal learning level and adaptive challenge tier.
   - Longitudinal progress trends in reading accuracy, comfortable reading speed, and practice consistency.
   - Identified personal strengths and superpowers.
   - Constructive, actionable next steps and words to review.
   - Visual SVG timeline and streak tracking.

2. **Teacher ("Which students are progressing? Who needs additional practice?"):**
   - Classroom-wide longitudinal KPIs (average accuracy, average WPM, distribution of students improving vs. steady vs. needing practice).
   - Class-level common practice priorities.
   - Individual learner summary cards with single-click drilldown into detailed analytics modal, powered by an aggregation strategy with zero N+1 database queries.

3. **Parent / Guardian ("Is my child practicing consistently? How can I help at home?"):**
   - Clear, parent-friendly summary of reading progress and active consistency.
   - Oral reading and comprehension trajectory without diagnostic jargon.
   - Supportive, evidence-based at-home reading encouragement tips.

---

## 2. Architecture & File Structure

Following DyslexAid V2 standards, the implementation strictly adheres to the existing modular pattern:

```text
backend/
  core/
    config.py                     # Feature flag: V2_LEARNING_INSIGHTS (default: True)
  models/
    v2_learning_insights.py       # Pydantic v2 schemas & response contracts
    __init__.py                   # Re-exports Phase 13 models
  services/
    learning/
      learning_insights.py        # Trend analysis, data sufficiency, aggregation engine
  routers/
    v2_learning_insights.py       # Role-guarded API endpoints (/api/v2/learning-insights)
  test_phase13_learning_insights.py # 22 deterministic unit/integration tests

frontend/
  src/
    api/v2/
      client.js                   # insightsV2API endpoints
    components/
      insights/
        PeriodSelector.jsx        # Accessible 7d / 30d / 90d selector
        TrendCard.jsx             # Accessible metric card with text & symbol indicators
        ProgressChart.jsx         # Pure inline SVG longitudinal accuracy & speed chart
        DataSufficiencyBanner.jsx # Encouraging empty/insufficient history banners
        StrengthsFocusCard.jsx    # Real metric-driven strengths & tricky words
        ClassInsightsSection.jsx  # Teacher cohort KPI & learner cards component
        ParentProgressSection.jsx # Parent portal longitudinal progress component
        index.js                  # Barrel export
    pages/
      student/
        LearningInsightsPage.jsx  # Dedicated student progress route (/student/insights)
      teacher/
        TeacherAnalyticsPage.jsx  # Embedded ClassInsightsSection with modal drilldown
    features/
      parent/
        ParentDashboard.jsx       # Embedded ParentProgressSection
    i18n/
      locales/en.js               # English insights dictionary
      locales/hi.js               # Hindi insights dictionary
      locales/mr.js               # Marathi insights dictionary
    App.jsx                       # Route registration & screening exception
```

---

## 3. Data Sources

Phase 13 consumes **strictly real data** from previous phases without fabricating history or synthesizing static mocks:

1. **`reading_sessions` (Phase 4 & 5):**
   - Reading accuracy (`comprehensionAccuracy`, `accuracyScore`, `accuracy_score`).
   - Reading speed (`wordsPerMinute`, `speed_wpm`, `wpm`).
   - Words attempted and session duration.
   - Session completion timestamps (`createdAt`, `completedAt`).
2. **`speech_reading_analyses` (Phase 5):**
   - Oral reading word accuracy and phoneme pronunciation signals.
3. **`learning_states` & `learner_profiles` (Phase 2 & 3):**
   - Current learning level (1–5) and level designation (`Foundation`, `Developing`, `Expanding`, `Bridging`, `Fluent`).
   - Adaptive challenge tier (1–5).
   - Domain competency scores and identified tricky words.
4. **`activity_attempts` & `user_gamification` (Phase 3 & 9):**
   - Active practice streak, badges unlocked, and daily learning activity completions.
5. **`classrooms` & `parent_learner_links` (Phases 7 & 11):**
   - Classroom rosters and verified parent-child relationship records for strict tenant isolation.

---

## 4. Reporting Periods

Three standardized time windows are supported:
- **`7d` (Last 7 Days):** Focuses on weekly practice cadence and immediate feedback.
- **`30d` (Last 30 Days — Default):** Standard monthly evaluation window for steady skill progression.
- **`90d` (Last 90 Days):** Longitudinal term-wide trajectory.

All period bounds are computed in UTC:
$$\text{period\_start} = \text{now} - \text{period\_days}$$
Prior comparison period bounds are calculated identically:
$$\text{prior\_start} = \text{period\_start} - \text{period\_days}$$

---

## 5. Trend Calculation & Classification Rules

### Trend Classification
Trends are classified into one of four explainable, non-clinical categories:
- **`improving`:** Metric increased by $\ge 3\%$ (or $\ge 2$ WPM) compared to the prior period.
- **`stable`:** Metric changed by less than $3\%$ (or $< 2$ WPM) compared to the prior period.
- **`needs_attention`:** Metric decreased by $\ge 3\%$ (or $\ge 2$ WPM) compared to the prior period.
- **`insufficient_data`:** Fewer than 2 sessions recorded across the comparison windows.

### Intra-Window Fallback for New Learners
If a learner has 0 sessions in the prior window but $\ge 2$ sessions in the current period, DyslexAid compares the earlier half of the current period to the latter half, enabling new learners to see early progress without waiting 30+ days.

### Educational Language Guarantee
No diagnostic, clinical, or medical terminology is permitted.
- **Prohibited:** "Dyslexic deficit", "Statistical regression coefficient", "Cure rate", "Clinical abnormality".
- **Enforced:** "Reading accuracy is improving", "Practice consistency has been steady", "Continue practicing tricky words", "More practice is needed to identify a trend".

---

## 6. Data Sufficiency Rules

To prevent misleading or fabricated conclusions, three explicit data sufficiency states are enforced:

1. **`no_data` (0 sessions in period):**
   - Banner: *"No learning activity recorded yet."*
   - Encouragement: *"Complete a story or reading activity in the Reading Coach to begin building your progress history and insights!"*
   - Call to Action: Direct link to Reading Coach (`/student/reading-coach`).

2. **`insufficient_data` (1 session in period):**
   - Banner: *"Building your practice history."*
   - Encouragement: *"Great start on your reading journey! Complete a few more sessions to reveal clear progress trends."*
   - Calculated trends: Explicitly marked as `insufficient_data` with educational guidance.

3. **`sufficient_data` ($\ge 2$ sessions):**
   - Renders directional indicators, deltas, and multi-point SVG progress curves.

---

## 7. API Specifications

### 7.1 Student Endpoint
- **URL:** `GET /api/v2/learning-insights/student?period=30d`
- **Auth:** Bearer JWT token (`role: student`). Learner ID is extracted strictly from authentication credentials (preventing IDOR).
- **Response:** `StudentInsightsResponse` containing `summary`, `trends`, `timeline`, and `reportingPeriod`.

### 7.2 Teacher Endpoints
- **URL:** `GET /api/v2/learning-insights/teacher/overview?period=30d`
  - **Auth:** Bearer JWT token (`role: teacher`).
  - **Function:** Returns classroom aggregated KPIs, student distribution, and learner cards in a single query pass (zero N+1 queries).
- **URL:** `GET /api/v2/learning-insights/teacher/{learner_id}?period=30d`
  - **Auth:** Bearer JWT token (`role: teacher`).
  - **Guard:** Validates that `learner_id` belongs to one of the teacher's enrolled classrooms (`403 Forbidden` if unassigned).

### 7.3 Parent Endpoint
- **URL:** `GET /api/v2/learning-insights/parent/{learner_id}?period=30d`
  - **Auth:** Bearer JWT token (`role: parent`).
  - **Guard:** Enforces active, approved `parent_learner_links` record (`403 Forbidden` if unauthorized or revoked).
  - **Response:** `ParentInsightsResponse` with parent-friendly metrics and at-home encouragement suggestions.

---

## 8. Privacy & Data Boundaries

- **Raw Speech Audio:** Strictly zero raw audio stored or returned. Speech analysis only processes Web Speech API transcripts on the client and persists derived educational accuracy scores.
- **AI Tutor Transcripts:** AI Tutor multi-turn conversational transcripts are strictly shielded from public progress endpoints.
- **Teacher-Private Notes:** Private educator notes and IEP flags remain strictly isolated within Teacher Analytics and are never exposed to parent or student endpoints.
- **Tenant Isolation:** Enforced on every database query using authenticated user identifiers and relational joins.

---

## 9. Multilingual Support (Phase 10 Integration)

All Phase 13 frontend interfaces are fully localized across all 3 supported languages:
- **English (`en`)**
- **Hindi (`hi`)**
- **Marathi (`mr`)**

Translated elements include page headers, period selector labels, trend cards (Improving, Steady, Needs Practice, Building Habit), empty states, charts, table columns, and educational disclaimers.

---

## 10. Accessibility Integration (Phase 12 Integration)

- **Pure SVG Charting:** Zero canvas or external charting library dependencies. Fully responsive SVG `viewBox` prevents horizontal scrolling.
- **Screen Reader Accessible:** Includes hidden HTML table summaries for assistive technology (WCAG 2.1 AA).
- **Multi-Cue Indicators:** Trend directions are communicated via text, symbols (`↑`, `→`, `⚠️`, `ℹ️`), and color simultaneously (never color alone).
- **Typography & Theme Elasticity:** Responds dynamically to CSS custom variables `--font-family`, `--font-size`, `--line-spacing`, `--letter-spacing`, high contrast mode, and reduced motion preferences.

---

## 11. Feature Flag

Controlled via centralized environment setting in `backend/core/config.py`:
```python
V2_LEARNING_INSIGHTS: bool = True
```
When set to `False`, all `/api/v2/learning-insights` endpoints return HTTP `503 Service Unavailable` with message `"Learning insights feature is currently disabled."`.

---

## 12. Verification & Test Suite

### Backend Test Coverage
Implemented in `backend/test_phase13_learning_insights.py`:
- 22 deterministic unit and endpoint integration tests:
  1. Default 30-day reporting period calculation.
  2. 7-day reporting period calculation.
  3. 90-day reporting period calculation.
  4. Reading accuracy trend identification (improving).
  5. Reading speed trend identification (WPM increase).
  6. Speech analysis trend integration.
  7. Practice frequency and active days calculation.
  8. Current adaptive level and tier resolution.
  9. Real metric-derived strengths identification.
  10. Focus area and difficult words identification.
  11. Insufficient data handling (1 data point).
  12. Zero activity handling (empty state).
  13. Student endpoint authentication.
  14. Student tenancy enforcement (no IDOR).
  15. Teacher classroom authorization guard.
  16. Parent relationship verification guard.
  17. Unauthorized student access rejection.
  18. Tutor transcript privacy shielding.
  19. Raw audio privacy shielding.
  20. Feature flag 503 behavior when disabled.
  21. Invalid reporting period fallback (`30d`).
  22. Teacher classroom overview cohort aggregation.

**Test Results:** All **22/22** Phase 13 tests passed. All **291/291** total backend tests passed (0 failures, 0 regressions).

### Frontend Verification
- **Build:** `npm run build` completed cleanly in 5.04s.
- **Lint:** `npm run lint` completed with 0 errors and 0 warnings.
