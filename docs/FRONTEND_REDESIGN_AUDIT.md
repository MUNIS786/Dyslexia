# DyslexAid V2 — Frontend Redesign Architecture Audit & Plan

**Phase 0 Deliverable:** Comprehensive Repository Audit, Route Inventory, Baseline Test Metrics & Design System Strategy  
**Document Date:** 2026-10-19  
**Git Branch:** `main`  
**Current Baseline Commit:** `203f6be`  
**Target Visual Theme:** Balanced Design System (Light Theme Foundation, High-Contrast & Dyslexia-Ergonomic Adaptations)

---

## 1. Executive Summary & Audit Objectives

DyslexAid V2 is an intelligent assistive educational reading platform engineered to support neurodivergent learners, educators, and parents. The application consists of a Python/FastAPI backend, MongoDB database, and a React + Vite frontend.

This audit establishes the baseline architectural inventory, verifies all existing routes and dependencies, records initial lint and build health, identifies UI/UX friction points, and formulates a phased redesign roadmap from **Phase 1 (Global Design System & App Shell)** through **Phase 7 (Final QA & Delivery)** without breaking a single backend API contract, security boundary, or existing accessibility feature.

---

## 2. Existing Frontend Architecture

### 2.1 Technology Stack & Tooling

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Framework** | React | `18.2.0` | Declarative UI rendering |
| **DOM Renderer** | React DOM | `18.2.0` | Web DOM integration |
| **Build Tool & Dev Server** | Vite | `5.4.21` | Fast HMR, Rollup production bundling |
| **Routing** | React Router DOM | `6.20.0` | Client-side routing, protected routes, code splitting |
| **Styling** | Tailwind CSS + Vanilla CSS | `3.3.5` | Utility classes, CSS custom properties in `index.css` |
| **HTTP Client** | Axios | `1.6.0` | Centralized REST client with JWT authorization interceptors |
| **Toasts & Feedback** | `react-hot-toast` | `2.4.1` | Accessible non-blocking notifications |
| **Linter** | ESLint | `8.53.0` | Static code analysis with zero-warning enforcement |

### 2.2 Global State & Context Providers Hierarchy

The application root (`frontend/src/App.jsx`) mounts providers in a strict, predictable hierarchy:

```
BrowserRouter
└── AuthProvider (AuthContext: user profile, JWT token, role, login/logout/register)
    └── I18nProvider (I18nContext: en, hi, mr translation dictionaries, language switching)
        └── AccessibilityProvider (AccessibilityContext: dyslexia font, font size, ruler, color tints, high contrast, reduced motion)
            └── NotifProvider (NotifContext: in-app notifications, unread count)
                └── Toaster (react-hot-toast: styled with dyslexia font variables)
                    └── AppRoutes (Suspense fallback with LoadingScreen)
```

### 2.3 API Service Architecture

- **`frontend/src/api/client.js`:** Core API client handling V1 services:
  - `authAPI`: signin, signup, getMe, updateProfile
  - `screeningAPI`: getQuestions, submitTest, getHistory
  - `tasksAPI`: getTasks, completeTask
  - `progressAPI`: getProgress, getSummary
  - `libraryAPI`: getDocs, getDoc, saveDoc, deleteDoc
  - `scanAPI`: ocrImage, simplifyText, askQuestion
  - `planAPI`: getPlan, generatePlan
  - `classroomAPI`: getStudents, getAssignments, joinClassroom
- **`frontend/src/api/v2/client.js`:** Centralized V2 API services:
  - `learnerProfileV2API`: getProfile, getState, updatePreferences
  - `adaptiveLearningV2API`: getTierInfo, getActivities, submitAttempt
  - `readingCoachV2API`: getRecommendation, getPassages, startSession, completeSession, speech telemetry
  - `tutorV2API`: getContext, sendChatMessage, getHistory, clearHistory
  - `teacherAnalyticsV2API`: getOverview, getLearners, getLearnerDetail, getLearnerTrend
  - `interventionV2API`: createIntervention, updateIntervention, start, review, complete, addMeasurement
  - `gamificationV2API`: getSummary, getAchievements, getMilestones, claimEvent
  - `multilingualV2API`: getLanguages, getPreference, updatePreference
  - `accessibilityV2API`: getPreferences, updatePreferences
  - `learningInsightsV2API`: getStudentInsights, getTeacherOverview, getParentInsights
  - `learningRecommendationsV2API`: getStudentRecommendations, refreshRecommendations
  - `personalizedContentV2API`: getNextContent, getActivities, launchActivity
  - `contentAuthoringV2API`: createDraft, updateDraft, validate, submit, review, publish

