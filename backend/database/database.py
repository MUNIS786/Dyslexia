"""
MongoDB connection, indexes, migration, and demo seeding.
Real users start with zero data — demo data only seeds once if DB is empty.
"""
import os
import time
import uuid
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "dyslexaid")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

ASSESSMENT_SCHEMA_VERSION = 2


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _default_progress() -> dict:
    return {
        "docsScanned": 0, "wordsRead": 0, "hoursReading": 0.0,
        "avgComprehension": 0, "wordsMastered": 0, "streak": 0,
        "lastActiveDate": None,
        "weeklyActivity": {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0},
        "comprehensionScores": [], "masteredWords": [], "recentActivity": [],
        "sessionCount": 0, "totalTimeMinutes": 0,
        "screeningCompleted": False, "planGenerated": False,
        "aiPlanAdaptations": 0, "tasksCompleted": 0, "tasksAssigned": 0,
    }


def _default_settings() -> dict:
    return {
        "font": "OpenDyslexic", "fontSize": 18, "lineSpacing": 2.0,
        "letterSpacing": 0.1, "bgColor": "#FFF8F0", "textColor": "#1A2A2A",
        "ttsSpeed": 0.85, "ttsLanguage": "en-IN",
        "highlightWords": True, "showBulletPoints": True, "autoSimplify": True,
    }


def _default_ui_settings() -> dict:
    return {
        "font": "OpenDyslexic", "background": "white", "font_size": "medium",
        "line_spacing": 1.4, "tts_default_on": False, "tts_speed": 1.0,
        "extended_time": False, "chunk_length": "medium", "highlight_syllables": False,
    }


def _default_reading_profile() -> dict:
    """Canonical v2 readingProfile shape embedded on users.{id}.readingProfile.
    All screening-derived data lives here for fast reads; full history in
    screening_results."""
    return {
        "assessmentVersion": ASSESSMENT_SCHEMA_VERSION,
        "type": None,
        "primaryProfile": None,
        "level": None,
        "riskLevel": None,
        "score": None,
        "confidence": None,
        "domainScores": {},
        "cognitiveProfile": {},
        "learningProfiles": {},
        "strengths": [],
        "weaknesses": [],
        "learningStyle": None,
        "uiSettings": _default_ui_settings(),
        "recommendedActivities": [],
        "recommendedGames": [],
        "interventions": [],
        "recommendation": None,
        "lastScreeningId": None,
        "screenedAt": None,
    }


# ─── Indexes ────────────────────────────────────────────────────────────────

