# DyslexAid V2 MongoDB Database Schema Specification

**Status:** Target V2 Schema Architecture  
**Compatibility Guarantee:** Fully Backward Compatible with V1 Data. Zero Data Migration Required.

---

## 1. Schema Design Principles

1. **Non-Destructive Coexistence:** Existing V1 collections (`users`, `progress`, `screening_results`, `classrooms`, etc.) remain in place.
2. **Dual-Read / Single-Write Synchronization:** V2 learner profiles seamlessly synchronize with `users.readingProfile` so V1 frontend views continue to display data without modification.
3. **Auditability & Append-Only History:** Assessment results, predictions, and reading attempts are stored as immutable time-series events.
4. **Appropriate Granularity:** Detailed per-word or per-question telemetry is stored in dedicated session collections (`activity_attempts`, `reading_performance`) rather than bloating the primary user document.

---

## 2. Collection Classification Overview

| Collection Name | Status | Purpose | Primary Key / Indexes |
|---|---|---|---|
| `users` | **EXISTING COLLECTION** | Core identity, auth, settings, embedded V1 readingProfile | `id` (unique), `email` (unique) |
| `learner_profiles` | **NEW V2 COLLECTION** | Comprehensive V2 learner intelligence profiles | `learnerId` (unique), `updatedAt` |
| `screening_results` | **EXISTING COLLECTION** | Standardized 12-domain screening attempts history | `id` (unique), `userId`, `createdAt` |
| `prediction_history` | **EXISTING COLLECTION** | Audit log of scoring events (ML vs rule-based) | `id` (unique), `userId`, `screeningResultId` |
| `learning_states` | **NEW V2 COLLECTION** | Real-time adaptive learning state and progression stage | `learnerId` (unique), `currentTier` |
| `learning_activities` | **NEW V2 COLLECTION** | Catalog of interactive micro-learning tasks | `id` (unique), `domain`, `difficultyTier` |
| `activity_attempts` | **NEW V2 COLLECTION** | Granular attempt records for micro-tasks | `id` (unique), `learnerId`, `activityId`, `createdAt` |
| `reading_sessions` | **NEW V2 COLLECTION** | Reading coach sessions (text, duration, settings) | `id` (unique), `learnerId`, `createdAt` |
| `reading_performance` | **NEW V2 COLLECTION** | Telemetry: WPM, hesitations, syllables, accuracy | `id` (unique), `sessionId`, `learnerId` |
| `adaptive_recommendations` | **NEW V2 COLLECTION** | Decisions produced by the Adaptive Decision Engine | `id` (unique), `learnerId`, `generatedAt` |
| `interventions` | **NEW V2 COLLECTION** | Structured teacher/clinician instructional strategies | `id` (unique), `targetProfile`, `domain` |
| `intervention_results` | **NEW V2 COLLECTION** | Measured pre/post outcomes of interventions | `id` (unique), `interventionId`, `studentId` |
| `achievements` | **NEW V2 COLLECTION** | Gamification milestone & badge definitions | `id` (unique), `code` |
| `streaks` | **NEW V2 COLLECTION** | Gamification streak & habit telemetry | `learnerId` (unique), `lastActivityDate` |
| `ai_tutor_sessions` | **NEW V2 COLLECTION** | Multi-turn tutoring conversation transcripts | `id` (unique), `learnerId`, `startedAt` |
| `teacher_notes` | **EXISTING COLLECTION** | Teacher qualitative observations on students | `studentId`, `teacherId`, `createdAt` |
| `parent_links` | **NEW V2 COLLECTION** | Associations connecting parent accounts to students | `parentId`, `studentId`, `status` |
| `notifications` | **EXISTING COLLECTION** | User notification stream (SSE-backed) | `userId`, `createdAt` |
| `classrooms` | **EXISTING COLLECTION** | School classrooms and codes | `code` (unique), `teacherId` |
| `assignments` | **EXISTING COLLECTION** | Teacher assignments and OCR materials | `classroomCode`, `teacherId` |
| `submissions` | **EXISTING COLLECTION** | Student assignment submissions & grades | `assignmentId` + `studentId` (compound unique) |
| `progress` | **EXISTING COLLECTION** | V1 aggregated progress counters | `userId` (unique) |
| `daily_tasks` | **EXISTING COLLECTION** | Daily task lists | `userId`, `date` |
| `ai_plans` | **EXISTING COLLECTION** | 4-week tailored learning plans | `userId` (unique) |
| `libraries` | **EXISTING COLLECTION** | Student-saved simplified documents | `userId`, `createdAt` |

---

## 3. Detailed Collection Schemas