---

## 3. Comprehensive Route & Page Inventory

The frontend exposes **30 total routes** divided across three distinct user roles (Student, Teacher, Parent) plus public authentication.

| Route Path | Page Component | Role / Protection | Navigation Item & Purpose |
|---|---|---|---|
| `/login` | `LoginPage` | Public | Authentication entrypoint |
| `/register` | `RegisterPage` | Public | Multi-role registration (Student, Teacher, Parent) |
| `/student` | `StudentHome` | Student | Primary student dashboard, cognitive radar chart, streak, quick links |
| `/student/profile` | `StudentProfilePage` | Student | Detailed learner intelligence profile and domain mastery breakdown |
| `/student/adaptive-learning` | `AdaptiveLearningPage` | Student | Adaptive exercises tailored to student's current tier |
| `/student/reading-coach` | `ReadingCoachPage` | Student | Interactive passage reading, audio listening, word highlighting |
| `/student/insights` | `LearningInsightsPage` | Student | Visual progress metrics, strengths, and growth indicators |
| `/student/recommendations` | `LearningRecommendationsPage` | Student | Next learning steps, suggested goals, and focus areas |
| `/student/activity` | `PersonalizedActivityPage` | Student | Dynamic activity launcher (comprehension, phonics drills) |
| `/student/personalized-content`| `PersonalizedActivityPage` | Student | Alias route for published personalized content |
| `/student/tutor` | `TutorPage` | Student | Personal AI Tutor conversational chat interface |
| `/student/screening` | `ScreeningTest` | Student (Unwrapped) | Clinical Dyslexia Screening Test (DST) 20-question evaluation |
| `/student/tasks` | `DailyTasks` | Student | Daily structured tasks and progress tracking |
| `/student/rewards` | `RewardsPage` | Student | Gamification badges, milestones, XP ledger, and achievements |
| `/student/scan` | `ScanPage` | Student | Camera/upload OCR document scanner and text simplifier |
| `/student/library` | `LibraryPage` | Student | Personal saved document and simplified text library |
| `/student/library/:id` | `LibraryDocPage` | Student | Document reader with text-to-speech and vocabulary tools |
| `/student/progress` | `ProgressPage` | Student | Historical session logs, WPM trends, and accuracy charts |
| `/student/plan` | `PlanPage` | Student | 4-week structured AI learning plan |
| `/student/chat` | `ChatPage` | Student | Legacy AI chat companion |
| `/student/accessibility` | `AccessibilitySettingsPage` | Student | Dedicated typography, ruler, and visual overlay settings |
| `/student/settings` | `SettingsPage` | Student | Account settings, password change, classroom linking |
| `/student/classroom` | `JoinClassroom` | Student | Classroom code entry dialog to link with a teacher |
| `/teacher` | `TeacherHome` | Teacher | Teacher command center, classroom code, summary cards |
| `/teacher/analytics` | `TeacherAnalyticsPage` | Teacher | Class-wide analytics, domain distributions, learner progress |
| `/teacher/interventions` | `InterventionsPage` | Teacher | Tier 1-3 support plans, baseline tracking, follow-ups |
| `/teacher/content` | `ContentAuthoringPage` | Teacher | Curriculum authoring workbench, quality validator, review queue |
| `/teacher/students` | `StudentsPage` | Teacher | Enrolled classroom roster and learner search |
| `/teacher/students/:id` | `StudentDetailPage` | Teacher | Deep-dive individual student diagnostic dossier |
| `/teacher/assignments` | `AssignmentsPage` | Teacher | Reading assignment distributor and submission tracker |
| `/teacher/scan` | `TeacherScanPage` | Teacher | Batch OCR document scanning for classroom handouts |
| `/teacher/chat` | `ChatPage` | Teacher | Teacher pedagogical AI assistant |
| `/parent` | Redirect -> `/parent/dashboard` | Parent | Auto-redirect |
| `/parent/dashboard` | `ParentDashboardPage` | Parent | Reassuring progress summary, home tips, student linking |
| `*` | Redirect -> `/login` | Any | Fallback routing |

