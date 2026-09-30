"""
backend/core/config.py — Centralized configuration, version metadata, and V2 feature flags.
Allows progressive rollout and safe toggling of V2 modules.
"""
import os
from typing import Dict


class Settings:
    APPLICATION_NAME: str = "DyslexAid"
    APPLICATION_VERSION: str = "4.1.0"
    API_VERSION: str = "v1/v2"

    # Environment
    ENV: str = os.environ.get("ENV", "development")
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # Feature Flags (overrideable via environment variables)
    V2_ENABLED: bool = os.environ.get("V2_ENABLED", "true").lower() in ("true", "1", "yes")
    V2_LEARNER_PROFILE: bool = os.environ.get("V2_LEARNER_PROFILE", "true").lower() in ("true", "1", "yes")
    V2_ADAPTIVE_ENGINE: bool = os.environ.get("V2_ADAPTIVE_ENGINE", "true").lower() in ("true", "1", "yes")
    V2_READING_COACH: bool = os.environ.get("V2_READING_COACH", "true").lower() in ("true", "1", "yes")
    V2_AI_TUTOR: bool = os.environ.get("V2_AI_TUTOR", "false").lower() in ("true", "1", "yes")
    V2_GAMIFICATION: bool = os.environ.get("V2_GAMIFICATION", "false").lower() in ("true", "1", "yes")
    V2_MULTILINGUAL: bool = os.environ.get("V2_MULTILINGUAL", "false").lower() in ("true", "1", "yes")
    V2_PARENT_PORTAL: bool = os.environ.get("V2_PARENT_PORTAL", "false").lower() in ("true", "1", "yes")

    @classmethod
    def get_feature_flags(cls) -> Dict[str, bool]:
        return {
            "V2_ENABLED": cls.V2_ENABLED,
            "V2_LEARNER_PROFILE": cls.V2_LEARNER_PROFILE,
            "V2_ADAPTIVE_ENGINE": cls.V2_ADAPTIVE_ENGINE,
            "V2_READING_COACH": cls.V2_READING_COACH,
            "V2_AI_TUTOR": cls.V2_AI_TUTOR,
            "V2_GAMIFICATION": cls.V2_GAMIFICATION,
            "V2_MULTILINGUAL": cls.V2_MULTILINGUAL,
            "V2_PARENT_PORTAL": cls.V2_PARENT_PORTAL,
        }

    @classmethod
    def get_version_info(cls) -> Dict[str, any]:
        return {
            "application": cls.APPLICATION_NAME,
            "version": cls.APPLICATION_VERSION,
            "api_version": cls.API_VERSION,
            "v2_enabled": cls.V2_ENABLED,
            "feature_flags": cls.get_feature_flags(),
        }


settings = Settings()
