"""
backend/models/v2_accessibility.py — Pydantic Schemas for V2 Accessibility, Personalization & Inclusive Learning.
Provides validated, child-friendly reading ergonomics, focus guides, and non-clinical safeguards.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, AliasChoices


ALLOWED_FONTS = (
    "OpenDyslexic",
    "OpenDyslexic, sans-serif",
    "Lexend",
    "Lexend, sans-serif",
    "System",
    "System, sans-serif",
    "Comic Neue",
    "Comic Neue, cursive",
    "Arial",
    "Arial, sans-serif",
)

ALLOWED_WIDTHS = ("standard", "narrow", "compact")
ALLOWED_RULER_COLORS = ("amber", "cyan", "yellow", "gray")
ALLOWED_TINT_OVERLAYS = ("none", "peach", "mint", "sky", "butter")


class V2AccessibilityPreferences(BaseModel):
    """Canonical model for a student/user's accessibility and reading ergonomics preferences."""
    model_config = ConfigDict(populate_by_name=True)

    font: str = Field(default="OpenDyslexic", description="Selected reading typography")
    fontSize: int = Field(default=18, ge=12, le=36, validation_alias=AliasChoices("fontSize", "font_size"), description="Base reading font size in pixels")
    lineSpacing: float = Field(default=2.0, ge=1.2, le=3.5, validation_alias=AliasChoices("lineSpacing", "line_spacing"), description="Line height multiplier")
    letterSpacing: float = Field(default=0.08, ge=0.0, le=0.5, validation_alias=AliasChoices("letterSpacing", "letter_spacing"), description="Letter spacing in em units")
    wordSpacing: float = Field(default=0.05, ge=0.0, le=0.5, validation_alias=AliasChoices("wordSpacing", "word_spacing"), description="Word spacing in em units")
    contentWidth: str = Field(default="standard", validation_alias=AliasChoices("contentWidth", "content_width"), description="Maximum content line length ('standard', 'narrow', 'compact')")
    bgColor: str = Field(default="#FFF8F0", validation_alias=AliasChoices("bgColor", "bg_color"), description="Background tint color hex")
    textColor: str = Field(default="#1A2A2A", validation_alias=AliasChoices("textColor", "text_color"), description="Text color hex")
    highContrast: bool = Field(default=False, validation_alias=AliasChoices("highContrast", "high_contrast"), description="High-contrast display toggle")
    reducedMotion: bool = Field(default=False, validation_alias=AliasChoices("reducedMotion", "reduced_motion"), description="Suppress celebratory animations and pulse motion")
    readingRuler: bool = Field(default=False, validation_alias=AliasChoices("readingRuler", "reading_ruler"), description="Reading ruler focus guide overlay active")
    rulerSize: int = Field(default=60, ge=30, le=160, validation_alias=AliasChoices("rulerSize", "ruler_size"), description="Reading ruler height in pixels")
    rulerColor: str = Field(default="amber", validation_alias=AliasChoices("rulerColor", "ruler_color"), description="Reading ruler guide accent color")
    tintOverlay: str = Field(default="none", validation_alias=AliasChoices("tintOverlay", "tint_overlay"), description="Visual stress colored tint overlay ('none', 'peach', 'mint', 'sky', 'butter')")
    ttsSpeed: float = Field(default=0.85, ge=0.5, le=2.0, validation_alias=AliasChoices("ttsSpeed", "tts_speed"), description="Text-to-speech reading rate")
    ttsLanguage: str = Field(default="en-IN", validation_alias=AliasChoices("ttsLanguage", "tts_language"), description="Speech locale voice code")
    highlightWords: bool = Field(default=True, validation_alias=AliasChoices("highlightWords", "highlight_words"), description="Visual highlight for key vocabulary")
    showBulletPoints: bool = Field(default=True, validation_alias=AliasChoices("showBulletPoints", "show_bullet_points"), description="Structured bullet point reading layout")
    autoSimplify: bool = Field(default=True, validation_alias=AliasChoices("autoSimplify", "auto_simplify"), description="Automatic readability simplification on scan")

    @field_validator("contentWidth")
    @classmethod
    def validate_content_width(cls, v: str) -> str:
        if v not in ALLOWED_WIDTHS:
            raise ValueError(f"contentWidth must be one of {ALLOWED_WIDTHS}")
        return v

    @field_validator("rulerColor")
    @classmethod
    def validate_ruler_color(cls, v: str) -> str:
        if v not in ALLOWED_RULER_COLORS:
            raise ValueError(f"rulerColor must be one of {ALLOWED_RULER_COLORS}")
        return v

    @field_validator("tintOverlay")
    @classmethod
    def validate_tint_overlay(cls, v: str) -> str:
        if v not in ALLOWED_TINT_OVERLAYS:
            raise ValueError(f"tintOverlay must be one of {ALLOWED_TINT_OVERLAYS}")
        return v


