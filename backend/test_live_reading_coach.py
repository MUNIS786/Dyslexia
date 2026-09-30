"""
backend/test_live_reading_coach.py — Exercises all Phase 4 Live Reading Coach Endpoints.
"""
import urllib.request
import urllib.error
import json

BASE = "http://127.0.0.1:8000/api"

def run():
    print("=" * 60)
    print("      DYSLEXAID V2 PHASE 4: LIVE READING COACH TESTS      ")
    print("=" * 60)

    # 1. Authenticate student
    print("\n[1/8] Authenticating student Aarav Sharma...")
    req = urllib.request.Request(
        f"{BASE}/auth/signin",
        data=json.dumps({"email": "aarav@demo.school", "password": "Demo@123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        auth_data = json.loads(r.read())
        student_token = auth_data.get("token") or auth_data.get("access_token")
        student_id = auth_data["user"]["id"]
        print(f"  --> Student token obtained for ID: {student_id}")

    student_headers = {
        "Authorization": f"Bearer {student_token}",
        "Content-Type": "application/json"
    }

    # 2. Get Reading Recommendation
    print("\n[2/8] Testing GET /v2/reading/recommendation...")
    req = urllib.request.Request(f"{BASE}/v2/reading/recommendation", headers=student_headers)
    with urllib.request.urlopen(req) as r:
        rec = json.loads(r.read())
        passage = rec["recommendedPassage"]
        print(f"  --> Recommended Story: '{passage['title']}' (Level {rec['difficulty']})")
        print(f"  --> Rationale: {rec['reason']}")
        print(f"  --> Questions count: {len(passage.get('questions', []))}")
        print(f"  --> Vocabulary count: {len(passage.get('vocabulary', []))}")

    # 3. List Passages with Tier Filter
    print("\n[3/8] Testing GET /v2/reading/passages?tier=2...")
    req = urllib.request.Request(f"{BASE}/v2/reading/passages?tier=2", headers=student_headers)
    with urllib.request.urlopen(req) as r:
        plist = json.loads(r.read())
        print(f"  --> Found {plist['count']} passages at Level 2")
        for p in plist["passages"]:
            print(f"      - {p['passageId']}: '{p['title']}' ({p['wordCount']} words)")

    # 4. Get Passage by ID
    print("\n[4/8] Testing GET /v2/reading/passages/pas-t1-001...")
    req = urllib.request.Request(f"{BASE}/v2/reading/passages/pas-t1-001", headers=student_headers)
    with urllib.request.urlopen(req) as r:
        p_detail = json.loads(r.read())
        assert p_detail["passage"]["passageId"] == "pas-t1-001"
        print(f"  --> Retrieved: {p_detail['passage']['title']}")

    # 5. Start Reading Session
    print("\n[5/8] Testing POST /v2/reading/session/start...")
    start_payload = {
        "passageId": "pas-t1-001",
        "readingMode": "guided",
        "language": "en"
    }
    req = urllib.request.Request(
        f"{BASE}/v2/reading/session/start",
        data=json.dumps(start_payload).encode(),
        headers=student_headers
    )
    with urllib.request.urlopen(req) as r:
        session_data = json.loads(r.read())
        session_id = session_data["session"]["sessionId"]
        print(f"  --> Started Session ID: {session_id}")
        print(f"  --> Reading Mode: {session_data['session']['readingMode']}")

    # 6. Complete Reading Session
    print("\n[6/8] Testing POST /v2/reading/session/complete...")
    complete_payload = {
        "sessionId": session_id,
        "durationSeconds": 85,
        "readingMode": "guided",
        "wordsRead": 60,
        "comprehensionAnswers": {
            "q-t1-001-1": 1,
            "q-t1-001-2": 2,
            "q-t1-001-3": 1
        },
        "difficultWords": ["purrs"],
        "practicedWords": ["purrs", "paw"],
        "hintsUsed": 0,
        "replaysUsed": 1,
        "completed": True,
        "skipped": False
    }
    req = urllib.request.Request(
        f"{BASE}/v2/reading/session/complete",
        data=json.dumps(complete_payload).encode(),
        headers=student_headers
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
        print(f"  --> Comprehension Score: {result['comprehensionScore']}%")
        print(f"  --> Overall Score: {result['overallScore']}%")
        print(f"  --> Adaptive Next Step: '{result['nextStepMessage']}'")
        print(f"  --> Active Streak: {result['streak']}")

    # 7. Get Reading Stats
    print("\n[7/8] Testing GET /v2/reading/stats...")
    req = urllib.request.Request(f"{BASE}/v2/reading/stats", headers=student_headers)
    with urllib.request.urlopen(req) as r:
        stats = json.loads(r.read())
        print(f"  --> Total Completed Sessions: {stats['completedSessions']}")
        print(f"  --> Total Words Read: {stats['totalWordsRead']}")
        print(f"  --> Avg Comprehension: {stats['avgComprehensionAccuracy']}%")
        print(f"  --> Reading Trend: {stats['trend']}")

    # 8. Teacher Authorization & Student Isolation Check
    print("\n[8/8] Testing Teacher Access & Student Isolation...")
    # Authenticate Teacher
    req = urllib.request.Request(
        f"{BASE}/auth/signin",
        data=json.dumps({"email": "teacher@demo.school", "password": "Demo@123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        t_auth = json.loads(r.read())
        teacher_token = t_auth.get("token") or t_auth.get("access_token")

    t_headers = {
        "Authorization": f"Bearer {teacher_token}",
        "Content-Type": "application/json"
    }

    # Teacher viewing enrolled student reading stats -> should succeed
    req = urllib.request.Request(f"{BASE}/v2/reading/stats?student_id={student_id}", headers=t_headers)
    with urllib.request.urlopen(req) as r:
        t_stats = json.loads(r.read())
        print(f"  --> Teacher successfully viewed student stats: {t_stats['totalSessions']} sessions")

    # Student trying to view someone else's stats -> must be 403 Forbidden
    student_iso_req = urllib.request.Request(
        f"{BASE}/v2/reading/stats?student_id=unauthorized-student-id",
        headers=student_headers
    )
    try:
        with urllib.request.urlopen(student_iso_req) as r:
            assert False, "Should have been rejected!"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print("  --> Student isolation verified: 403 Forbidden on unauthorized student_id")

    print("\n" + "=" * 60)
    print("   >>> ALL 8 LIVE READING COACH TESTS PASSED! <<<   ")
    print("=" * 60)

if __name__ == "__main__":
    run()
