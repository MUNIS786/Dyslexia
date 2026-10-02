# DyslexAid V2 — Phase 10: Multilingual Support Architecture & Documentation

## 1. Overview & Pedagogical Philosophy

DyslexAid V2 Phase 10 introduces a comprehensive, accessible, and resilient internationalization (i18n) and multilingual learning framework for English (`en`), Marathi (`mr`), and Hindi (`hi`).

### Core Pedagogical Principles:
1. **Linguistic Equity for Diverse Learners**:
   - Children with reading difficulties often face compounded cognitive load when navigating learning platforms in a non-native interface.
   - Supporting English, Marathi (`मराठी`), and Hindi (`हिन्दी`) enables children to engage with reading tools, instructions, and positive reinforcement in the language they speak at home.
2. **Zero-Crash Fallback Guarantee**:
   - Interface rendering **never** crashes due to a missing translation key.
   - Any missing key or untranslated string seamlessly falls back to English (`en`). If English is also missing, the raw key path is safely displayed.
3. **Script-Preserving Text Processing**:
   - Devanagari script relies heavily on Unicode combining characters (matras, virama/halant, anusvara, and nukta) in the `\u0900-\u097F` block.
   - Regex processing in speech analysis, tokenization, and reading coach is specifically calibrated to never strip diacritics or split complex conjunct consonants (*samyuktakshar*).
4. **Offline & Low-Bandwidth Resilience**:
   - Translations are statically bundled in the frontend for instantaneous zero-latency switching without network requests.
   - AI Tutor contains verified, offline, child-friendly localized fallback messages for Marathi and Hindi when connectivity is impaired.

---

## 2. Supported Languages & Locale Architecture

### Supported Language Catalog
The system defines an immutable supported language catalog:

| Code | Native Name | English Name | Script | Direction | Default | Speech Locales |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `en` | **English** | English | Latin | `ltr` | **Yes** | `en-US`, `en-IN`, `en-GB` |
| `mr` | **मराठी** | Marathi | Devanagari | `ltr` | No | `mr-IN`, `mr` |
| `hi` | **हिन्दी** | Hindi | Devanagari | `ltr` | No | `hi-IN`, `hi` |

### Locale Normalization
The system normalizes all incoming locale strings (e.g. from browser headers or legacy API payloads):
- `mr-IN`, `mr_IN` $\to$ `mr`
- `hi-IN`, `hi_IN` $\to$ `hi`
- `en-US`, `en-GB`, `en-IN`, `en_US` $\to$ `en`
- Unsupported codes fallback to `en`.

---

## 3. Frontend Internationalization (i18n) System

### Architecture
Located in `frontend/src/i18n/`:
- `locales/en.js`: Canonical English dictionary (source of truth).
- `locales/mr.js`: Child-friendly, authentic Marathi dictionary.
- `locales/hi.js`: Child-friendly, authentic Hindi dictionary.
- `I18nContext.jsx`: React context provider providing `useTranslation()`, `locale`, `changeLanguage()`, and supported language metadata.

### Translation Hook Usage
```javascript
import { useTranslation } from '../../i18n/I18nContext';

function MyComponent() {
  const { t, locale, changeLanguage } = useTranslation();
  
  return (
    <div>
      <h1>{t('nav.reading')}</h1>
      <p>{t('studentHome.welcomeBack', { name: 'Aarav' })}</p>
    </div>
  );
}
```

### Translation Domains Covered:
- **`common`**: Standard actions (`save`, `cancel`, `loading`, `error`, `back`, `close`, `retry`, `offline`).
- **`nav`**: Shared navigation items (`dashboard`, `reading`, `tutor`, `rewards`, `teacher`, `analytics`, `interventions`, `profile`, `logout`).
- **`auth`**: Login, registration, role selection, validation errors, and switch-prompt messages.
- **`studentHome`**: Welcome headers, quick-start cards, streak summaries, and recommended actions.
- **`reading`**: Reading coach controls, syllables, word-by-word highlights, comprehension checks, and session summaries.
- **`tutor`**: AI tutor introductions, quick prompts, thinking states, input placeholders, and offline notices.
- **`rewards`**: Badges, points, streaks, milestones, celebratory toasts, and claim statuses.
- **`teacher`**: Analytics dashboard, student lists, intervention plans, and effectiveness metrics.

