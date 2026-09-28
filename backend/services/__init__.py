from services.ai_service import (
    simplify_with_ai, generate_lesson_plan, chat_reply,
    generate_ai_plan, generate_progress_suggestion,
    convert_notes_offline, generate_daily_tasks,
)
from services.offline_simplifier import simplify_offline
from services.ocr_service import ocr_image, preprocess_image
from services.screening_analyzer import analyze_screening
