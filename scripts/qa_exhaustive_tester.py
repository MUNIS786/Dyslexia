#!/usr/bin/env python3
"""
scripts/qa_exhaustive_tester.py — Comprehensive Manual QA Testing Automation for DyslexAid.
Exercises full user workflows (Student, Teacher, Parent), all V1 & V2 APIs,
data integrity, error boundary cases, and role security boundaries.
"""
import sys
import os
import json
import uuid
import asyncio
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import httpx
from main import app
from database.database import init_db

errors = []
test_count = 0
passed_count = 0

def test_step(title):
    global test_count
    test_count += 1
    print(f"\n[{test_count}] TEST: {title}")

def check_status(response, expected_status, step_name):
    global passed_count, errors
    expected_list = expected_status if isinstance(expected_status, (list, tuple, set)) else [expected_status]
    if response.status_code in expected_list:
        passed_count += 1
        print(f"  [PASS] {step_name} (Status {response.status_code})")
        return True
    else:
        err_msg = f"  [FAIL] {step_name} FAILED! Expected {expected_status}, got {response.status_code}. Body: {response.text[:300]}"
        print(err_msg)
        errors.append((step_name, response.status_code, response.text[:300]))
        return False


async def run_exhaustive_qa():
    global passed_count, test_count, errors
    print("=" * 70)
    print("  DYSLEXAID EXHAUSTIVE MANUAL QA TEST EXECUTION")
    print("=" * 70)

    await init_db()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=30.0) as client:
        unique_suffix = uuid.uuid4().hex[:6]
        student_email = f"student_{unique_suffix}@example.com"
        teacher_email = f"teacher_{unique_suffix}@example.com"
        parent_email = f"parent_{unique_suffix}@example.com"
        password = "Password123!"

        # ----------------------------------------------------
        # 1. Health, Readiness, and Version
        # ----------------------------------------------------
        test_step("Health, Readiness & Version Endpoints")
        r = await client.get("/api/health")
        check_status(r, 200, "GET /api/health")
        
        r = await client.get("/api/ready")
        check_status(r, 200, "GET /api/ready")
        
        r = await client.get("/api/version")
        check_status(r, 200, "GET /api/version")

        # ----------------------------------------------------
        # 2. Student Registration & Authentication
        # ----------------------------------------------------
        test_step("Student Signup, Login & Profile")
        r = await client.post("/api/auth/signup", json={
            "name": "Arjun QA Student",
            "email": student_email,
            "password": password,
            "role": "student",
            "schoolName": "Modern Public School",
            "age": 10,
            "languages": ["english", "marathi"]
        })
        check_status(r, 200, "Student Signup")
        s_data = r.json() if r.status_code == 200 else {}
        student_token = s_data.get("token", "")
        student_id = s_data.get("user", {}).get("id", "")
        student_headers = {"Authorization": f"Bearer {student_token}"}

        r = await client.post("/api/auth/signin", json={"email": student_email, "password": password})
        check_status(r, 200, "Student Signin")

        r = await client.get("/api/auth/me", headers=student_headers)
        check_status(r, 200, "Student GET /api/auth/me")

        # ----------------------------------------------------
        # 3. Dyslexia Screening & DST Evaluation
        # ----------------------------------------------------
        test_step("Dyslexia Screening Test (/api/dyslexia-test)")
        r = await client.get("/api/dyslexia-test/questions", headers=student_headers)
        check_status(r, 200, "GET /api/dyslexia-test/questions")
        questions_resp = r.json()
        sections_dict = questions_resp.get("sections", {})
        questions = []
        for sec_list in sections_dict.values():
            if isinstance(sec_list, list):
                questions.extend(sec_list)

        # Submit answers
        sample_answers = []
        for q in questions[:10]:
            sample_answers.append({
                "question_id": q.get("id"),
                "question_type": q.get("question_type") or q.get("type") or "rhyme",
                "given_answer": "sample answer",
                "correct": True,
                "slow_response": False,
                "time_taken_seconds": 3.5
            })
        
        r = await client.post("/api/dyslexia-test/submit", json={
            "answers": sample_answers,
            "student_age": 10
        }, headers=student_headers)
        check_status(r, 200, "POST /api/dyslexia-test/submit")

        r = await client.get("/api/dyslexia-test/history", headers=student_headers)
        check_status(r, 200, "GET /api/dyslexia-test/history")

        # ----------------------------------------------------
        # 4. V2 Learner Profile & Adaptive Engine
        # ----------------------------------------------------
        test_step("V2 Learner Profile & Adaptive Learning")
        r = await client.get("/api/v2/learner/profile", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learner/profile")

        r = await client.get("/api/v2/learner/state", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learner/state")

        r = await client.get("/api/v2/learning/tier-info", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learning/tier-info")

        r = await client.get("/api/v2/learning/activities", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learning/activities")

        r = await client.get("/api/v2/learning/recommendations?count=3", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learning/recommendations")

        r = await client.post("/api/v2/learning/attempt", json={
            "activityId": "act-phon-001",
            "scorePercent": 85.0,
            "durationSeconds": 60,
            "hesitationCount": 1,
            "hintsRequested": 0,
            "completed": True,
            "mistakes": []
        }, headers=student_headers)
        check_status(r, 200, "POST /api/v2/learning/attempt")

        # ----------------------------------------------------
        # 5. Accessibility & Multilingual Preferences
        # ----------------------------------------------------
        test_step("Accessibility & Multilingual Preferences")
        r = await client.get("/api/v2/accessibility/preferences", headers=student_headers)
        check_status(r, 200, "GET /api/v2/accessibility/preferences")

        r = await client.patch("/api/v2/accessibility/preferences", json={
            "font": "OpenDyslexic",
            "fontSize": 20,
            "lineSpacing": 1.8,
            "readingRuler": True,
            "highContrast": False
        }, headers=student_headers)
        check_status(r, 200, "PATCH /api/v2/accessibility/preferences")

        r = await client.get("/api/v2/multilingual/languages", headers=student_headers)
        check_status(r, 200, "GET /api/v2/multilingual/languages")

        r = await client.put("/api/v2/multilingual/preference", json={"language": "mr"}, headers=student_headers)
        check_status(r, 200, "PUT /api/v2/multilingual/preference")

        r = await client.get("/api/v2/multilingual/preference", headers=student_headers)
        check_status(r, 200, "GET /api/v2/multilingual/preference")

        # ----------------------------------------------------
        # 6. Reading Coach & Speech Analysis
        # ----------------------------------------------------
        test_step("Reading Coach, Passages, Sessions & Speech")
        r = await client.get("/api/v2/reading/recommendation?language=mr", headers=student_headers)
        check_status(r, 200, "GET /api/v2/reading/recommendation")

        r = await client.get("/api/v2/reading/passages", headers=student_headers)
        check_status(r, 200, "GET /api/v2/reading/passages")
        passages = r.json().get("passages", [])
        if passages:
            passage = passages[0]
            passage_id = passage.get("passageId") or passage.get("id")

            r = await client.get(f"/api/v2/reading/passages/{passage_id}", headers=student_headers)
            check_status(r, 200, f"GET /api/v2/reading/passages/{passage_id}")

            r = await client.post("/api/v2/reading/session/start", json={
                "passageId": passage_id,
                "readingMode": "standard"
            }, headers=student_headers)
            check_status(r, 200, "POST /api/v2/reading/session/start")
            session_id = r.json().get("sessionId")

            # Speech Analysis
            r = await client.post("/api/v2/reading/speech/analyze", json={
                "passageId": passage_id,
                "sessionId": session_id,
                "expectedText": passage.get("text", "The quick brown fox"),
                "transcript": "The quick brown fox jumped high",
                "speakingDurationSeconds": 12,
                "pauseCount": 1,
                "hesitationCount": 0,
                "averageConfidence": 0.95,
                "language": passage.get("language", "en")
            }, headers=student_headers)
            check_status(r, 200, "POST /api/v2/reading/speech/analyze")

            if session_id:
                r = await client.get(f"/api/v2/reading/speech/sessions/{session_id}", headers=student_headers)
                check_status(r, 200, f"GET /api/v2/reading/speech/sessions/{session_id}")

            # Complete reading session
            r = await client.post("/api/v2/reading/session/complete", json={
                "sessionId": session_id,
                "passageId": passage_id,
                "durationSeconds": 35,
                "wordsRead": len(passage.get("text", "").split()),
                "comprehensionAnswers": {"q1": "a"},
                "hintsUsed": 0,
                "replaysUsed": 0,
                "practicedDifficultWords": []
            }, headers=student_headers)
            check_status(r, 200, "POST /api/v2/reading/session/complete")

            r = await client.get("/api/v2/reading/sessions", headers=student_headers)
            check_status(r, 200, "GET /api/v2/reading/sessions")

            r = await client.get("/api/v2/reading/stats", headers=student_headers)
            check_status(r, 200, "GET /api/v2/reading/stats")

        # ----------------------------------------------------
        # 7. Gamification & Rewards
        # ----------------------------------------------------
        test_step("Gamification, Achievements & Streaks")
        r = await client.get("/api/v2/gamification/summary", headers=student_headers)
        check_status(r, 200, "GET /api/v2/gamification/summary")

        r = await client.get("/api/v2/gamification/achievements", headers=student_headers)
        check_status(r, 200, "GET /api/v2/gamification/achievements")

        r = await client.get("/api/v2/gamification/milestones", headers=student_headers)
        check_status(r, 200, "GET /api/v2/gamification/milestones")

        r = await client.post("/api/v2/gamification/claim-event", json={
            "eventType": "READING_SESSION_COMPLETED",
            "metadata": {"wordsRead": 50}
        }, headers=student_headers)
        check_status(r, 200, "POST /api/v2/gamification/claim-event")

        # ----------------------------------------------------
        # 8. Personalized Content & Insights
        # ----------------------------------------------------
        test_step("Personalized Content, Insights & Recommendations")
        r = await client.get("/api/v2/personalized-content/next", headers=student_headers)
        check_status(r, 200, "GET /api/v2/personalized-content/next")

        r = await client.get("/api/v2/personalized-content/activities", headers=student_headers)
        check_status(r, 200, "GET /api/v2/personalized-content/activities")

        r = await client.post("/api/v2/personalized-content/launch", json={
            "activityId": "act-test-001",
            "activityType": "GUIDED_READING"
        }, headers=student_headers)
        check_status(r, 200, "POST /api/v2/personalized-content/launch")

        r = await client.get("/api/v2/learning-insights/student?period=30d", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learning-insights/student")

        r = await client.get("/api/v2/learning-recommendations/student", headers=student_headers)
        check_status(r, 200, "GET /api/v2/learning-recommendations/student")

        r = await client.post("/api/v2/learning-recommendations/student/refresh", headers=student_headers)
        check_status(r, 200, "POST /api/v2/learning-recommendations/student/refresh")

        # ----------------------------------------------------
        # 9. AI Tutor Chat & History
        # ----------------------------------------------------
        test_step("AI Tutor Chat & Context")
        r = await client.get("/api/v2/tutor/context", headers=student_headers)
        check_status(r, 200, "GET /api/v2/tutor/context")

        r = await client.post("/api/v2/tutor/chat", json={
            "message": "Hello tutor! Can you help me read better?",
            "context": {"topic": "reading"}
        }, headers=student_headers)
        check_status(r, 200, "POST /api/v2/tutor/chat")

        r = await client.get("/api/v2/tutor/history", headers=student_headers)
        check_status(r, 200, "GET /api/v2/tutor/history")

        r = await client.delete("/api/v2/tutor/history", headers=student_headers)
        check_status(r, 200, "DELETE /api/v2/tutor/history")

        # ----------------------------------------------------
        # 10. Tasks, Library, Progress & Simplification
        # ----------------------------------------------------
        test_step("Tasks, Library, Progress & Simplifier")
        r = await client.get("/api/tasks", headers=student_headers)
        check_status(r, 200, "GET /api/tasks")
        tasks = r.json()
        if isinstance(tasks, list) and tasks:
            t_id = tasks[0].get("id")
            if t_id:
                r = await client.post(f"/api/tasks/{t_id}/complete", headers=student_headers)
                check_status(r, 200, f"POST /api/tasks/{t_id}/complete")

        r = await client.get("/api/library", headers=student_headers)
        check_status(r, 200, "GET /api/library")

        r = await client.post("/api/library", json={
            "title": "QA Test Story",
            "author": "Arjun",
            "text": "Once upon a time in a beautiful forest lived a friendly deer.",
            "simplified": "A friendly deer lived in a nice forest.",
            "grade": "Grade 2",
            "tags": ["nature", "animals"]
        }, headers=student_headers)
        check_status(r, 200, "POST /api/library")
        saved_doc_id = r.json().get("id")

        if saved_doc_id:
            r = await client.get(f"/api/library/{saved_doc_id}", headers=student_headers)
            check_status(r, 200, f"GET /api/library/{saved_doc_id}")

        r = await client.get("/api/progress", headers=student_headers)
        check_status(r, 200, "GET /api/progress")

        r = await client.get("/api/progress/summary", headers=student_headers)
        check_status(r, 200, "GET /api/progress/summary")

        r = await client.post("/api/simplify", json={
            "text": "Photosynthesis is the chemical process by which green plants synthesize nutrients from carbon dioxide and water.",
            "grade": "Grade 3"
        }, headers=student_headers)
        check_status(r, 200, "POST /api/simplify")

        r = await client.get("/api/ai-plan", headers=student_headers)
        check_status(r, 200, "GET /api/ai-plan")

        # ----------------------------------------------------
        # 11. Teacher Signup, Classroom & Analytics
        # ----------------------------------------------------
        test_step("Teacher Experience: Classroom & Analytics")
        r = await client.post("/api/auth/signup", json={
            "name": "Prof. Meera Sharma",
            "email": teacher_email,
            "password": password,
            "role": "teacher",
            "schoolName": "Modern Public School"
        })
        check_status(r, 200, "Teacher Signup")
        t_data = r.json() if r.status_code == 200 else {}
        teacher_token = t_data.get("token", "")
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        classroom_code = t_data.get("user", {}).get("classroomCode")
        print(f"  Classroom Code: {classroom_code}")

        # Student joins classroom
        r = await client.post("/api/classroom/join", json={"code": classroom_code}, headers=student_headers)
        check_status(r, 200, "Student joins classroom")

        r = await client.get("/api/classroom/students", headers=teacher_headers)
        check_status(r, 200, "Teacher lists classroom students")

        r = await client.post("/api/classroom/announce", json={"message": "Welcome students to new reading goals!"}, headers=teacher_headers)
        check_status(r, 200, "Teacher classroom announce")

        r = await client.get("/api/v2/teacher/analytics/overview", headers=teacher_headers)
        check_status(r, 200, "GET /api/v2/teacher/analytics/overview")

        r = await client.get("/api/v2/teacher/analytics/learners", headers=teacher_headers)
        check_status(r, 200, "GET /api/v2/teacher/analytics/learners")

        r = await client.get(f"/api/v2/teacher/analytics/learners/{student_id}", headers=teacher_headers)
        check_status(r, 200, f"GET /api/v2/teacher/analytics/learners/{student_id}")

        r = await client.get(f"/api/v2/teacher/analytics/learners/{student_id}/trend", headers=teacher_headers)
        check_status(r, 200, f"GET /api/v2/teacher/analytics/learners/{student_id}/trend")

        r = await client.get(f"/api/v2/learner/student/{student_id}/profile", headers=teacher_headers)
        check_status(r, 200, f"GET /api/v2/learner/student/{student_id}/profile")

        r = await client.get(f"/api/v2/learning-insights/teacher/overview", headers=teacher_headers)
        check_status(r, 200, "GET /api/v2/learning-insights/teacher/overview")

        r = await client.get(f"/api/v2/learning-insights/teacher/{student_id}", headers=teacher_headers)
        check_status(r, 200, f"GET /api/v2/learning-insights/teacher/{student_id}")

        r = await client.get(f"/api/v2/learning-recommendations/teacher/{student_id}", headers=teacher_headers)
        check_status(r, 200, f"GET /api/v2/learning-recommendations/teacher/{student_id}")

        r = await client.get(f"/api/v2/personalized-content/teacher/{student_id}", headers=teacher_headers)
        check_status(r, 200, f"GET /api/v2/personalized-content/teacher/{student_id}")

        # ----------------------------------------------------
        # 12. Teacher Interventions Engine
        # ----------------------------------------------------
        test_step("Teacher Interventions Lifecycle")
        r = await client.post("/api/v2/teacher/interventions", json={
            "studentId": student_id,
            "title": "Phonics Mastery Intervention",
            "tier": 2,
            "targetArea": "Phonological Awareness",
            "description": "Structured daily blending drill",
            "startDate": "2026-10-15",
            "durationWeeks": 4
        }, headers=teacher_headers)
        check_status(r, [200, 201], "Create Intervention")
        intervention_id = r.json().get("interventionId") or r.json().get("id")

        if intervention_id:
            r = await client.post(f"/api/v2/teacher/interventions/{intervention_id}/start", headers=teacher_headers)
            check_status(r, 200, "Start Intervention")

            r = await client.post(f"/api/v2/teacher/interventions/{intervention_id}/measurements", json={
                "accuracy": 89.0,
                "wpm": 60.0,
                "comprehension": 80.0,
                "notes": "Good progress"
            }, headers=teacher_headers)
            check_status(r, [200, 201], "Add Intervention Measurement")

            r = await client.get(f"/api/v2/teacher/interventions/{intervention_id}/effectiveness", headers=teacher_headers)
            check_status(r, 200, "Get Intervention Effectiveness")

            r = await client.post(f"/api/v2/teacher/interventions/{intervention_id}/review", headers=teacher_headers)
            check_status(r, 200, "Review Intervention")

            r = await client.post(f"/api/v2/teacher/interventions/{intervention_id}/complete", headers=teacher_headers)
            check_status(r, 200, "Complete Intervention")

        # ----------------------------------------------------
        # 13. Content Authoring Lifecycle
        # ----------------------------------------------------
        test_step("Teacher Content Authoring Lifecycle")
        # Author creates draft
        r = await client.post("/api/v2/content-authoring/drafts", json={
            "title": "A Day in the Rainforest",
            "description": "Engaging reading passage about trees and wildlife",
            "text": "Tall trees reach up to the sunny sky. Colorful birds sing cheerful songs from high branches.",
            "language": "en",
            "difficultyTier": 2,
            "targetSkills": ["phonics", "comprehension"]
        }, headers=teacher_headers)
        check_status(r, [200, 201], "Create Content Draft")
        draft_content_id = r.json().get("contentId") or r.json().get("id")

        # Second educator account for separation-of-duties peer review
        reviewer_email = f"reviewer_{unique_suffix}@example.com"
        r_rev = await client.post("/api/auth/signup", json={
            "name": "Prof Anita Reviewer",
            "email": reviewer_email,
            "password": password,
            "role": "teacher"
        })
        reviewer_token = r_rev.json().get("token", "")
        reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

        if draft_content_id:
            r = await client.post("/api/v2/content-authoring/validate", json={
                "title": "A Day in the Rainforest",
                "text": "Tall trees reach up to the sunny sky. Colorful birds sing cheerful songs from high branches.",
                "language": "en",
                "difficultyTier": 2
            }, headers=teacher_headers)
            check_status(r, 200, "Validate Content")

            r = await client.post(f"/api/v2/content-authoring/drafts/{draft_content_id}/submit", headers=teacher_headers)
            check_status(r, 200, "Submit Draft for Review")

            r = await client.get("/api/v2/content-authoring/review-queue", headers=reviewer_headers)
            check_status(r, 200, "Get Review Queue")

            # Peer reviewer evaluates draft
            r = await client.post(f"/api/v2/content-authoring/review/{draft_content_id}/decision", json={
                "decision": "APPROVED",
                "notes": "Approved for classroom release"
            }, headers=reviewer_headers)
            check_status(r, 200, "Approve Content Review")

            # Publication
            r = await client.post(f"/api/v2/content-authoring/items/{draft_content_id}/publish", headers=reviewer_headers)
            check_status(r, 200, "Publish Content Item")

            r = await client.get(f"/api/v2/content-authoring/items/{draft_content_id}/history", headers=reviewer_headers)
            check_status(r, 200, "Get Content Item History")

        # ----------------------------------------------------
        # 14. Parent Portal Experience
        # ----------------------------------------------------
        test_step("Parent Signup, Linking & Dashboards")
        r = await client.post("/api/auth/signup", json={
            "name": "Sunita QA Parent",
            "email": parent_email,
            "password": password,
            "role": "parent"
        })
        check_status(r, 200, "Parent Signup")
        p_data = r.json() if r.status_code == 200 else {}
        parent_token = p_data.get("token", "")
        parent_headers = {"Authorization": f"Bearer {parent_token}"}

        # Student generates invitation code
        r = await client.post("/api/v2/parent/invitations/generate", headers=student_headers)
        check_status(r, 200, "Student Generates Invitation Code")
        invitation_code = r.json().get("invitationCode") or r.json().get("code")

        if invitation_code:
            r = await client.post("/api/v2/parent/link/claim-code", json={
                "code": invitation_code,
                "relationship": "Mother"
            }, headers=parent_headers)
            check_status(r, [200, 201], "Parent Claims Invitation Code")

        r = await client.get(f"/api/v2/parent/dashboard?student_id={student_id}", headers=parent_headers)
        check_status(r, 200, f"Parent Dashboard for Student {student_id}")

        r = await client.get("/api/v2/parent/learners", headers=parent_headers)
        check_status(r, 200, "Parent lists linked learners")

        r = await client.get(f"/api/v2/parent/learners/{student_id}/activity", headers=parent_headers)
        check_status(r, 200, f"Parent views learner activity for {student_id}")

        r = await client.get(f"/api/v2/learning-insights/parent/{student_id}", headers=parent_headers)
        check_status(r, 200, f"Parent views learner insights for {student_id}")

        r = await client.get(f"/api/v2/learning-recommendations/parent/{student_id}", headers=parent_headers)
        check_status(r, 200, f"Parent views learner recommendations for {student_id}")

        r = await client.get(f"/api/v2/personalized-content/parent/{student_id}", headers=parent_headers)
        check_status(r, 200, f"Parent views personalized content for {student_id}")

        # ----------------------------------------------------
        # 15. Security Boundaries & Authorization Tests
        # ----------------------------------------------------
        test_step("Security Boundaries & Role Access Control")
        # Student attempting teacher endpoint
        r = await client.get("/api/v2/teacher/analytics/overview", headers=student_headers)
        check_status(r, 403, "Student blocked from Teacher Analytics (403)")

        r = await client.post("/api/v2/teacher/interventions", json={"studentId": student_id}, headers=student_headers)
        check_status(r, 403, "Student blocked from Creating Interventions (403)")

        # Unauthenticated calls
        r = await client.get("/api/v2/reading/stats")
        check_status(r, 401, "Unauthenticated blocked from Reading Stats (401)")

        r = await client.get("/api/v2/learner/profile")
        check_status(r, 401, "Unauthenticated blocked from Learner Profile (401)")

        # Invalid route
        r = await client.get("/api/v2/non-existent-qa-path")
        check_status(r, 404, "Invalid route returns 404")

        # ----------------------------------------------------
        # Summary Report
        # ----------------------------------------------------
        print("\n" + "=" * 70)
        print(f"  EXHAUSTIVE QA TESTING SUMMARY")
        print(f"  TOTAL TESTS EXECUTED : {test_count}")
        print(f"  PASSED               : {passed_count}")
        print(f"  FAILED               : {len(errors)}")
        if errors:
            print("\n  DETECTED FAILURES:")
            for name, code, body in errors:
                print(f"   [!] {name} -> Status {code}: {body}")
        else:
            print("\n  ALL TESTS PASSED CLEANLY WITH ZERO ERRORS!")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_exhaustive_qa())
