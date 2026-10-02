# DyslexAid V2 — Phase 9: Gamification & Engagement Architecture & Documentation

## 1. Overview & Pedagogical Philosophy

DyslexAid V2 Phase 9 introduces an encouraging, effort-based, dyslexia-friendly gamification experience designed to celebrate meaningful practice effort, consistency, and reading milestones without triggering anxiety, sensory overload, or unhealthy peer comparison.

### Core Educational Principles:
1. **Effort & Consistency Over Competition**:
   - Points and badges reward practice participation, time invested, and reading consistency.
   - **No Public Leaderboards or Rankings**: Learners are never compared against peers or ranked publicly.
   - **No Performance Shaming**: Missing practice days never triggers alarms, penalties, or guilt-inducing loss warnings.
2. **Server-Determined Integrity**:
   - Points and achievements are strictly determined, validated, and awarded by the backend server.
   - Clients cannot supply arbitrary point totals or force badge unlocks.
   - Screening outcomes, clinical severity, and diagnostic labels **never** generate points or badges.
3. **Strict Idempotency**:
   - Every reward corresponds to a unique `sourceEventId` (e.g., `attemptId` or `sessionId`).
   - Duplicate API calls, browser refreshes, or network retries never award points or badges twice.
4. **Accessible, Reduced-Motion Design**:
   - Calming pastel aesthetics, high contrast, readable OpenDyslexic / Lexend typography.
   - Audio autoplay is strictly prohibited; sound is never required to understand an achievement.
   - Respects `prefers-reduced-motion` to ensure safe, comfortable experiences for all neurodivergent learners.

---

## 2. Points & Reward System

### Eligible Learning Events
Points are awarded exclusively upon verified, persisted completion of learning events:

| Event Type | Qualifying Condition | Base Points | Bonus Points | Max Event Points |
| :--- | :--- | :--- | :--- | :--- |
| **Adaptive Learning Activity** (`activity_attempt`) | Successfully completed an adaptive skill challenge | 10 pts | +5 bonus (score $\ge 80\%$) | 15 pts |
| **Reading Coach Session** (`reading_session`) | Completed full reading passage and questions | 10 pts | +5 bonus (comprehension $\ge 80\%$), +5 bonus (100% words read) | 20 pts |
| **Speech Reading Practice** (`speech_analysis`) | Verified speech fluency practice completed | 10 pts | +5 bonus (accuracy $\ge 85\%$) | 15 pts |
| **Practice Milestones** | Reaching cumulative activity milestones (e.g. 10th activity) | — | 15–20 bonus pts (via badge unlocks) | 20 pts |

### Non-Qualifying Events (No Points Awarded):
- Opening or refreshing a page.
- Merely chatting with the Personal AI Tutor without completing an actual practice task.
- Taking or reviewing dyslexia screening assessments.
- Teacher intervention creation or review.
- Incomplete, aborted, or skipped reading sessions.

---

## 3. Achievement & Badge Catalogue

The Phase 9 catalogue includes 11 carefully calibrated educational badges:

| Badge ID | Title | Icon | Category | Threshold / Rule | Repeatable | Description |
| :--- | :--- | :---: | :--- | :--- | :---: | :--- |
| `first_steps` | **First Steps** | 🌱 | milestone | 1 completed learning activity | No | Completed your very first learning activity! |
| `reading_explorer` | **Reading Explorer** | 📖 | reading | 5 completed reading sessions | No | Read 5 full stories in Reading Coach! |
| `story_champion` | **Story Champion** | 📚 | reading | 15 completed reading sessions | No | Completed 15 reading adventures! |
| `practice_builder` | **Practice Builder** | 🛠️ | practice | 10 completed practice activities | No | Finished 10 adaptive skill exercises! |
| `practice_champion` | **Practice Champion** | ⚡ | practice | 25 completed practice activities | No | Completed 25 adaptive practice challenges! |
| `word_detective` | **Word Detective** | 🔍 | vocabulary | 20 distinct vocabulary words practiced | No | Explored and practiced 20 vocabulary words! |
| `comprehension_star` | **Comprehension Star** | 🌟 | reading | 5 sessions with comprehension $\ge 85\%$ | No | Achieved great comprehension on 5 stories! |
| `consistency_spark` | **Consistency Spark** | ✨ | streak | 3 distinct calendar days practiced | No | Practiced on 3 distinct days! Consistency builds mastery! |
| `streak_hero` | **Habit Hero** | 🚀 | streak | 7 distinct calendar days practiced | No | Dedicated learner! Practiced across 7 different days! |
| `century_club` | **Century Club** | 💯 | milestone | 100 total points earned | No | Accumulated 100 practice points! |
| `super_learner` | **Super Learner** | 👑 | milestone | 250 total points earned | No | Reached 250 learning points through dedication! |

