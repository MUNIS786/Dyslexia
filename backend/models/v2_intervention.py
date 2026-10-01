"""
backend/models/v2_intervention.py — Pydantic Schemas for V2 Intervention Effectiveness.

Defines schemas for:
- Support Activity & Intervention tracking
- Baseline measurements grounded in existing learner data
- Follow-up measurements collected during support activity
- Descriptive metric comparison (absolute & relative change, neutral non-clinical interpretation)
- Teacher-authored observations and controlled lifecycle state transitions

IMPORTANT NOTICE:
This is a descriptive educational measurement system. It does NOT claim that an
intervention caused an improvement, nor does it provide clinical or diagnostic claims.
"""
import time
import uuid
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field, field_validator


# Controlled Lifecycle Statuses
VALID_INTERVENTION_STATUSES: Set[str] = {
    "planned",
    "active",
    "review",
    "completed",
    "cancelled",
}

# Controlled State Transitions
ALLOWED_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
    "planned": {"active", "cancelled"},
    "active": {"review", "completed", "cancelled"},
    "review": {"active", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

# Comparison Outcome Labels
COMPARISON_STATUS_LABELS: Set[str] = {
    "improved_on_measure",
    "declined_on_measure",
    "no_material_change",
    "insufficient_data",
    "not_comparable",
}


class BaselineMeasurement(BaseModel):
    """Historical baseline established from existing learner practice data prior to intervention start."""
    metricName: str = Field(..., description="Unique metric identifier, e.g. reading_comprehension_accuracy")
    displayName: str = Field(..., description="Teacher-friendly metric title")
    value: Optional[float] = Field(default=None, description="Numeric baseline score or None if insufficient")
    unit: str = Field(default="%", description="Unit of measurement, e.g. %, wpm, score")
    scale: str = Field(default="0-100%", description="Scale range, e.g. 0-100%, words_per_minute")
    source: str = Field(..., description="Data source: reading_sessions | speech_reading_analyses | activity_attempts | learner_profiles")
    periodStart: Optional[int] = None
    periodEnd: Optional[int] = None
    observationCount: int = Field(default=0, ge=0, description="Number of observed attempts or sessions")
    status: str = Field(default="insufficient_data", description="'sufficient' | 'insufficient_data'")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FollowUpMeasurement(BaseModel):
    """Subsequent measurement collected after support activity start date."""
    measurementId: str = Field(default_factory=lambda: f"meas_{uuid.uuid4().hex[:10]}")
    interventionId: str
    metricName: str
    displayName: str
    value: float
    unit: str = "%"
    scale: str = "0-100%"
    source: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    periodStart: Optional[int] = None
    periodEnd: Optional[int] = None
    observationCount: int = Field(default=1, ge=1)
    meetsComparisonRules: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TeacherObservation(BaseModel):
    """Pedagogical observation or review note authored by the authorized teacher."""
    observationId: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:8]}")
    teacherId: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    stage: str = Field(default="active_checkin", description="'planning' | 'active_checkin' | 'review' | 'completion'")
    notes: str = Field(..., min_length=1)


class V2Intervention(BaseModel):
    """Complete persisted intervention record."""
    interventionId: str = Field(..., description="Unique identifier, e.g. intv_a1b2c3d4")
    teacherId: str = Field(..., description="Creator teacher user ID")
    learnerId: str = Field(..., description="Target student user ID")
    classroomCode: str = Field(..., description="Authorized classroom code")
    goal: str = Field(..., min_length=3, description="Educational learning goal")
    targetDomain: str = Field(..., description="Learning domain, e.g. reading_comprehension")
    supportActivity: str = Field(..., min_length=3, description="Description of educational support activity")
    startDate: int = Field(..., description="Epoch timestamp in seconds")
    plannedReviewDate: Optional[int] = Field(default=None, description="Optional review epoch timestamp")
    status: str = Field(default="planned", description="'planned' | 'active' | 'review' | 'completed' | 'cancelled'")
    baselineMeasurements: List[BaselineMeasurement] = Field(default_factory=list)
    followUpMeasurements: List[FollowUpMeasurement] = Field(default_factory=list)
    teacherObservations: List[TeacherObservation] = Field(default_factory=list)
    createdAt: int = Field(default_factory=lambda: int(time.time()))
    updatedAt: int = Field(default_factory=lambda: int(time.time()))

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_INTERVENTION_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed: {sorted(list(VALID_INTERVENTION_STATUSES))}")
        return v


