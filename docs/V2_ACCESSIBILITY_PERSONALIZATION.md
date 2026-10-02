# DyslexAid V2 — Phase 12: Accessibility, Personalization & Inclusive Learning Experience

## 1. Overview & Pedagogical Philosophy

DyslexAid V2 Phase 12 establishes a unified, learner-centered accessibility and personalization architecture. It empowers neurodivergent learners—particularly students with dyslexia, visual stress, ADHD, or processing challenges—to customize typography, spacing, contrast, visual focus scaffolding, and assistive audio tools across their entire learning environment.

### Core Pedagogical & Privacy Principles:

1. **Learner Agency & Comfort**:
   - Students have diverse perceptual needs. Allowing children to adjust font size, letter spacing, line height, word spacing, font family, and tint transforms reading from a frustrating task into a comfortable, self-directed activity.
2. **Descriptive Personalization, Not Clinical Diagnosis**:
   - Accessibility preferences are strictly educational comfort adjustments.
   - The platform never infers a dyslexia diagnosis, cognitive subtype, or medical profile based on preferred fonts, colors, or reading speeds.
   - A child-friendly notice reminds users that settings are for visual comfort and practice enjoyment.
3. **Seamless Integration in Real Learning Workflows**:
   - Settings are not confined to a decorative preview screen. They dynamically apply to real reading passages, the Adaptive Reading Coach, AI tutor conversation bubbles, and classroom dashboard areas.
4. **Quick-Access Ergonomics**:
   - In addition to a comprehensive settings page (`/student/accessibility`), an accessible toolbar is anchored in the top navigation bar, allowing immediate text-size stepping, ruler toggling, contrast toggling, and visual tints without interrupting the active reading task.

---

## 2. Accessibility Preference Model & Taxonomy

The preference schema is defined in `backend/models/v2_accessibility.py` and managed in `frontend/src/context/AccessibilityContext.jsx`:

| Setting | Type / Allowed Values | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `fontSize` | `'small'`, `'medium'`, `'large'`, `'xlarge'` | `'medium'` (18px) | Text scale across learning interfaces. |
| `fontFamily` | `'opendyslexic'`, `'lexend'`, `'system'`, `'comic-neue'` | `'opendyslexic'` | Dyslexia-scaffolded typography with heavy bottom weight. |
| `lineSpacing` | `'normal'`, `'relaxed'`, `'extra-relaxed'` | `'relaxed'` (1.8) | Vertical breathability between lines of text. |
| `letterSpacing` | `'normal'`, `'wide'`, `'extra-wide'` | `'wide'` (0.05em) | Reduces letter crowding and visual crowding effects. |
| `wordSpacing` | `'normal'`, `'wide'`, `'extra-wide'` | `'wide'` (0.15em) | Helps distinguish word boundaries during phonological decoding. |
| `readingWidth` | `'standard'`, `'narrow'` | `'standard'` (100% / ~65ch narrow) | Narrows line length to prevent eye tracking fatigue. |
| `visualTint` | `'none'`, `'peach'`, `'mint'`, `'sky'`, `'butter'` | `'none'` | Color overlay filter mitigating Meares-Irlen visual stress. |
| `readingRuler` | `bool` | `false` | Horizontal focus aperture window following pointer/keyboard. |
| `rulerHeight` | `'small'`, `'medium'`, `'large'` | `'medium'` (60px) | Height of reading ruler aperture. |
| `rulerColor` | `'amber'`, `'blue'`, `'mint'`, `'lavender'` | `'amber'` | Tint accent for the reading ruler focus line. |
| `highContrast` | `bool` | `false` | High-contrast palette (dark charcoal / high legibility borders). |
| `reducedMotion` | `bool` | `false` | Disables transitions, smooth scrolling, and animated effects. |
| `ttsSpeed` | `float` (0.7 to 1.3) | `1.0` | Default narration pacing for Text-to-Speech playback. |
| `highlightCurrentWord` | `bool` | `true` | Guided synchronized word highlighting during TTS playback. |

---

## 3. Backend Architecture & Persistence