---

## 4. Learning Streak Methodology

### Definition
A learning streak measures **distinct UTC calendar days (`YYYY-MM-DD`)** on which the learner completed at least one eligible learning event.

### Key Rules:
1. **Multiple Activities on Same Day**:
   - Completing 5 activities in one day counts as **1 streak day**, not 5.
2. **Consecutive Days**:
   - Activities completed on today and yesterday increment the active streak.
   - If the learner's last activity was today, the streak remains intact.
3. **Non-Shaming Reset**:
   - If a learner misses a day, `currentStreak` displays 0 without alarming alerts, broken streak icons, or guilt messaging.
   - Example encouraging copy: *"Ready for today's practice? Every little bit counts! Keep learning at your own pace."*
4. **Monotonic Personal Best**:
   - `longestStreak` represents the learner's historical record and **never decreases**, even if the current streak ends or older session records are archived.
5. **No Loss of Rewards**:
   - Points and earned badges are permanent achievements and are **never revoked** when a streak lapses.

---

## 5. Idempotency & Reward Ledger Integrity

To prevent duplicate points from network retries, page refreshes, or malicious replay attacks:
1. **Unique Ledger Constraint**:
   - MongoDB collection `reward_events` enforces a compound unique index on `("learnerId", "sourceEventId")`.
2. **Event Verification**:
   - Before recording an award, the backend checks if a reward event already exists for `("learnerId", "sourceEventId")`.
   - If found, it returns the cached result with `isDuplicate: true` and `pointsAwarded: 0`.
3. **Database Concurrency Protection**:
   - Handled gracefully via `pymongo.errors.DuplicateKeyError` fallback.
4. **Ledger Auditing**:
   - `totalPoints` in `gamification_summaries` reconciles directly with `sum(points)` in `reward_events`.

---

## 6. Backend Architecture & Data Models

### MongoDB Collections:
1. **`gamification_summaries`**:
   - `learnerId` (string, unique index)
   - `totalPoints` (integer, non-negative)
   - `currentStreak` (integer)
   - `longestStreak` (integer)
   - `lastActiveDate` (string `YYYY-MM-DD`, UTC)
   - `streakMessage` (encouraging message string)
   - `earnedBadges` (list of `EarnedBadge` objects)
   - `updatedAt` (epoch timestamp)
2. **`reward_events`**:
   - `eventId` (string, unique index, UUID)
   - `learnerId` (string, indexed)
   - `sourceEventId` (string, compound unique index with `learnerId`)
   - `eventType` (string: `activity_attempt`, `reading_session`, `bonus_comprehension`, etc.)
   - `points` (integer, 1–50)
   - `description` (human-readable reason)
   - `metadata` (associated scores, domains, passage titles)
   - `createdAt` (epoch timestamp, indexed for history queries)

---

## 7. REST APIs

All endpoints require JWT bearer authentication and are prefixed with `/api/v2/gamification`. Governed by feature flag `V2_GAMIFICATION` (returns 503 Service Unavailable when disabled).

### 1. `GET /api/v2/gamification/summary`
- **Role**: Student (retrieves self)
- **Response**: `GamificationSummary` (points, current/longest streak, earned badges, recent 5 reward events).

### 2. `GET /api/v2/gamification/achievements`
- **Role**: Student (retrieves self)
- **Response**: List of all 11 badges enriched with real-time `currentProgress`, `threshold`, `progressPercent`, and `unlocked` status.

### 3. `GET /api/v2/gamification/milestones`
- **Role**: Student (retrieves self)
- **Response**: Top 3 closest upcoming milestones with progress percentages.

