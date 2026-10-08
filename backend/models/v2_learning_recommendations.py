"""
backend/models/v2_learning_recommendations.py — Pydantic Schemas for Phase 14 Recommendations & Study Plan.

Provides clean data contracts for:
- Student personalized learning recommendations & daily study plans
- Teacher learner recommended focus & evidence summaries
- Parent at-home reading suggestions & support tips
- Controlled recommendation categories, explainable rationales, and data sufficiency flags
"""
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field

# Controlled recommendation categories
RecommendationCategory = Literal[
    "READING_PRACTICE",
    "DIFFICULT_WORD_PRACTICE",
    "SPEECH_PRACTICE",
    "REVIEW",
    "STRETCH",
    "CONSISTENCY",
]

# Explainable evidence confidence (non-clinical)
RecommendationConfidence = Literal["high", "medium", "low", "insufficient_data"]

# Data sufficiency indicators (aligned with Phase 13)
DataSufficiencyStatus = Literal["no_data", "insufficient_data", "sufficient_data"]


class StudyPlanItem(BaseModel):
    """An individual activity item within the student's study plan."""
    id: str = Field(..., description="Unique activity item identifier")
    activityType: str = Field(..., description="Controlled category e.g. READING_PRACTICE")
    title: str = Field(..., description="Child-friendly activity title")
    reason: str = Field(..., description="Clear, non-clinical explanation of why this activity is recommended")
    estimatedDurationMinutes: int = Field(..., description="Estimated completion duration in minutes (e.g. 5, 10, 15)")
    priority: int = Field(..., description="Priority sequence (1 = top priority)")
    actionUrl: str = Field(..., description="Frontend navigation route e.g. /student/reading-coach")
    targetSkill: Optional[str] = Field(None, description="Key target skill e.g. phoneme_blending")
    targetWords: Optional[List[str]] = Field(default_factory=list, description="Specific vocabulary or tricky words")
    completed: bool = Field(False, description="Whether this activity was completed today based on real session records")
    sourceEvidence: Optional[str] = Field(None, description="Underlying pedagogical signal or evidence summary")


class RecommendationItem(BaseModel):
    """An actionable, ranked recommendation card with explainable rationale."""
    id: str = Field(..., description="Unique recommendation ID")
    category: str = Field(..., description="Controlled category (READING_PRACTICE, DIFFICULT_WORD_PRACTICE, etc.)")
    title: str = Field(..., description="Child-friendly recommendation title")
    reason: str = Field(..., description="Short child-friendly 'Why?' explanation")
    detailedExplanation: Optional[str] = Field(None, description="Extended educational explanation")
    actionUrl: str = Field(..., description="Destination route to launch practice")
    actionLabel: str = Field("Start Practice", description="Button call-to-action label")
    estimatedDurationMinutes: int = Field(5, description="Estimated duration in minutes")
    confidence: RecommendationConfidence = Field("medium", description="Confidence based on available evidence")
    priority: int = Field(1, description="Relative ranking priority (1 = highest)")
    targetSkill: Optional[str] = None
    targetWords: Optional[List[str]] = Field(default_factory=list)
    completed: bool = False
    evidenceSignals: Optional[List[str]] = Field(default_factory=list, description="Observable signals that motivated this card")


class StudyPlan(BaseModel):
    """Lightweight daily or 7-day personalized study plan."""
    horizon: str = Field("today", description="Planning horizon: 'today' or '7d'")
    items: List[StudyPlanItem] = Field(default_factory=list, description="Bounded list of 2-4 activities")
    totalEstimatedMinutes: int = Field(0, description="Sum of estimated durations")
    completedCount: int = Field(0, description="Number of items completed today")
    totalCount: int = Field(0, description="Total number of items in plan")


class StudentRecommendationsResponse(BaseModel):
    """Top-level student response containing recommendations, daily plan, and level status."""
    learnerId: str
    horizon: str = "today"
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    studyPlan: StudyPlan
    currentLearningLevel: Union[int, str] = 1
    currentLearningLevelName: str = "Foundation"
    currentAdaptiveTier: Union[int, str] = 1
    currentAdaptiveTierName: str = "Foundation"
    dataSufficiency: DataSufficiencyStatus = "sufficient_data"
    dataSufficiencyMessage: Optional[str] = None
    generatedAt: str
    disclaimer: str = (
        "These recommendations provide personalized educational practice priorities based on your "
        "recent reading activity. They do not constitute a medical, psychological, or clinical diagnosis."
    )


class TeacherLearnerRecommendationsResponse(BaseModel):
    """Teacher view of an individual student's recommended focus and supporting evidence."""
    learnerId: str
    studentName: Optional[str] = None
    currentLearningLevel: Union[int, str] = 1
    currentAdaptiveTier: Union[int, str] = 1
    recommendedFocus: str = Field(..., description="Primary learning focus area")
    primaryReason: str = Field(..., description="Pedagogical rationale grounded in recent evidence")
    priority: int = 1
    recentEvidence: List[str] = Field(default_factory=list, description="Key metrics and historical observations")
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    studyPlan: StudyPlan
    dataSufficiency: DataSufficiencyStatus = "sufficient_data"


class ParentLearnerRecommendationsResponse(BaseModel):
    """Parent view of suggested home practice and supportive reading tips."""
    learnerId: str
    studentName: Optional[str] = None
    suggestedPracticeAtHome: str = Field(..., description="Encouraging summary of suggested reading practice")
    recommendedMinutes: int = Field(10, description="Suggested daily reading time at home")
    focusWords: List[str] = Field(default_factory=list, description="Gentle tricky words to review together")
    parentTips: List[str] = Field(default_factory=list, description="Supportive at-home reading encouragement tips")
    dataSufficiency: DataSufficiencyStatus = "sufficient_data"