---

## 4. Existing Design System & Styling Analysis

### 4.1 Current Styling Primitives

- **Current Colors:**
  - Background: `--bg-color: #FFF8F0` (warm peach/cream)
  - Primary: `--primary: #1A6B6B` (deep dark teal)
  - Accent: `--accent: #E8A020` (amber/orange)
  - Card Surfaces: `--card-bg: #FFFFFF` (white cards)
  - Sidebar: `#1A6B6B` (monolithic dark teal block)
  - Borders: `--border: #E5E0D8` (warm beige)
- **Current Typography:**
  - Base Font: `'Lexend', 'OpenDyslexic', sans-serif`
  - Body Size: `--font-size: 18px`
  - Line Height: `--line-spacing: 2.0`
  - Letter Spacing: `--letter-spacing: 0.05em`
  - Word Spacing: `--word-spacing: 0.05em`
- **Current Component Library (`frontend/src/components/ui/index.jsx`):**
  - `Button`: Primary, secondary, danger, ghost, accent with loading spinner.
  - `Card`: White card with rounded-2xl, border-[#E5E0D8].
  - `Input` / `Select` / `Textarea`: Standard styled inputs with 44px min-height touch targets.
  - `Badge`: Teal, amber, green, red, gray, blue pill badges.
  - `ProgressBar`: Animated percentage bar.
  - `StatCard`: Large icon tile + value display.
  - `EmptyState`: Centered icon + headline + action button.
  - `Modal`: Fixed overlay with backdrop and escape dismiss.
  - `Alert`: Info, success, warning, error banner.
  - `ReadingText` / `TTSButton`: Word-level karaoke highlighting and speech synthesizer.

### 4.2 Identified UI/UX Friction Points & Visual Inconsistencies

1. **Heavy Dark Sidebar in Application Shell:**
   - The desktop navigation sidebar is a solid, heavy dark teal (`#1A6B6B`), which creates a harsh contrast against the soft main content area. A modern, light-themed educational SaaS application should feature a clean, crisp, neutral sidebar (`#FFFFFF` with subtle slate borders) with vibrant active-item indicators.
2. **Color Palette Cohesion:**
   - The current mix of `#1A6B6B` (dark teal), `#E8A020` (amber), and `#FFF8F0` (cream) feels dated. Upgrading to an **accessible modern indigo/slate palette** (`#4F46E5` primary, `#0D9488` secondary teal accent, `#F8FAFC` clean off-white background) gives a polished, premium aesthetic while maintaining high contrast.
3. **Role-Differentiated Polish:**
   - Currently, Student, Teacher, and Parent interfaces use the exact same layout shell without visual personality.
   - *Student:* Needs reassuring, friendly progress cards, clear icon badges, and encouraging milestone celebrations.
   - *Teacher:* Needs compact data tables, clean metric badges, and clear separation-of-duties review cues.
   - *Parent:* Needs calm, simplified cards without dense educational jargon.
4. **Mobile Responsiveness & Table Overflow:**
   - Wide tables in `StudentsPage`, `TeacherAnalyticsPage`, and `ContentAuthoringPage` need responsive container wrappers (`overflow-x-auto`) and mobile card fallback views to prevent layout clipping on small screens.
5. **Loading States:**
   - Full-page blocking spinner (`LoadingScreen`) is used everywhere. Introducing localized skeleton placeholders (`CardSkeleton`, `TextSkeleton`) will make page transitions feel instantaneous and smooth.

---

## 5. Accessibility Inventory & Preservation Requirements

Accessibility is a non-negotiable core value of DyslexAid. All existing accessibility capabilities must be preserved and enhanced.

### 5.1 Persisted Accessibility Settings (`AccessibilityContext.jsx`)

1. **Dyslexia Font Support:**
   - Native support for `'OpenDyslexic'`, `'Lexend'`, and system sans-serif.
   - Preserves user toggle and letter-weight calibration.
2. **Ergonomic Typography Controls:**
   - Dynamic font resizing (14px to 26px).
   - Line spacing adjustment (1.4 to 2.4).
   - Letter spacing adjustment (0.02em to 0.15em).
   - Word spacing adjustment (0.02em to 0.15em).
3. **Visual Stress Color Tints:**
   - Real-time page color tint overlay: `peach`, `mint`, `sky`, `butter`, or `none`.
4. **Reading Focus Tools:**
   - `ReadingRuler`: Horizontal visual guide tracking mouse/finger position with adjustable height (40px–100px) and tint colors (amber, cyan, yellow, gray).
5. **Display Modes:**
   - `highContrast`: Pure black on white (`#000000` text on `#FFFFFF` background) with 4px distinct focus rings.
   - `reducedMotion`: Disables transitions and animations for vestibular accessibility.
6. **Assistive Text-to-Speech:**
   - Web Speech API integration with adjustable speech rate (0.6x to 1.4x) and accent support (`en-IN`, `en-US`, `en-GB`, `hi-IN`).

---

## 6. Baseline Quality & Test Verification

All baseline checks executed cleanly prior to initiating frontend design modifications:

| Check | Tool / Command | Baseline Output | Status |
|---|---|---|---|
| **Frontend Linting** | `npm run lint` (`eslint . --max-warnings 0`) | Exited `0`: 0 errors, 0 warnings | **PASS** |
| **Frontend Production Build** | `npm run build` (`vite build`) | Exited `0`: 221 modules compiled in 11.65s (332 kB main bundle) | **PASS** |
| **Backend Release Validation** | `pytest backend/test_phase19_release_validation.py -q` | Exited `0`: 19 passed in 5.04s | **PASS** |
| **Full Backend Regression** | `pytest backend/ -q` | Exited `0`: 416 passed in 11.62s | **PASS** |
| **Live End-to-End QA Harness** | `python scripts/qa_exhaustive_tester.py` | Exited `0`: 91/91 scenarios passed across 15 journeys | **PASS** |

---

## 7. Proposed Light Theme Design System Tokens

### 7.1 Color Tokens

```css
:root {
  /* Surface Foundations */
  --color-bg-app: #F8FAFC;            /* Clean, modern slate off-white */
  --color-surface-card: #FFFFFF;      /* Crisp pure white for cards and modals */
  --color-surface-sidebar: #FFFFFF;   /* Light, airy sidebar surface */
  --color-surface-header: #FFFFFFE6;  /* Glass-like translucent header */

  /* Brand Palette (WCAG AA/AAA Compliant) */
  --color-brand-primary: #4F46E5;     /* Accessible Indigo */
  --color-brand-primary-hover: #4338CA;
  --color-brand-primary-light: #EEF2FF;/* Tint for active nav and subtle highlights */
  --color-brand-secondary: #0D9488;   /* Soft supportive teal */
  --color-brand-secondary-light: #F0FDFA;
  --color-brand-accent: #F59E0B;      /* Warm golden amber for student celebration */
  --color-brand-accent-light: #FEF3C7;

  /* Typography Colors */
  --color-text-primary: #1E293B;      /* Deep slate-900 (12.8:1 contrast on white) */
  --color-text-secondary: #475569;    /* Muted slate-600 (5.8:1 contrast on white) */
  --color-text-muted: #64748B;        /* Neutral slate-500 */
  --color-text-inverse: #FFFFFF;

  /* Borders & Dividers */
  --color-border-subtle: #E2E8F0;     /* Crisp slate-200 */
  --color-border-medium: #CBD5E1;     /* Slate-300 */
  --color-border-focused: #4F46E5;    /* 3px focus ring */

  /* Status Colors */
  --color-status-success: #10B981;    /* Emerald */
  --color-status-success-light: #ECFDF5;
  --color-status-warning: #F59E0B;    /* Amber */
  --color-status-warning-light: #FFFBEB;
  --color-status-danger: #EF4444;     /* Rose Red */
  --color-status-danger-light: #FEF2F2;
  --color-status-info: #3B82F6;       /* Blue */
  --color-status-info-light: #EFF6FF;

  /* Elevation & Shadows */
  --shadow-card: 0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04);
  --shadow-card-hover: 0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.04);
  --shadow-modal: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);

  /* Radius Scale */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;
}
```

### 7.2 Typography Scale

```css
/* Standard Body & Headings with Lexend/OpenDyslexic fallback */
--font-display: 2.25rem;   /* 36px / line-height 1.25 — Main banner / Hero */
--font-h1: 1.75rem;        /* 28px / line-height 1.3  — Page Titles */
--font-h2: 1.375rem;       /* 22px / line-height 1.35 — Section Titles */
--font-h3: 1.125rem;       /* 18px / line-height 1.4  — Card Headers */
--font-body: 1rem;         /* 16px (scalable to 24px) — Body Text */
--font-small: 0.875rem;    /* 14px — Metadata, Helper text */
--font-micro: 0.75rem;     /* 12px — Badges, Timestamps */
```

---

## 8. Phased Implementation Roadmap

To ensure zero downtime, backward compatibility, and rigorous test gating, the redesign will execute across 7 sequential phases:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 0: Repository Audit & Design System Plan (THIS PHASE - COMPLETE)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Global Design Tokens & Application Shell (Nav, Layout, UI Kit) │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Landing Page, Authentication & Role Entry (Login, Register)    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Student Experience (Dashboard, Reading Coach, AI Tutor, Gamif) │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Teacher Experience (COMPLETE - docs/PHASE_4_TEACHER_EXPERIENCE)│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 5: Parent Portal (COMPLETE - docs/PHASE_5_PARENT_EXPERIENCE.md)   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 6: Cross-App Polish, Responsive Mobile & Accessibility Audits     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 7: Final End-to-End QA, Production Build Verification & Delivery  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Checkpoints and Gating Protocol:
- After each phase, a formal checkpoint report is produced.
- Automated lint (`npm run lint`), build (`npm run build`), and regression suites (`pytest`) are executed.
- Changes are committed and pushed safely.
- Work stops at the checkpoint until explicit user approval is granted before initiating the next phase.

---

## 9. Risk Management & Preservation Strategy

| Potential Risk | Root Concern | Mitigation & Engineering Strategy |
|---|---|---|
| **Breaking Accessibility DOM Sync** | Custom CSS variables in `index.css` could be overridden by static Tailwind styles. | Preserve `applyAccessibilityDOM()` in `AccessibilityContext.jsx` and use CSS variable references (`var(--bg-color)`, `var(--text-color)`) so user preferences take precedence. |
| **Separation of Duties Bypass** | Redesigning Content Authoring might accidentally expose self-approval buttons. | Keep UI review actions tied to `user.id !== content.authorId` and enforce backend `HTTP 403` validation rules. |
| **Parent Link Revocation Leaks** | Parent dashboard might render stale cached data after relationship revocation. | Preserve active authorization checks on every learner data query; display clean `HTTP 403` access-denied state. |
| **Vite Bundle Size Inflation** | Adding heavy UI libraries could bloat the bundle beyond 500 kB. | Zero new runtime dependencies; utilize native Tailwind utility classes, CSS custom properties, and existing SVG rendering. |
| **Mobile Drawer Traversal** | Sidebar navigation might trap keyboard focus or clip on narrow screens. | Enforce accessible modal overlay patterns with `Escape` key listeners, touch overlays, and visible focus rings. |

---

## 10. Phase 0 Verdict & Readiness Status

- **Repository Audit:** Completed & verified.
- **Route & Component Inventory:** 30 routes, 4 contexts, 29 pages fully mapped.
- **Baseline Lint & Build:** Clean (0 warnings, 0 errors, 332 kB main bundle).
- **Backend Regressions:** 416/416 passing.
- **Phase 0 Status:** **COMPLETE & READY FOR REVIEW.**
