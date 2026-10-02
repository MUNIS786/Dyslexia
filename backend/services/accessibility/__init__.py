"""backend/services/accessibility package"""
from .accessibility_service import (
    get_user_accessibility_preferences,
    update_user_accessibility_preferences,
    reset_user_accessibility_preferences,
)

__all__ = [
    "get_user_accessibility_preferences",
    "update_user_accessibility_preferences",
    "reset_user_accessibility_preferences",
]
