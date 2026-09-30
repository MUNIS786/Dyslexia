"""backend/services/analytics module"""
from .teacher_analytics import (
    get_class_overview,
    get_classroom_learners,
    get_learner_analytics_detail,
    calculate_progress_trends,
    verify_teacher_student_access,
)

__all__ = [
    "get_class_overview",
    "get_classroom_learners",
    "get_learner_analytics_detail",
    "calculate_progress_trends",
    "verify_teacher_student_access",
]
