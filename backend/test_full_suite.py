"""
backend/test_full_suite.py — Comprehensive End-to-End API Integration Suite
Tests all core services:
1. Health & Version
2. Auth (Student & Teacher login, /auth/me)
3. Screening (/api/screening/questions)
4. V2 Learner Profile & Adaptive Engine
5. Daily Tasks
6. Text Simplification & Reading Companion
7. Library
8. Progress & Analytics
9. Teacher Classroom & Student Roster
"""
import urllib.request
import json
import sys

BASE = 'http://127.0.0.1:8000/api'

def run():
    print("=" * 60)
    print("  DYSLEXAID FULL PLATFORM TEST SUITE (FRONT & BACKEND APIS) ")
    print("=" * 60)
    
    passed = 0
    total = 0

    def check(name, fn):
        nonlocal passed, total
        total += 1
        print(f"\n[Test {total}] {name}...", end=" ")
        try:
            fn()
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            raise e

    # 1. Health & Version
    def test_health():
        with urllib.request.urlopen(f"{BASE}/health") as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert data.get("status") == "ok"
    check("System Health API", test_health)

    def test_version():
        with urllib.request.urlopen(f"{BASE}/version") as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert data.get("application") == "DyslexAid"
            assert data.get("v2_enabled") is True
    check("Version & V2 Feature Flags", test_version)

    # 2. Student Auth
    student_token = None
    student_id = None
    def test_student_auth():
        nonlocal student_token, student_id
        payload = json.dumps({'email': 'aarav@demo.school', 'password': 'Demo@123'}).encode()
        req = urllib.request.Request(f"{BASE}/auth/signin", data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            student_token = data.get("token") or data.get("access_token")
            student_id = data["user"]["id"]
            assert student_token is not None
            assert data["user"]["role"] == "student"
    check("Student Authentication (/auth/signin)", test_student_auth)

    st_headers = {'Authorization': f'Bearer {student_token}', 'Content-Type': 'application/json'}

    # 3. Auth Me
    def test_auth_me():
        req = urllib.request.Request(f"{BASE}/auth/me", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert data.get("id") == student_id
    check("Token Identity Verification (/auth/me)", test_auth_me)

    # 4. Screening Questions
    def test_screening_questions():
        req = urllib.request.Request(f"{BASE}/dyslexia-test/questions?age=10", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert data.get("total_questions", 0) > 0
            assert "sections" in data
    check("Dyslexia Screening Questions Catalog", test_screening_questions)

    # 5. V2 Learner Profile
    def test_learner_profile():
        req = urllib.request.Request(f"{BASE}/v2/learner/profile", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert "profile" in data
            assert "learning_level" in data["profile"]
    check("V2 Learner Profile & Diagnostic Data", test_learner_profile)

    # 6. V2 Recommendations
    def test_recommendations():
        req = urllib.request.Request(f"{BASE}/v2/learning/recommendations?count=3", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0
    check("V2 Adaptive Activity Recommendations", test_recommendations)

    # 7. Daily Tasks
    def test_daily_tasks():
        req = urllib.request.Request(f"{BASE}/tasks", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert "tasks" in data or "items" in data or isinstance(data, list)
    check("Student Daily Tasks Service", test_daily_tasks)

    # 8. Text Simplify
    def test_simplify():
        body = json.dumps({
            "text": "Photosynthesis is the sophisticated biochemical process by which photochemical energy converts carbon dioxide into glucose.",
            "mode": "standard"
        }).encode()
        req = urllib.request.Request(f"{BASE}/simplify", data=body, headers=st_headers)
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert "simplified" in data or "text" in data
    check("Assistive Text Simplification Pipeline", test_simplify)

    # 9. Library
    def test_library():
        req = urllib.request.Request(f"{BASE}/library", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert "docs" in data or "items" in data or isinstance(data, list)
    check("Student Document Library", test_library)

    # 10. Progress
    def test_progress():
        req = urllib.request.Request(f"{BASE}/progress/summary", headers={'Authorization': f'Bearer {student_token}'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            assert "streak" in data
    check("Reading Progress & Analytics Summary", test_progress)

    # 11. Teacher Auth & Classroom
    teacher_token = None
    def test_teacher():
        nonlocal teacher_token
        payload = json.dumps({'email': 'teacher@demo.school', 'password': 'Demo@123'}).encode()
        req = urllib.request.Request(f"{BASE}/auth/signin", data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            data = json.loads(r.read())
            teacher_token = data.get("token") or data.get("access_token")
            assert data["user"]["role"] == "teacher"

        req2 = urllib.request.Request(f"{BASE}/teacher/students", headers={'Authorization': f'Bearer {teacher_token}'})
        with urllib.request.urlopen(req2) as r2:
            assert r2.status == 200
            c_data = json.loads(r2.read())
            assert isinstance(c_data, list)
            assert len(c_data) > 0
    check("Teacher Portal & Classroom Roster", test_teacher)

    print("\n" + "=" * 60)
    print(f"  RESULT: ALL {passed}/{total} TESTS PASSED SUCCESSFULLY! ")
    print("=" * 60)

if __name__ == "__main__":
    run()
