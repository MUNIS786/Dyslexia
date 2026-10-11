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

    # Environment & Server
    ENV: str = os.environ.get("ENV", "development").lower()
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # Database Configuration & Timeouts
    MONGO_URL: str = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME: str = os.environ.get("DB_NAME", "dyslexaid")
    DB_SERVER_SELECTION_TIMEOUT_MS: int = int(os.environ.get("DB_SERVER_SELECTION_TIMEOUT_MS", "3000"))
    DB_CONNECT_TIMEOUT_MS: int = int(os.environ.get("DB_CONNECT_TIMEOUT_MS", "3000"))

    # Security & Auth Configuration
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "dyslexaid-dev-secret-change-in-prod")
    JWT_ALG: str = os.environ.get("JWT_ALG", "HS256")
    JWT_EXP_DAYS: int = int(os.environ.get("JWT_EXP_DAYS", "30"))

    # CORS Configuration (comma-separated origins or default list)
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "")

    # Feature Flags (overrideable via environment variables)
    V2_ENABLED: bool = os.environ.get("V2_ENABLED", "true").lower() in ("true", "1", "yes")
    V2_LEARNER_PROFILE: bool = os.environ.get("V2_LEARNER_PROFILE", "true").lower() in ("true", "1", "yes")
    V2_ADAPTIVE_ENGINE: bool = os.environ.get("V2_ADAPTIVE_ENGINE", "true").lower() in ("true", "1", "yes")
    V2_READING_COACH: bool = os.environ.get("V2_READING_COACH", "true").lower() in ("true", "1", "yes")
    V2_SPEECH_ANALYSIS: bool = os.environ.get("V2_SPEECH_ANALYSIS", "true").lower() in ("true", "1", "yes")
    V2_AI_TUTOR: bool = os.environ.get("V2_AI_TUTOR", "true").lower() in ("true", "1", "yes")
    V2_TEACHER_ANALYTICS: bool = os.environ.get("V2_TEACHER_ANALYTICS", "true").lower() in ("true", "1", "yes")
    V2_INTERVENTION_EFFECTIVENESS: bool = os.environ.get("V2_INTERVENTION_EFFECTIVENESS", "true").lower() in ("true", "1", "yes")
    V2_GAMIFICATION: bool = os.environ.get("V2_GAMIFICATION", "true").lower() in ("true", "1", "yes")
    V2_MULTILINGUAL: bool = (
        os.environ.get("V2_MULTILINGUAL_SUPPORT", os.environ.get("V2_MULTILINGUAL", "true"))
    ).lower() in ("true", "1", "yes")
    V2_MULTILINGUAL_SUPPORT: bool = V2_MULTILINGUAL
    V2_PARENT_PORTAL: bool = os.environ.get("V2_PARENT_PORTAL", "true").lower() in ("true", "1", "yes")
    V2_ACCESSIBILITY_PREFERENCES: bool = os.environ.get("V2_ACCESSIBILITY_PREFERENCES", "true").lower() in ("true", "1", "yes")
    V2_LEARNING_INSIGHTS: bool = os.environ.get("V2_LEARNING_INSIGHTS", "true").lower() in ("true", "1", "yes")
    V2_LEARNING_RECOMMENDATIONS: bool = os.environ.get("V2_LEARNING_RECOMMENDATIONS", "true").lower() in ("true", "1", "yes")
    V2_PERSONALIZED_CONTENT: bool = os.environ.get("V2_PERSONALIZED_CONTENT", "true").lower() in ("true", "1", "yes")
    V2_CONTENT_AUTHORING: bool = os.environ.get("V2_CONTENT_AUTHORING", "true").lower() in ("true", "1", "yes")

    @classmethod
    def get_allowed_cors_origins(cls) -> list[str]:
        raw = cls.CORS_ORIGINS.strip() if cls.CORS_ORIGINS else ""
        if raw:
            if raw == "*":
                return ["*"]
            return [o.strip() for o in raw.split(",") if o.strip()]
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    @classmethod
    def validate_production_config(cls, strict: bool = False) -> list[str]:
        """
        Validates environment configuration for production safety.
        Returns a list of issue descriptions. In strict mode, raises ValueError.
        """
        issues: list[str] = []
        if cls.ENV == "production":
            insecure_secrets = {
                "dyslexaid-dev-secret-change-in-prod",
                "your_jwt_secret_here",
                "secret",
                "changeme",
                "password",
                "",
            }
            if cls.JWT_SECRET.lower() in insecure_secrets or len(cls.JWT_SECRET) < 16:
                issues.append("JWT_SECRET must be set to a secure string with at least 16 characters in production.")

            origins = cls.get_allowed_cors_origins()
            if "*" in origins:
                issues.append("CORS_ORIGINS cannot contain wildcard '*' in production when credentials are enabled.")

            if not cls.MONGO_URL or not (cls.MONGO_URL.startswith("mongodb://") or cls.MONGO_URL.startswith("mongodb+srv://")):
                issues.append("MONGO_URL must be a valid mongodb:// or mongodb+srv:// connection URI.")

        if strict and issues:
            raise ValueError(f"Production configuration validation failed: {'; '.join(issues)}")
        return issues

    @classmethod
    def get_feature_flags(cls) -> Dict[str, bool]:
        return {
            "V2_ENABLED": cls.V2_ENABLED,
            "V2_LEARNER_PROFILE": cls.V2_LEARNER_PROFILE,
            "V2_ADAPTIVE_ENGINE": cls.V2_ADAPTIVE_ENGINE,
            "V2_READING_COACH": cls.V2_READING_COACH,
            "V2_SPEECH_ANALYSIS": cls.V2_SPEECH_ANALYSIS,
            "V2_AI_TUTOR": cls.V2_AI_TUTOR,
            "V2_TEACHER_ANALYTICS": cls.V2_TEACHER_ANALYTICS,
            "V2_INTERVENTION_EFFECTIVENESS": cls.V2_INTERVENTION_EFFECTIVENESS,
            "V2_GAMIFICATION": cls.V2_GAMIFICATION,
            "V2_MULTILINGUAL": cls.V2_MULTILINGUAL,
            "V2_MULTILINGUAL_SUPPORT": cls.V2_MULTILINGUAL,
            "V2_PARENT_PORTAL": cls.V2_PARENT_PORTAL,
            "V2_ACCESSIBILITY_PREFERENCES": cls.V2_ACCESSIBILITY_PREFERENCES,
            "V2_LEARNING_INSIGHTS": cls.V2_LEARNING_INSIGHTS,
            "V2_LEARNING_RECOMMENDATIONS": cls.V2_LEARNING_RECOMMENDATIONS,
            "V2_PERSONALIZED_CONTENT": cls.V2_PERSONALIZED_CONTENT,
            "V2_CONTENT_AUTHORING": cls.V2_CONTENT_AUTHORING,
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
