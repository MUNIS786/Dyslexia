"""
backend/models/v2_tutor.py — Pydantic Schemas for V2 Personal AI Tutor.

Provides structured models for:
- Compact, minimized learner context
- User tutor requests and progressive hint inquiries
- AI tutor responses with optional pedagogical learning actions
- Conversational message exchanges with bounded history

IMPORTANT:
These models support assistive educational coaching and practice.
They do NOT provide or claim clinical speech, neurological, or dyslexia diagnoses.
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class TutorSuggestedAction(BaseModel):
    """Pedagogical next action recommended by the AI Tutor."""
    type: str = Field(
        ...,
        description="'practice_word' | 'read_again' | 'try_question' | 'open_reading_coach' | 'start_adaptive_practice' | 'review_hint'"
    )
    label: str = Field(..., description="Child-friendly button label, e.g. 'Practice this word'")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata required by the action")


class TutorMessage(BaseModel):
    """Single chat turn in a tutor interaction."""
    id: Optional[str] = Field(default=None)
    role: str = Field(..., description="'user' | 'assistant' | 'system'")
    content: str = Field(..., min_length=1, description="Message text content")
    timestamp: Optional[int] = Field(default=None)
    suggestedAction: Optional[TutorSuggestedAction] = Field(default=None)


class CompactPassageContext(BaseModel):
    """Minimized representation of the active reading passage for the tutor."""
    passageId: str
    title: str
    excerpt: str = Field(..., description="Truncated text excerpt (up to 400 chars) to prevent context bloat")
    difficulty: int = 1
    vocabularyWords: List[str] = Field(default_factory=list)


class TutorContext(BaseModel):
    """
    Compact, privacy-safe context package assembled deterministically for the AI Tutor.
    Strictly excludes passwords, JWT tokens, DB IDs, and raw speech/audio.
    """
    learnerId: str
    displayName: Optional[str] = "Student"
    learningLevel: int = Field(default=2, ge=1, le=5, description="1=Foundation, 2=Developing, 3=Progressing, 4=Competent, 5=Mastering")
    learningLevelName: str = "Developing"
    adaptiveTier: int = Field(default=1, ge=1, le=5)
    strengths: List[str] = Field(default_factory=list, description="Top friendly strength domain names")
    practiceAreas: List[str] = Field(default_factory=list, description="Top friendly growth practice areas")
    currentPassage: Optional[CompactPassageContext] = None
    activeWord: Optional[str] = None
    recentReading: Optional[Dict[str, Any]] = None  # e.g. {"comprehension": 75, "fluency": 70, "wordsRead": 120}
    accessibility: Optional[Dict[str, Any]] = None  # e.g. {"font": "OpenDyslexic", "fontSize": 20}
    speechSignals: Optional[Dict[str, Any]] = None  # e.g. {"accuracy": 82.0, "wpm": 75.0}


class TutorRequest(BaseModel):
    """Student prompt submission to the Personal AI Tutor."""
    message: str = Field(..., min_length=1, max_length=2000, description="Student's question or message")
    activePassageId: Optional[str] = Field(default=None, description="Optional ID of passage being read")
    activeWord: Optional[str] = Field(default=None, description="Optional word queried from DifficultWords")
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Previous conversation turns (up to 6)")


class TutorResponse(BaseModel):
    """Personalized educational response returned by the AI Tutor."""
    status: str = Field(default="ok")
    message: str = Field(..., description="Child-friendly response message")
    explanation: Optional[str] = Field(default=None, description="Optional detailed concept breakdown")
    suggestedAction: Optional[TutorSuggestedAction] = Field(default=None, description="Next learning practice action")
    followUpQuestion: Optional[str] = Field(default=None, description="Encouraging check-for-understanding question")
    source: str = Field(default="gemini", description="'gemini' | 'offline-fallback'")
    learningLevel: int = Field(default=2, ge=1, le=5)
    contextSummary: Optional[Dict[str, Any]] = Field(default=None, description="Brief summary of context recognized")
    timestamp: int = Field(default=0)
