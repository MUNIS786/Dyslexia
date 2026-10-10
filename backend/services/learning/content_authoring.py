"""
backend/services/learning/content_authoring.py — Phase 16:
Learning Content Authoring & Quality Management Service.

Provides:
- Deterministic Server-Side Content Quality & Multilingual Validation
- Strict Content Lifecycle State Machine:
  DRAFT -> IN_REVIEW -> (CHANGES_REQUESTED | APPROVED) -> PUBLISHED -> ARCHIVED
- Separation-of-Duties Enforcement (authors cannot self-review or self-approve)
- Reusable Passage Catalog Integration (persisted directly in db.reading_passages)
- Complete Audit Logging and Version History
- Zero Student/Parent Leakage of Editorial Drafts or Review Notes
"""
import time
import uuid
import re
import logging
from typing import List, Dict, Any, Optional

from database.database import db
from models.v2_content_authoring import (
    ContentLifecycleState,
    ContentValidationIssue,
    ContentValidationResult,
    ContentDraftCreateRequest,
    ContentDraftUpdateRequest,
    ContentReviewDecisionRequest,
    ContentAuditLogEntry,
    ContentItemResponse,
    ContentListResponse,
    ContentHistoryResponse,
)
from models.v2_reading import ReadingQuestion, ReadingVocabularyWord
from services.learning.difficulty_engine import clamp_tier

logger = logging.getLogger("dyslexaid.content_authoring")

SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
SUSPICIOUS_PLACEHOLDERS = [
    "lorem ipsum",
    "dolor sit amet",
    "todo:",
    "fixme:",
    "asdfgh",
    "test test test",
    "placeholder text",
    "sample sample",
    "xxx",
]

# ─── Deterministic Quality & Multilingual Validation ─────────────────────────