### 1. Data Models (`backend/models/v2_accessibility.py`)
- `V2AccessibilityPreferences`: Complete preference entity with validation, field aliases (`validation_alias=AliasChoices(...)`), and canonical defaults.
- `AccessibilityPreferencesPatch`: Partial update model supporting granular setting adjustments.
- `AccessibilityPreferencesResponse`: Standardized V2 API response envelope with camelCase serialization.

### 2. Service Layer (`backend/services/accessibility/accessibility_service.py`)
- `get_user_accessibility_preferences(user_id)`: Fetches user-specific preferences from the `user_accessibility_preferences` MongoDB collection. If no record exists, initializes with canonical defaults and syncs with `users.settings.accessibility`.
- `update_user_accessibility_preferences(user_id, updates)`: Validates, sanitizes, and upserts user preferences. Also synchronizes relevant settings into the legacy `users` document for backward compatibility.
- `reset_user_accessibility_preferences(user_id)`: Restores canonical defaults cleanly.

### 3. API Endpoints (`backend/routers/v2_accessibility.py`)
All endpoints require JWT Bearer authentication and enforce tenant ownership (users can only inspect or modify their own preferences).

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v2/accessibility/preferences` | Retrieve authenticated user's accessibility preferences. |
| `PUT` | `/api/v2/accessibility/preferences` | Replace full preference configuration. |
| `PATCH` | `/api/v2/accessibility/preferences` | Update partial preference fields. |
| `POST` | `/api/v2/accessibility/preferences/reset` | Reset preferences to factory defaults. |

### 4. Feature Flag Protection
Controlled by `V2_ACCESSIBILITY_PREFERENCES = True` in `backend/core/config.py`. When disabled, all Phase 12 endpoints return HTTP `503 Service Unavailable` with `detail="V2 Accessibility Preferences feature is currently disabled"`.

---

## 4. Frontend Architecture & Inclusive Learning UI

### 1. Central Accessibility Context (`AccessibilityContext.jsx`)
- Mounts at the application root in `App.jsx`.
- Injects CSS custom properties dynamically on `:root` and toggles utility classes on `document.body`:
  - `--reading-font-family`: `'OpenDyslexic', 'Lexend', 'Comic Neue', sans-serif`
  - `--reading-font-size`: `16px`, `18px`, `22px`, `26px`
  - `--reading-line-height`: `1.5`, `1.8`, `2.2`
  - `--reading-letter-spacing`: `0em`, `0.05em`, `0.1em`
  - `--reading-word-spacing`: `0em`, `0.15em`, `0.25em`
  - `--reading-max-width`: `100%` vs `65ch`
  - `body.high-contrast`: High-contrast dark styling and visible focus rings.
  - `body.reduced-motion`: Disables all CSS keyframes and animations (`animation: none !important; transition: none !important`).
- Multi-layer persistence: Authenticated backend sync (`accessibilityV2API`) with instant `localStorage` caching (`dyslexaid_accessibility_preferences_v2`) for instantaneous loading without layout shifts.

### 2. Reading Focus Tools

#### A. Reading Ruler (`ReadingRuler.jsx`)
- Screen aperture guide with a semi-opaque backdrop and an illuminated reading slot.
- Follows the user's cursor or touch position smoothly.
- **Keyboard accessible**: Can be adjusted using <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>&uarr;</kbd> / <kbd>&darr;</kbd> (or <kbd>&uarr;</kbd>/<kbd>&darr;</kbd> when focused) and dismissed via <kbd>Esc</kbd>.
- Completely non-blocking: Pointer events pass through the aperture (`pointer-events: none`) so links, words, and controls remain clickable.

#### B. Visual Tint Overlay (`VisualTintOverlay.jsx`)
- Fullscreen color filter for learners experiencing visual stress (Meares-Irlen syndrome).
- Supported tints: Soft Peach (`#ffeedd`), Pale Mint (`#e3f9ed`), Sky Blue (`#e1f2fc`), Warm Butter (`#fff9db`).
- Uses `mix-blend-mode: multiply` with `pointer-events: none` to preserve interactive usability.

