"""backend/services/learning module"""
from .learner_profile_service import (
    get_or_create_learner_profile,
    update_learner_profile,
    get_learning_state,
)
from .reading_service import (
    seed_reading_passages,
    get_passages,
    get_passage_by_id,
    start_reading_session,
    complete_reading_session,
    get_learner_sessions,
    get_learner_reading_stats,
)
from .reading_recommender import recommend_reading_passage
from .reading_performance import (
    calculate_comprehension_score,
    calculate_completion_rate,
    calculate_overall_score,
    grade_comprehension_answers,
)

from .speech_analysis import (
    normalize_text_to_tokens,
    align_word_sequences,
    calculate_word_accuracy,
    calculate_coverage_rate,
    calculate_words_per_minute,
    calculate_reading_practice_score,
    analyze_speech_reading,
    get_speech_analysis_for_session,
)
from .tutor_context import build_tutor_context
from .tutor_service import (
    build_tutor_instruction,
    generate_offline_fallback,
    handle_tutor_chat,
    get_tutor_history,
    clear_tutor_history,
)
from .gamification_service import (
    ACHIEVEMENT_CATALOGUE,
    calculate_event_points,
    calculate_learner_streak,
    process_learning_reward,
    get_gamification_summary,
    get_achievements_with_progress,
    get_milestones_progress,
    get_reward_history,
    get_teacher_learner_reward_summary,
)

__all__ = [
    "get_or_create_learner_profile",
    "update_learner_profile",
    "get_learning_state",
    "seed_reading_passages",
    "get_passages",
    "get_passage_by_id",
    "start_reading_session",
    "complete_reading_session",
    "get_learner_sessions",
    "get_learner_reading_stats",
    "recommend_reading_passage",
    "calculate_comprehension_score",
    "calculate_completion_rate",
    "calculate_overall_score",
    "grade_comprehension_answers",
    "normalize_text_to_tokens",
    "align_word_sequences",
    "calculate_word_accuracy",
    "calculate_coverage_rate",
    "calculate_words_per_minute",
    "calculate_reading_practice_score",
    "analyze_speech_reading",
    "get_speech_analysis_for_session",
    "build_tutor_context",
    "build_tutor_instruction",
    "generate_offline_fallback",
    "handle_tutor_chat",
    "get_tutor_history",
    "clear_tutor_history",
    "ACHIEVEMENT_CATALOGUE",
    "calculate_event_points",
    "calculate_learner_streak",
    "process_learning_reward",
    "get_gamification_summary",
    "get_achievements_with_progress",
    "get_milestones_progress",
    "get_reward_history",
    "get_teacher_learner_reward_summary",
]

