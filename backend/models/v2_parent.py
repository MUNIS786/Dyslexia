"""
backend/models/v2_parent.py — V2 Parent & Guardian Portal Data Models.

Defines schemas for:
- Parent link state and verified relationships
- One-time cryptographic link invitation tokens
- Parent dashboard aggregations (learning overview, reading sessions, gamification)
- Sincere, supportive home practice suggestions
- Explicit educational, non-clinical disclaimers
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

# Valid relationship statuses
ParentLinkStatus = Literal["pending", "active", "rejected", "revoked", "expired"]


class ParentLinkItem(BaseModel):
    """Safe, public representation of a parent-student relationship."""
    id: str
    studentId: str
    studentName: str
    relationship: str = "parent"
    status: ParentLinkStatus = "active"
    requestedAt: int
    verifiedAt: Optional[int] = None
    createdAt: int


class ParentProfileSummary(BaseModel):
    """Parent user profile and linked children summary."""
    id: str
    name: str
    email: str
    role: str = "parent"
    linkedLearnersCount: int = 0
    pendingRequestsCount: int = 0
    preferredLanguage: str = "en"


class ClaimCodeRequest(BaseModel):
    """Parent enters a verified invitation code to link with their child."""
    code: str = Field(..., min_length=6, max_length=32, description="Short-lived invitation code")
    relationship: Optional[str] = Field("parent", description="Relationship type (e.g. parent, guardian)")


class LinkRequestCreate(BaseModel):
    """Parent initiates a link request using student's email or student ID."""
    studentIdentifier: str = Field(..., min_length=2, max_length=120, description="Student email or user ID")
    relationship: Optional[str] = Field("parent", description="Relationship type")


class InvitationCreateResponse(BaseModel):
    """Response returned when a student or teacher generates a parent link invitation code."""
    invitationCode: str
    expiresAt: int
    studentId: str
    studentName: str
    success: bool = True
    message: str = "Share this code with your parent or guardian. It expires in 48 hours."


class HomePracticeSuggestion(BaseModel):
    """Encouraging, supportive, non-clinical activity suggestion for families at home."""
    id: str
    title: str
    description: str
    category: str = "shared_reading"  # shared_reading, routine, celebration, phonics_game
    practicalTip: str


class ParentRecentSession(BaseModel):
    """Summarized reading session for parent view (excludes raw audio/transcripts)."""
    id: Optional[str] = None
    title: str
    difficultyTier: int = 1
    wordsRead: int = 0
    comprehensionScore: Optional[float] = None
    durationMinutes: float = 0.0
    date: str
    timestamp: int


class ParentRecentActivity(BaseModel):
    """Summarized adaptive learning task attempt."""
    id: Optional[str] = None
    domain: str
    scorePercent: float
    difficultyTier: int = 1
    date: str
    timestamp: int


class ParentLearningOverview(BaseModel):
    """Aggregated learning indicators across reading, adaptive practice, and streaks."""
    totalReadingMinutes: float = 0.0
    storiesCompleted: int = 0
    avgComprehensionScore: Optional[float] = None
    adaptiveActivitiesCompleted: int = 0
    currentDifficultyTier: int = 1
    currentStreak: int = 0
    longestStreak: int = 0
    totalPoints: int = 0
    badgesEarnedCount: int = 0


class ParentProgressTrend(BaseModel):
    """Longitudinal learning trends over time with descriptive explanation."""
    readingTrend: str = "insufficient_data"  # improving, stable, declining, insufficient_data
    adaptiveTrend: str = "insufficient_data"
    speechTrend: str = "insufficient_data"
    points: List[Dict[str, Any]] = Field(default_factory=list)
    trendExplanation: str = (
        "Learning progress develops at a natural, individual pace. Practice consistency is the most effective driver of long-term reading confidence."
    )


class ParentDashboardResponse(BaseModel):
    """Complete, authorized parent dashboard payload for a selected child."""
    parent: ParentProfileSummary
    selectedLearner: Optional[ParentLinkItem] = None
    linkedLearners: List[ParentLinkItem] = Field(default_factory=list)
    overview: Optional[ParentLearningOverview] = None
    recentReadingSessions: List[ParentRecentSession] = Field(default_factory=list)
    recentAdaptiveActivities: List[ParentRecentActivity] = Field(default_factory=list)
    gamificationSummary: Optional[Dict[str, Any]] = None
    trends: Optional[ParentProgressTrend] = None
    homeSuggestions: List[HomePracticeSuggestion] = Field(default_factory=list)
    disclaimer: str = (
        "DyslexAid progress summaries reflect recorded learning practice and effort to encourage positive reading habits at home. They are educational observations, not a clinical or medical diagnosis."
    )
    hasLinkedLearners: bool = True