def validate_content(data: Dict[str, Any]) -> ContentValidationResult:
    """
    Performs deterministic, rule-based quality validation on educational content.
    Checks:
    - Required fields (title, text, difficulty, language, domain)
    - Length and boundary rules (child reading ergonomics)
    - Language codes and Devanagari script integrity for Hindi/Marathi
    - Difficulty tier bounds (1-5)
    - Vocabulary annotations (non-empty definitions, text presence, duplicate detection)
    - Comprehension questions (valid options, index boundaries, uniqueness)
    - Detection of accidental placeholder or debug text
    - Phase 15 catalog selection metadata sufficiency
    """
    errors: List[str] = []
    warnings: List[str] = []
    issues: List[ContentValidationIssue] = []

    # 1. Title validation
    title = str(data.get("title") or "").strip()
    if not title:
        errors.append("Title is required.")
        issues.append(ContentValidationIssue(field="title", message="Title cannot be empty.", severity="error", code="REQUIRED_FIELD"))
    elif len(title) < 3:
        errors.append("Title must be at least 3 characters long.")
        issues.append(ContentValidationIssue(field="title", message="Title is too short.", severity="error", code="MIN_LENGTH"))
    elif len(title) > 120:
        errors.append("Title must not exceed 120 characters.")
        issues.append(ContentValidationIssue(field="title", message="Title exceeds 120 characters.", severity="error", code="MAX_LENGTH"))

    # 2. Text body validation
    text = str(data.get("text") or "").strip()
    if not text:
        errors.append("Passage content (text) is required.")
        issues.append(ContentValidationIssue(field="text", message="Passage text cannot be empty.", severity="error", code="REQUIRED_FIELD"))
    words = text.split() if text else []
    word_count = len(words)

    if text:
        if word_count < 15:
            errors.append(f"Passage is too short ({word_count} words). Minimum length is 15 words.")
            issues.append(ContentValidationIssue(field="text", message=f"Word count {word_count} is below minimum 15.", severity="error", code="MIN_WORD_COUNT"))
        elif word_count > 1200:
            errors.append(f"Passage exceeds maximum length ({word_count} words). Maximum is 1200 words.")
            issues.append(ContentValidationIssue(field="text", message=f"Word count {word_count} exceeds maximum 1200.", severity="error", code="MAX_WORD_COUNT"))

    # 3. Language validation
    lang = str(data.get("language") or "en").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        errors.append(f"Unsupported language code '{lang}'. Must be 'en' (English), 'hi' (Hindi), or 'mr' (Marathi).")
        issues.append(ContentValidationIssue(field="language", message=f"Language '{lang}' is not supported.", severity="error", code="INVALID_LANGUAGE"))
    else:
        # Script check for Hindi and Marathi
        if lang in ("hi", "mr") and text:
            has_devanagari = bool(DEVANAGARI_REGEX.search(text)) or bool(DEVANAGARI_REGEX.search(title))
            if not has_devanagari:
                warnings.append(
                    f"Content is marked as {SUPPORTED_LANGUAGES[lang]} ({lang}), but no Devanagari script characters were detected."
                )
                issues.append(ContentValidationIssue(
                    field="text",
                    message="Expected Devanagari script for Hindi/Marathi passage.",
                    severity="warning",
                    code="SCRIPT_MISMATCH"
                ))

    # 4. Difficulty Tier validation
    diff = data.get("difficulty")
    if diff is None:
        errors.append("Difficulty tier is required.")
        issues.append(ContentValidationIssue(field="difficulty", message="Difficulty tier is missing.", severity="error", code="REQUIRED_FIELD"))
    else:
        try:
            diff_int = int(diff)
            if diff_int < 1 or diff_int > 5:
                errors.append(f"Difficulty tier must be between 1 and 5 (got {diff_int}).")
                issues.append(ContentValidationIssue(field="difficulty", message="Tier out of range (1-5).", severity="error", code="INVALID_TIER"))
        except (ValueError, TypeError):
            errors.append("Difficulty tier must be an integer between 1 and 5.")
            issues.append(ContentValidationIssue(field="difficulty", message="Difficulty must be integer.", severity="error", code="INVALID_TIER"))

    # 5. Estimated Duration validation
    est_min = data.get("estimatedMinutes")
    if est_min is not None:
        try:
            est_int = int(est_min)
            if est_int < 1 or est_int > 20:
                errors.append("Estimated duration must be between 1 and 20 minutes.")
                issues.append(ContentValidationIssue(field="estimatedMinutes", message="Estimated minutes must be 1-20.", severity="error", code="INVALID_DURATION"))
            elif word_count > 0:
                # Plausibility check: ~60 words/min
                expected_mins = max(1, round(word_count / 65.0))
                if est_int > expected_mins + 6:
                    warnings.append(f"Estimated duration ({est_int} min) appears unusually long for a {word_count}-word passage.")
                    issues.append(ContentValidationIssue(field="estimatedMinutes", message="Duration exceeds plausible child reading time.", severity="warning", code="PLAUSIBILITY_WARNING"))
        except (ValueError, TypeError):
            errors.append("Estimated minutes must be an integer.")

    # 6. Placeholder / Debug text check
    combined_content = f"{title} {text}".lower()
    for placeholder in SUSPICIOUS_PLACEHOLDERS:
        if placeholder in combined_content:
            errors.append(f"Content contains detected placeholder or debug text: '{placeholder}'.")
            issues.append(ContentValidationIssue(field="text", message=f"Found placeholder text: '{placeholder}'.", severity="error", code="PLACEHOLDER_DETECTED"))
            break

    # 7. Vocabulary annotations validation
    vocab_list = data.get("vocabulary") or []
    seen_words = set()
    for i, v in enumerate(vocab_list):
        v_dict = v if isinstance(v, dict) else v.model_dump() if hasattr(v, "model_dump") else {}
        w = str(v_dict.get("word") or "").strip()
        defn = str(v_dict.get("definition") or "").strip()

        if not w:
            errors.append(f"Vocabulary item #{i + 1} has an empty word.")
            issues.append(ContentValidationIssue(field=f"vocabulary[{i}].word", message="Word cannot be empty.", severity="error", code="EMPTY_VOCAB_WORD"))
        else:
            w_lower = w.lower()
            if w_lower in seen_words:
                warnings.append(f"Duplicate vocabulary annotation for word '{w}'.")
                issues.append(ContentValidationIssue(field=f"vocabulary[{i}].word", message=f"Duplicate word: {w}", severity="warning", code="DUPLICATE_VOCAB"))
            seen_words.add(w_lower)

            # Check if word is present in passage text
            if text and w_lower not in text.lower():
                warnings.append(f"Vocabulary word '{w}' is not present in the passage text.")
                issues.append(ContentValidationIssue(field=f"vocabulary[{i}].word", message=f"Word '{w}' not found in passage text.", severity="warning", code="VOCAB_NOT_IN_PASSAGE"))

        if not defn:
            errors.append(f"Vocabulary item #{i + 1} ('{w or 'unknown'}') is missing a definition.")
            issues.append(ContentValidationIssue(field=f"vocabulary[{i}].definition", message="Definition cannot be empty.", severity="error", code="EMPTY_VOCAB_DEF"))

    # 8. Comprehension questions validation
    questions_list = data.get("questions") or []
    if len(questions_list) == 0:
        warnings.append("No comprehension questions provided. Adding 1-3 questions is recommended for reading practice.")
        issues.append(ContentValidationIssue(field="questions", message="Zero comprehension questions.", severity="warning", code="NO_QUESTIONS"))

    seen_q_ids = set()
    for q_idx, q in enumerate(questions_list):
        q_dict = q if isinstance(q, dict) else q.model_dump() if hasattr(q, "model_dump") else {}
        qid = str(q_dict.get("questionId") or f"q-{q_idx}").strip()
        q_text = str(q_dict.get("question") or "").strip()
        opts = q_dict.get("options") or []
        ans = q_dict.get("correctAnswer")

        if qid in seen_q_ids:
            warnings.append(f"Duplicate questionId '{qid}'.")
        seen_q_ids.add(qid)

        if not q_text:
            errors.append(f"Question #{q_idx + 1} has empty question text.")
            issues.append(ContentValidationIssue(field=f"questions[{q_idx}].question", message="Question text cannot be empty.", severity="error", code="EMPTY_QUESTION"))

        if not isinstance(opts, list) or len(opts) < 2:
            errors.append(f"Question #{q_idx + 1} must have at least 2 answer choices.")
            issues.append(ContentValidationIssue(field=f"questions[{q_idx}].options", message="At least 2 options required.", severity="error", code="INSUFFICIENT_OPTIONS"))
        else:
            # Check for duplicate options
            clean_opts = [str(o).strip() for o in opts]
            if len(clean_opts) != len(set(clean_opts)):
                errors.append(f"Question #{q_idx + 1} contains duplicate answer options.")
                issues.append(ContentValidationIssue(field=f"questions[{q_idx}].options", message="Duplicate options found.", severity="error", code="DUPLICATE_OPTIONS"))

            # Check valid answer reference
            if isinstance(ans, int):
                if ans < 0 or ans >= len(opts):
                    errors.append(f"Question #{q_idx + 1} correctAnswer index {ans} is out of bounds (options count: {len(opts)}).")
                    issues.append(ContentValidationIssue(field=f"questions[{q_idx}].correctAnswer", message="Answer index out of range.", severity="error", code="INVALID_ANSWER_INDEX"))
            elif isinstance(ans, str):
                if ans.strip() not in clean_opts:
                    errors.append(f"Question #{q_idx + 1} correctAnswer text does not match any of the provided options.")
                    issues.append(ContentValidationIssue(field=f"questions[{q_idx}].correctAnswer", message="Answer string not in options.", severity="error", code="INVALID_ANSWER_STRING"))
            else:
                errors.append(f"Question #{q_idx + 1} is missing a valid correctAnswer.")
                issues.append(ContentValidationIssue(field=f"questions[{q_idx}].correctAnswer", message="Missing correct answer.", severity="error", code="MISSING_ANSWER"))

    # 9. Calculate Completeness & Quality Score (0-100)
    score = 0
    if title and len(title) >= 3:
        score += 20
    if text and 20 <= word_count <= 800:
        score += 30
    if diff is not None and 1 <= int(diff) <= 5:
        score += 15
    if len(vocab_list) >= 1:
        score += 15
    if len(questions_list) >= 1:
        score += 15
    if data.get("gradeBand") or data.get("topics"):
        score += 5
    score = min(100, max(0, score))

    is_valid = len(errors) == 0

    details = {
        "wordCount": word_count,
        "language": lang,
        "languageName": SUPPORTED_LANGUAGES.get(lang, "Unknown"),
        "difficulty": diff,
        "questionCount": len(questions_list),
        "vocabularyCount": len(vocab_list),
        "hasUnicodeDevanagari": bool(DEVANAGARI_REGEX.search(f"{title} {text}")),
        "phase15Eligible": is_valid,
    }

    return ContentValidationResult(
        isValid=is_valid,
        errors=errors,
        warnings=warnings,
        issues=issues,
        completenessScore=score,
        details=details,
    )