async def init_db():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.users.create_index("classroomCode")
    await db.users.create_index("readingProfile.riskLevel")
    await db.users.create_index("readingProfile.primaryProfile")

    await db.assignments.create_index([("classroomCode", 1), ("createdAt", -1)])
    try:
        await db.submissions.create_index([("assignmentId", 1), ("studentId", 1)], unique=True)
    except Exception:
        pass

    await db.notifications.create_index([("userId", 1), ("createdAt", -1)])
    await db.progress.create_index("userId", unique=True)
    await db.libraries.create_index([("userId", 1), ("createdAt", -1)])
    await db.ai_plans.create_index("userId", unique=True)
    await db.daily_tasks.create_index([("userId", 1), ("date", 1)])

    try:
        await db.classrooms.create_index("code", unique=True)
    except Exception:
        pass

    # Assessment History — one document per screening attempt.
    await db.screening_results.create_index([("userId", 1), ("createdAt", -1)])
    await db.screening_results.create_index([("userId", 1), ("assessmentVersion", 1)])
    await db.screening_results.create_index("riskLevel")
    await db.screening_results.create_index("primaryProfile")

    # Prediction History — every model/rule-based prediction event, append-only,
    # kept separate from screening_results so re-scoring the same answers with a
    # new engine version doesn't overwrite the original attempt.
    await db.prediction_history.create_index([("userId", 1), ("createdAt", -1)])
    await db.prediction_history.create_index([("userId", 1), ("assessmentVersion", 1)])
    await db.prediction_history.create_index("screeningResultId")

    # Teacher Notes — per student, per teacher, timestamped.
    await db.teacher_notes.create_index([("studentId", 1), ("createdAt", -1)])
    await db.teacher_notes.create_index([("teacherId", 1), ("createdAt", -1)])
    await db.teacher_notes.create_index([("classroomCode", 1), ("createdAt", -1)])

    # Recommended Activities/Games — reusable catalog, matched to profile at read time.
    await db.recommended_activities.create_index("domains")
    await db.recommended_activities.create_index("profileTags")
    await db.recommended_games.create_index("domains")
    # V2 Collections
    await db.learner_profiles.create_index("learnerId", unique=True)
    await db.learning_states.create_index("learnerId", unique=True)
    await db.learning_activities.create_index("id", unique=True)
    await db.learning_activities.create_index([("domain", 1), ("difficultyTier", 1)])
    await db.activity_attempts.create_index([("learnerId", 1), ("completedAt", -1)])
    await db.activity_attempts.create_index([("activityId", 1), ("scorePercent", 1)])
    await db.adaptive_recommendations.create_index([("learnerId", 1), ("generatedAt", -1)])

    # V2 Reading Coach Collections
    try:
        await db.reading_sessions.create_index("sessionId", unique=True)
    except Exception:
        pass
    await db.reading_sessions.create_index("learnerId")
    await db.reading_sessions.create_index("createdAt")
    await db.reading_sessions.create_index([("learnerId", 1), ("createdAt", -1)])
    await db.reading_sessions.create_index([("learnerId", 1), ("activityId", 1)])

    try:
        await db.reading_passages.create_index("passageId", unique=True)
    except Exception:
        pass
    await db.reading_passages.create_index([("difficulty", 1), ("domain", 1)])

    # V2 Speech & Reading Analysis Collection
    try:
        await db.speech_reading_analyses.create_index("analysisId", unique=True)
    except Exception:
        pass
    await db.speech_reading_analyses.create_index("sessionId")
    await db.speech_reading_analyses.create_index("learnerId")
    await db.speech_reading_analyses.create_index("createdAt")
    await db.speech_reading_analyses.create_index([("learnerId", 1), ("createdAt", -1)])

    # Phase 6: Personal AI Tutor conversations
    try:
        await db.tutor_conversations.create_index("conversationId", unique=True)
    except Exception:
        pass
    await db.tutor_conversations.create_index("learnerId")
    await db.tutor_conversations.create_index([("learnerId", 1), ("updatedAt", -1)])

    # Phase 8: Interventions & Support Activities
    try:
        await db.interventions.create_index("interventionId", unique=True)
    except Exception:
        pass
    await db.interventions.create_index("teacherId")
    await db.interventions.create_index("learnerId")
    await db.interventions.create_index("classroomCode")
    await db.interventions.create_index("status")
    await db.interventions.create_index("createdAt")
    await db.interventions.create_index([("learnerId", 1), ("status", 1)])
    await db.interventions.create_index([("teacherId", 1), ("createdAt", -1)])
    await db.interventions.create_index([("classroomCode", 1), ("createdAt", -1)])

    try:
        from services.learning.activity_recommender import seed_learning_activities
        await seed_learning_activities()
    except Exception:
        pass

    try:
        from services.learning.reading_service import seed_reading_passages
        await seed_reading_passages()
    except Exception:
        pass

    await _migrate_legacy_profiles()
    await _seed_demo_data()
    print("[db] Indexes ready.")


# ─── Migration ──────────────────────────────────────────────────────────────

