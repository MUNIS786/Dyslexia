"""
backend/models/v2_content_authoring.py — Pydantic Schemas for Phase 16:
Learning Content Authoring & Quality Management.

Defines schemas for:
- Content Lifecycle State machine (DRAFT, IN_REVIEW, CHANGES_REQUESTED, APPROVED, PUBLISHED, ARCHIVED, REJECTED)
- Deterministic Quality Validation & Multilingual checks
- Content Authoring Draft Creation, Editing, Review, and Publishing
- Audit trail, Versioning, and Separation-of-Duties records

IMPORTANT:
These models support educational content authoring and quality management.
They do NOT represent clinical, diagnostic, or medical assessment claims.
"""
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field

from models.v2_reading import ReadingQuestion, ReadingVocabularyWord

ContentLifecycleState = Literal[
    "DRAFT",
    "IN_REVIEW",
    "CHANGES_REQUESTED",
    "APPROVED",
    "PUBLISHED",
    "ARCHIVED",
    "REJECTED",
]


class ContentValidationIssue(BaseModel):
    """Specific error or warning identified during deterministic quality validation."""
    field: Optional[str] = Field(default=None, description="Field name where the issue was detected")
    message: str = Field(..., description="Actionable explanation of the issue")
    severity: Literal["error", "warning"] = Field(..., description="'error' blocks submission; 'warning' is informational")
    code: Optional[str] = Field(default=None, description="Standard machine-readable error code")


class ContentValidationResult(BaseModel):
    """Comprehensive validation output detailing quality checks, completeness, and suitability."""
    isValid: bool = Field(..., description="True if and only if zero blocking errors were found")
    errors: List[str] = Field(default_factory=list, description="List of blocking error messages")
    warnings: List[str] = Field(default_factory=list, description="List of non-blocking warning messages")
    issues: List[ContentValidationIssue] = Field(default_factory=list, description="Structured issues")
    completenessScore: int = Field(default=0, ge=0, le=100, description="Quality & completeness score 0-100")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata statistics: wordCount, language, etc.")


class ContentDraftCreateRequest(BaseModel):
    """Payload to initiate a new educational content draft."""
    title: str = Field(..., description="Engaging, child-friendly title (3-120 characters)")
    text: str = Field(..., description="Passage body text")
    language: str = Field(default="en", description="Supported language: 'en', 'hi', or 'mr'")
    difficulty: int = Field(default=1, ge=1, le=5, description="Difficulty tier (1=Foundation to 5=Advanced)")
    domain: str = Field(default="reading_comprehension", description="Educational domain targeted")
    gradeBand: Optional[str] = Field(default="Grade 1-2", description="Target grade band or age group")
    topics: List[str] = Field(default_factory=list, description="Topics/themes, e.g. ['animals', 'nature']")
    skillTags: List[str] = Field(default_factory=list, description="Target skill tags, e.g. ['cvc_words', 'inference']")
    estimatedMinutes: Optional[int] = Field(default=None, ge=1, le=20, description="Estimated reading duration in minutes")
    vocabulary: List[ReadingVocabularyWord] = Field(default_factory=list, description="Difficult-word annotations")
    questions: List[ReadingQuestion] = Field(default_factory=list, description="Comprehension questions")
    translationGroupId: Optional[str] = Field(default=None, description="UUID linking translated equivalents across languages")
    accessibility: Dict[str, Any] = Field(default_factory=dict, description="Recommended display presets")


class ContentDraftUpdateRequest(BaseModel):
    """Payload to update an existing editable draft (DRAFT or CHANGES_REQUESTED)."""
    title: Optional[str] = None
    text: Optional[str] = None
    language: Optional[str] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    domain: Optional[str] = None
    gradeBand: Optional[str] = None
    topics: Optional[List[str]] = None
    skillTags: Optional[List[str]] = None
    estimatedMinutes: Optional[int] = Field(default=None, ge=1, le=20)
    vocabulary: Optional[List[ReadingVocabularyWord]] = None
    questions: Optional[List[ReadingQuestion]] = None
    translationGroupId: Optional[str] = None
    accessibility: Optional[Dict[str, Any]] = None


