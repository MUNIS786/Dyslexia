"""backend/models module"""
from .v2_learner_profile import (
    V2LearnerProfile,
    V2LearnerProfileUpdate,
    V2LearningState,
    DyslexiaIndicators,
    DomainScores,
    CognitiveIndicators,
    ReadingMetrics,
    AccessibilityPreferences,
    AdaptiveDifficulty,
)
from .v2_reading import (
    ReadingQuestion,
    ReadingVocabularyWord,
    ReadingAccessibilityConfig,
    ReadingPassage,
    ReadingSessionStartRequest,
    ReadingSessionCompleteRequest,
    ReadingSession,
    ReadingRecommendationResponse,
    ReadingStatsResponse,
)

from .v2_speech_analysis import (
    WordAlignmentItem,
    SpeechConfidenceSummary,
    SpeechAnalysisRequest,
    SpeechReadingAnalysis,
    SpeechAnalysisResponse,
)
from .v2_tutor import (
    TutorSuggestedAction,
    TutorMessage,
    CompactPassageContext,
    TutorContext,
    TutorRequest,
    TutorResponse,
)

__all__ = [
    "V2LearnerProfile",
    "V2LearnerProfileUpdate",
    "V2LearningState",
    "DyslexiaIndicators",
    "DomainScores",
    "CognitiveIndicators",
    "ReadingMetrics",
    "AccessibilityPreferences",
    "AdaptiveDifficulty",
    "ReadingQuestion",
    "ReadingVocabularyWord",
    "ReadingAccessibilityConfig",
    "ReadingPassage",
    "ReadingSessionStartRequest",
    "ReadingSessionCompleteRequest",
    "ReadingSession",
    "ReadingRecommendationResponse",
    "ReadingStatsResponse",
    "WordAlignmentItem",
    "SpeechConfidenceSummary",
    "SpeechAnalysisRequest",
    "SpeechReadingAnalysis",
    "SpeechAnalysisResponse",
    "TutorSuggestedAction",
    "TutorMessage",
    "CompactPassageContext",
    "TutorContext",
    "TutorRequest",
    "TutorResponse",
]