### 3.1. `users` (EXISTING COLLECTION)
```json
{
  "_id": "ObjectId(...)",
  "id": "uuid-v4-string",
  "name": "Aarav Sharma",
  "email": "aarav@demo.school",
  "passwordHash": "$2b$12$...",
  "role": "student", // "student" | "teacher" | "parent"
  "classroomCode": "DA-DEMO",
  "classroomJoined": "DA-DEMO",
  "schoolName": "Government Primary School, Pune",
  "readingProfile": {
    "assessmentVersion": 2,
    "type": "Phonological Dyslexia",
    "primaryProfile": "Phonological Dyslexia",
    "level": "moderate",
    "riskLevel": "Moderate",
    "score": 55,
    "confidence": 72.0,
    "domainScores": {
      "phonological_processing": 78,
      "rapid_naming": 45,
      "working_memory": 60
    },
    "strengths": ["Visual Processing"],
    "weaknesses": ["Phonological Processing"],
    "learningStyle": "Auditory-First (Phonics-Based)",
    "uiSettings": {
      "font": "OpenDyslexic",
      "font_size": "medium",
      "line_spacing": 1.4,
      "background": "white"
    },
    "screenedAt": 1727548000
  },
  "settings": {
    "font": "OpenDyslexic",
    "fontSize": 18,
    "lineSpacing": 2.0,
    "letterSpacing": 0.1,
    "bgColor": "#FFF8F0",
    "textColor": "#1A2A2A",
    "ttsSpeed": 0.85,
    "ttsLanguage": "en-IN",
    "highlightWords": true,
    "showBulletPoints": true,
    "autoSimplify": true
  },
  "languages": ["english", "hindi"],
  "onboardingComplete": true,
  "isDemo": false,
  "createdAt": 1727548000
}
```

---

### 3.2. `learner_profiles` (NEW V2 COLLECTION)
Provides an expanded, normalized data structure for the V2 intelligence engine.
```json
{
  "_id": "ObjectId(...)",
  "learnerId": "uuid-v4-user-id",
  "schemaVersion": 2,
  "currentLevel": "moderate",
  "riskLevel": "Moderate",
  "dyslexiaIndicators": {
    "primaryProfile": "Phonological Dyslexia",
    "subtypeProbabilities": {
      "phonological": 0.78,
      "surface": 0.22,
      "rapid_naming": 0.35,
      "double_deficit": 0.30,
      "visual": 0.15,
      "working_memory": 0.25
    },
    "confidence": 0.72
  },
  "domainScores": {
    "phonological_awareness": 78,
    "phonological_memory": 65,
    "rapid_naming": 45,
    "letter_reversal": 30,
    "reading_fluency": 50,
    "orthographic_spelling": 42,
    "reading_comprehension": 68,
    "motor_writing": 25,
    "visual_processing": 85,
    "processing_speed": 40
  },
  "cognitiveProfile": {
    "workingMemory": "moderate_capacity",
    "visualProcessing": "strong",
    "auditoryProcessing": "needs_scaffolding",
    "processingSpeed": "extended_time_beneficial"
  },
  "strengths": [
    "Visual memory and pattern synthesis",
    "High contextual inferencing in comprehension"
  ],
  "focusAreas": [
    "Phoneme segmenting and blending",
    "Irregular sight-word automaticity"
  ],
  "readingMetrics": {
    "readingLevel": "grade_3_intermediate",
    "comprehensionLevel": 68,
    "vocabularyLevel": "grade_4_standard",
    "avgWordsPerMinute": 65,
    "wordsMastered": 42
  },
  "learningStyle": "Multisensory Auditory-Visual",
  "preferredLanguage": "en-IN",
  "accessibilityPreferences": {
    "font": "OpenDyslexic",
    "fontSize": 18,
    "lineSpacing": 2.0,
    "letterSpacing": 0.12,
    "bgColor": "#FFF8F0",
    "textColor": "#1A2A2A",
    "ttsSpeed": 0.85,
    "ttsVoice": "en-IN-Standard-A",
    "highlightWords": true,
    "syllableSplit": true
  },
  "adaptiveDifficulty": {
    "activeTier": 2, // 1 to 5
    "maxSentenceLength": 12,
    "vocabularyComplexity": "controlled",
    "scaffoldingLevel": "high"
  },
  "currentGoals": [
    "Master 10 new phoneme blends",
    "Complete 5 consecutive daily reading sessions"
  ],
  "teacherObservations": [
    "Responds well to audio accompaniment during reading."
  ],
  "parentObservations": [
    "Prefers reading in 15-minute focused bursts."
  ],
  "disclaimer": "These screening indicators represent educational accommodations and do not constitute a medical or clinical diagnosis.",
  "lastUpdated": 1727548000,
  "createdAt": 1727548000
}
```

