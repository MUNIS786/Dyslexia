"""
backend/models/v2_learning_insights.py — Pydantic Schemas for Phase 13: Learning Insights & Progress Reports.

Provides models for:
- Student progress summaries, metrics, and data sufficiency
- Longitudinal trend calculations (accuracy, speed, speech, consistency)
- Timeline series for accessible charting
- Teacher class-wide learning insights overview and learner cards
- Simplified, jargon-free parent progress insights
- Non-clinical educational safeguards
"""
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    NEEDS_ATTENTION = "needs_attention"
    INSUFFICIENT_DATA = "insufficient_data"


class DataSufficiencyStatus(str, Enum):
    NO_DATA = "no_data"
    INSUFFICIENT_DATA = "insufficient_data"
    SUFFICIENT_DATA = "sufficient_data"


class MetricTrend(BaseModel):
    """Encapsulates change over time for an educational metric."""
    model_config = ConfigDict(populate_by_name=True)

    metric: str = Field(..., description="Metric key (e.g. reading_accuracy, reading_speed, speech_accuracy, practice_consistency)")
    currentValue: Optional[float] = Field(default=None, description="Average in current reporting window")
    previousValue: Optional[float] = Field(default=None, description="Average in previous baseline window")
    change: Optional[float] = Field(default=None, description="Difference between current and previous values")
    unit: str = Field(default="%", description="Display unit (%, WPM, days, sessions)")
    direction: TrendDirection = Field(default=TrendDirection.INSUFFICIENT_DATA, description="Calculated trajectory")
    label: str = Field(..., description="Short child-friendly label, e.g. 'Improving (+5%)'")
    message: str = Field(..., description="Encouraging explanatory sentence")


class TimelineDataPoint(BaseModel):
    """Historical data point for accessible time-series progress charts."""
    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    timestamp: int = Field(..., description="Epoch timestamp of date")
    readingAccuracy: Optional[float] = Field(default=None, description="Comprehension/reading accuracy percentage")
    wordsRead: int = Field(default=0, description="Total words read on this date")
    readingSpeedWpm: Optional[float] = Field(default=None, description="Average words per minute")
    activitiesCompleted: int = Field(default=0, description="Number of sessions or tasks finished")
    speechAccuracy: Optional[float] = Field(default=None, description="Average speech word accuracy percentage")


class StudentProgressSummary(BaseModel):
    """Aggregated learning metrics for a student over a selected time period."""
    model_config = ConfigDict(populate_by_name=True)

    learnerId: str = Field(..., description="Student user ID")
    reportingPeriod: str = Field(default="30d", description="Window length: 7d, 30d, 90d")
    periodStart: int = Field(default=0, description="Epoch start timestamp of window")
    periodEnd: int = Field(default=0, description="Epoch end timestamp of window")

    currentLearningLevel: Union[int, str] = Field(default=1, description="Adaptive learning level 1-5")
    currentLearningLevelName: str = Field(default="Foundation", description="Descriptive educational level label")
    currentAdaptiveTier: Union[int, str] = Field(default=1, description="Active ZPD difficulty tier 1-5")
    currentAdaptiveTierName: str = Field(default="Foundation", description="Tier name")

    readingSessionsCount: int = Field(default=0, description="Number of reading coach sessions completed in period")
    readingWordsAttempted: int = Field(default=0, description="Total words attempted across passages")
    readingAccuracyAvg: Optional[float] = Field(default=None, description="Average comprehension accuracy percentage")
    readingSpeedWpmAvg: Optional[float] = Field(default=None, description="Average words per minute")

    speechAccuracyAvg: Optional[float] = Field(default=None, description="Average speech word match accuracy")
    speechCoverageAvg: Optional[float] = Field(default=None, description="Average speech passage coverage percentage")
    practiceScoreAvg: Optional[float] = Field(default=None, description="Blended reading practice score")

    activePracticeDays: int = Field(default=0, description="Number of distinct days with practice activity")
    currentStreak: int = Field(default=0, description="Current consecutive practice days streak")
    completedLearningActivities: int = Field(default=0, description="Interactive micro-tasks completed in period")

    difficultWordsCount: int = Field(default=0, description="Number of unique difficult words tapped")
    difficultWordsTop: List[str] = Field(default_factory=list, description="Top vocabulary words for ongoing review")

    dataSufficiency: DataSufficiencyStatus = Field(default=DataSufficiencyStatus.NO_DATA)
    dataSufficiencyMessage: str = Field(default="", description="Child-friendly explanation of data state")


