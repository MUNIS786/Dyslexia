# DyslexAid V2 — Phase 5: Speech & Reading Analysis Architecture Documentation

**Module:** Speech & Reading Analysis (`V2_SPEECH_ANALYSIS`)  
**Status:** Complete & Verified  
**Parent System:** DyslexAid V2 Adaptive Reading Coach  
**Standard:** Privacy-First, Deterministic, Non-Clinical Educational Practice Telemetry  

---

## 1. Architectural Overview

Phase 5 extends the DyslexAid Reading Coach with optional **speech-assisted reading practice**. When a learner chooses to read aloud, browser-native speech recognition converts speech to text locally in the browser. The recognized transcript is submitted to the backend, where a deterministic Dynamic Programming sequence alignment engine objectively compares the learner's spoken words with the expected passage text.

```
+-----------------------------------------------------------------------------------+
|                                  STUDENT BROWSER                                  |
|                                                                                   |
|  +--------------------+         +-----------------------+                         |
|  |   Reading Passage  | ------> |  🎤 Read Aloud Mode   |                         |
|  +--------------------+         +-----------------------+                         |
|                                             |                                     |
|                                             v                                     |
|                           window.SpeechRecognition (Native API)                   |
|                           [Temporary In-Memory Transcript]                        |
|                           * NO AUDIO RECORDED OR STORED *                         |
|                                             |                                     |
|                                             v                                     |
|                              POST /v2/reading/speech/analyze                      |
+---------------------------------------------|-------------------------------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|                                                                                   |
|  1. Text Normalization: lowercase, strip punctuation, clean whitespace            |
|  2. DP Sequence Alignment: Word-level Wagner-Fischer token alignment              |
|  3. Metric Calculations:                                                          |
|     - Word Accuracy (% matched words)                                             |
|     - Coverage Rate (% of passage attempted)                                     |
|     - Words Per Minute (WPM with zero/short duration safeguards)                  |
|     - Educational Reading Practice Score (balanced 60/25/15 weighted formula)     |
|  4. Database: Persist derived metrics to 'speech_reading_analyses'                |
|  5. Session Link: Attach speech telemetry to 'reading_sessions'                   |
|  6. Recalibration: Feed fluency signal to Phase 2 Learner Profile                 |
|  7. Adaptive Engine: Sync with Phase 3 ZPD Learning State                         |
+-----------------------------------------------------------------------------------+
```

---

## 2. Privacy-First Audio Model

