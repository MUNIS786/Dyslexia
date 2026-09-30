"""
backend/models/v2_teacher_analytics.py — Pydantic Schemas for V2 Teacher Analytics.

Provides structured response models for:
- Classroom overview & cohort performance aggregation
- Individual learner deep-dive analytics (profile, adaptive tier, reading, speech)
- Longitudinal progress trend analysis with explicit insufficient-data rules
- Descriptive educational insights and actionable instructional next steps

IMPORTANT:
These models support descriptive educational analytics ONLY.
They do NOT provide or imply medical, psychological, or clinical dyslexia diagnoses.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProgressTrendPoint(BaseModel):
    """Single chronological time point for performance trend visualization."""
    timestamp: int
    date: str
    comprehensionScore: Optional[float] = None
    speechAccuracy: Optional[float] = None
    activityScore: Optional[float] = None
    difficultyTier: Optional[int] = None


class ProgressTrendSummary(BaseModel):
    """Longitudinal trend evaluation across core educational modalities."""
    readingTrend: str = Field(
        default="insufficient_data",
        description="'improving' | 'stable' | 'declining' | 'insufficient_data'"
    )
    speechTrend: str = Field(
        default="insufficient_data",
        description="'improving' | 'stable' | 'declining' | 'insufficient_data'"
    )
    adaptiveTrend: str = Field(
        default="insufficient_data",
        description="'improving' | 'stable' | 'declining' | 'insufficient_data'"
    )
    points: List[ProgressTrendPoint] = Field(default_factory=list)


class DomainPerformanceItem(BaseModel):
    """Individual cognitive/learning domain score from the Phase 2 profile."""
    domainKey: str
    domainName: str
    score: float = Field(ge=0.0, le=100.0)
    label: str
    description: Optional[str] = None
    isStrength: bool = False
    isPracticeArea: bool = False


class TeacherInsight(BaseModel):
    """Descriptive, non-clinical educational observation grounded in learner data."""
    id: str
    category: str = Field(..., description="'reading' | 'speech' | 'adaptive' | 'engagement'")
    type: str = Field(default="info", description="'info' | 'success' | 'warning'")
    title: str
    description: str
    evidence: Optional[str] = None


class TeacherAction(BaseModel):
    """Recommended pedagogical instructional step for the teacher."""
    id: str
    category: str = Field(default="review", description="'review' | 'practice' | 'assign' | 'discuss'")
    label: str
    description: str
    target: Optional[str] = None


class LearnerAnalyticsSummary(BaseModel):
    """Compact learner row for teacher class roster view."""
    studentId: str
    name: str
    email: str
    learningLevel: int = Field(default=2, ge=1, le=5)
    learningLevelName: str = "Developing"
    adaptiveTier: int = Field(default=1, ge=1, le=5)
    screeningCompleted: bool = False
    avgComprehension: float = 0.0
    speechAccuracy: Optional[float] = None
    wordsPerMinute: Optional[float] = None
    totalSessions: int = 0
    wordsRead: int = 0
    streak: int = 0
    lastActive: str = "Never"
    status: str = Field(default="progressing", description="'needs_attention' | 'progressing' | 'on_track' | 'not_screened'")
    strengths: List[str] = Field(default_factory=list)
    practiceAreas: List[str] = Field(default_factory=list)
    readingTrend: str = "insufficient_data"


class ClassOverviewMetrics(BaseModel):
    """Class-wide aggregate performance metrics."""
    totalLearners: int = 0
    activeLearners: int = 0
    screenedLearners: int = 0
    needsAttentionCount: int = 0
    onTrackCount: int = 0
    avgLearningLevel: float = 0.0
    avgAdaptiveTier: float = 1.0
    avgReadingComprehension: float = 0.0
    avgSpeechAccuracy: float = 0.0
    avgWordsPerMinute: float = 0.0
    totalWordsRead: int = 0
    totalMinutesRead: float = 0.0
    activityAttemptsCount: int = 0


class ClassAnalyticsResponse(BaseModel):
    """Full class overview payload for teacher dashboard."""
    classroomCode: str
    classroomName: Optional[str] = None
    timeRange: str = "all"
    overview: ClassOverviewMetrics
    learners: List[LearnerAnalyticsSummary] = Field(default_factory=list)
    commonPracticeAreas: List[Dict[str, Any]] = Field(default_factory=list)
    classInsights: List[TeacherInsight] = Field(default_factory=list)


class LearnerAnalyticsDetail(BaseModel):
    """Complete multi-domain drill-down for an individual authorized learner."""
    studentId: str
    name: str
    email: str
    classroomCode: str
    learningLevel: int
    learningLevelName: str
    adaptiveTier: int
    screeningCompleted: bool
    confidence: Optional[Dict[str, Any]] = None
    strengths: List[Dict[str, Any]] = Field(default_factory=list)
    practiceAreas: List[Dict[str, Any]] = Field(default_factory=list)
    domainScores: List[DomainPerformanceItem] = Field(default_factory=list)
    readingMetrics: Dict[str, Any] = Field(default_factory=dict)
    speechSignals: Dict[str, Any] = Field(default_factory=dict)
    adaptiveState: Dict[str, Any] = Field(default_factory=dict)
    recentReadingSessions: List[Dict[str, Any]] = Field(default_factory=list)
    recentActivityAttempts: List[Dict[str, Any]] = Field(default_factory=list)
    trends: ProgressTrendSummary
    insights: List[TeacherInsight] = Field(default_factory=list)
    suggestedActions: List[TeacherAction] = Field(default_factory=list)