---

### 3.3. `learning_states` (NEW V2 COLLECTION)
Maintains current progress, active session state, and proximal learning boundaries.
```json
{
  "_id": "ObjectId(...)",
  "learnerId": "uuid-v4-user-id",
  "activeDifficultyTier": 2,
  "currentModule": "phonological_awareness_level_2",
  "todayTasksAssigned": 4,
  "todayTasksCompleted": 2,
  "currentStreak": 5,
  "lastSessionTimestamp": 1727548000,
  "adaptiveState": {
    "consecutivePasses": 3,
    "consecutiveFailures": 0,
    "recommendedNextAction": "phoneme_blending_practice",
    "adaptationTriggerDue": false
  },
  "updatedAt": 1727548000
}
```

---

### 3.4. `learning_activities` & `activity_attempts` (NEW V2 COLLECTIONS)
Reusable activity definitions and student attempt telemetry.
```json
// learning_activities
{
  "_id": "ObjectId(...)",
  "id": "act-blend-001",
  "title": "Phoneme Sound Match",
  "domain": "phonological_awareness",
  "difficultyTier": 2,
  "targetSkills": ["phoneme_isolation", "rhyme_detection"],
  "contentPayload": {
    "promptAudio": "/audio/blends/cat.mp3",
    "targetWord": "cat",
    "phonemes": ["k", "æ", "t"],
    "distractors": ["b", "m"]
  },
  "durationSecondsExpected": 120,
  "isActive": true
}

// activity_attempts
{
  "_id": "ObjectId(...)",
  "id": "attempt-uuid",
  "learnerId": "uuid-v4-user-id",
  "activityId": "act-blend-001",
  "scorePercent": 85,
  "durationSeconds": 94,
  "hesitationCount": 2,
  "hintsRequested": 1,
  "completedAt": 1727548000
}
```

---

### 3.5. `reading_sessions` & `reading_performance` (NEW V2 COLLECTIONS)
```json
// reading_sessions
{
  "_id": "ObjectId(...)",
  "id": "read-session-uuid",
  "learnerId": "uuid-v4-user-id",
  "documentId": "doc-uuid",
  "source": "ocr_scan", // "ocr_scan" | "library" | "curriculum"
  "durationSeconds": 480,
  "wordsRead": 240,
  "ttsUsed": true,
  "createdAt": 1727548000
}

// reading_performance
{
  "_id": "ObjectId(...)",
  "id": "perf-uuid",
  "sessionId": "read-session-uuid",
  "learnerId": "uuid-v4-user-id",
  "wordsPerMinute": 62,
  "hesitationIntervalsMs": [1200, 3400, 800],
  "frequentlyPausedWords": ["continuous", "evaporates"],
  "comprehensionQuizScore": 80,
  "calculatedAccuracy": 92.5
}
```

---

### 3.6. `adaptive_recommendations` & `interventions` (NEW V2 COLLECTIONS)
```json
// adaptive_recommendations
{
  "_id": "ObjectId(...)",
  "id": "rec-uuid",
  "learnerId": "uuid-v4-user-id",
  "triggerEvent": "comprehension_improvement_threshold",
  "previousTier": 1,
  "recommendedTier": 2,
  "recommendedActivities": ["act-blend-001", "act-ran-004"],
  "reasoning": "Student comprehension increased by 18% over the last 5 sessions with consistent streak.",
  "generatedAt": 1727548000,
  "applied": true
}
```

---

### 3.7. `parent_links` (NEW V2 COLLECTION)
Links parents to their children without compromising security or other students' privacy.
```json
{
  "_id": "ObjectId(...)",
  "id": "link-uuid",
  "parentId": "uuid-v4-parent-id",
  "studentId": "uuid-v4-student-id",
  "inviteCode": "PL-849201",
  "status": "active", // "pending" | "active" | "revoked"
  "relationship": "Mother",
  "permissions": ["view_progress", "view_recommendations", "log_home_reading"],
  "linkedAt": 1727548000
}
```

---

## 4. Indexing & Optimization Strategy

1. **`learner_profiles`:**
   - `{ learnerId: 1 }` (unique)
   - `{ riskLevel: 1, "dyslexiaIndicators.primaryProfile": 1 }`
2. **`activity_attempts`:**
   - `{ learnerId: 1, createdAt: -1 }`
   - `{ activityId: 1, scorePercent: 1 }`
3. **`reading_performance`:**
   - `{ learnerId: 1, sessionId: 1 }`
4. **`parent_links`:**
   - `{ parentId: 1, status: 1 }`
   - `{ studentId: 1, status: 1 }`
   - `{ inviteCode: 1 }` (sparse, unique)
