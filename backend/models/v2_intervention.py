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
from typing import Optional, List, Dict, Any, Set, Union
from pydantic import BaseModel, Field, field_validator, model_validator


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
    id: Optional[str] = None
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

    @model_validator(mode="before")
    @classmethod
    def populate_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("id") and data.get("interventionId"):
                data["id"] = data["interventionId"]
            elif not data.get("interventionId") and data.get("id"):
                data["interventionId"] = data["id"]
        return data

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_INTERVENTION_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed: {sorted(list(VALID_INTERVENTION_STATUSES))}")
        return v


# ─── Request Models ──────────────────────────────────────────────────────────

class InterventionCreateRequest(BaseModel):
    """Payload to create and establish baseline for a learning support activity."""
    learnerId: Optional[str] = Field(default=None, description="Student user ID")
    studentId: Optional[str] = Field(default=None, description="Alias for learnerId")
    goal: Optional[str] = Field(default=None, min_length=3, max_length=200, description="Educational goal")
    title: Optional[str] = Field(default=None, min_length=3, max_length=200, description="Alias for goal")
    targetDomain: Optional[str] = Field(default=None, min_length=2, max_length=100, description="Target learning domain")
    targetArea: Optional[str] = Field(default=None, min_length=2, max_length=100, description="Alias for targetDomain")
    supportActivity: Optional[str] = Field(default=None, min_length=3, max_length=500, description="Description of support activity")
    description: Optional[str] = Field(default=None, min_length=3, max_length=500, description="Alias for supportActivity")
    tier: Optional[int] = Field(default=None, ge=1, le=5)
    startDate: Optional[Union[int, str]] = Field(default=None, description="Start epoch timestamp or ISO string")
    durationWeeks: Optional[int] = None
    plannedReviewDate: Optional[Union[int, str]] = Field(default=None, description="Optional planned review date")
    initialNotes: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("learnerId") and data.get("studentId"):
                data["learnerId"] = data["studentId"]
            if not data.get("goal") and data.get("title"):
                data["goal"] = data["title"]
            if not data.get("targetDomain") and data.get("targetArea"):
                data["targetDomain"] = data["targetArea"]
            if not data.get("supportActivity") and data.get("description"):
                data["supportActivity"] = data["description"]
            # Convert string dates to epoch timestamps
            sd = data.get("startDate")
            if isinstance(sd, str):
                try:
                    data["startDate"] = int(time.mktime(time.strptime(sd[:10], "%Y-%m-%d")))
                except Exception:
                    data["startDate"] = int(time.time())
            prd = data.get("plannedReviewDate")
            if isinstance(prd, str):
                try:
                    data["plannedReviewDate"] = int(time.mktime(time.strptime(prd[:10], "%Y-%m-%d")))
                except Exception:
                    data["plannedReviewDate"] = None
        return data

    @field_validator("plannedReviewDate")
    @classmethod
    def validate_dates(cls, v: Optional[Union[int, str]], info) -> Optional[Union[int, str]]:
        if v is not None and isinstance(v, (int, float)):
            start = info.data.get("startDate")
            if start is not None and isinstance(start, (int, float)) and v < start:
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
    metricName: str = Field(default="reading_accuracy")
    value: float = Field(default=85.0)
    unit: Optional[str] = "%"
    scale: Optional[str] = "0-100%"
    source: Optional[str] = "teacher_observed_assessment"
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_measurement(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "metricName" not in data or not data.get("metricName"):
                if "accuracy" in data:
                    data["metricName"] = "reading_accuracy"
                    data["value"] = float(data["accuracy"])
                elif "wpm" in data:
                    data["metricName"] = "words_per_minute"
                    data["value"] = float(data["wpm"])
                    data["unit"] = "wpm"
                    data["scale"] = "words_per_minute"
                elif "comprehension" in data:
                    data["metricName"] = "reading_comprehension_accuracy"
                    data["value"] = float(data["comprehension"])
                elif "score" in data:
                    data["metricName"] = "performance_score"
                    data["value"] = float(data["score"])
                else:
                    data["metricName"] = "general_progress"
            if "value" not in data:
                for k in ("accuracy", "comprehension", "score", "wpm"):
                    if k in data:
                        data["value"] = float(data[k])
                        break
        return data


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