async def _migrate_legacy_profiles():
    """Upgrade v1 readingProfile docs (score/level/type/recommendation only)
    to the v2 shape in-place, without touching users who have no profile yet
    or who are already on v2. Fully backward compatible — old keys are kept."""
    cursor = db.users.find(
        {
            "readingProfile": {"$ne": None},
            "readingProfile.assessmentVersion": {"$ne": ASSESSMENT_SCHEMA_VERSION},
        },
        {"id": 1, "readingProfile": 1},
    )
    async for u in cursor:
        legacy = u.get("readingProfile") or {}
        upgraded = _default_reading_profile()
        upgraded.update({
            "type": legacy.get("type"),
            "primaryProfile": legacy.get("type"),
            "level": legacy.get("level"),
            "riskLevel": {"low": "Low", "moderate": "Moderate", "high": "High"}.get(legacy.get("level"), None),
            "score": legacy.get("score"),
            "domainScores": legacy.get("domain_scores", {}),
            "strengths": legacy.get("strengths", []),
            "weaknesses": legacy.get("weaknesses", []),
            "recommendation": legacy.get("recommendation"),
            "screenedAt": legacy.get("screenedAt"),
        })
        await db.users.update_one({"id": u["id"]}, {"$set": {"readingProfile": upgraded}})

    # Backfill assessmentVersion on old screening_results docs so version
    # queries/indexes work uniformly across old and new attempts.
    await db.screening_results.update_many(
        {"assessmentVersion": {"$exists": False}},
        {"$set": {"assessmentVersion": 1}},
    )


def build_screening_result_doc(
    user_id: str,
    result: dict,
    student_age: int | None,
    language: str,
    answers_count: int,
) -> dict:
    """Canonical Assessment History document shape (db.screening_results)."""
    now = int(time.time())
    return {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "assessmentVersion": ASSESSMENT_SCHEMA_VERSION,
        "result": result,  # full analyzer output, kept whole for traceability
        "domainScores": result.get("cognitive_profile", result.get("domain_scores", {})),
        "confidence": result.get("confidence"),
        "riskLevel": result.get("risk_level"),
        "primaryProfile": result.get("primary_profile", result.get("type")),
        "learningProfiles": result.get("learning_profiles", {}),
        "strengths": result.get("strengths", []),
        "weaknesses": result.get("weaknesses", []),
        "learningStyle": result.get("learning_style"),
        "uiSettings": result.get("ui_settings", {}),
        "interventions": result.get("interventions", []),
        "studentAge": student_age,
        "language": language,
        "answersCount": answers_count,
        "createdAt": now,
    }


def build_prediction_history_doc(
    user_id: str,
    screening_result_id: str,
    result: dict,
    source: str,
) -> dict:
    """Append-only log of every prediction event (rule-based or ML), so
    re-running an older analyzer version never destroys prior predictions."""
    return {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "screeningResultId": screening_result_id,
        "assessmentVersion": ASSESSMENT_SCHEMA_VERSION,
        "source": source,  # "rule_based" | "ml_model"
        "primaryProfile": result.get("primary_profile", result.get("type")),
        "learningProfiles": result.get("learning_profiles", {}),
        "riskLevel": result.get("risk_level"),
        "confidence": result.get("confidence"),
        "createdAt": int(time.time()),
    }


def build_user_reading_profile(result: dict, screening_result_id: str) -> dict:
    """Fast-read projection embedded at users.{id}.readingProfile — kept in
    sync with the latest screening_results doc."""
    now = int(time.time())
    return {
        "assessmentVersion": ASSESSMENT_SCHEMA_VERSION,
        "type": result.get("primary_profile", result.get("type")),
        "primaryProfile": result.get("primary_profile", result.get("type")),
        "level": result.get("level"),
        "riskLevel": result.get("risk_level"),
        "score": result.get("score"),
        "confidence": result.get("confidence"),
        "domainScores": result.get("cognitive_profile", result.get("domain_scores", {})),
        "cognitiveProfile": result.get("cognitive_profile", {}),
        "learningProfiles": result.get("learning_profiles", {}),
        "strengths": result.get("strengths", []),
        "weaknesses": result.get("weaknesses", []),
        "learningStyle": result.get("learning_style"),
        "uiSettings": result.get("ui_settings", _default_ui_settings()),
        "recommendedActivities": result.get("recommended_activities", []),
        "recommendedGames": result.get("recommended_games", []),
        "interventions": result.get("interventions", []),
        "recommendation": result.get("recommendation"),
        "lastScreeningId": screening_result_id,
        "screenedAt": now,
    }


