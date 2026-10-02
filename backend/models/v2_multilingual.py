"""
backend/models/v2_multilingual.py — Pydantic Schemas & Catalogs for V2 Multilingual Support.

Models & Constants:
- LanguageInfo: metadata about supported interface & learning languages
- SUPPORTED_LANGUAGES: central dictionary of supported language metadata
- normalize_locale / normalize_language_code: alias resolution and validation
- LanguagePreferenceUpdate: payload to update authenticated user's preferred language
- LanguagePreferenceResponse: response detailing active language and available locales
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    """Metadata describing a supported system language."""
    code: str = Field(..., description="ISO 639-1 language code, e.g. 'en', 'mr', 'hi'")
    name: str = Field(..., description="English display name, e.g. 'Marathi'")
    nativeName: str = Field(..., description="Native display name, e.g. 'मराठी'")
    speechCode: str = Field(..., description="BCP 47 speech synthesis/recognition code, e.g. 'mr-IN'")
    flag: str = Field(default="🌐", description="Emoji flag or symbol")
    direction: str = Field(default="ltr", description="Text direction, e.g. 'ltr' or 'rtl'")
    hasPassages: bool = Field(default=True, description="Whether learning passages exist in this language")
    interface_supported: bool = Field(default=True, description="Whether UI translations exist")
    learning_content_supported: bool = Field(default=True, description="Whether learning content exists")

    @property
    def native_name(self) -> str:
        return self.nativeName


SUPPORTED_LANGUAGES: Dict[str, LanguageInfo] = {
    "en": LanguageInfo(
        code="en",
        name="English",
        nativeName="English",
        speechCode="en-IN",
        flag="🇬🇧",
        direction="ltr",
        hasPassages=True,
        interface_supported=True,
        learning_content_supported=True,
    ),
    "mr": LanguageInfo(
        code="mr",
        name="Marathi",
        nativeName="मराठी",
        speechCode="mr-IN",
        flag="🇮🇳",
        direction="ltr",
        hasPassages=True,
        interface_supported=True,
        learning_content_supported=True,
    ),
    "hi": LanguageInfo(
        code="hi",
        name="Hindi",
        nativeName="हिन्दी",
        speechCode="hi-IN",
        flag="🇮🇳",
        direction="ltr",
        hasPassages=True,
        interface_supported=True,
        learning_content_supported=True,
    ),
}

LOCALE_ALIASES: Dict[str, str] = {
    "en-in": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    "mr-in": "mr",
    "marathi": "mr",
    "hi-in": "hi",
    "hindi": "hi",
}


def normalize_locale(code: Optional[str]) -> Optional[str]:
    """Normalizes raw locale string or alias to canonical 2-letter code if supported."""
    if not code:
        return None
    cleaned = code.strip().lower()
    canonical = LOCALE_ALIASES.get(cleaned, cleaned)
    if canonical in SUPPORTED_LANGUAGES:
        return canonical
    return None


normalize_language_code = normalize_locale


class LanguagePreferenceUpdate(BaseModel):
    """Payload to update the authenticated user's language preference."""
    preferredLanguage: Optional[str] = Field(
        default=None,
        description="Target language code ('en', 'mr', 'hi' or BCP-47 variant 'en-IN')"
    )
    language: Optional[str] = Field(
        default=None,
        description="Alternative field for target language code"
    )

    def get_target_code(self) -> str:
        code = self.preferredLanguage or self.language
        return (code or "").strip()


class LanguagePreferenceResponse(BaseModel):
    """Response containing active language and supported locale catalogue."""
    status: str = "ok"
    preferredLanguage: str
    activeLanguage: LanguageInfo
    supportedLanguages: List[LanguageInfo]

    @property
    def language(self) -> str:
        return self.preferredLanguage

    @property
    def name(self) -> str:
        return self.activeLanguage.name
