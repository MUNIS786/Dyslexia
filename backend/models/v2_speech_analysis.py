"""
backend/models/v2_speech_analysis.py — Pydantic Schemas for V2 Speech & Reading Analysis.

Educational reading practice telemetry and alignment models:
- Dynamic sequence alignment results (expected vs. recognized tokens)
- Reading rate (WPM), coverage rate, and word-level accuracy
- Browser pause & hesitation signals
- Privacy-first: strictly derived educational metrics; NO raw audio is stored.

IMPORTANT:
These models are designed for assistive educational reading practice.
They do NOT provide or imply clinical speech, language, cognitive, or dyslexia diagnoses.
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class WordAlignmentItem(BaseModel):
    """Word-level alignment between expected passage and recognized speech token."""
    expected: Optional[str] = Field(default=None, description="Expected word from the passage")
    recognized: Optional[str] = Field(default=None, description="Word recognized by speech recognition")
    status: str = Field(
        ...,
        description="'matched' | 'substitution' | 'omission' | 'insertion'"
    )


class SpeechConfidenceSummary(BaseModel):
    """Aggregate confidence score provided by browser speech recognition API."""
    average: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sampleCount: int = Field(default=0, ge=0)


class SpeechAnalysisRequest(BaseModel):
    """Payload sent by the frontend after a learner reads aloud."""
    sessionId: str = Field(..., description="ID of the associated reading session")
    passageId: Optional[str] = Field(default=None, description="Optional passage ID (retrieved from session if omitted)")
    transcript: str = Field(..., description="Transcribed text from browser Web Speech API")
    durationSeconds: int = Field(default=0, ge=0, description="Observed speaking duration in seconds")
    pauseCount: Optional[int] = Field(default=None, ge=0, description="Observed speech pauses / silence intervals")
    hesitationCount: Optional[int] = Field(default=None, ge=0, description="Observed hesitations / repetitions")
    confidenceSummary: Optional[SpeechConfidenceSummary] = Field(
        default=None,
        description="Browser-provided confidence metrics (null if unsupported)"
    )
    readingMode: Optional[str] = Field(default="speech", description="Reading mode identifier")


class SpeechReadingAnalysis(BaseModel):
    """Authoritative server-side speech reading analysis record."""
    analysisId: str = Field(..., description="Unique analysis record identifier")
    sessionId: str = Field(..., description="Reading session identifier")
    learnerId: str = Field(..., description="Student identifier")
    passageId: str = Field(..., description="Reading passage identifier")

    passageWordCount: int = Field(..., ge=0, description="Total expected words in the passage")
    recognizedWordCount: int = Field(..., ge=0, description="Total words transcribed by speech recognition")
    matchedWordCount: int = Field(..., ge=0, description="Expected words accurately spoken")

    wordAccuracy: float = Field(..., ge=0.0, le=100.0, description="Percentage of expected words matched")
    coverageRate: float = Field(..., ge=0.0, le=100.0, description="Percentage of the passage covered")

    omissions: List[str] = Field(default_factory=list, description="Expected words that were omitted")
    insertions: List[str] = Field(default_factory=list, description="Extraneous words recognized")
    substitutions: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Substitutions observed: [{'expected': '...', 'recognized': '...'}]"
    )

    hesitationCount: Optional[int] = Field(default=None, description="Observed hesitations")
    pauseCount: Optional[int] = Field(default=None, description="Observed pauses")

    readingDurationSeconds: int = Field(default=0, ge=0, description="Observed speaking duration")
    wordsPerMinute: float = Field(default=0.0, ge=0.0, description="Observed reading pace (WPM)")

    confidenceSummary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Confidence statistics when provided by browser"
    )

    readingPracticeScore: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Educational practice metric combining accuracy, coverage, and pace"
    )

    alignmentSummary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sequence alignment tokens for supportive UI feedback"
    )

    feedback: str = Field(
        default="Great reading practice!",
        description="Encouraging, child-friendly feedback message"
    )

    analysisVersion: str = Field(default="1.0", description="Analysis engine version")
    createdAt: int = Field(..., description="Timestamp of analysis creation")


class SpeechAnalysisResponse(BaseModel):
    """Response returned to the frontend upon speech analysis completion."""
    status: str = Field(default="ok")
    analysis: SpeechReadingAnalysis
    childFriendlyFeedback: str
    nextActionSuggestion: str