def build_teacher_note_doc(teacher_id: str, student_id: str, classroom_code: str, note: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "teacherId": teacher_id,
        "studentId": student_id,
        "classroomCode": classroom_code,
        "note": note,
        "createdAt": int(time.time()),
    }


# ─── Demo seeding ───────────────────────────────────────────────────────────

async def _seed_demo_data():
    existing = await db.users.count_documents({"isDemo": True})
    if existing > 0:
        return

    now = int(time.time())
    teacher_id = str(uuid.uuid4())

    await db.users.insert_one({
        "id": teacher_id, "name": "Mrs. Anjali Sharma",
        "email": "teacher@demo.school", "passwordHash": hash_password("Demo@123"),
        "role": "teacher", "classroomCode": "DA-DEMO",
        "schoolName": "Government Primary School, Pune",
        "readingProfile": None, "onboardingComplete": True,
        "languages": ["english", "hindi", "marathi"], "classroomJoined": None,
        "settings": _default_settings(), "isDemo": True, "createdAt": now,
    })

    try:
        await db.classrooms.insert_one({
            "code": "DA-DEMO", "teacherId": teacher_id,
            "teacherName": "Mrs. Anjali Sharma",
            "schoolName": "Government Primary School, Pune",
            "subject": "English & Reading", "createdAt": now,
        })
    except Exception:
        pass

    demo_students = [
        {"name": "Aarav Sharma", "email": "aarav@demo.school", "language": "english",
         "profile": {**_default_reading_profile(), "type": "Phonological Dyslexia", "primaryProfile": "Phonological Dyslexia",
                     "level": "moderate", "riskLevel": "Moderate", "score": 55, "confidence": 72,
                     "learningProfiles": {"Phonological Dyslexia": 78, "Surface Dyslexia": 22, "Visual Dyslexia": 15, "Double Deficit Dyslexia": 30, "Working Memory Deficit": 25, "Reading Fluency Deficit": 40, "Mixed Profile": 18},
                     "strengths": ["Visual Processing"], "weaknesses": ["Phonological Processing", "Reading Accuracy"],
                     "learningStyle": "Auditory-First (Phonics-Based)",
                     "recommendedActivities": ["Phoneme blending games", "Daily rhyme practice"],
                     "recommendedGames": ["Sound Match", "Rhyme Time"],
                     "recommendation": "Daily phonics exercises recommended.", "screenedAt": now},
         "prog": {"docsScanned": 12, "wordsRead": 4200, "avgComprehension": 68, "streak": 5, "sessionCount": 18, "screeningCompleted": True, "planGenerated": True, "weeklyActivity": {"Mon": 2, "Tue": 1, "Wed": 3, "Thu": 0, "Fri": 2, "Sat": 1, "Sun": 2}, "comprehensionScores": [55, 60, 65, 68, 72], "masteredWords": ["water", "cycle", "plant", "cloud"], "wordsMastered": 4, "recentActivity": [{"icon": "scan", "text": "Scanned 'Water Cycle'", "time": "2h ago"}, {"icon": "check", "text": "Quiz 72%", "time": "3h ago"}]}},
        {"name": "Priya Patel", "email": "priya@demo.school", "language": "hindi",
         "profile": {**_default_reading_profile(), "type": "No significant indicators", "primaryProfile": "No significant indicators",
                     "level": "low", "riskLevel": "Low", "score": 15, "confidence": 80,
                     "learningProfiles": {"Phonological Dyslexia": 10, "Surface Dyslexia": 8, "Visual Dyslexia": 5, "Double Deficit Dyslexia": 4, "Working Memory Deficit": 6, "Reading Fluency Deficit": 9, "Mixed Profile": 5},
                     "strengths": ["Phonological Processing", "Reading Fluency"], "weaknesses": [],
                     "learningStyle": "Balanced Multisensory Approach",
                     "recommendedActivities": ["Free reading time"], "recommendedGames": ["Word Explorer"],
                     "recommendation": "Keep reading daily!", "screenedAt": now},
         "prog": {"docsScanned": 18, "wordsRead": 6800, "avgComprehension": 84, "streak": 8, "sessionCount": 25, "screeningCompleted": True, "planGenerated": True, "weeklyActivity": {"Mon": 3, "Tue": 2, "Wed": 2, "Thu": 1, "Fri": 3, "Sat": 2, "Sun": 1}, "comprehensionScores": [75, 80, 82, 84, 86], "masteredWords": ["photosynthesis", "oxygen", "carbon", "leaf", "sunlight"], "wordsMastered": 5}},
        {"name": "Ravi Kumar", "email": "ravi@demo.school", "language": "tamil",
         "profile": {**_default_reading_profile(), "type": "Double Deficit Dyslexia", "primaryProfile": "Double Deficit Dyslexia",
                     "level": "high", "riskLevel": "High", "score": 78, "confidence": 65,
                     "learningProfiles": {"Phonological Dyslexia": 70, "Surface Dyslexia": 30, "Visual Dyslexia": 35, "Double Deficit Dyslexia": 82, "Working Memory Deficit": 55, "Reading Fluency Deficit": 68, "Mixed Profile": 60},
                     "strengths": [], "weaknesses": ["Phonological Processing", "Rapid Automatized Naming (RAN)", "Reading Fluency"],
                     "learningStyle": "Repetition & Fluency-Building",
                     "recommendedActivities": ["Multi-modal phonics + fluency drills"], "recommendedGames": ["Speed Naming", "Sound Match"],
                     "recommendation": "Intensive multi-modal approach — consider specialist referral.", "screenedAt": now},
         "prog": {"docsScanned": 5, "wordsRead": 1200, "avgComprehension": 38, "streak": 1, "sessionCount": 7, "screeningCompleted": True, "planGenerated": True, "weeklyActivity": {"Mon": 1, "Tue": 0, "Wed": 1, "Thu": 0, "Fri": 0, "Sat": 1, "Sun": 0}, "comprehensionScores": [30, 35, 40, 38], "masteredWords": ["water", "sun"], "wordsMastered": 2}},
        {"name": "Sneha Joshi", "email": "sneha@demo.school", "language": "marathi",
         "profile": {**_default_reading_profile(), "type": "Surface Dyslexia", "primaryProfile": "Surface Dyslexia",
                     "level": "moderate", "riskLevel": "Moderate", "score": 42, "confidence": 70,
                     "learningProfiles": {"Phonological Dyslexia": 20, "Surface Dyslexia": 64, "Visual Dyslexia": 30, "Double Deficit Dyslexia": 15, "Working Memory Deficit": 22, "Reading Fluency Deficit": 28, "Mixed Profile": 20},
                     "strengths": ["Phonological Processing"], "weaknesses": ["Orthographic Processing", "Spelling Ability"],
                     "learningStyle": "Visual-Multisensory",
                     "recommendedActivities": ["Irregular word drills", "Sight-word practice"], "recommendedGames": ["Word Builder"],
                     "recommendation": "Irregular word drills recommended.", "screenedAt": now},
         "prog": {"docsScanned": 9, "wordsRead": 3100, "avgComprehension": 61, "streak": 3, "sessionCount": 12, "screeningCompleted": True, "planGenerated": True, "weeklyActivity": {"Mon": 1, "Tue": 1, "Wed": 2, "Thu": 0, "Fri": 1, "Sat": 0, "Sun": 1}, "comprehensionScores": [50, 55, 60, 61], "masteredWords": ["rain", "cloud", "river"], "wordsMastered": 3}},
    ]

    student_ids = []
    for s in demo_students:
        sid = str(uuid.uuid4())
        student_ids.append((sid, s["name"]))
        await db.users.insert_one({
            "id": sid, "name": s["name"], "email": s["email"],
            "passwordHash": hash_password("Demo@123"), "role": "student",
            "classroomCode": None, "schoolName": "Government Primary School, Pune",
            "readingProfile": s["profile"], "onboardingComplete": True,
            "languages": [s["language"]], "classroomJoined": "DA-DEMO",
            "settings": _default_settings(), "isDemo": True, "createdAt": now,
        })
        prog = _default_progress()
        prog.update(s["prog"])
        await db.progress.insert_one({"userId": sid, **prog})
        await db.libraries.insert_one({
            "id": "doc-" + str(uuid.uuid4())[:8], "userId": sid,
            "title": "The Water Cycle", "language": "english", "wordCount": 60,
            "source": "scan",
            "original": "The water cycle describes the continuous movement of water on the Earth.",
            "simplified": "Water moves in a cycle. Sun heats water. Water rises as vapor. Clouds form. Rain falls.",
            "bullet_points": ["Water moves in a cycle.", "Sun heats water into vapor.", "Rain falls from clouds."],
            "highlights": ["water cycle", "vapor", "clouds"], "createdAt": now,
        })

        screening_doc = build_screening_result_doc(
            user_id=sid,
            result={
                "score": s["profile"]["score"], "level": s["profile"]["level"],
                "type": s["profile"]["type"], "primary_profile": s["profile"]["primaryProfile"],
                "risk_level": s["profile"]["riskLevel"], "confidence": s["profile"]["confidence"],
                "learning_profiles": s["profile"]["learningProfiles"],
                "strengths": s["profile"]["strengths"], "weaknesses": s["profile"]["weaknesses"],
                "learning_style": s["profile"]["learningStyle"],
                "ui_settings": s["profile"]["uiSettings"],
                "interventions": [s["profile"]["recommendation"]],
                "cognitive_profile": {}, "domain_scores": {},
            },
            student_age=10, language=s["language"], answers_count=20,
        )
        await db.screening_results.insert_one(screening_doc)
        await db.prediction_history.insert_one(
            build_prediction_history_doc(sid, screening_doc["id"], screening_doc["result"], "rule_based")
        )
        await db.users.update_one(
            {"id": sid},
            {"$set": {"readingProfile.lastScreeningId": screening_doc["id"]}},
        )

    aid = str(uuid.uuid4())
    await db.assignments.insert_one({
        "id": aid, "classroomCode": "DA-DEMO",
        "teacherId": teacher_id, "teacherName": "Mrs. Anjali Sharma",
        "title": "Read Chapter 2: The Water Cycle",
        "description": "Read the simplified Water Cycle passage and answer the quiz.",
        "originalText": "The water cycle describes the continuous movement of water on, above, and below the surface of the Earth. Water evaporates from oceans due to heat from the sun.",
        "simplifiedText": "Water moves in a cycle. The sun heats water. Water rises as vapor. Clouds form. Rain falls.",
        "language": "english", "createdAt": now, "dueDate": now + 86400 * 7, "isDemo": True,
    })

    for i, (sid, sname) in enumerate(student_ids[:2]):
        try:
            await db.submissions.update_one(
                {"assignmentId": aid, "studentId": sid},
                {"$set": {"id": str(uuid.uuid4()), "assignmentId": aid, "studentId": sid, "studentName": sname, "score": [72, 85][i], "comment": "Done", "answers": [], "submittedAt": now}},
                upsert=True,
            )
        except Exception:
            pass

    for sid, sname in student_ids:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()), "userId": sid,
            "title": "New Assignment",
            "message": "Mrs. Anjali Sharma assigned: Read Chapter 2: The Water Cycle",
            "type": "assignment", "assignmentId": aid, "read": False, "createdAt": now,
        })

    await db.teacher_notes.insert_one(
        build_teacher_note_doc(teacher_id, student_ids[2][0], "DA-DEMO", "Needs specialist referral follow-up.")
    )

    print("[seed] Demo ready — teacher@demo.school | aarav/priya/ravi/sneha@demo.school | Demo@123 | code: DA-DEMO")