class AccessibilityPreferencesPatch(BaseModel):
    """Partial update payload for accessibility preferences."""
    model_config = ConfigDict(populate_by_name=True)

    font: Optional[str] = None
    fontSize: Optional[int] = Field(default=None, ge=12, le=36, validation_alias=AliasChoices("fontSize", "font_size"))
    lineSpacing: Optional[float] = Field(default=None, ge=1.2, le=3.5, validation_alias=AliasChoices("lineSpacing", "line_spacing"))
    letterSpacing: Optional[float] = Field(default=None, ge=0.0, le=0.5, validation_alias=AliasChoices("letterSpacing", "letter_spacing"))
    wordSpacing: Optional[float] = Field(default=None, ge=0.0, le=0.5, validation_alias=AliasChoices("wordSpacing", "word_spacing"))
    contentWidth: Optional[str] = Field(default=None, validation_alias=AliasChoices("contentWidth", "content_width"))
    bgColor: Optional[str] = Field(default=None, validation_alias=AliasChoices("bgColor", "bg_color"))
    textColor: Optional[str] = Field(default=None, validation_alias=AliasChoices("textColor", "text_color"))
    highContrast: Optional[bool] = Field(default=None, validation_alias=AliasChoices("highContrast", "high_contrast"))
    reducedMotion: Optional[bool] = Field(default=None, validation_alias=AliasChoices("reducedMotion", "reduced_motion"))
    readingRuler: Optional[bool] = Field(default=None, validation_alias=AliasChoices("readingRuler", "reading_ruler"))
    rulerSize: Optional[int] = Field(default=None, ge=30, le=160, validation_alias=AliasChoices("rulerSize", "ruler_size"))
    rulerColor: Optional[str] = Field(default=None, validation_alias=AliasChoices("rulerColor", "ruler_color"))
    tintOverlay: Optional[str] = Field(default=None, validation_alias=AliasChoices("tintOverlay", "tint_overlay"))
    ttsSpeed: Optional[float] = Field(default=None, ge=0.5, le=2.0, validation_alias=AliasChoices("ttsSpeed", "tts_speed"))
    ttsLanguage: Optional[str] = Field(default=None, validation_alias=AliasChoices("ttsLanguage", "tts_language"))
    highlightWords: Optional[bool] = Field(default=None, validation_alias=AliasChoices("highlightWords", "highlight_words"))
    showBulletPoints: Optional[bool] = Field(default=None, validation_alias=AliasChoices("showBulletPoints", "show_bullet_points"))
    autoSimplify: Optional[bool] = Field(default=None, validation_alias=AliasChoices("autoSimplify", "auto_simplify"))

    @field_validator("contentWidth")
    @classmethod
    def validate_content_width(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_WIDTHS:
            raise ValueError(f"contentWidth must be one of {ALLOWED_WIDTHS}")
        return v

    @field_validator("rulerColor")
    @classmethod
    def validate_ruler_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_RULER_COLORS:
            raise ValueError(f"rulerColor must be one of {ALLOWED_RULER_COLORS}")
        return v

    @field_validator("tintOverlay")
    @classmethod
    def validate_tint_overlay(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_TINT_OVERLAYS:
            raise ValueError(f"tintOverlay must be one of {ALLOWED_TINT_OVERLAYS}")
        return v


class AccessibilityPreferencesResponse(BaseModel):
    """Response envelope with educational and clinical disclaimer."""
    preferences: V2AccessibilityPreferences
    disclaimer: str = (
        "Educational Accessibility Indicator: Visual, typography, and focus preferences are personal "
        "learning adjustments to support reading comfort. They do not constitute a medical, "
        "psychological, or clinical diagnosis."
    )
    updatedAt: Optional[str] = None