#### C. Quick-Access Toolbar (`AccessibilityToolbar.jsx`)
- Positioned in the global navigation bar (`Layout.jsx`).
- Features immediate text size adjustment (`A-` / `A+`), reading ruler toggle, high contrast toggle, and tint palette switcher.
- Allows students to adjust reading comfort mid-passage without navigating away.

#### D. Full Settings Panel (`AccessibilitySettingsCard.jsx` & `/student/accessibility`)
- Preset buttons: "Comfortable (Default)", "High Spacing", "Focus Mode".
- Fine-grained controls for font family, text scale, line spacing, letter spacing, word spacing, and reading column width.
- **Live Bilingual Preview**: Displays both English and Devanagari (Marathi/Hindi) sample passages side-by-side that update in real time as sliders and toggles change.
- Non-clinical pedagogical banner reassuring the student.

---

## 5. Learning Screens Integration

The accessibility engine propagates directly to core learning activities:

1. **Reading Passage & Coach (`ReadingPassage.jsx`, `ReadingCoach.jsx`, `useReadingCoach.js`)**:
   - Inherits `--reading-font-family`, `--reading-font-size`, `--reading-line-height`, `--reading-letter-spacing`, and `--reading-word-spacing`.
   - Constrains passage width when `narrow` mode is active to prevent eye drift.
   - Synchronizes TTS playback rate and guided word highlighting with user preferences.
2. **Personal AI Tutor (`TutorMessageBubble.jsx`)**:
   - Tutor explanation bubbles inherit `dyslexia-text` styles, applying dyslexia-scaffolded typography and comfortable letter/word spacing.
3. **Student Navigation & Layout (`Layout.jsx`)**:
   - Global reading ruler and visual tint overlays are rendered at the root layout.
   - Added direct "Reading & Accessibility" link in student sidebar/bottom navigation.
4. **Student Settings (`SettingsPage.jsx`)**:
   - Modern tabbed interface switching smoothly between "Reading & Accessibility" and "Classroom Settings".

---

## 6. Multilingual Localization

Full authentic translations across English (`en.js`), Marathi (`mr.js`), and Hindi (`hi.js`):
- All setting titles, descriptions, preset names, and button labels.
- Live preview passages in Devanagari script:
  - Marathi: *"वाचणे हा एक सुंदर प्रवास आहे. प्रत्येक शब्द आपल्याला नवीन गोष्ट शिकवतो."*
  - Hindi: *"पढ़ना एक सुंदर यात्रा है। हर शब्द हमें कुछ नया सिखाता है।"*
- Screen reader ARIA labels and status messages.

---

## 7. Automated Testing & Verification

### 1. Test Suite (`backend/test_phase12_accessibility.py`)
9 focused unit and integration tests verifying:
- Unauthenticated requests rejected with 401.
- Initial preference retrieval yields canonical defaults.
- Full preference replacement (`PUT`) with validation.
- Partial updates (`PATCH`) with state persistence.
- Safe reset to factory defaults (`POST /preferences/reset`).
- Rejection of invalid enum values (`lineSpacing: "super_giant"` $\to$ 422).
- Zero cross-user data leakage (tenant boundary enforcement).
- Feature flag disabled behavior (503 Service Unavailable).
- Pydantic model serialization and alias compatibility.

### 2. Full Regression Test Suite
- **Result:** `pytest backend/ -v` passed **264 / 264 tests** in 4.13s.
- Zero regressions across Phases 1–11.

### 3. Frontend Production Build
- **Command:** `cd frontend && npm run build`
- **Result:** Vite 5.4.21 bundle built cleanly with 0 errors in 3.04s.

---

## 8. Non-Clinical Educational Safeguard

> **Accessibility Notice:**  
> The accessibility preferences and visual comfort tools in DyslexAid are educational accommodations designed to support comfortable reading, reduce visual fatigue, and encourage practice. They do not constitute a medical, neurological, or clinical diagnosis of dyslexia or visual processing disorders.
