"""
backend/models/v2_reading.py — Pydantic Schemas for V2 Adaptive Reading Coach.

Defines schemas for:
- Reading Passages, Comprehension Questions, and Word Support (Vocabulary)
- Reading Sessions & Lifecycle Telemetry
- Accessibility Configurations
- Adaptive Reading Recommendations & Performance Results

IMPORTANT:
These models support educational reading practice and assistive accommodations.
They do NOT represent clinical, medical, or neuropsychological diagnoses.
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class ReadingQuestion(BaseModel):
    """Multiple-choice comprehension question associated with a reading passage."""
    questionId: str = Field(..., description="Unique question identifier, e.g. q-01")
    question: str = Field(..., description="The comprehension question text")
    options: List[str] = Field(..., min_length=2, description="List of answer choices")
    correctAnswer: Union[int, str] = Field(..., description="0-based index or matching text of correct option")
    explanation: str = Field(..., description="Supportive, educational explanation of the answer")
    questionType: str = Field(
        default="detail",
        description="Type: 'main_idea' | 'detail' | 'sequence' | 'vocabulary_in_context' | 'simple_inference'"
    )


class ReadingVocabularyWord(BaseModel):
    """Vocabulary word definition and phonics support for difficult-word interaction."""
    word: str = Field(..., description="Target vocabulary word")
    definition: str = Field(..., description="Simple, child-friendly definition")
    phonetic: Optional[str] = Field(default=None, description="Phonetic respelling or IPA guide")
    exampleSentence: Optional[str] = Field(default=None, description="Contextual example sentence")
    syllables: Optional[List[str]] = Field(default=None, description="Syllable breakdown, e.g. ['won', 'der', 'ful']")


class ReadingAccessibilityConfig(BaseModel):
    """Typography and layout ergonomics for dyslexia-friendly reading."""
    fontSize: int = Field(default=18, ge=14, le=36)
    letterSpacing: float = Field(default=0.12, ge=0.0, le=0.5)
    lineHeight: float = Field(default=2.0, ge=1.2, le=3.0)
    fontFamily: str = Field(default="OpenDyslexic", description="'OpenDyslexic' | 'Lexend' | 'Arial'")
    paragraphSpacing: float = Field(default=1.5, ge=1.0, le=3.0)
    readingWidth: str = Field(default="normal", description="'narrow' | 'normal' | 'wide'")


class ReadingPassage(BaseModel):
    """Structured educational reading passage with comprehension questions and word support."""
    passageId: str = Field(..., description="Unique passage ID, e.g. pas-t1-001")
    title: str = Field(..., description="Engaging, child-friendly title")
    text: str = Field(..., description="Full text of the reading passage")
    difficulty: int = Field(default=1, ge=1, le=5, description="Difficulty tier (1=Foundation to 5=Advanced)")
    domain: str = Field(default="reading_comprehension", description="Primary educational domain targeted")
    estimatedMinutes: int = Field(default=3, ge=1, le=20, description="Estimated time to complete reading")
    wordCount: int = Field(default=50, ge=1, description="Total word count of the passage")
    language: str = Field(default="en", description="Passage language code")
    gradeBand: str = Field(default="Grade 1-2", description="Target educational level")
    topics: List[str] = Field(default_factory=list, description="Subject tags, e.g. ['animals', 'nature']")
    questions: List[ReadingQuestion] = Field(default_factory=list, description="Comprehension questions")
    vocabulary: List[ReadingVocabularyWord] = Field(default_factory=list, description="Predefined difficult words")
    accessibility: Dict[str, Any] = Field(default_factory=dict, description="Recommended display presets")
    active: bool = Field(default=True, description="Whether available in the catalog")
    createdAt: int = Field(default=0)
    updatedAt: int = Field(default=0)


class ReadingSessionStartRequest(BaseModel):
    """Payload to initiate a new reading coach session."""
    passageId: str = Field(..., description="ID of the passage to read")
    activityId: Optional[str] = Field(default=None, description="Optional linked activity ID")
    readingMode: Optional[str] = Field(default="standard", description="'standard' | 'focus' | 'guided' | 'listen'")
    language: Optional[str] = Field(default="en")


class ReadingSessionCompleteRequest(BaseModel):
    """Telemetry and interaction payload submitted upon finishing a reading session."""
    sessionId: str = Field(..., description="UUID of the active reading session")
    durationSeconds: int = Field(default=0, ge=0, description="Total time spent in seconds")
    readingMode: Optional[str] = Field(default="standard")
    wordsRead: Optional[int] = Field(default=None, ge=0, description="Reported words read")
    comprehensionAnswers: Dict[str, Union[int, str]] = Field(
        default_factory=dict,
        description="Map of questionId -> student selected answer (index or text)"
    )
    difficultWords: List[str] = Field(default_factory=list, description="Words tapped for definitions")
    practicedWords: List[str] = Field(default_factory=list, description="Words tapped for pronunciation practice")
    hintsUsed: int = Field(default=0, ge=0, description="Hints requested during comprehension")
    replaysUsed: int = Field(default=0, ge=0, description="Audio TTS replays used")
    completed: bool = Field(default=True)
    skipped: bool = Field(default=False)


class ReadingSession(BaseModel):
    """Persisted session record containing telemetric and educational outcome data."""
    sessionId: str
    learnerId: str
    activityId: Optional[str] = None
    passageId: str
    domain: str = "reading_comprehension"
    difficulty: int = 1
    startedAt: int
    completedAt: Optional[int] = None

    readingMode: str = "standard"
    language: str = "en"

    wordsPresented: int = 0
    wordsRead: int = 0
    wordsCompleted: int = 0

    durationSeconds: int = 0

    comprehensionQuestions: int = 0
    comprehensionCorrect: int = 0
    comprehensionAccuracy: float = 0.0

    hintsUsed: int = 0
    replaysUsed: int = 0

    difficultWords: List[str] = Field(default_factory=list)
    practicedWords: List[str] = Field(default_factory=list)

    readingScore: float = 0.0
    comprehensionScore: float = 0.0
    overallScore: float = 0.0

    completed: bool = False
    skipped: bool = False

    adaptation: Optional[Dict[str, Any]] = None
    createdAt: int
    updatedAt: int


class ReadingRecommendationResponse(BaseModel):
    """Personalized reading recommendation with explainable pedagogical rationale."""
    recommendedPassage: ReadingPassage
    difficulty: int
    domain: str
    reason: str
    confidence: float = 0.85


class ReadingStatsResponse(BaseModel):
    """Reading progress overview and historical practice statistics."""
    totalSessions: int = 0
    completedSessions: int = 0
    totalWordsRead: int = 0
    totalMinutesRead: float = 0.0
    avgComprehensionAccuracy: float = 0.0
    avgOverallScore: float = 0.0
    currentTier: int = 1
    wordsPracticedCount: int = 0
    recentSessions: List[Dict[str, Any]] = Field(default_factory=list)
    domainPerformance: Dict[str, float] = Field(default_factory=dict)
    trend: str = "steady"  # "improving" | "steady" | "needs_support"