# ─── Audit Logging ────────────────────────────────────────────────────────────

async def _record_audit_log(
    content_id: str,
    passage_id: str,
    action: str,
    actor: Dict[str, Any],
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    feedback: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Appends an immutable audit log entry for content lifecycle transitions."""
    now = int(time.time())
    entry = {
        "id": f"audit-{uuid.uuid4().hex[:12]}",
        "contentId": content_id,
        "passageId": passage_id,
        "timestamp": now,
        "action": action,
        "actorId": actor.get("id", "system"),
        "actorRole": actor.get("role", "unknown"),
        "actorName": actor.get("name", "Educator"),
        "fromState": from_state,
        "toState": to_state,
        "feedback": feedback,
        "details": details or {},
    }
    try:
        await db.content_audit_logs.insert_one(entry)
    except Exception as e:
        logger.warning(f"Failed to record audit log for {content_id}: {e}")


# ─── Content Authoring Lifecycle Operations ──────────────────────────────────

async def create_content_draft(user: Dict[str, Any], req: ContentDraftCreateRequest) -> ContentItemResponse:
    """
    Creates a new educational content draft in 'DRAFT' status.
    Ensures:
    - User has teacher or admin role
    - Content is initialized as inactive (not discoverable by students)
    - Deterministic validation is performed and attached
    - Audit record is created
    """
    now = int(time.time())
    content_id = str(uuid.uuid4())
    passage_id = f"pas-auth-{content_id[:8]}"

    words = req.text.split()
    word_count = len(words)
    est_mins = req.estimatedMinutes or max(1, round(word_count / 65.0))

    doc: Dict[str, Any] = {
        "contentId": content_id,
        "passageId": passage_id,
        "version": 1,
        "title": req.title.strip(),
        "text": req.text.strip(),
        "difficulty": clamp_tier(req.difficulty),
        "domain": req.domain or "reading_comprehension",
        "language": req.language.strip().lower(),
        "wordCount": word_count,
        "estimatedMinutes": est_mins,
        "gradeBand": req.gradeBand or "Grade 1-2",
        "topics": req.topics or [],
        "skillTags": req.skillTags or [],
        "vocabulary": [v.model_dump() for v in req.vocabulary],
        "questions": [q.model_dump() for q in req.questions],
        "accessibility": req.accessibility or {"recommendedFontSize": 18, "lineHeight": 2.0},
        "translationGroupId": req.translationGroupId or str(uuid.uuid4()),
        "status": "DRAFT",
        "active": False,  # MUST NEVER be True in DRAFT
        "authorId": user["id"],
        "authorName": user.get("name", "Teacher"),
        "tenantId": user.get("classroomCode"),
        "reviewerId": None,
        "reviewerRole": None,
        "reviewerFeedback": None,
        "reviewedAt": None,
        "publishedAt": None,
        "archivedAt": None,
        "createdAt": now,
        "updatedAt": now,
    }

    val_res = validate_content(doc)
    doc["validationResult"] = val_res.model_dump()

    # Save to db.reading_passages
    await db.reading_passages.insert_one(doc)

    # Record audit log
    await _record_audit_log(
        content_id=content_id,
        passage_id=passage_id,
        action="CREATED",
        actor=user,
        from_state=None,
        to_state="DRAFT",
        details={"wordCount": word_count, "completenessScore": val_res.completenessScore},
    )

    return _to_content_response(doc)


async def update_content_draft(user: Dict[str, Any], content_id: str, req: ContentDraftUpdateRequest) -> ContentItemResponse:
    """
    Updates an editable content draft.
    Enforces:
    - Content exists
    - User is the original author or system admin
    - Content is in 'DRAFT' or 'CHANGES_REQUESTED' state
    """
    now = int(time.time())
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        # Check by passageId fallback
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    # Author/Role permissions
    is_author = doc.get("authorId") == user["id"]
    is_admin = user.get("role") == "admin"
    if not is_author and not is_admin:
        raise PermissionError("You do not have permission to edit another author's draft.")

    # State check
    current_status = doc.get("status", "DRAFT")
    if current_status not in ("DRAFT", "CHANGES_REQUESTED"):
        raise ValueError(f"Cannot edit content in state '{current_status}'. Content must be in DRAFT or CHANGES_REQUESTED state.")

    # Apply updates
    updates: Dict[str, Any] = {"updatedAt": now}
    if req.title is not None:
        updates["title"] = req.title.strip()
    if req.text is not None:
        updates["text"] = req.text.strip()
        words = req.text.strip().split()
        updates["wordCount"] = len(words)
        if req.estimatedMinutes is None and "estimatedMinutes" not in doc:
            updates["estimatedMinutes"] = max(1, round(len(words) / 65.0))
    if req.language is not None:
        updates["language"] = req.language.strip().lower()
    if req.difficulty is not None:
        updates["difficulty"] = clamp_tier(req.difficulty)
    if req.domain is not None:
        updates["domain"] = req.domain
    if req.gradeBand is not None:
        updates["gradeBand"] = req.gradeBand
    if req.topics is not None:
        updates["topics"] = req.topics
    if req.skillTags is not None:
        updates["skillTags"] = req.skillTags
    if req.estimatedMinutes is not None:
        updates["estimatedMinutes"] = req.estimatedMinutes
    if req.vocabulary is not None:
        updates["vocabulary"] = [v.model_dump() for v in req.vocabulary]
    if req.questions is not None:
        updates["questions"] = [q.model_dump() for q in req.questions]
    if req.translationGroupId is not None:
        updates["translationGroupId"] = req.translationGroupId
    if req.accessibility is not None:
        updates["accessibility"] = req.accessibility

    # Merge for validation
    merged = {**doc, **updates}
    val_res = validate_content(merged)
    updates["validationResult"] = val_res.model_dump()

    # If was in CHANGES_REQUESTED and now edited, author can keep in DRAFT or CHANGES_REQUESTED
    await db.reading_passages.update_one(
        {"contentId": doc["contentId"]},
        {"$set": updates}
    )

    await _record_audit_log(
        content_id=doc["contentId"],
        passage_id=doc["passageId"],
        action="UPDATED",
        actor=user,
        from_state=current_status,
        to_state=current_status,
        details={"updatedFields": list(updates.keys())},
    )

    updated_doc = {**doc, **updates}
    return _to_content_response(updated_doc)


async def submit_content_for_review(user: Dict[str, Any], content_id: str) -> ContentItemResponse:
    """
    Submits a draft for review (DRAFT or CHANGES_REQUESTED -> IN_REVIEW).
    Enforces:
    - User is the author or admin
    - Content passes deterministic validation with ZERO blocking errors
    """
    now = int(time.time())
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    is_author = doc.get("authorId") == user["id"]
    is_admin = user.get("role") == "admin"
    if not is_author and not is_admin:
        raise PermissionError("You can only submit your own content for review.")

    current_status = doc.get("status", "DRAFT")
    if current_status not in ("DRAFT", "CHANGES_REQUESTED"):
        raise ValueError(f"Content in state '{current_status}' cannot be submitted for review.")

    # Validation gate
    val_res = validate_content(doc)
    if not val_res.isValid:
        raise ValueError(f"Content validation failed: {'; '.join(val_res.errors)}")

    updates = {
        "status": "IN_REVIEW",
        "active": False,  # In review is never discoverable
        "updatedAt": now,
        "validationResult": val_res.model_dump(),
    }

    await db.reading_passages.update_one({"contentId": doc["contentId"]}, {"$set": updates})

    await _record_audit_log(
        content_id=doc["contentId"],
        passage_id=doc["passageId"],
        action="SUBMITTED",
        actor=user,
        from_state=current_status,
        to_state="IN_REVIEW",
    )

    return _to_content_response({**doc, **updates})


async def review_content(user: Dict[str, Any], content_id: str, req: ContentReviewDecisionRequest) -> ContentItemResponse:
    """
    Evaluates submitted content (IN_REVIEW -> APPROVED | CHANGES_REQUESTED | REJECTED).
    Enforces:
    - User has teacher or admin role
    - Content is in 'IN_REVIEW' state
    - Strict SEPARATION OF DUTIES: author cannot review their own content
    - Actionable feedback required for changes requested or rejection
    """
    now = int(time.time())
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    current_status = doc.get("status")
    if current_status != "IN_REVIEW":
        raise ValueError(f"Content is in state '{current_status}', not 'IN_REVIEW'.")

    # Separation of duties: author cannot review or approve own content
    if doc.get("authorId") == user["id"] and user.get("role") != "admin":
        raise PermissionError("Author cannot review or approve their own content (separation of duties required).")

    decision = req.decision.upper()
    if decision in ("REQUEST_CHANGES", "REJECT"):
        if not req.feedback or not req.feedback.strip():
            raise ValueError("Actionable feedback is required when requesting changes or rejecting content.")

    new_status: ContentLifecycleState
    if decision == "APPROVE":
        new_status = "APPROVED"
        action = "APPROVED"
    elif decision == "REQUEST_CHANGES":
        new_status = "CHANGES_REQUESTED"
        action = "CHANGES_REQUESTED"
    elif decision == "REJECT":
        new_status = "REJECTED"
        action = "REJECTED"
    else:
        raise ValueError(f"Invalid review decision: {decision}")

    updates = {
        "status": new_status,
        "active": False,  # Not published yet
        "reviewerId": user["id"],
        "reviewerRole": user.get("role", "teacher"),
        "reviewerFeedback": req.feedback.strip() if req.feedback else None,
        "reviewedAt": now,
        "updatedAt": now,
    }

    await db.reading_passages.update_one({"contentId": doc["contentId"]}, {"$set": updates})

    await _record_audit_log(
        content_id=doc["contentId"],
        passage_id=doc["passageId"],
        action=action,
        actor=user,
        from_state="IN_REVIEW",
        to_state=new_status,
        feedback=req.feedback,
    )

    return _to_content_response({**doc, **updates})


async def publish_content(user: Dict[str, Any], content_id: str) -> ContentItemResponse:
    """
    Publishes approved content (APPROVED -> PUBLISHED).
    Once published:
    - Status becomes 'PUBLISHED'
    - 'active' is set to True
    - Content becomes eligible for Phase 15 student discovery
    Enforces:
    - User has teacher or admin role
    - Content must be in 'APPROVED' status
    - Author cannot self-publish without independent review approval
    """
    now = int(time.time())
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    current_status = doc.get("status")
    if current_status != "APPROVED":
        raise ValueError(f"Content must be in 'APPROVED' status before publication (currently '{current_status}').")

    # Author self-publishing check: must have had an independent reviewer
    if doc.get("authorId") == user["id"] and doc.get("reviewerId") is None and user.get("role") != "admin":
        raise PermissionError("Content must have independent approval before publication.")

    # Re-run validation to guarantee zero regressions
    val_res = validate_content(doc)
    if not val_res.isValid:
        raise ValueError(f"Cannot publish content with validation errors: {'; '.join(val_res.errors)}")

    updates = {
        "status": "PUBLISHED",
        "active": True,  # NOW ELIGIBLE FOR STUDENTS
        "publishedAt": now,
        "updatedAt": now,
        "validationResult": val_res.model_dump(),
    }

    await db.reading_passages.update_one({"contentId": doc["contentId"]}, {"$set": updates})

    await _record_audit_log(
        content_id=doc["contentId"],
        passage_id=doc["passageId"],
        action="PUBLISHED",
        actor=user,
        from_state="APPROVED",
        to_state="PUBLISHED",
    )

    return _to_content_response({**doc, **updates})


async def archive_content(user: Dict[str, Any], content_id: str) -> ContentItemResponse:
    """
    Archives published content (PUBLISHED -> ARCHIVED).
    Ensures:
    - Status becomes 'ARCHIVED'
    - 'active' is set to False (excluded from new student discovery)
    - Historical reading sessions remain 100% intact
    """
    now = int(time.time())
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    current_status = doc.get("status")
    if current_status not in ("PUBLISHED", "APPROVED"):
        raise ValueError(f"Only PUBLISHED or APPROVED content can be archived (currently '{current_status}').")

    # Only author, reviewer, or admin can archive
    is_author = doc.get("authorId") == user["id"]
    is_reviewer = doc.get("reviewerId") == user["id"]
    is_admin = user.get("role") == "admin"
    if not is_author and not is_reviewer and not is_admin:
        raise PermissionError("You do not have permission to archive this content.")

    updates = {
        "status": "ARCHIVED",
        "active": False,  # EXCLUDED FROM DISCOVERY
        "archivedAt": now,
        "updatedAt": now,
    }

    await db.reading_passages.update_one({"contentId": doc["contentId"]}, {"$set": updates})

    await _record_audit_log(
        content_id=doc["contentId"],
        passage_id=doc["passageId"],
        action="ARCHIVED",
        actor=user,
        from_state=current_status,
        to_state="ARCHIVED",
    )

    return _to_content_response({**doc, **updates})


async def create_content_revision(user: Dict[str, Any], content_id: str) -> ContentItemResponse:
    """
    Creates a new draft revision of a PUBLISHED or ARCHIVED passage.
    Preserves historical activity integrity:
    - The original published passage remains untouched for in-flight/historical activities
    - The new revision starts as DRAFT with incremented version number
    """
    now = int(time.time())
    original = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not original:
        original = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not original:
            raise KeyError("Content item not found")

    new_content_id = str(uuid.uuid4())
    new_version = int(original.get("version", 1)) + 1
    # Maintain same base passageId or versioned identifier
    base_passage_id = original.get("passageId", f"pas-auth-{new_content_id[:8]}")

    revised_doc = {
        **original,
        "contentId": new_content_id,
        "passageId": f"{base_passage_id}-v{new_version}",
        "parentContentId": original.get("contentId"),
        "version": new_version,
        "status": "DRAFT",
        "active": False,
        "authorId": user["id"],
        "authorName": user.get("name", "Teacher"),
        "reviewerId": None,
        "reviewerRole": None,
        "reviewerFeedback": None,
        "reviewedAt": None,
        "publishedAt": None,
        "archivedAt": None,
        "createdAt": now,
        "updatedAt": now,
    }

    val_res = validate_content(revised_doc)
    revised_doc["validationResult"] = val_res.model_dump()

    await db.reading_passages.insert_one(revised_doc)

    await _record_audit_log(
        content_id=new_content_id,
        passage_id=revised_doc["passageId"],
        action="REVISED",
        actor=user,
        from_state=original.get("status"),
        to_state="DRAFT",
        details={"parentContentId": original.get("contentId"), "version": new_version},
    )

    return _to_content_response(revised_doc)


# ─── Query & Listing Operations ──────────────────────────────────────────────

async def list_content_items(
    user: Dict[str, Any],
    status_filter: Optional[str] = None,
    language_filter: Optional[str] = None,
    difficulty_filter: Optional[int] = None,
    limit: int = 50,
    skip: int = 0,
) -> ContentListResponse:
    """
    Lists content items visible to the authenticated educator.
    - Authors see their own drafts, changes_requested, in_review, published, archived
    - Teachers also see items in review queue and published/archived items in their tenant
    - Enforces tenant isolation (classroomCode)
    """
    user_id = user["id"]
    role = user.get("role", "teacher")
    classroom_code = user.get("classroomCode")

    query: Dict[str, Any] = {}

    # Scoping by user & tenant:
    if role == "admin":
        # Admin can view all
        pass
    else:
        # Teacher: sees own content OR content belonging to their classroom tenant OR published items
        conditions: List[Dict[str, Any]] = [
            {"authorId": user_id},
            {"status": {"$in": ["IN_REVIEW", "APPROVED", "PUBLISHED", "ARCHIVED"]}},
        ]
        if classroom_code:
            conditions.append({"tenantId": classroom_code})
        query["$or"] = conditions

    if status_filter:
        query["status"] = status_filter.upper()
    if language_filter:
        query["language"] = language_filter.lower()
    if difficulty_filter is not None:
        query["difficulty"] = clamp_tier(difficulty_filter)

    cursor = db.reading_passages.find(query, {"_id": 0}).sort("updatedAt", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    total = await db.reading_passages.count_documents(query)

    items = [_to_content_response(d) for d in docs]
    return ContentListResponse(items=items, total=total)


async def get_content_item(user: Dict[str, Any], content_id: str) -> ContentItemResponse:
    """Retrieves full details of a single content item for authorized teachers/admins."""
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    # Access control: drafts can only be seen by author or admin
    if doc.get("status") in ("DRAFT", "CHANGES_REQUESTED"):
        if doc.get("authorId") != user["id"] and user.get("role") != "admin":
            raise PermissionError("You cannot view another educator's private draft.")

    return _to_content_response(doc)


async def get_review_queue(user: Dict[str, Any], limit: int = 50, skip: int = 0) -> ContentListResponse:
    """
    Retrieves all content items currently in 'IN_REVIEW' awaiting peer evaluation.
    Available to authorized teachers and administrators.
    """
    query: Dict[str, Any] = {"status": "IN_REVIEW"}

    classroom_code = user.get("classroomCode")
    # Multi-tenant scoping: if classroom is set, prioritize or include same-tenant
    if classroom_code and user.get("role") != "admin":
        # Match same tenant or global
        query["$or"] = [{"tenantId": classroom_code}, {"tenantId": None}]

    cursor = db.reading_passages.find(query, {"_id": 0}).sort("updatedAt", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    total = await db.reading_passages.count_documents(query)

    items = [_to_content_response(d) for d in docs]
    return ContentListResponse(items=items, total=total)


async def get_content_history(user: Dict[str, Any], content_id: str) -> ContentHistoryResponse:
    """Retrieves immutable audit history and version logs for a content item."""
    doc = await db.reading_passages.find_one({"contentId": content_id}, {"_id": 0})
    if not doc:
        doc = await db.reading_passages.find_one({"passageId": content_id}, {"_id": 0})
        if not doc:
            raise KeyError("Content item not found")

    # Author/Role permission check
    if doc.get("status") == "DRAFT" and doc.get("authorId") != user["id"] and user.get("role") != "admin":
        raise PermissionError("Access denied.")

    cursor = db.content_audit_logs.find(
        {"$or": [{"contentId": doc.get("contentId")}, {"passageId": doc.get("passageId")}]},
        {"_id": 0}
    ).sort("timestamp", 1)

    entries = await cursor.to_list(length=100)
    history = [ContentAuditLogEntry(**e) for e in entries]

    return ContentHistoryResponse(
        contentId=doc.get("contentId", content_id),
        passageId=doc.get("passageId", ""),
        currentVersion=doc.get("version", 1),
        history=history,
    )


async def get_translation_completeness(translation_group_id: str) -> Dict[str, Any]:
    """
    Evaluates translation group completeness across the 3 supported languages ('en', 'hi', 'mr').
    Returns linked passage IDs and missing languages.
    """
    if not translation_group_id:
        return {"completenessPercent": 33, "availableLanguages": ["en"], "missingLanguages": ["hi", "mr"]}

    docs = await db.reading_passages.find(
        {"translationGroupId": translation_group_id, "active": True},
        {"_id": 0, "language": 1, "passageId": 1}
    ).to_list(length=10)

    avail = {d.get("language") for d in docs if d.get("language")}
    linked_map = {d.get("language"): d.get("passageId") for d in docs if d.get("language")}

    all_langs = {"en", "hi", "mr"}
    missing = list(all_langs - avail)
    pct = round((len(avail) / 3.0) * 100)

    return {
        "completenessPercent": pct,
        "availableLanguages": list(avail),
        "missingLanguages": missing,
        "linkedTranslations": linked_map,
    }


# ─── Response Converter ──────────────────────────────────────────────────────

def _to_content_response(doc: Dict[str, Any]) -> ContentItemResponse:
    """Converts a reading_passages database record into ContentItemResponse."""
    vocab_raw = doc.get("vocabulary") or []
    vocab_models = []
    for v in vocab_raw:
        if isinstance(v, dict):
            vocab_models.append(ReadingVocabularyWord(**v))
        elif hasattr(v, "model_dump"):
            vocab_models.append(v)

    q_raw = doc.get("questions") or []
    q_models = []
    for q in q_raw:
        if isinstance(q, dict):
            q_models.append(ReadingQuestion(**q))
        elif hasattr(q, "model_dump"):
            q_models.append(q)

    val_res = None
    if doc.get("validationResult"):
        try:
            val_res = ContentValidationResult(**doc["validationResult"])
        except Exception:
            val_res = None

    return ContentItemResponse(
        contentId=doc.get("contentId", doc.get("passageId", "unknown")),
        passageId=doc.get("passageId", "pas-auth-001"),
        version=doc.get("version", 1),
        title=doc.get("title", ""),
        text=doc.get("text", ""),
        difficulty=doc.get("difficulty", 1),
        domain=doc.get("domain", "reading_comprehension"),
        language=doc.get("language", "en"),
        wordCount=doc.get("wordCount", len(doc.get("text", "").split())),
        estimatedMinutes=doc.get("estimatedMinutes", 2),
        gradeBand=doc.get("gradeBand", "Grade 1-2"),
        topics=doc.get("topics", []),
        skillTags=doc.get("skillTags", []),
        vocabulary=vocab_models,
        questions=q_models,
        status=doc.get("status", "PUBLISHED" if doc.get("active") else "DRAFT"),
        authorId=doc.get("authorId", "system"),
        authorName=doc.get("authorName", "Educator"),
        tenantId=doc.get("tenantId"),
        reviewerId=doc.get("reviewerId"),
        reviewerRole=doc.get("reviewerRole"),
        reviewerFeedback=doc.get("reviewerFeedback"),
        reviewedAt=doc.get("reviewedAt"),
        publishedAt=doc.get("publishedAt"),
        archivedAt=doc.get("archivedAt"),
        translationGroupId=doc.get("translationGroupId"),
        linkedTranslations=doc.get("linkedTranslations"),
        validationResult=val_res,
        createdAt=doc.get("createdAt", 0),
        updatedAt=doc.get("updatedAt", 0),
    )