### Persistence Hierarchy
1. Active session state in `I18nContext`.
2. Browser `localStorage` (`dyslexaid_language_preference`).
3. Backend MongoDB preference (`user_language_preferences` collection) when logged in.
4. Default fallback: `en`.

---

## 4. Language Selector Component

### Component Overview
Implemented in `frontend/src/components/shared/LanguageSelector.jsx`:
- Displays native language names (`English`, `मराठी`, `हिन्दी`) for immediate recognition by non-English speakers.
- Integrated into:
  - Global navigation bar (`Layout.jsx`) for authenticated student, teacher, and parent views.
  - Authentication shell (`AuthPages.jsx`) for unauthenticated login and registration screens.

### Accessibility Standards
- **Keyboard Navigation**: Full `Tab` focus, `Enter`/`Space` activation, and `Escape` key dismissal.
- **ARIA Attributes**: `role="combobox"`, `aria-expanded`, `aria-haspopup="listbox"`, `aria-label="Select Language"`.
- **Outside-Click Dismissal**: Closes automatically when clicking elsewhere on the page.

---

## 5. Backend Multilingual API

### Router & Endpoints
Implemented in `backend/routers/v2_multilingual.py` and registered at `/api/v2/multilingual`:

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v2/multilingual/languages` | Returns supported language catalog and metadata | No |
| `GET` | `/api/v2/multilingual/preference` | Retrieves current user's persisted language preference | **Yes** |
| `PUT` | `/api/v2/multilingual/preference` | Updates and persists user's preferred language code | **Yes** |
| `PATCH` | `/api/v2/multilingual/preference` | Alias for updating user's preferred language code | **Yes** |

### Request & Response Models (`backend/models/v2_multilingual.py`)
```python
class LanguagePreferenceUpdate(BaseModel):
    language: str  # Must be one of: "en", "mr", "hi"

class LanguagePreferenceResponse(BaseModel):
    learnerId: str
    preferredLanguage: str
    updatedAt: datetime
    success: bool = True
