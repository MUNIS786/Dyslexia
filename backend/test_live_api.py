"""
test_live_api.py — Exercises all live FastAPI endpoints on http://127.0.0.1:8000
"""
import urllib.request
import json

def run_live_tests():
    base = 'http://127.0.0.1:8000/api'
    print("==================================================")
    print("      DYSLEXAID LIVE BACKEND END-TO-END TEST      ")
    print("==================================================")
    
    print("\n[1/7] Testing /version & /health...")
    with urllib.request.urlopen(f'{base}/version') as r:
        ver = json.loads(r.read())
        print(f"  --> App: {ver['application']} v{ver['version']}")
        print(f"  --> V2 Feature Flags: {ver['feature_flags']}")
    with urllib.request.urlopen(f'{base}/health') as r:
        h = json.loads(r.read())
        print(f"  --> Service Health: {h['status']}")

    print("\n[2/7] Testing Student Authentication (aarav@demo.school)...")
    req = urllib.request.Request(
        f'{base}/auth/signin',
        data=json.dumps({'email': 'aarav@demo.school', 'password': 'Demo@123'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        auth_data = json.loads(r.read())
        token = auth_data.get('token') or auth_data.get('access_token')
        student_id = auth_data['user']['id']
        print(f"  --> Authenticated: {auth_data['user']['name']} (ID: {student_id})")

    headers = {'Authorization': f'Bearer {token}'}

    print("\n[3/7] Testing GET /v2/learner/profile (Learner Intelligence)...")
    req = urllib.request.Request(f'{base}/v2/learner/profile', headers=headers)
    with urllib.request.urlopen(req) as r:
        p_data = json.loads(r.read())
        profile = p_data['profile']
        lvl = profile['learning_level']
        print(f"  --> Learning Level: Level {lvl['level']} ({lvl['name']})")
        strengths = [s['friendly_name'] for s in profile.get('strengths', [])]
        print(f"  --> Detected Strengths: {strengths}")
        practice = [a['friendly_name'] for a in profile.get('areas_for_practice', [])]
        print(f"  --> Areas for Practice: {practice}")
        print(f"  --> Disclaimer: {profile.get('disclaimer')[:60]}...")

    print("\n[4/7] Testing GET /v2/learning/recommendations (ZPD Challenges)...")
    req = urllib.request.Request(f'{base}/v2/learning/recommendations?count=4', headers=headers)
    with urllib.request.urlopen(req) as r:
        recs = json.loads(r.read())
        print(f"  --> Retrieved {recs['count']} personalized challenges:")
        for rec in recs['recommendations']:
            act = rec['activity']
            print(f"      * [{rec['targetDomain']}] Lvl {rec['difficultyTier']}: '{act['title']}' ({rec['matchType']})")
            print(f"        Rationale: {rec['rationale'][:85]}...")

    print("\n[5/7] Testing POST /v2/learning/attempt (Interaction Telemetry)...")
    attempt_payload = {
        'activityId': 'act-phon-001',
        'scorePercent': 92.0,
        'durationSeconds': 38,
        'hesitationCount': 1,
        'hintsRequested': 0,
        'completed': True
    }
    req = urllib.request.Request(
        f'{base}/v2/learning/attempt',
        data=json.dumps(attempt_payload).encode(),
        headers={'Content-Type': 'application/json', **headers}
    )
    with urllib.request.urlopen(req) as r:
        att_res = json.loads(r.read())
        print(f"  --> Attempt Result: Score {att_res['scorePercent']}% | Status: {att_res['status']}")
        print(f"  --> Active Difficulty Tier: {att_res['currentTier']} (Previous: {att_res['previousTier']})")
        print(f"  --> Celebration Triggered: {att_res['celebration']}")
        print(f"  --> Feedback Message: \"{att_res['message']}\"")
        print(f"  --> Updated Day Streak: {att_res['streak']}")

    print("\n[6/7] Testing GET /v2/learning/state (Progression State)...")
    req = urllib.request.Request(f'{base}/v2/learning/state', headers=headers)
    with urllib.request.urlopen(req) as r:
        st_res = json.loads(r.read())
        state = st_res['state']
        tier_cal = st_res['tierCalibration']
        print(f"  --> Active Tier: Level {state.get('activeDifficultyTier') or state.get('active_difficulty_tier')}")
        print(f"  --> Tier Name: {tier_cal.get('name')} | Max Words: {tier_cal.get('maxSentenceLength')}")
        print(f"  --> Consecutive Passes: {state.get('consecutivePasses') or state.get('consecutive_passes')}")
        print(f"  --> Tasks Completed Today: {state.get('todayTasksCompleted') or state.get('today_tasks_completed')}")

    print("\n[7/7] Testing Teacher Authentication & Secure Student Profile Access...")
    req = urllib.request.Request(
        f'{base}/auth/login',
        data=json.dumps({'email': 'teacher@demo.school', 'password': 'Demo@123'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        t_auth = json.loads(r.read())
        t_token = t_auth.get('token') or t_auth.get('access_token')
        print(f"  --> Authenticated Teacher: {t_auth['user']['name']} (Classroom: {t_auth['user']['classroomCode']})")

    t_headers = {'Authorization': f'Bearer {t_token}'}
    req = urllib.request.Request(f'{base}/v2/learner/student/{student_id}/profile', headers=t_headers)
    with urllib.request.urlopen(req) as r:
        t_prof = json.loads(r.read())
        print(f"  --> Verified Classroom Profile Access: {t_prof['student_name']}")
        print(f"  --> Student Level: {t_prof['profile']['learning_level']['name']}")

    print("\n==================================================")
    print("   >>> ALL 7 LIVE BACKEND API CHECKS PASSED! <<<   ")
    print("==================================================")

if __name__ == '__main__':
    run_live_tests()