### 4. `GET /api/v2/gamification/history`
- **Role**: Student (retrieves self)
- **Parameters**: `page` (default 1), `limit` (default 20, max 50)
- **Response**: `GamificationHistoryResponse` with paginated audit ledger of earned points.

### 5. `GET /api/v2/gamification/teacher/learner/{student_id}`
- **Role**: Teacher (classroom-authorized)
- **Response**: Limited educational view of the learner's total points, active streak, and earned badges.
- **Privacy & Security**: Enforces teacher-classroom tenant validation; strictly rejects students or cross-classroom teachers with 403 Forbidden.

### 6. `POST /api/v2/gamification/claim-event`
- **Role**: Student
- **Body**: `{"sourceEventId": "...", "eventType": "activity_attempt" | "reading_session"}`
- **Description**: Validates that the event exists in the database and belongs to the caller, then idempotently awards verified points.

---

## 8. Frontend Experience

### Student Rewards Page (`/student/rewards`)
- **Route**: Accessible via primary navigation (`/student/rewards`, 🏆 icon).
- **Header**: Warm, encouraging heading with quick actions to practice.
- **KPI Metrics**: 4 clean summary cards (Total Points, Active Streak, Badges Earned, Best Record).
- **Streak Tracker**: Encouraging banner celebrating consistency with non-shaming phrasing.
- **Milestone Tracker**: Visual progress bars showing proximity to next achievement badges.
- **Achievements Grid**: Filterable tabs (All, Unlocked, Locked) displaying `BadgeCard` components with clear icons, descriptions, and progress indicators.
- **Audit Feed**: Recent reward history ledger with timestamps and points breakdown.

### Inline Celebrations:
- **`CelebrationModal`**: Triggered upon unlocking a new badge or milestone. Non-overwhelming, calming confetti, dismissable via Escape key or backdrop click.
- **Reading Coach Banner**: Highlights points and badges earned immediately on session completion (`ReadingSessionResult.jsx`).
- **Teacher Visibility**: Teachers can inspect student practice consistency and badges via `LearnerAnalyticsModal.jsx`.

---

## 9. Accessibility & Inclusive Dyslexia Design

- **Font & Typography**: Uses high-legibility sans-serif and OpenDyslexic typography with generous line-height (`leading-relaxed`) and letter spacing.
- **Color Contrast**: All text conforms to WCAG 2.1 AA standards ($>4.5:1$ contrast against card backgrounds).
- **Non-Color Indicators**: Unlocked vs. locked statuses include explicit icon indicators (🔒 vs. 🎖️), clear textual tags ("UNLOCKED", "IN PROGRESS"), and percentage bars.
- **Keyboard Navigation**: Fully interactive via Tab, Enter, and Space with visible focus rings (`focus:ring-2 focus:ring-teal-600`).
- **Screen Reader Support**: Complete ARIA attributes (`role="dialog"`, `aria-label`, `aria-hidden` on decorative emojis).
- **Reduced Motion**: Respects `prefers-reduced-motion: reduce` by disabling dynamic CSS animations and particles.

---

## 10. Verification & Test Coverage

### Automated Test Suite:
- `backend/test_phase9_gamification.py`: 31 test cases covering:
  - Pydantic models, boundary validation, and sanitization.
  - Server-determined points calculation and bonus logic.
  - Strict idempotency and duplicate prevention.
  - Streak calculations (consecutive days, same-day multiple events, UTC midnight boundary).
  - Achievement unlocking and milestone ranking.
  - Feature flag enforcement (503 when disabled) and unauthenticated rejection (401).
  - Teacher authorization and tenant boundary isolation (403 for unauthorized teachers).
  - Integration with adaptive attempt, reading coach, and tutor isolation.
  - Ledger points audit reconciliation.
- Full Regression Test Suite: **213 passed, 0 failed** across Phases 2 through 9.
- Frontend Production Build: **0 errors, 174 modules transformed** cleanly via Vite.

---

## 11. Known Limitations & Next Steps

1. **No External Competitive Mechanics**: By design, no public leaderboards or student vs. student competitions exist to protect learners with reading difficulties from discouragement.
2. **Phase 10 Multilingual Alignment**: All badge strings and celebratory messages are currently localized in English; multilingual strings (Hindi, Marathi, Tamil, etc.) will be introduced in Phase 10.
