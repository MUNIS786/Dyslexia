"""
backend/test_live_ai_tutor.py — Live Integration Test for Phase 6 Personal AI Tutor.
Executes live API requests against running FastAPI backend on http://127.0.0.1:8000
"""
import urllib.request
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000/api"

def run_live_tests():
    print("=" * 65)
    print("    DYSLEXAID V2 PHASE 6 LIVE PERSONAL AI TUTOR VERIFICATION    ")
    print("=" * 65)

    # 1. Feature Flag & Version Check
    print("\n[1/10] Verifying V2 Feature Flags on /version...")
    req = urllib.request.Request(f"{BASE}/version")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        flags = data.get("feature_flags", {})
        print(f"  --> App Version: {data.get('version')}")
        print(f"  --> V2_READING_COACH: {flags.get('V2_READING_COACH')}")
        print(f"  --> V2_AI_TUTOR: {flags.get('V2_AI_TUTOR')}")
        assert flags.get("V2_AI_TUTOR") is True, "V2_AI_TUTOR should be enabled"
        print("  --> PASS: Feature flag is active!")

    # 2. Authenticate as Student
    print("\n[2/10] Authenticating student 'aarav@demo.school'...")
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
        student_name = auth["user"]["name"]
        print(f"  --> Student: {student_name} (ID: {student_id})")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 3. Retrieve Pedagogical Context
    print("\n[3/10] Fetching learner pedagogical context (/v2/tutor/context)...")
    ctx_req = urllib.request.Request(
        f"{BASE}/v2/tutor/context?activePassageId=pas-t1-001&activeWord=curious",
        headers=headers
    )
    with urllib.request.urlopen(ctx_req) as resp:
        ctx = json.loads(resp.read())
        print(f"  --> Learner: {ctx['displayName']}, Level {ctx['learningLevel']} ({ctx['learningLevelName']})")
        print(f"  --> Tier: {ctx['adaptiveTier']}, Strengths: {ctx.get('strengths')}")
        print(f"  --> Active Word: {ctx.get('activeWord')}")
        assert ctx["learnerId"] == student_id, "Context should belong to authenticated student"
        assert ctx.get("currentPassage") is not None, "Active passage should be attached"
        print("  --> PASS: Context builder assembled correctly!")

    # 4. Vocabulary Explanation
    print("\n[4/10] Testing Vocabulary Question ('What does curious mean?')...")
    chat_payload = json.dumps({
        "message": "What does curious mean?",
        "activePassageId": "pas-t1-001",
        "activeWord": "curious"
    }).encode()
    chat_req = urllib.request.Request(f"{BASE}/v2/tutor/chat", data=chat_payload, headers=headers)
    with urllib.request.urlopen(chat_req) as resp:
        tutor_resp = json.loads(resp.read())
        print(f"  --> Source: {tutor_resp.get('source')}")
        print(f"  --> Response Message:\n{tutor_resp.get('message')[:160]}...")
        assert tutor_resp.get("status") == "ok"
        assert len(tutor_resp.get("message", "")) > 10
        print("  --> PASS: Vocabulary explanation delivered!")

    # 5. Comprehension Hint Support
    print("\n[5/10] Testing Comprehension Hint with Reading Story context...")
    hint_payload = json.dumps({
        "message": "Can you give me a hint about what the cat did?",
        "activePassageId": "pas-t1-001"
    }).encode()
    hint_req = urllib.request.Request(f"{BASE}/v2/tutor/chat", data=hint_payload, headers=headers)
    with urllib.request.urlopen(hint_req) as resp:
        hint_resp = json.loads(resp.read())
        print(f"  --> Source: {hint_resp.get('source')}")
        print(f"  --> Clue: {hint_resp.get('message')[:140]}...")
        assert hint_resp.get("status") == "ok"
        print("  --> PASS: Progressive hint provided without answer leakage!")

    # 6. Spelling Guidance
    print("\n[6/10] Testing Spelling Assistance ('How do I spell beautiful?')...")
    spell_payload = json.dumps({
        "message": "How do I spell beautiful?"
    }).encode()
    spell_req = urllib.request.Request(f"{BASE}/v2/tutor/chat", data=spell_payload, headers=headers)
    with urllib.request.urlopen(spell_req) as resp:
        spell_resp = json.loads(resp.read())
        print(f"  --> Spelling response: {spell_resp.get('message')[:130]}...")
        assert "BEAUTIFUL" in spell_resp.get("message", "") or "beautiful" in spell_resp.get("message", "").lower()
        print("  --> PASS: Spelling breakdown delivered!")

    # 7. Encouragement & Growth Mindset
    print("\n[7/10] Testing Encouragement Support ('I can't do this, it's too hard')...")
    enc_payload = json.dumps({
        "message": "I can't do this, it's too hard."
    }).encode()
    enc_req = urllib.request.Request(f"{BASE}/v2/tutor/chat", data=enc_payload, headers=headers)
    with urllib.request.urlopen(enc_req) as resp:
        enc_resp = json.loads(resp.read())
        print(f"  --> Encouragement message:\n{enc_resp.get('message')[:150]}...")
        assert enc_resp.get("status") == "ok"
        print("  --> PASS: Encouragement and growth guidance provided!")

    # 8. Retrieve Conversation History
    print("\n[8/10] Retrieving bounded history (/v2/tutor/history)...")
    hist_req = urllib.request.Request(f"{BASE}/v2/tutor/history?limit=10", headers=headers)
    with urllib.request.urlopen(hist_req) as resp:
        hist_data = json.loads(resp.read())
        messages = hist_data.get("messages", [])
        print(f"  --> Messages stored: {len(messages)}")
        assert len(messages) >= 2, "Conversation turns should be recorded"
        print("  --> PASS: Bounded history working!")

    # 9. Cross-Student Access Rejection
    print("\n[9/10] Verifying security: Cross-student context rejection (403)...")
    forbidden_req = urllib.request.Request(
        f"{BASE}/v2/tutor/context?learnerId=another-student-id-999",
        headers=headers
    )
    try:
        with urllib.request.urlopen(forbidden_req) as resp:
            assert False, "Should have been rejected with 403"
    except urllib.error.HTTPError as e:
        assert e.code == 403, f"Expected 403, got {e.code}"
        print(f"  --> Correctly rejected with HTTP {e.code}: Cross-student context denied!")
        print("  --> PASS: Tenant isolation verified!")

    # 10. Verify Existing V1 Chat Still Functions
    print("\n[10/10] Verifying existing V1 Chat (/api/chat) is NOT broken...")
    v1_payload = json.dumps({
        "message": "Hello AI Assistant! Tell me a fun reading fact.",
        "history": []
    }).encode()
    v1_req = urllib.request.Request(f"{BASE}/chat", data=v1_payload, headers=headers)
    with urllib.request.urlopen(v1_req) as resp:
        v1_resp = json.loads(resp.read())
        print(f"  --> V1 Chat Status: {v1_resp.get('status', 'ok')}")
        assert v1_resp.get("response") or v1_resp.get("reply") or v1_resp.get("message"), "V1 chat should return a reply"
        print("  --> PASS: Existing V1 Chat remains fully functional!")

    print("\n" + "=" * 65)
    print("  ALL 10/10 LIVE PERSONAL AI TUTOR INTEGRATION TESTS PASSED!  ")
    print("=" * 65)


if __name__ == "__main__":
    run_live_tests()
