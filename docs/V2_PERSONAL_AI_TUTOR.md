# DyslexAid V2 — Personal AI Tutor Specification & Implementation

## 1. Vision & Architecture

The **Personal AI Tutor** is an empathetic, learner-aware educational companion designed specifically for dyslexic students. Unlike a generic conversational chatbot, the AI Tutor understands where the learner is in their learning journey:

```text
       Learner Profile (Phase 2)
                 ↓
     Adaptive Learning State (Phase 3)
                 ↓
      Active Reading Coach (Phase 4)
                 ↓
     Speech Practice Signals (Phase 5)
                 ↓
     ┌────────────────────────────────┐
     │  Compact Tutor Context Builder │
     └───────────────┬────────────────┘
                     │
                     ▼
     ┌────────────────────────────────┐
     │   Level-Adapted Prompt Builder │
     └───────────────┬────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  Gemini 3.5 Flash        Deterministic Fallback
  (AI Provider)           (Offline Resilience)
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
     ┌────────────────────────────────┐
     │   Structured Response & Action │
     └────────────────────────────────┘
```

The tutor preserves the existing V1 Chat system intact (`/student/chat`, `routers/chat.py`, `services/ai_service.py`), adding a dedicated, highly specialized V2 pedagogical workspace (`/student/tutor`, `routers/v2_tutor.py`, `services/learning/tutor_service.py`).

---

## 2. Compact Learner Context (`TutorContext`)

To prevent model context bloat and guarantee data privacy, context is strictly minimized:

```json
{
  "learnerId": "f22654ae-...",
  "displayName": "Aarav",
  "learningLevel": 2,
  "learningLevelName": "Developing",
  "adaptiveTier": 1,
  "strengths": ["Sound & Word Practice", "Visual Learning"],
  "practiceAreas": ["Reading Fluency", "Letter Recognition"],
  "currentPassage": {
    "passageId": "pas-t1-001",
    "title": "Sam the Orange Cat",
    "excerpt": "Sam is a fat cat. Sam is bright orange. He sits on a red mat...",
    "difficulty": 1,
    "vocabularyWords": ["cat", "orange", "mat", "sun"]
  },
  "activeWord": "curious",
  "recentReading": {
    "comprehension": 80.0,
    "wordsRead": 45
  },
  "speechSignals": {
    "accuracy": 88.0,
    "wpm": 72.0
  },
  "accessibility": {
    "font": "OpenDyslexic",
    "fontSize": 20,
    "ttsSpeed": 0.85
  }
}
```

### Strict Privacy Constraints:
- **Zero raw audio or recordings** transmitted or saved.
- **Zero passwords, tokens, JWTs, or internal database keys** sent to AI providers.
- **Zero teacher private notes** exposed.
- All context assembly is purely deterministic on the server.

---

## 3. Pedagogical Level Adaptation

The tutor dynamically shifts its instruction style to match the student's Phase 2 canonical learning level:

| Level | Name | Sentence Structure | Pedagogical Style | Check Question |
| :--- | :--- | :--- | :--- | :--- |
| **Level 1** | Foundation | 6–10 words | Very short, single-concept, vivid everyday examples, heavy praise. | "Can you point to the sound?" |
| **Level 2** | Developing | 8–14 words | Clear explanations, one relatable example, syllable breakdown. | "Can you try it in a short sentence?" |
| **Level 3** | Progressing | 12–18 words | Explanations with simple reasoning and connections. | "Why do you think that happened?" |
| **Levels 4–5**| Competent / Mastering | Rich & varied | Deeper reasoning, inference, and gentle challenge questions. | "What clue helps us understand this?" |

---

## 4. Deterministic Offline Fallback

If the AI provider (Gemini) is unreachable, times out, returns malformed text, or lacks an API key, the tutor engages a deterministic educational fallback engine without crashing:

1. **Vocabulary Inquiries**:
   - Parses target word from active context or query.
   - Looks up definition, syllable chunking (`cu · ri · ous`), child-friendly examples, and simple synonyms.
   - Attaches `practice_word` action.
2. **Reading Comprehension & Hints**:
   - Uses the active passage excerpt.
   - Employs progressive hint staging (clues based on character actions) rather than revealing quiz answers.
   - If no passage is active, states missing context honestly: *"I don't have the story you're reading right now. Please open a story in Reading Coach."* (Anti-hallucination rule).
3. **Spelling Inquiries**:
   - Breaks word into letter chunks and syllable sounds.
   - Spells word in uppercase and lowercase for visual reinforcement.
4. **Encouragement & Growth Mindset**:
   - Responds to frustration (`"I can't do this"`, `"too hard"`, `"give up"`).
   - Validates that reading takes time and practice, reinforcing perseverance and self-compassion.

---

## 5. Reading Coach Integration

The tutor directly connects with the Phase 4 Reading Coach:
- **DifficultWords Popup**: When a student taps any word in a reading passage, the modal includes an **"🤖 Ask AI Tutor"** button.
- **Direct Navigation with Query Parameters**: Clicking navigates to `/student/tutor?word={word}&passageId={passageId}`.
- **Context Pill Banner**: Displays active story and active word in the tutor interface with clear removal buttons.

---

## 6. Actionable Pedagogical Next Steps (`TutorSuggestedAction`)

Every tutor response can recommend a learning action:
- `practice_word`: Pre-fills conversational word practice.
- `read_again`: Opens the Reading Coach to re-read the story.
- `try_question`: Navigates to the comprehension questions.
- `open_reading_coach`: Direct link to reading library.
- `start_adaptive_practice`: Direct link to Phase 3 Adaptive Practice.

---

## 7. Strict Non-Clinical & Anti-Hallucination Boundaries

- **Non-Clinical Boundary**: The tutor is purely an educational coach. It NEVER mentions, implies, or claims to diagnose dyslexia, ADHD, learning disabilities, or medical conditions.
- **Anti-Hallucination Boundary**: The tutor never invents story plot points, past test scores, or assignments. Missing data is stated transparently.
- **Answer Guarding**: The tutor provides progressive hints rather than immediately giving the final answer to comprehension quizzes or school assignments.

---

## 8. API Specification

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v2/tutor/chat` | Send student inquiry; returns structured response | Yes (Student) |
| `GET` | `/api/v2/tutor/context` | Inspect compact pedagogical context | Yes (Student/Teacher) |
| `GET` | `/api/v2/tutor/history` | Retrieve bounded conversational history (max 20) | Yes (Student) |
| `DELETE`| `/api/v2/tutor/history` | Reset conversation history | Yes (Student) |

### Tenant Security:
- All student requests derive identity from `current_user["id"]`.
- Querying another student's context (`?learnerId=another_id`) by a student is rejected with `403 Forbidden`.
- Teachers can access student context for classroom instructional support.

---

## 9. Feature Flag

Governed by `settings.V2_AI_TUTOR`:
- Controlled via environment variable `V2_AI_TUTOR=true|false`.
- When disabled, endpoints return `503 Service Unavailable`.
- Enabled and verified in Phase 6.
