"""
backend/test_live_speech_analysis.py — Live Integration Test for Phase 5 Speech Analysis.
Executes live API requests against running FastAPI backend on http://127.0.0.1:8000
"""
import urllib.request
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000/api"

def run_live_tests():
    print("=" * 60)
    print("    DYSLEXAID V2 PHASE 5 LIVE SPEECH ANALYSIS VERIFICATION    ")
    print("=" * 60)

    # 1. Feature Flag & Version Check
    print("\n[1/8] Verifying V2 Feature Flags on /version...")
    req = urllib.request.Request(f"{BASE}/version")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        flags = data.get("feature_flags", {})
        print(f"  --> App Version: {data.get('version')}")
        print(f"  --> V2_READING_COACH: {flags.get('V2_READING_COACH')}")
        print(f"  --> V2_SPEECH_ANALYSIS: {flags.get('V2_SPEECH_ANALYSIS')}")
        assert flags.get("V2_SPEECH_ANALYSIS") is True, "V2_SPEECH_ANALYSIS should be enabled"
        print("  --> PASS: Feature flag is active!")

    # 2. Authenticate as Student
    print("\n[2/8] Authenticating student 'aarav@demo.school'...")
    login_data = json.dumps({"email": "aarav@demo.school", "password": "Demo@123"}).encode()
    login_req = urllib.request.Request(
        f"{BASE}/auth/signin",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(login_req) as resp:
        auth = json.loads(resp.read())
        token = auth.get("token") or auth.get("access_token")
        student_id = auth["user"]["id"]
        print(f"  --> Student: {auth['user']['name']} (ID: {student_id})")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 3. Start a Reading Session
    print("\n[3/8] Starting a Reading Session for 'pas-t1-001'...")
    start_payload = json.dumps({
        "passageId": "pas-t1-001",
        "readingMode": "speech",
        "language": "en"
    }).encode()
    start_req = urllib.request.Request(f"{BASE}/v2/reading/session/start", data=start_payload, headers=headers)
    with urllib.request.urlopen(start_req) as resp:
        session_data = json.loads(resp.read())
        session_id = session_data["session"]["sessionId"]
        print(f"  --> Started Session ID: {session_id}")
        assert session_id, "Session ID must be returned"

    # 4. Submit Live Speech Analysis
    print("\n[4/8] Submitting live speech reading transcript to POST /v2/reading/speech/analyze...")
    speech_payload = json.dumps({
        "sessionId": session_id,
        "passageId": "pas-t1-001",
        "transcript": (
            "Sam is a fat cat. Sam is bright orange. "
            "He sits on a red mat. The sun is hot. "
            "Sam sees a little bug. The bug hops on the log."
        ),
        "durationSeconds": 20,
        "pauseCount": 2,
        "hesitationCount": 1,
        "confidenceSummary": {
            "average": 0.94,
            "min": 0.88,
            "max": 0.99,
            "sampleCount": 14
        },
        "readingMode": "speech"
    }).encode()

    speech_req = urllib.request.Request(f"{BASE}/v2/reading/speech/analyze", data=speech_payload, headers=headers)
    with urllib.request.urlopen(speech_req) as resp:
        res = json.loads(resp.read())
        analysis = res["analysis"]
        print(f"  --> Analysis ID: {analysis['analysisId']}")
        print(f"  --> Word Accuracy: {analysis['wordAccuracy']}%")
        print(f"  --> Coverage Rate: {analysis['coverageRate']}%")
        print(f"  --> Reading Pace: {analysis['wordsPerMinute']} WPM")
        print(f"  --> Practice Score: {analysis['readingPracticeScore']}/100")
        print(f"  --> Child-friendly Feedback: {res['childFriendlyFeedback']}")
        print(f"  --> Next Action: {res['nextActionSuggestion']}")

        assert analysis["wordAccuracy"] > 40.0
        assert analysis["wordsPerMinute"] > 0.0
        assert "audio" not in analysis, "PRIVACY VIOLATION: Raw audio must not be stored"

    # 5. Fetch Analysis via GET /v2/reading/speech/sessions/{sessionId}
    print(f"\n[5/8] Fetching analysis via GET /v2/reading/speech/sessions/{session_id}...")
    fetch_req = urllib.request.Request(f"{BASE}/v2/reading/speech/sessions/{session_id}", headers=headers)
    with urllib.request.urlopen(fetch_req) as resp:
        fetch_res = json.loads(resp.read())
        fetched_analysis = fetch_res["analysis"]
        assert fetched_analysis["sessionId"] == session_id
        assert fetched_analysis["wordAccuracy"] == analysis["wordAccuracy"]
        print("  --> PASS: Retrieved matching analysis record!")

    # 6. Complete Reading Session (blending speech metrics)
    print("\n[6/8] Completing session via POST /v2/reading/session/complete...")
    complete_payload = json.dumps({
        "sessionId": session_id,
        "durationSeconds": 35,
        "readingMode": "speech",
        "wordsRead": 54,
        "comprehensionAnswers": {
            "q-t1-001-1": 1,
            "q-t1-001-2": 1,
            "q-t1-001-3": 2,
        },
        "difficultWords": ["bug"],
        "practicedWords": ["orange"],
        "hintsUsed": 0,
        "replaysUsed": 0,
        "completed": True,
        "skipped": False,
    }).encode()

    complete_req = urllib.request.Request(f"{BASE}/v2/reading/session/complete", data=complete_payload, headers=headers)
    with urllib.request.urlopen(complete_req) as resp:
        comp_res = json.loads(resp.read())
        print(f"  --> Session Complete Status: {comp_res['status']}")
        print(f"  --> Reading Score: {comp_res['readingScore']}")
        print(f"  --> Comprehension Score: {comp_res['comprehensionScore']}%")
        print(f"  --> Overall Score: {comp_res['overallScore']}/100")
        print(f"  --> Child-friendly Next Step: {comp_res['nextStepMessage']}")

    # 7. Verify Reading Stats
    print("\n[7/8] Verifying Reading Stats reflect speech practice...")
    stats_req = urllib.request.Request(f"{BASE}/v2/reading/stats", headers=headers)
    with urllib.request.urlopen(stats_req) as resp:
        stats = json.loads(resp.read())
        print(f"  --> Total Sessions: {stats['totalSessions']}")
        print(f"  --> Total Words Read: {stats['totalWordsRead']}")
        print(f"  --> Fluency Domain Score: {stats['domainPerformance'].get('reading_fluency')}")
        assert stats["totalSessions"] > 0

    # 8. Cross-student Security Verification
    print("\n[8/8] Verifying cross-student access is rejected (403)...")
    sec_req = urllib.request.Request(
        f"{BASE}/v2/reading/speech/sessions/{session_id}?student_id=some-other-student-999",
        headers=headers
    )
    try:
        urllib.request.urlopen(sec_req)
        raise AssertionError("Cross-student query should have been rejected with 403!")
    except urllib.error.HTTPError as he:
        print(f"  --> Correctly rejected with HTTP {he.code}: {he.reason}")
        assert he.code == 403
        print("  --> PASS: Security check succeeded!")

    print("\n" + "=" * 60)
    print("   ALL 8 LIVE SPEECH READING INTEGRATION CHECKS PASSED!   ")
    print("=" * 60)


if __name__ == "__main__":
    run_live_tests()
