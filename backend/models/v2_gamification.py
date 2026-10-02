"""
backend/models/v2_gamification.py — V2 Gamification & Positive Engagement Models.

Provides models and validation schemas for:
- Transparent, effort-based reward events and auditable point ledger
- Dyslexia-friendly achievement badges and milestone definitions
- Practice streak metrics with encouraging, non-shaming streak calculations
- Reward notification payloads and learner reward summaries
"""
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ─── Achievement Catalogue Models ───────────────────────────────────────────

class BadgeDefinition(BaseModel):
    """Static metadata defining an unlockable achievement."""
    badgeId: str = Field(..., description="Unique badge identifier, e.g. 'first_steps'")
    title: str = Field(..., description="Child-friendly title")
    description: str = Field(..., description="Clear, encouraging description of requirements")
    icon: str = Field(..., description="Child-friendly icon emoji or visual symbol")
    category: str = Field(default="practice", description="'milestone' | 'reading' | 'practice' | 'vocabulary' | 'comprehension' | 'streak' | 'points'")
    threshold: int = Field(..., ge=1, description="Numerical threshold required to unlock")
    metricKey: str = Field(..., description="Telemetry metric evaluated for this badge")
    repeatable: bool = Field(default=False, description="Whether badge can be awarded repeatedly")


class EarnedBadge(BaseModel):
    """Represents an achievement badge unlocked by a learner."""
    badgeId: str
    title: str
    description: str = ""
    icon: str = "🏅"
    category: str = "general"
    unlockedAt: int = Field(default_factory=lambda: int(time.time()), description="Epoch seconds when unlocked")


class BadgeProgressItem(BaseModel):
    """Achievement item enriched with real-time learner progress toward completion."""
    badgeId: str
    title: str
    description: str
    icon: str
    category: str
    threshold: int
    currentProgress: int = 0
    progressPercent: float = 0.0
    unlocked: bool = False
    unlockedAt: Optional[int] = None


# ─── Reward Event & Ledger Models ───────────────────────────────────────────

VALID_EVENT_TYPES = {
    "activity_attempt",
    "reading_session",
    "bonus_comprehension",
    "bonus_completion",
    "practice_milestone",
    "manual_observation",
}


class RewardEvent(BaseModel):
    """Auditable, immutable record of points awarded for a verified learning event."""
    eventId: str = Field(..., description="Unique reward event identifier, e.g. 'rew_abc123'")
    learnerId: str = Field(..., description="Student user ID who earned the reward")
    sourceEventId: str = Field(..., description="Unique source event identifier for idempotency, e.g. attemptId or sessionId")
    eventType: str = Field(..., description="Type of learning event")
    points: int = Field(..., ge=1, le=50, description="Server-determined points awarded")
    description: str = Field(..., description="Encouraging, child-friendly description of what was accomplished")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual info (scores, passageId, domain)")
    createdAt: int = Field(default_factory=lambda: int(time.time()))

    @field_validator("eventType")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid eventType '{v}'. Allowed: {sorted(list(VALID_EVENT_TYPES))}")
        return v


# ─── Milestone Models ────────────────────────────────────────────────────────

class MilestoneProgressItem(BaseModel):
    """Child-friendly milestone target encouraging next practice steps."""
    milestoneId: str
    title: str
    description: str
    icon: str
    current: int
    target: int
    progressPercent: float
    completed: bool


# ─── Learner Gamification Summary ────────────────────────────────────────────

class GamificationSummary(BaseModel):
    """Aggregate rewards summary returned to the student rewards view."""
    learnerId: str
    totalPoints: int = 0
    currentStreak: int = 0
    longestStreak: int = 0
    lastActiveDate: Optional[str] = None
    streakMessage: str = "Keep learning at your own pace!"
    earnedBadgesCount: int = 0
    totalBadgesCount: int = 0
    recentBadges: List[EarnedBadge] = Field(default_factory=list)
    recentEvents: List[Dict[str, Any]] = Field(default_factory=list)
    updatedAt: int = Field(default_factory=lambda: int(time.time()))


class GamificationHistoryResponse(BaseModel):
    """Bounded, paginated reward ledger entries."""
    learnerId: str
    totalEvents: int
    page: int = 1
    limit: int = 20
    events: List[Dict[str, Any]] = Field(default_factory=list)


# ─── Activity Completion Reward Payload ──────────────────────────────────────

class RewardEvaluationResult(BaseModel):
    """Payload attached to activity completion responses when gamification is active."""
    pointsAwarded: int = 0
    totalPoints: int = 0
    newBadges: List[EarnedBadge] = Field(default_factory=list)
    currentStreak: int = 0
    streakMaintained: bool = False
    celebrationMessage: Optional[str] = None
    isDuplicate: bool = False
