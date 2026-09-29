"""
backend/models/v2_learning_state.py — Pydantic Schemas for V2 Adaptive Learning Engine.

Data models for:
- Learning Activities (micro-tasks catalog)
- Activity Attempts & interaction telemetry
- Adaptive State & Progression (ZPD, Tiers 1-5, streak, consecutive passes/fails)
- Adaptive Recommendations & Pedagogical Rationale
- Tier Calibration Parameters
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class LearningActivity(BaseModel):
    """Catalog micro-task definition for dyslexia-tailored learning activities."""
    id: str = Field(..., description="Unique activity identifier (e.g. act-phon-001)")
    title: str = Field(..., description="Child-friendly title")
    domain: str = Field(..., description="Cognitive/educational domain targeted")
    difficultyTier: int = Field(default=1, ge=1, le=5, description="Difficulty tier (1=Foundation to 5=Advanced)")
    targetSkills: List[str] = Field(default_factory=list, description="Specific skills practiced")
    contentPayload: Dict[str, Any] = Field(..., description="Interactive challenge data, prompts, options, assets")
    durationSecondsExpected: int = Field(default=120, description="Expected time in seconds")
    isActive: bool = Field(default=True, description="Whether activity is available in catalog")


class ActivityAttemptCreate(BaseModel):
    """Input payload from frontend upon completing an interactive micro-task."""
    activityId: str = Field(..., description="ID of the attempted activity")
    scorePercent: float = Field(..., ge=0.0, le=100.0, description="Student score percentage (0-100)")
    durationSeconds: int = Field(..., ge=0, description="Time taken in seconds")
    hesitationCount: int = Field(default=0, ge=0, description="Number of prolonged pauses or hesitations detected")
    hintsRequested: int = Field(default=0, ge=0, description="Number of hints requested by student")
    completed: bool = Field(default=True, description="Whether student completed the activity")
    mistakes: Optional[List[Dict[str, Any]]] = Field(default=None, description="Details of incorrect attempts for remediation")


class ActivityAttempt(BaseModel):
    """Persisted attempt record with telemetry and adaptation outcomes."""
    id: str = Field(..., description="Attempt UUID")
    learnerId: str = Field(..., description="Student UUID")
    activityId: str = Field(..., description="Activity ID")
    domain: str = Field(..., description="Target domain of the activity")
    difficultyTier: int = Field(..., ge=1, le=5)
    scorePercent: float = Field(..., ge=0.0, le=100.0)
    durationSeconds: int = Field(..., ge=0)
    hesitationCount: int = Field(default=0)
    hintsRequested: int = Field(default=0)
    completedAt: int = Field(..., description="Unix timestamp of completion")
    adaptationTriggered: bool = Field(default=False)
    previousTier: int = Field(default=1)
    newTier: int = Field(default=1)


class AdaptiveStateInfo(BaseModel):
    """Real-time progression state within the Zone of Proximal Development."""
    learnerId: str
    activeDifficultyTier: int = Field(default=1, ge=1, le=5)
    tierName: str = Field(default="Foundation")
    currentModule: str = Field(default="reading_foundations")
    todayTasksAssigned: int = Field(default=4)
    todayTasksCompleted: int = Field(default=0)
    currentStreak: int = Field(default=0)
    lastSessionTimestamp: Optional[int] = None
    consecutivePasses: int = Field(default=0)
    consecutiveFailures: int = Field(default=0)
    rollingComprehensionScores: List[float] = Field(default_factory=list)
    recommendedNextAction: str = Field(default="daily_reading_practice")
    adaptationTriggerDue: bool = Field(default=False)
    lastAdaptationReason: Optional[str] = None
    updatedAt: int


class AdaptiveRecommendation(BaseModel):
    """Curated activity recommendation with explainable pedagogical rationale."""
    id: str
    activity: LearningActivity
    targetDomain: str
    difficultyTier: int
    rationale: str = Field(..., description="Explainable rationale: why this activity is recommended")
    confidenceScore: float = Field(default=0.85)
    matchType: str = Field(default="practice_area", description="'practice_area' | 'strength_reinforcement'")


class TierCalibration(BaseModel):
    """Readability and UI parameters calibrated for each difficulty tier."""
    tier: int
    name: str
    description: str
    maxSentenceLength: int
    vocabularyComplexity: str
    scaffoldingLevel: str
    allowedHints: int
    timeLimitMultiplier: float


class AdaptiveAttemptResponse(BaseModel):
    """Response returned to the frontend after submitting an activity attempt."""
    status: str = "ok"
    attemptId: str
    scorePercent: float
    adaptationTriggered: bool
    previousTier: int
    currentTier: int
    tierChanged: bool
    celebration: bool
    message: str
    streak: int
    learningState: Dict[str, Any]