class StudentInsightsResponse(BaseModel):
    """Primary response envelope for student learning insights."""
    model_config = ConfigDict(populate_by_name=True)

    learnerId: Optional[str] = Field(default=None, description="Student user ID")
    reportingPeriod: str = Field(default="30d", description="Reporting period 7d/30d/90d")
    dataSufficiency: DataSufficiencyStatus = Field(default=DataSufficiencyStatus.NO_DATA, description="Sufficiency status")
    sufficiencyMessage: str = Field(default="", description="Child-friendly sufficiency explanation")
    summary: StudentProgressSummary
    trends: Dict[str, MetricTrend] = Field(default_factory=dict, description="Keyed by metric name")
    timeline: List[TimelineDataPoint] = Field(default_factory=list, description="Daily aggregated history for charts")
    strengths: List[str] = Field(default_factory=list, description="Data-backed positive practice observations")
    focusAreas: List[str] = Field(default_factory=list, description="Gentle suggestions for next practice sessions")
    recommendedNextAction: str = Field(default="daily_reading", description="Actionable next step recommendation")
    activeInterventionsCount: int = Field(default=0, description="Count of ongoing educational support activities")
    disclaimer: str = Field(
        default="Educational Progress Indicator: These insights track practice consistency and learning progress. They do not constitute a medical, psychological, or clinical diagnosis."
    )


class LearnerInsightCardItem(BaseModel):
    """Summary item for a single student in class-wide teacher reports."""
    model_config = ConfigDict(populate_by_name=True)

    studentId: str
    studentName: str
    level: Union[int, str] = 1
    tier: Union[int, str] = 1
    overallTrend: TrendDirection = TrendDirection.INSUFFICIENT_DATA
    readingAccuracy: Optional[float] = None
    accuracyTrend: TrendDirection = TrendDirection.INSUFFICIENT_DATA
    readingSpeedWpm: Optional[float] = None
    activeDays: int = 0
    sessionsCount: int = 0
    needsAttention: bool = False
    lastActive: Optional[str] = None
    topStrength: Optional[str] = None
    topFocusArea: Optional[str] = None


class ClassInsightsOverviewResponse(BaseModel):
    """Cohort insights summary for educators."""
    model_config = ConfigDict(populate_by_name=True)

    classroomCode: str
    reportingPeriod: str = "30d"
    totalStudents: int = 0
    improvingCount: int = 0
    stableCount: int = 0
    needsAttentionCount: int = 0
    insufficientDataCount: int = 0

    averageAccuracy: Optional[float] = None
    averageSpeedWpm: Optional[float] = None

    topStrengths: List[str] = Field(default_factory=list)
    commonFocusAreas: List[str] = Field(default_factory=list)
    students: List[LearnerInsightCardItem] = Field(default_factory=list)

    disclaimer: str = Field(
        default="Descriptive Classroom Analytics: Insights are educational observations to support personalized instruction. They do not represent clinical diagnoses."
    )


class ParentInsightsResponse(BaseModel):
    """Jargon-free, supportive learning insights for parents and guardians."""
    model_config = ConfigDict(populate_by_name=True)

    studentId: str
    studentName: str
    reportingPeriod: str = "30d"
    learningLevelName: str = "Foundation"
    practiceConsistencyMessage: str
    readingAccuracyTrend: TrendDirection
    readingTrendMessage: str
    activePracticeDays: int = 0
    currentStreak: int = 0
    totalWordsRead: int = 0
    strengths: List[str] = Field(default_factory=list)
    homeSupportTips: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Parent Practice Indicator: These notes share reading engagement and encouragement tips. They are non-clinical educational observations."
    )