DyslexAid adheres to strict student data privacy (COPPA / FERPA principles and India's DPDP Act):
* **No Raw Audio Stored:** The backend never receives, processes, or persists audio binary streams, WAV/MP3 files, or voice recordings.
* **No Audio Uploads:** Recognition occurs entirely inside the client browser using `window.SpeechRecognition` or `window.webkitSpeechRecognition`.
* **Derived Metrics Only:** Only derived educational telemetry (word accuracy, coverage rate, reading pace, pause count, hesitation count) is stored in MongoDB.
* **Temporary Client State:** In-browser recognition tokens are cleared from memory once analysis completes or upon session reset.

---

## 3. Transcript Normalization

Before comparing the expected passage with the spoken transcript, both strings are normalized using deterministic rules in `services/learning/speech_analysis.py`:
1. **Lowercasing:** All characters are converted to lowercase.
2. **Punctuation Sanitization:** Commas, periods, exclamation marks, question marks, semicolons, brackets, and quotes are replaced with spaces.
3. **Contraction Preservation:** Apostrophes inside words (e.g. `don't`, `we'll`, `it's`) are preserved to prevent splitting valid English contractions into fragmented tokens.
4. **Whitespace Collapse:** All consecutive whitespace characters (spaces, tabs, newlines) are collapsed into single space delimiters.
5. **Edge Trimming:** Extraneous quotes and punctuation at word boundaries are stripped.

---

## 4. Sequence Alignment Algorithm

Word comparison uses an optimal Dynamic Programming sequence alignment (Wagner-Fischer string metric adapted for word tokens):

### Alignment Costs
* **Match:** Cost $0.0$ ($E[i] = R[j]$)
* **Substitution:** Cost $1.0$ ($E[i] \neq R[j]$)
* **Omission (Deletion):** Cost $1.0$ (Word present in expected passage but omitted in speech)
* **Insertion:** Cost $1.0$ (Extraneous word recognized in speech but not in passage)

### Recurrence Relation
$$DP[i][j] = \min \begin{cases} DP[i-1][j-1] + \text{cost\_match}(E[i], R[j]) \\ DP[i-1][j] + \text{COST\_OMISSION} \\ DP[i][j-1] + \text{COST\_INSERTION} \end{cases}$$

### Backtracking Output
The algorithm backtracks from $(m, n)$ to $(0, 0)$ to produce an ordered sequence of token alignment records:
```json
[
  {"expected": "sam", "recognized": "sam", "status": "matched"},
  {"expected": "sees", "recognized": "saw", "status": "substitution"},
  {"expected": "a", "recognized": null, "status": "omission"},
  {"expected": null, "recognized": "very", "status": "insertion"}
]
```

---

## 5. Metrics & Formulas

All metrics are authoritatively computed server-side. Client-supplied scores are never trusted.

### 5.1 Word Accuracy
Percentage of expected words in the passage that the learner spoke accurately:
$$\text{Word Accuracy} = \frac{\text{Matched Words}}{\max(1, \text{Expected Words})} \times 100$$

### 5.2 Coverage Rate
Percentage of the reading passage covered by speech:
$$\text{Coverage Rate} = \min\left(100.0, \frac{\text{Recognized Words}}{\max(1, \text{Expected Words})} \times 100\right)$$

### 5.3 Words Per Minute (WPM)
Reading pace with safeguards against division by zero and short sessions:
$$\text{WPM} = \begin{cases} 0.0 & \text{if duration} < 3 \text{ seconds or recognized words} = 0 \\ \min\left(300.0, \frac{\text{Recognized Words}}{\text{durationSeconds} / 60.0}\right) & \text{otherwise} \end{cases}$$

### 5.4 Educational Reading Practice Score
A transparent composite score combining accuracy, coverage, and age-appropriate reading pace:
$$\text{Reading Practice Score} = (0.60 \times \text{Accuracy}) + (0.25 \times \text{Coverage}) + \min\left(15.0, \frac{\text{WPM}}{120.0} \times 15.0\right)$$
Clamped strictly between $0.0$ and $100.0$.

---

## 6. Confidence & Hesitation Signals

* **Browser Recognition Confidence:** When browser Web Speech API provides `confidence` values ($[0.0, 1.0]$), they are aggregated into a summary (`average`, `min`, `max`, `sampleCount`). If the browser does not provide confidence, the field is stored as `null` rather than fabricated.
* **Pauses & Hesitations:** Silence intervals ($> 2.0\text{s}$) between recognition events increment `pauseCount`. Longer speech stalls ($> 3.5\text{s}$) increment `hesitationCount`. If unsupported, values are `null`.

---

## 7. Database Models & Indexes

### Collection: `speech_reading_analyses`
```json
{
  "analysisId": "fee9a087-9e40-4627-a5cd-d13c0f53a8f3",
  "sessionId": "fa587018-a407-40fe-a04b-9b1c328cb17f",
  "learnerId": "f22654ae-2231-4756-97d1-5d8d9ca5cfd4",
  "passageId": "pas-t1-001",
  "passageWordCount": 54,
  "recognizedWordCount": 30,
  "matchedWordCount": 30,
  "wordAccuracy": 55.6,
  "coverageRate": 55.6,
  "omissions": ["with", "his", "soft", "paw"],
  "insertions": [],
  "substitutions": [],
  "hesitationCount": 1,
  "pauseCount": 2,
  "readingDurationSeconds": 20,
  "wordsPerMinute": 90.0,
  "confidenceSummary": {
    "average": 0.94,
    "min": 0.88,
    "max": 0.99,
    "sampleCount": 14
  },
  "readingPracticeScore": 58.5,
  "alignmentSummary": [...],
  "feedback": "Good try reading aloud! Every practice makes your reading brain stronger.",
  "analysisVersion": "1.0",
  "createdAt": 1790775355
}
```

### MongoDB Indexes
* `analysisId` (unique)
* `sessionId`
* `learnerId`
* `createdAt`
* `learnerId + createdAt`

---

## 8. API Endpoints

### `POST /api/v2/reading/speech/analyze`
* **Access:** Authenticated student owning the reading session.
* **Payload:** `SpeechAnalysisRequest` (`sessionId`, `passageId`, `transcript`, `durationSeconds`, `pauseCount`, `hesitationCount`, `confidenceSummary`).
* **Response:** `SpeechAnalysisResponse` (`status`, `analysis`, `childFriendlyFeedback`, `nextActionSuggestion`).

### `GET /api/v2/reading/speech/sessions/{session_id}`
* **Access:** Student (own session only) or Teacher (assigned classroom students).
* **Response:** Speech analysis document.

---

## 9. Phase 3 & Learner Profile Integration

1. **Domain Signal Update:** Upon analysis completion, `recalibrate_from_activity()` updates the student's `reading_fluency` competency in `learner_profiles`.
2. **Session Score Blending:** When `complete_reading_session()` is invoked, if speech practice telemetry exists on the session, it is blended into `readingScore` and `overallScore`.
3. **ZPD Tier Adaptation:** Phase 3 Adaptive Engine incorporates the session score into the rolling comprehension and pass/failure counters.

---

## 10. Educational Safety & Non-Clinical Boundaries

DyslexAid V2 is an assistive educational learning tool:
* **No Medical Claims:** The system does NOT diagnose, treat, or evaluate clinical dyslexia, speech disorders, or language impairments.
* **Encouraging Vocabulary:** Child-facing feedback strictly avoids pathologizing terms ("disordered", "impaired", "bad reading") and uses supportive language ("practice opportunity", "building reading strength", "read clearly").
* **Non-Blocking Flow:** Microphone access is completely optional. Learners can always read silently or use Listen Mode.

---

## 11. Feature Flag

Controlled by `V2_SPEECH_ANALYSIS`:
* When `False`: Speech endpoints return `503 Service Unavailable`.
* When `True`: Full speech analysis endpoints are active.
