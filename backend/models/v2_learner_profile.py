"""
backend/models/v2_learner_profile.py — Pydantic models for the V2 Learner Profile.

IMPORTANT:
These models provide educational and screening indicators to tailor assistive
learning accommodations. They do NOT provide or represent medical or clinical diagnoses.
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class DyslexiaIndicators(BaseModel):
    primary_profile: Optional[str] = Field(default=None, description="Primary screening classification (e.g. Phonological Dyslexia)")
    subtype_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Estimated probability distribution across subtypes (0.0 to 1.0)"
    )
    confidence: Optional[float] = Field(default=None, description="Diagnostic confidence percentage (0 to 100)")


class DomainScores(BaseModel):
    phonological_awareness: Optional[float] = 0.0
    phonological_memory: Optional[float] = 0.0
    rapid_naming: Optional[float] = 0.0
    letter_reversal: Optional[float] = 0.0
    reading_fluency: Optional[float] = 0.0
    orthographic_spelling: Optional[float] = 0.0
    reading_comprehension: Optional[float] = 0.0
    motor_writing: Optional[float] = 0.0
    visual_processing: Optional[float] = 0.0
    visual_attention: Optional[float] = 0.0
    language_processing: Optional[float] = 0.0
    processing_speed: Optional[float] = 0.0
    working_memory: Optional[float] = 0.0


class StrengthItem(BaseModel):
    domain: str
    score: float
    label: str = "Strength"
    friendly_name: str
    description: str


class PracticeAreaItem(BaseModel):
    domain: str
    score: float
    priority: str = "medium"  # high | medium | low
    friendly_name: str
    description: str
    suggested_activity_type: str


class LearningLevelInfo(BaseModel):
    level: int = Field(default=1, ge=1, le=5, description="Educational level from 1 (Foundation) to 5 (Advanced)")
    name: str = "Foundation"
    description: str = "Starting your reading journey with foundational letter sounds and word shapes."
    calculated_at: int = 0
    inputs: Dict[str, Any] = Field(default_factory=dict)


class ProfileConfidence(BaseModel):
    overall: float = 0.0
    screening: float = 0.0
    performance: float = 0.0
    screening_questions_answered: int = 0
    scored_domains_count: int = 0


class CognitiveIndicators(BaseModel):
    working_memory: str = Field(default="standard", description="Indicator: strong | standard | needs_scaffolding")
    visual_processing: str = Field(default="standard", description="Indicator: strong | standard | needs_scaffolding")
    auditory_processing: str = Field(default="standard", description="Indicator: strong | standard | needs_scaffolding")
    processing_speed: str = Field(default="standard", description="Indicator: typical | extended_time_beneficial")


class ReadingMetrics(BaseModel):
    reading_level: str = "standard"
    comprehension_level: int = 0
    vocabulary_level: str = "standard"
    avg_words_per_minute: float = 0.0
    words_mastered: int = 0


class AccessibilityPreferences(BaseModel):
    font: str = "OpenDyslexic"
    font_size: int = 18
    line_spacing: float = 2.0
    letter_spacing: float = 0.12
    bg_color: str = "#FFF8F0"
    text_color: str = "#1A2A2A"
    tts_speed: float = 0.85
    tts_language: str = "en-IN"
    highlight_words: bool = True
    syllable_split: bool = True
    auto_simplify: bool = True


class AdaptiveDifficulty(BaseModel):
    active_tier: int = Field(default=1, ge=1, le=5, description="Difficulty tier between 1 and 5")
    max_sentence_length: int = 12
    vocabulary_complexity: str = "controlled"
    scaffolding_level: str = "standard"


class GoalItem(BaseModel):
    id: str
    title: str
    completed: bool = False


class V2LearnerProfile(BaseModel):
    learner_id: str
    display_name: Optional[str] = None
    schema_version: int = 2
    screening_completed: bool = False
    learning_level: LearningLevelInfo = Field(default_factory=LearningLevelInfo)
    current_level: Optional[str] = "moderate"  # backward compat
    risk_level: Optional[str] = "Moderate"     # backward compat
    dyslexia_indicators: DyslexiaIndicators = Field(default_factory=DyslexiaIndicators)
    domain_scores: DomainScores = Field(default_factory=DomainScores)
    domain_interpretations: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    cognitive_indicators: CognitiveIndicators = Field(default_factory=CognitiveIndicators)
    strengths: List[StrengthItem] = Field(default_factory=list)
    areas_for_practice: List[PracticeAreaItem] = Field(default_factory=list)
    focus_areas: List[str] = Field(default_factory=list)  # backward compat string list
    reading_metrics: ReadingMetrics = Field(default_factory=ReadingMetrics)
    preferred_learning_modes: List[str] = Field(default_factory=lambda: ["Reading", "Visual", "Interactive"])
    preferred_language: str = "en-IN"
    accessibility_preferences: AccessibilityPreferences = Field(default_factory=AccessibilityPreferences)
    adaptive_difficulty: AdaptiveDifficulty = Field(default_factory=AdaptiveDifficulty)
    learning_streak: int = 0
    current_goals: List[Union[GoalItem, str, Dict[str, Any]]] = Field(default_factory=list)
    confidence: ProfileConfidence = Field(default_factory=ProfileConfidence)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    teacher_observations: List[str] = Field(default_factory=list)
    parent_observations: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "Educational Screening Indicator: This profile summarizes educational screening observations "
        "and reading preferences to guide assistive accommodations. It does not constitute a medical, "
        "psychological, or clinical diagnosis."
    )
    last_updated: int = 0
    created_at: int = 0


class V2LearnerProfileUpdate(BaseModel):
    current_goals: Optional[List[Any]] = None
    preferred_language: Optional[str] = None
    preferred_learning_modes: Optional[List[str]] = None
    accessibility_preferences: Optional[Dict[str, Any]] = None
    parent_observations: Optional[List[str]] = None
    teacher_observations: Optional[List[str]] = None


class V2LearningState(BaseModel):
    learner_id: str
    active_difficulty_tier: int = 1
    current_module: str = "foundations"
    today_tasks_assigned: int = 0
    today_tasks_completed: int = 0
    current_streak: int = 0
    last_session_timestamp: Optional[Union[int, str]] = None
    consecutive_passes: int = 0
    consecutive_failures: int = 0
    recommended_next_action: str = "daily_reading_practice"
    adaptation_due: bool = False
    updated_at: int = 0
