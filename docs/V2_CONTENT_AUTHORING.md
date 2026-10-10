# DyslexAid V2 — Phase 16: Learning Content Authoring & Quality Management

## 1. Overview & Architecture

Phase 16 establishes a controlled, pedagogically sound, and deterministic authoring and review workflow for DyslexAid educators and administrators. It empowers authorized educators to create, edit, validate, review, and publish dyslexia-friendly reading passages, vocabulary annotations, and comprehension questions without risking premature or unvetted content reaching student learners.

```
                           ┌─────────────────────────────────────────┐
                           │            Content Lifecycle            │
                           └─────────────────────────────────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │    DRAFT     │◄────────────┐
                                         └──────┬───────┘             │
                                                │                     │
                             Passes Validation? │                     │
                                                ▼                     │
                                         ┌──────────────┐             │ (Author revises)
                                         │  IN_REVIEW   │             │
                                         └──────┬───────┘             │
                                                │                     │
                        ┌───────────────────────┴───────────────────┐ │
                        │ Peer Evaluation (Separation of Duties)    │ │
                        ▼                                           ▼ │
                 ┌──────────────┐                            ┌──────┴────────────┐
                 │   APPROVED   │                            │ CHANGES_REQUESTED │
                 └──────┬───────┘                            └───────────────────┘
                        │
                        │ Independent Publish Action
                        ▼
                 ┌──────────────┐
                 │  PUBLISHED   │ ───► Eligible for Phase 15 Student Discovery
                 └──────┬───────┘
                        │
                        │ Archive Action
                        ▼
                 ┌──────────────┐
                 │   ARCHIVED   │ ───► Withdrawn from new discovery; history preserved
                 └──────────────┘
```

---

## 2. Content Lifecycle State Machine

The state machine is enforced strictly on the backend across all operations:

| State | Who Can Edit | Visible to Students? | Eligible for Phase 15 Discovery? | Allowed Next States |
|---|---|---|---|---|
| `DRAFT` | Author / Admin | ❌ No | ❌ No | `IN_REVIEW` |
| `IN_REVIEW` | Locked | ❌ No | ❌ No | `APPROVED`, `CHANGES_REQUESTED`, `REJECTED` |
| `CHANGES_REQUESTED` | Author / Admin | ❌ No | ❌ No | `IN_REVIEW`, `DRAFT` |
| `APPROVED` | Locked | ❌ No | ❌ No | `PUBLISHED`, `ARCHIVED` |
| `PUBLISHED` | Locked (requires Revision) | ✅ Yes | ✅ Yes | `ARCHIVED` |
| `ARCHIVED` | Locked (requires Revision) | ❌ No (historical sessions valid) | ❌ No | `PUBLISHED` (reactivate) |
| `REJECTED` | Locked | ❌ No | ❌ No | `DRAFT` (if revised) |

### Versioning & Historical Activity Preservation
- Editing a `PUBLISHED` or `ARCHIVED` passage does not overwrite live student learning records.
- Instead, `create_content_revision` forks the record into a new `DRAFT` with an incremented version number (`version: n + 1`), preserving the original passage ID and in-flight student reading attempts intact.

---

## 3. Roles, Permissions & Separation of Duties

DyslexAid operates on an authentic role hierarchy: `teacher`, `student`, `parent`, and `admin`.

1. **Role Enforcement:**
   - **Teachers & Admins**: Exclusively authorized to access `/api/v2/content-authoring/*` endpoints.
   - **Students & Parents**: Blocked with `HTTP 403 Forbidden` on all authoring and editorial endpoints.
2. **Separation of Duties Rule:**
   - An educator who authored a draft (`authorId == current_user.id`) **cannot** review, approve, or self-publish their own content unless an explicit admin override is present.
   - Evaluation decisions require an independent peer educator (`reviewerId != authorId`), ensuring pedagogical objectivity and quality control.
3. **Tenant & Classroom Isolation:**
   - Authored content documents capture `tenantId` (derived from `user.classroomCode`).
   - Educators only view and review items within their authorized tenant boundary or shared catalog.

---

## 4. Deterministic Quality Validation

Every content item undergoes rule-based validation before submission and publication. Validation produces actionable `errors` (blocking), `warnings` (recommendations), and a `completenessScore` (0–100):

1. **Title & Text Integrity:**
   - Title: Non-empty, 3–120 characters.
   - Text Length: Minimum 15 words, maximum 1200 words (matching child reading stamina).