# ─── Request Models ──────────────────────────────────────────────────────────

class InterventionCreateRequest(BaseModel):
    """Payload to create and establish baseline for a learning support activity."""
    learnerId: str = Field(..., min_length=1, description="Student user ID")
    goal: str = Field(..., min_length=3, max_length=200, description="Educational goal")
    targetDomain: str = Field(..., min_length=2, max_length=100, description="Target learning domain")
    supportActivity: str = Field(..., min_length=3, max_length=500, description="Description of support activity")
    startDate: Optional[int] = Field(default=None, description="Start epoch timestamp in seconds")
    plannedReviewDate: Optional[int] = Field(default=None, description="Optional planned review date in seconds")
    initialNotes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("plannedReviewDate")
    @classmethod
    def validate_dates(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None:
            start = info.data.get("startDate")
            if start is not None and v < start:
                raise ValueError("plannedReviewDate cannot be earlier than startDate.")
        return v


class InterventionUpdateRequest(BaseModel):
    """Payload for partial updates to planned or active intervention."""
    goal: Optional[str] = Field(default=None, min_length=3, max_length=200)
    targetDomain: Optional[str] = Field(default=None, min_length=2, max_length=100)
    supportActivity: Optional[str] = Field(default=None, min_length=3, max_length=500)
    plannedReviewDate: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class InterventionTransitionRequest(BaseModel):
    """Payload to transition status (e.g. start, review, complete, cancel)."""
    notes: Optional[str] = Field(default=None, max_length=1000, description="Teacher review or stage observation")
    reviewDecision: Optional[str] = Field(
        default=None,
        description="Optional decision note: 'continue' | 'complete' | 'adjust_support' | 'cancel'"
    )


class ManualFollowUpRequest(BaseModel):
    """Optional payload if teacher records an interim assessment observation."""
    metricName: str
    value: float
    unit: Optional[str] = "%"
    scale: Optional[str] = "0-100%"
    source: Optional[str] = "teacher_observed_assessment"
    notes: Optional[str] = None


# ─── Comparison & Effectiveness Report Models ────────────────────────────────

class MetricComparison(BaseModel):
    """Structured before-and-after comparison for a single metric."""
    metricName: str
    metricDisplayName: str
    targetDomain: str
    unit: str
    scale: str
    direction: str = Field(default="higher_is_better", description="'higher_is_better' | 'lower_is_better'")
    baselineValue: Optional[float] = None
    baselineObservations: int = 0
    baselinePeriod: Optional[str] = None
    baselineStatus: str = Field(default="insufficient_data", description="'sufficient' | 'insufficient_data'")
    followUpValue: Optional[float] = None
    followUpObservations: int = 0
    followUpPeriod: Optional[str] = None
    followUpStatus: str = Field(default="insufficient_data", description="'sufficient' | 'insufficient_data'")
    absoluteChange: Optional[float] = None
    relativeChangePercent: Optional[float] = None
    status: str = Field(
        ...,
        description="'improved_on_measure' | 'declined_on_measure' | 'no_material_change' | 'insufficient_data' | 'not_comparable'"
    )
    thresholdUsed: Optional[float] = None
    interpretation: str = Field(..., description="Neutral, descriptive summary of observed data association")


class InterventionEffectivenessReport(BaseModel):
    """Comprehensive effectiveness analysis report returned to the teacher."""
    interventionId: str
    goal: str
    targetDomain: str
    supportActivity: str
    status: str
    learnerId: str
    learnerName: Optional[str] = None
    startDate: int
    plannedReviewDate: Optional[int] = None
    comparisons: List[MetricComparison] = Field(default_factory=list)
    dataSufficiency: str = Field(
        default="insufficient_data",
        description="'sufficient' | 'insufficient_baseline' | 'insufficient_followup' | 'insufficient_data'"
    )
    overallSummary: str
    teacherObservations: List[TeacherObservation] = Field(default_factory=list)
    disclaimer: str = Field(
        default="This educational measurement system provides descriptive comparisons of observed learner practice data over time. It does not establish clinical efficacy or prove that the support activity caused the observed changes."
    )