class ContentReviewDecisionRequest(BaseModel):
    """Payload submitted by an authorized reviewer/peer when evaluating submitted content."""
    decision: Literal["APPROVE", "REQUEST_CHANGES", "REJECT"] = Field(..., description="Review outcome")
    feedback: Optional[str] = Field(default=None, description="Actionable reviewer comments (mandatory if requesting changes or rejecting)")
    notes: Optional[str] = Field(default=None, description="Optional internal editorial notes")


class ContentAuditLogEntry(BaseModel):
    """Immutable audit record for content lifecycle state transitions."""
    id: str = Field(..., description="Unique audit event ID")
    timestamp: int = Field(..., description="Epoch seconds timestamp")
    action: str = Field(..., description="Action taken, e.g. 'CREATED', 'SUBMITTED', 'APPROVED', 'PUBLISHED'")
    actorId: str = Field(..., description="User ID who performed the action")
    actorRole: str = Field(..., description="Role of the actor at time of action")
    actorName: Optional[str] = Field(default=None, description="Display name of the actor")
    fromState: Optional[str] = Field(default=None, description="Previous lifecycle state")
    toState: Optional[str] = Field(default=None, description="New lifecycle state")
    feedback: Optional[str] = Field(default=None, description="Review feedback or change notes")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context metadata")


class ContentItemResponse(BaseModel):
    """Complete content document response for authorized educators and reviewers."""
    contentId: str = Field(..., description="Authoring system unique content UUID")
    passageId: str = Field(..., description="Catalog-compatible passage identifier, e.g. 'pas-auth-...'")
    version: int = Field(default=1, description="Version number of this content")
    title: str = Field(..., description="Passage title")
    text: str = Field(..., description="Passage body text")
    difficulty: int = Field(default=1, ge=1, le=5, description="Difficulty tier (1-5)")
    domain: str = Field(default="reading_comprehension")
    language: str = Field(default="en", description="Language code: en, hi, mr")
    wordCount: int = Field(default=0, description="Calculated word count")
    estimatedMinutes: int = Field(default=2, description="Estimated duration in minutes")
    gradeBand: Optional[str] = Field(default="Grade 1-2")
    topics: List[str] = Field(default_factory=list)
    skillTags: List[str] = Field(default_factory=list)
    vocabulary: List[ReadingVocabularyWord] = Field(default_factory=list)
    questions: List[ReadingQuestion] = Field(default_factory=list)
    status: ContentLifecycleState = Field(default="DRAFT", description="Current lifecycle state")
    authorId: str = Field(..., description="User ID of author")
    authorName: Optional[str] = Field(default=None, description="Author display name")
    tenantId: Optional[str] = Field(default=None, description="Classroom code or school tenant identifier")
    reviewerId: Optional[str] = Field(default=None, description="Reviewer ID if evaluated")
    reviewerRole: Optional[str] = Field(default=None)
    reviewerFeedback: Optional[str] = Field(default=None, description="Latest reviewer feedback")
    reviewedAt: Optional[int] = Field(default=None)
    publishedAt: Optional[int] = Field(default=None)
    archivedAt: Optional[int] = Field(default=None)
    translationGroupId: Optional[str] = Field(default=None)
    linkedTranslations: Optional[Dict[str, str]] = Field(default=None, description="Map of lang -> passageId for translations")
    validationResult: Optional[ContentValidationResult] = Field(default=None)
    createdAt: int = Field(default=0)
    updatedAt: int = Field(default=0)


class ContentListResponse(BaseModel):
    """Paginated or filtered list of authored content items."""
    items: List[ContentItemResponse] = Field(default_factory=list)
    total: int = Field(default=0)


class ContentHistoryResponse(BaseModel):
    """Audit timeline and version history for a content item."""
    contentId: str = Field(...)
    passageId: str = Field(...)
    currentVersion: int = Field(default=1)
    history: List[ContentAuditLogEntry] = Field(default_factory=list)
