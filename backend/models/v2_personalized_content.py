"""
backend/models/v2_personalized_content.py — Pydantic Schemas for Phase 15 Personalized Learning Content Engine.

Provides clean data contracts for:
- Deterministic, explainable personalized activity selection matching Zone of Proximal Development (ZPD)
- Support for controlled activity types: Guided Reading, Difficult-Word Practice, Reading Comprehension,
  Vocabulary Practice, Oral Reading / Speech, and Skill Review
- Safe multilingual language matching with honest, explicit fallbacks for Marathi & Hindi
- Activity launch telemetry tracking distinguishing launch from confirmed completion
- Teacher and parent educational views respecting role authorization and privacy
"""
from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field

# Supported activity types
ActivityType = Literal[
    "GUIDED_READING",
    "DIFFICULT_WORD_PRACTICE",
    "READING_COMPREHENSION",
    "VOCABULARY_PRACTICE",
    "ORAL_READING_SPEECH",
    "SKILL_REVIEW",
]

# Content availability & language matching status
ContentAvailabilityStatus = Literal[
    "EXACT_MATCH",
    "LANGUAGE_FALLBACK_OFFERED",
    "INSUFFICIENT_DATA",
    "UNAVAILABLE",
]


class PersonalizedContentItem(BaseModel):
    """An individual educational learning activity curated for the student."""
    activityId: str = Field(..., description="Unique activity identifier (e.g. act-phon-001 or pas-t1-001)")
    activityType: ActivityType = Field(..., description="Educational activity type")
    contentId: str = Field(..., description="Underlying passage ID or micro-activity ID")
    title: str = Field(..., description="Child-friendly activity title")
    description: Optional[str] = Field(None, description="Short summary of what the learner will do")
    language: str = Field("en", description="Language of the content ('en', 'mr', 'hi')")
    requestedLanguage: str = Field("en", description="Original language requested by the learner")
    difficultyTier: int = Field(1, ge=1, le=5, description="Adaptive difficulty tier (1=Foundation to 5=Fluent)")
    tierName: str = Field("Foundation", description="Descriptive tier name")
    estimatedDurationMinutes: int = Field(5, ge=1, le=30, description="Estimated completion duration in minutes")
    reason: str = Field(..., description="Transparent, child-friendly explanation of why this activity was chosen")
    detailedRationale: Optional[str] = Field(None, description="Extended pedagogical rationale for educators")
    recommendationId: Optional[str] = Field(None, description="Linked Phase 14 recommendation ID if applicable")
    category: Optional[str] = Field(None, description="Matching Phase 14 category (e.g. READING_PRACTICE)")
    targetSkills: List[str] = Field(default_factory=list, description="Target cognitive or phonics skills")
    targetWords: List[str] = Field(default_factory=list, description="Specific vocabulary or tricky words in focus")
    contentSummary: Optional[str] = Field(None, description="Safe snippet or prompt preview without private notes")
    instructions: Optional[str] = Field(None, description="Student-facing instructions")
    actionUrl: str = Field(..., description="Frontend destination route to execute activity")
    actionLabel: str = Field("Start Activity", description="Call-to-action button label")
    completed: bool = Field(False, description="Whether this activity was genuinely completed today")
    availabilityStatus: ContentAvailabilityStatus = Field("EXACT_MATCH", description="Language and availability match status")
    languageFallbackMessage: Optional[str] = Field(None, description="Honest explanation if fallback language was used")
    accessibilityConfig: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Recommended display & typography presets")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Non-sensitive pedagogical metadata")


class PersonalizedActivityNextResponse(BaseModel):
    """The immediate next best personalized activity for the authenticated student."""
    learnerId: str
    activity: Optional[PersonalizedContentItem] = None
    currentAdaptiveTier: int = 1
    currentAdaptiveTierName: str = "Foundation"
    preferredLanguage: str = "en"
    hasContent: bool = True
    status: ContentAvailabilityStatus = "EXACT_MATCH"
    message: Optional[str] = None
    generatedAt: str
    disclaimer: str = (
        "This activity is selected based on your recent practice and active learning level. "
        "It does not constitute a medical, psychological, or clinical diagnosis."
    )


class PersonalizedActivitiesListResponse(BaseModel):
    """List of available personalized activities matching the student's level and language."""
    learnerId: str
    count: int = 0
    activities: List[PersonalizedContentItem] = Field(default_factory=list)
    currentAdaptiveTier: int = 1
    currentAdaptiveTierName: str = "Foundation"
    preferredLanguage: str = "en"
    generatedAt: str


class PersonalizedContentLaunchRequest(BaseModel):
    """Payload sent when a student launches an activity from recommendations or activity hub."""
    activityId: str = Field(..., description="ID of the activity being launched")
    activityType: Optional[str] = Field(None, description="Type of the activity")
    recommendationId: Optional[str] = Field(None, description="Optional linked Phase 14 recommendation ID")
    language: Optional[str] = Field(None, description="Selected language for activity")


class PersonalizedContentLaunchResponse(BaseModel):
    """Telemetry response acknowledging activity launch without prematurely marking completion."""
    launchId: str
    learnerId: str
    activityId: str
    activityType: str
    destinationUrl: str
    launchedAt: int
    completed: bool = False
    status: str = "launched"


class TeacherPersonalizedContentResponse(BaseModel):
    """Teacher view of a student's active personalized learning content and pedagogical suitability."""
    learnerId: str
    studentName: Optional[str] = None
    currentAdaptiveTier: int = 1
    currentAdaptiveTierName: str = "Foundation"
    recommendedActivity: Optional[PersonalizedContentItem] = None
    availableActivitiesCount: int = 0
    pedagogicalRationale: str = Field(..., description="Pedagogical justification grounded in recent evidence")
    evidenceSummary: List[str] = Field(default_factory=list, description="Supporting longitudinal signals")


class ParentPersonalizedContentResponse(BaseModel):
    """Parent view of child-friendly at-home practice activity."""
    learnerId: str
    studentName: Optional[str] = None
    suggestedActivityTitle: str
    suggestedActivityType: str
    estimatedMinutes: int = 10
    atHomeGuidance: str
    focusWords: List[str] = Field(default_factory=list)