```

### Feature Flag Protection
The router respects `V2_MULTILINGUAL` (and alias `V2_MULTILINGUAL_SUPPORT`) in `core/config.py`. When disabled, endpoints return `503 Service Unavailable` with `detail="Multilingual support is currently disabled"`.

---

## 6. Language-Aware Reading Passages & Recommender

### Content Catalog Integration
Reading passages in `backend/services/learning/reading_service.py` feature explicit `language` metadata tags (`en`, `mr`, `hi`).

Authentic educational passages curated for Indian learners:
- **Marathi (`mr`)**:
  - `pas-mr-t1-001` (Tier 1): *"मित्रांची मदत"* (A story of two friends, Raju and Meena, building a treehouse).
  - `pas-mr-t2-001` (Tier 2): *"निसर्गाची सफर"* (An exploratory nature walk discovering rivers, hills, and wildlife).
- **Hindi (`hi`)**:
  - `pas-hi-t1-001` (Tier 1): *"सच्चा मित्र"* (A heartwarming story of Aarav and Kabir helping each other in school).
  - `pas-hi-t2-001` (Tier 2): *"पेड़ों का महत्व"* (An engaging ecological passage on the beauty and value of trees).

Every multilingual passage includes:
- Grade level and Tier calibration (`Tier 1`, `Tier 2`).
- Target syllable count, word count, and estimated reading time.
- Vocabulary glossary with definitions and syllabified words.
- Age-appropriate comprehension questions with multiple-choice options and explanations.

### API Language Filtering
- `GET /api/v2/reading/passages?language=mr`: Filters catalog by language.
- `GET /api/v2/reading/recommendation?language=hi`: Returns optimal passage matching learner's profile and specified language. If no passage exists for a language/tier combo, falls back gracefully to default passages.

---

## 7. Speech Analysis & Devanagari Normalization

### Script-Aware Tokenization (`backend/services/learning/speech_analysis.py`)
Standard ASCII regex (`[^\w\s']`) strips Devanagari combining marks (such as *matras*, *anusvara*, *visarga*, and *halant*), splitting unified Devanagari words into isolated consonants and causing severe speech recognition alignment errors.

The Phase 10 normalization pipeline incorporates:
1. **Danda & Double Danda Normalization**:
   - Purna Virama (`।`, `\u0964`) and Deergha Virama (`॥`, `\u0965`) are normalized to standard whitespace boundaries.
2. **Devanagari Unicode Block Preservation**:
   - All characters within `\u0900-\u097F` are preserved intact alongside alphanumeric characters:
   ```python
   # Normalize Indian full stops (Danda) to spaces
   cleaned = text.replace("।", " ").replace("॥", " ")
   # Keep alphanumeric, apostrophes, and the entire Devanagari Unicode block
   cleaned = re.sub(r"[^\w\s'\u0900-\u097F]|_", " ", cleaned)
   ```
3. **Word Alignment**:
   - Accurate calculation of word error rates (WER), hesitation pauses, and reading pace across both Latin and Devanagari scripts.

---

## 8. Language-Aware AI Tutor

### Instruction Prompt Scaffolding (`backend/services/learning/tutor_service.py`)
When a learner's context specifies `mr` or `hi`, the system prompt injects explicit linguistic instructions:
- **Marathi**: *"The learner prefers Marathi (मराठी). Respond in warm, simple, encouraging Marathi appropriate for young learners. Keep sentences short and clear."*
- **Hindi**: *"The learner prefers Hindi (हिन्दी). Respond in warm, simple, encouraging Hindi appropriate for young learners. Keep sentences short and clear."*

### Offline Localized Fallbacks
If external AI generation fails or network is disconnected, `generate_offline_fallback` returns authentic localized responses:
- **Marathi**: *"छान प्रयत्न! आपण एकत्र वाचूया. हा शब्द पुन्हा वाचून पाहूया का?"* (Great effort! Let's read together. Shall we try reading this word again?)
- **Hindi**: *"बहुत अच्छा प्रयास! चलो मिलकर पढ़ते हैं। क्या हम इस शब्द को फिर से पढ़ें?"* (Very good effort! Let's read together. Shall we read this word again?)

---

## 9. Speech Synthesis & Web Speech Recognition

### Text-to-Speech (TTS) Voice Selection (`useReadingCoach.js`)
- Inspects available system voices via `window.speechSynthesis.getVoices()`.
- Prioritizes voices matching the active locale (`mr-IN`, `hi-IN`, `en-IN`, `en-US`).
- Falls back to general language prefix matching or default browser speech engine if specific region voices are absent.

### Web Speech Recognition API (`useSpeechReading.js`)
- Maps active language to appropriate recognition locales:
  - English $\to$ `en-IN` (or `en-US`)
  - Marathi $\to$ `mr-IN`
  - Hindi $\to$ `hi-IN`
- Provides graceful error handling if browser speech recognition lacks language packs.

---

## 10. Automated Testing & Verification

### Test Suite (`backend/test_phase10_multilingual.py`)
23 dedicated automated tests verifying:
1. **Catalog Integrity**: `GET /api/v2/multilingual/languages` structure, codes, native names.
2. **Preference Endpoints**: `GET`, `PUT`, `PATCH` preference persistence and retrieval.
3. **Input Validation**: Rejection of invalid language codes with `400 Bad Request`.
4. **Authentication**: Rejection of unauthenticated preference requests with `401 Unauthorized`.
5. **Feature Flag**: `503 Service Unavailable` returned when `V2_MULTILINGUAL` is disabled.
6. **Passage Filtering**: Language filtering on `get_passages()` and `recommend_reading_passage()`.
7. **Speech Analysis Normalization**: Devanagari tokens, matras, and Danda punctuation preserved.
8. **AI Tutor Multilingual Logic**: Language prompt injection and localized offline fallbacks.

### Regression & Production Build Results
- **Full Regression Suite**: **236 / 236 passed** across Phases 2 through 10.
- **Frontend Production Build**: `npm run build` completed with code `0` (built in 3.30s, 0 errors).