2. **Multilingual Script Verification:**
   - Supported language codes: `en` (English), `hi` (Hindi), `mr` (Marathi).
   - Devanagari script regex verification (`[\u0900-\u097F]`) for Hindi and Marathi content. Warns if Hindi or Marathi is submitted in Latin ASCII script.
3. **Difficulty Tier Calibration:**
   - Must be integer in 1..5, matching Phase 3 Adaptive Learning Engine difficulty tiers.
4. **Vocabulary & Annotation Ergonomics:**
   - Requires non-empty word and child-friendly definition.
   - Detects duplicate words and warns if annotated vocabulary does not appear in passage text.
5. **Comprehension Questions & Answer Integrity:**
   - Each question requires non-empty text and at least 2 distinct options.
   - Rejects duplicate options and out-of-bounds `correctAnswer` indices.
6. **Placeholder & Debug Detection:**
   - Deterministic filters reject "lorem ipsum", "TODO", "FIXME", "asdfgh", "test test test", and other accidental placeholder texts.

---

## 5. Phase 15 Discovery Gate & Legacy Compatibility

Only content with `status == "PUBLISHED"` and `active == True` is eligible for student discovery:

- **Phase 15 Selection Filter:** `_get_eligible_reading_passages()` in `personalized_content.py` queries `db.reading_passages` with:
  ```python
  {"active": True, "$or": [{"status": "PUBLISHED"}, {"status": {"$exists": False}}]}
  ```
- **Session Initiation Gate:** `reading_service.start_reading_session` explicitly checks `passage.get("status")` and rejects any attempt to initiate an activity on `DRAFT`, `IN_REVIEW`, `CHANGES_REQUESTED`, `ARCHIVED`, or `REJECTED` content.
- **Legacy V1 Backward Compatibility:** Pre-existing seed passages lacking a `status` field but possessing `active: True` continue to function seamlessly without mass migration or data corruption.

---

## 6. API Endpoints

All endpoints are hosted under `/api/v2/content-authoring` and require valid JWT Bearer authentication with educator role.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/content-authoring/items` | List content items with optional status, language, tier filters |
| `POST` | `/api/v2/content-authoring/drafts` | Create a new passage draft in `DRAFT` status |
| `GET` | `/api/v2/content-authoring/drafts/{id}` | Get full draft details and validation report |
| `PUT` | `/api/v2/content-authoring/drafts/{id}` | Update an editable draft (`DRAFT` or `CHANGES_REQUESTED`) |
| `POST` | `/api/v2/content-authoring/validate` | Run deterministic quality validation on any payload |
| `POST` | `/api/v2/content-authoring/drafts/{id}/submit` | Submit draft for peer review (`DRAFT` -> `IN_REVIEW`) |
| `GET` | `/api/v2/content-authoring/review-queue` | List passages currently in `IN_REVIEW` |
| `POST` | `/api/v2/content-authoring/review/{id}/decision` | Submit review decision (`APPROVE`, `REQUEST_CHANGES`, `REJECT`) |
| `POST` | `/api/v2/content-authoring/items/{id}/publish` | Publish approved content (`APPROVED` -> `PUBLISHED`) |
| `POST` | `/api/v2/content-authoring/items/{id}/archive` | Archive published content (`PUBLISHED` -> `ARCHIVED`) |
| `POST` | `/api/v2/content-authoring/items/{id}/revise` | Fork published/archived item into a new version draft |
| `GET` | `/api/v2/content-authoring/items/{id}/history` | Retrieve immutable audit timeline and version logs |
| `GET` | `/api/v2/content-authoring/translations/{group_id}`| Retrieve translation completeness across `en`, `hi`, `mr` |

---

## 7. Verification Results

### Backend Automated Test Suite
- Executed via `pytest backend/test_phase16_content_authoring.py`: **23/23 tests passed** in 2.55s.
- Full regression suite via `pytest backend/ -q`: **358/358 tests passed** in 5.01s with **0 regressions**.

### Frontend Automated Verification
- ESLint: `npm run lint` passed with **0 errors, 0 warnings**.
- Production Bundle: `npm run build` compiled cleanly via Vite in **3.15s** (0 errors).

---

## 8. Non-Clinical & Pedagogical Safeguards

DyslexAid content authoring tools are designed strictly for educational reading practice and teacher curation:
- Content difficulty tiers correspond to reading accessibility bands (1–5) based on word length, sentence structure, and phonetic decodability.
- The quality engine evaluates structural and linguistic clarity, not clinical efficacy.
- No clinical or diagnostic claims are made.
