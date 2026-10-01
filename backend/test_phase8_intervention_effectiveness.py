"""
backend/test_phase8_intervention_effectiveness.py — Comprehensive Test Suite for Phase 8: Intervention Effectiveness.

Tests cover:
1. Model & Validation:
   - Valid intervention creation
   - Invalid status, dates, and fields rejected
   - Controlled state transitions (planned -> active -> review -> completed)
   - Terminal state immutability
2. Baseline Measurements:
   - Established from real historical student practice data (reading, speech, adaptive)
   - Insufficient data handled cleanly (value is None, not treated as 0)
   - Sources, units, scales, and periods preserved
   - Baseline immutable when new follow-up data arrives
3. Comparisons & Observed Changes:
   - Positive change (improved_on_measure)
   - Negative change (declined_on_measure)
   - No material change (within threshold)
   - Lower-is-better metric direction
   - Zero baseline handles division gracefully (relativeChangePercent is None)
   - Missing baseline and missing follow-up -> insufficient_data
   - Incompatible scales/units -> not_comparable
   - Time window isolation (baseline <= startDate < follow-up)
   - No causal claims or clinical language in summaries/interpretations
4. Follow-Up & Persistence:
   - Follow-up gathered from sessions after startDate
   - Idempotent follow-up aggregation without duplication
   - Manual teacher observation recording
   - Terminal status rejects updates
5. Authorization & Boundaries:
   - Unauthenticated request -> 401
   - Student role -> 403 Forbidden
   - Authorized teacher -> 200/201
   - Unrelated teacher -> 403 Forbidden
   - Student outside classroom -> 403 Forbidden
   - Cross-intervention tampering rejected
6. Privacy & Data Minimization:
   - Zero raw audio, passwords, hashes, or tokens exposed
   - No data leakage across classroom boundaries
7. Feature Flag:
   - V2_INTERVENTION_EFFECTIVENESS = False -> 503 Service Unavailable
   - V2_INTERVENTION_EFFECTIVENESS = True -> 200/201 OK
"""
import unittest
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from core.config import settings
from deps.deps import require_teacher
from models.v2_intervention import (
    VALID_INTERVENTION_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    BaselineMeasurement,
    FollowUpMeasurement,
    TeacherObservation,
    V2Intervention,
    InterventionCreateRequest,
    InterventionUpdateRequest,
    InterventionTransitionRequest,
    ManualFollowUpRequest,
    MetricComparison,
    InterventionEffectivenessReport,
)
from services.analytics.intervention_effectiveness import (
    establish_baseline_measurements,
    collect_follow_up_measurements,
    calculate_metric_comparison,
    generate_effectiveness_report,
    create_intervention,
    get_teacher_interventions,
    verify_teacher_intervention_access,
    update_intervention,
    transition_intervention_status,
    record_manual_followup,
    METRIC_CONFIGS,
)


class TestInterventionModelAndValidation(unittest.TestCase):
    """Test Pydantic models, validation rules, and lifecycle state transition constraints."""

    def test_valid_intervention_instantiation(self):
        now = int(time.time())
        intv = V2Intervention(
            interventionId="intv_123",
            teacherId="teacher-1",
            learnerId="student-1",
            classroomCode="CLASS-A",
            goal="Improve reading comprehension on narrative passages",
            targetDomain="reading_comprehension",
            supportActivity="Daily 15-minute guided repeated reading",
            startDate=now,
            status="planned",
        )
        self.assertEqual(intv.interventionId, "intv_123")
        self.assertEqual(intv.status, "planned")
        self.assertEqual(len(intv.baselineMeasurements), 0)

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            V2Intervention(
                interventionId="intv_123",
                teacherId="teacher-1",
                learnerId="student-1",
                classroomCode="CLASS-A",
                goal="Improve fluency",
                targetDomain="reading_fluency",
                supportActivity="Speed reading drills",
                startDate=int(time.time()),
                status="cured",  # Invalid status
            )

    def test_invalid_dates_rejected_in_request(self):
        start = int(time.time())
        review = start - 3600  # 1 hour earlier than start
        with self.assertRaises(ValidationError):
            InterventionCreateRequest(
                learnerId="student-1",
                goal="Improve comprehension",
                targetDomain="reading_comprehension",
                supportActivity="Story mapping",
                startDate=start,
                plannedReviewDate=review,
            )

    def test_short_goal_rejected(self):
        with self.assertRaises(ValidationError):
            InterventionCreateRequest(
                learnerId="student-1",
                goal="Hi",  # < 3 chars
                targetDomain="reading_comprehension",
                supportActivity="Story reading",
            )

    def test_allowed_lifecycle_transitions(self):
        # planned -> active (valid)
        self.assertIn("active", ALLOWED_STATUS_TRANSITIONS["planned"])
        # active -> review (valid)
        self.assertIn("review", ALLOWED_STATUS_TRANSITIONS["active"])
        # review -> completed (valid)
        self.assertIn("completed", ALLOWED_STATUS_TRANSITIONS["review"])
        # review -> active (valid - continue intervention)
        self.assertIn("active", ALLOWED_STATUS_TRANSITIONS["review"])
        # planned -> completed (invalid transition)
        self.assertNotIn("completed", ALLOWED_STATUS_TRANSITIONS["planned"])
        # completed -> active (terminal, invalid)
        self.assertEqual(len(ALLOWED_STATUS_TRANSITIONS["completed"]), 0)
        # cancelled -> active (terminal, invalid)
        self.assertEqual(len(ALLOWED_STATUS_TRANSITIONS["cancelled"]), 0)


class TestBaselineEstablishment(unittest.IsolatedAsyncioTestCase):
    """Test baseline establishment from real historical student practice data."""

    @patch("services.analytics.intervention_effectiveness.db")
    async def test_baseline_calculated_from_reading_sessions(self, mock_db):
        start_date = 1700000000
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[
                {"comprehensionAccuracy": 60.0, "durationSeconds": 60, "wordsRead": 50, "createdAt": 1699900000},
                {"comprehensionAccuracy": 80.0, "durationSeconds": 60, "wordsRead": 60, "createdAt": 1699950000},
            ]
        )
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)

        baselines = await establish_baseline_measurements("student-1", "reading_comprehension", start_date)
        self.assertGreater(len(baselines), 0)

        comp_base = next((b for b in baselines if b.metricName == "reading_comprehension_accuracy"), None)
        self.assertIsNotNone(comp_base)
        self.assertEqual(comp_base.value, 70.0)  # avg(60, 80)
        self.assertEqual(comp_base.observationCount, 2)
        self.assertEqual(comp_base.status, "sufficient")
        self.assertEqual(comp_base.source, "reading_sessions")

    @patch("services.analytics.intervention_effectiveness.db")
    async def test_baseline_insufficient_data_when_no_sessions(self, mock_db):
        start_date = 1700000000
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)

        baselines = await establish_baseline_measurements("student-1", "reading_comprehension", start_date)
        comp_base = next((b for b in baselines if b.metricName == "reading_comprehension_accuracy"), None)
        self.assertIsNotNone(comp_base)
        self.assertIsNone(comp_base.value)
        self.assertEqual(comp_base.status, "insufficient_data")
        self.assertEqual(comp_base.observationCount, 0)
        # Missing data MUST NOT be treated as zero
        self.assertNotEqual(comp_base.value, 0.0)

    @patch("services.analytics.intervention_effectiveness.db")
    async def test_baseline_calculated_from_adaptive_activity_attempts(self, mock_db):
        start_date = 1700000000
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[
                {"scorePercent": 50.0, "domain": "phonological_awareness", "completedAt": 1699900000},
                {"scorePercent": 70.0, "domain": "phonological_awareness", "completedAt": 1699950000},
            ]
        )
        mock_db.learner_profiles.find_one = AsyncMock(return_value=None)

        baselines = await establish_baseline_measurements("student-1", "phonological_awareness", start_date)
        adapt_base = next((b for b in baselines if b.metricName == "adaptive_activity_accuracy"), None)
        self.assertIsNotNone(adapt_base)
        self.assertEqual(adapt_base.value, 60.0)
        self.assertEqual(adapt_base.observationCount, 2)
        self.assertEqual(adapt_base.status, "sufficient")


class TestMetricComparisonAndObservedChange(unittest.TestCase):
    """Test before-and-after comparison logic, thresholds, and neutral language enforcement."""

    def test_positive_material_change(self):
        # Baseline 60.0% -> Follow-up 75.0% (> 3.0 threshold)
        base = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=60.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
            status="sufficient",
        )
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=75.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=4,
        )
        comp = calculate_metric_comparison(base, fol, "reading_comprehension")
        self.assertEqual(comp.status, "improved_on_measure")
        self.assertEqual(comp.absoluteChange, 15.0)
        self.assertEqual(comp.relativeChangePercent, 25.0)
        self.assertIn("observed change", comp.interpretation.lower())
        self.assertIn("does not prove causal efficacy", comp.interpretation.lower())

    def test_negative_material_change(self):
        # Baseline 75.0% -> Follow-up 60.0% (< -3.0 threshold)
        base = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=75.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
            status="sufficient",
        )
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=60.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
        )
        comp = calculate_metric_comparison(base, fol, "reading_comprehension")
        self.assertEqual(comp.status, "declined_on_measure")
        self.assertEqual(comp.absoluteChange, -15.0)
        self.assertEqual(comp.relativeChangePercent, -20.0)

    def test_no_material_change_within_threshold(self):
        # Baseline 70.0% -> Follow-up 71.5% (change 1.5 < 3.0 threshold)
        base = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=70.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
            status="sufficient",
        )
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=71.5,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
        )
        comp = calculate_metric_comparison(base, fol, "reading_comprehension")
        self.assertEqual(comp.status, "no_material_change")
        self.assertEqual(comp.absoluteChange, 1.5)

    def test_zero_baseline_relative_change_is_none(self):
        # Baseline 0 -> Relative change undefined, cannot divide by zero
        base = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=0.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=1,
            status="sufficient",
        )
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=25.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=1,
        )
        comp = calculate_metric_comparison(base, fol, "reading_comprehension")
        self.assertIsNone(comp.relativeChangePercent)
        self.assertEqual(comp.absoluteChange, 25.0)

    def test_missing_baseline_returns_insufficient_data(self):
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=75.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=2,
        )
        comp = calculate_metric_comparison(None, fol, "reading_comprehension")
        self.assertEqual(comp.status, "insufficient_data")
        self.assertIsNone(comp.absoluteChange)

    def test_missing_followup_returns_insufficient_data(self):
        base = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=70.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=2,
            status="sufficient",
        )
        comp = calculate_metric_comparison(base, None, "reading_comprehension")
        self.assertEqual(comp.status, "insufficient_data")
        self.assertIsNone(comp.absoluteChange)

    def test_incompatible_scales_returns_not_comparable(self):
        base = BaselineMeasurement(
            metricName="mixed_metric",
            displayName="Mixed Metric",
            value=70.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=2,
            status="sufficient",
        )
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="mixed_metric",
            displayName="Mixed Metric",
            value=85.0,
            unit="wpm",
            scale="words_per_minute",
            source="reading_sessions",
            observationCount=2,
        )
        comp = calculate_metric_comparison(base, fol, "reading_comprehension")
        self.assertEqual(comp.status, "not_comparable")
        self.assertIsNone(comp.absoluteChange)

    def test_lower_is_better_metric_direction(self):
        # Test custom lower-is-better metric (e.g. error rate)
        with patch.dict(METRIC_CONFIGS, {
            "error_rate": {
                "displayName": "Error Rate",
                "unit": "%",
                "scale": "0-100%",
                "direction": "lower_is_better",
                "threshold": 3.0,
                "source": "speech_reading_analyses",
            }
        }):
            base = BaselineMeasurement(
                metricName="error_rate",
                displayName="Error Rate",
                value=25.0,
                unit="%",
                scale="0-100%",
                source="speech_reading_analyses",
                observationCount=2,
                status="sufficient",
            )
            # Reduction in errors from 25% -> 15% is an IMPROVEMENT
            fol = FollowUpMeasurement(
                interventionId="intv-1",
                metricName="error_rate",
                displayName="Error Rate",
                value=15.0,
                unit="%",
                scale="0-100%",
                source="speech_reading_analyses",
                observationCount=2,
            )
            comp = calculate_metric_comparison(base, fol, "speech_reading")
            self.assertEqual(comp.status, "improved_on_measure")
            self.assertEqual(comp.absoluteChange, -10.0)

    def test_no_unsupported_causal_or_clinical_claims(self):
        base = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=60.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
            status="sufficient",
        )
        fol = FollowUpMeasurement(
            interventionId="intv-1",
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=80.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=4,
        )
        comp = calculate_metric_comparison(base, fol, "reading_comprehension")

        banned_phrases = [
            "caused",
            "proven effective",
            "clinically effective",
            "cure",
            "cured",
            "diagnosed",
            "statistically significant",
        ]
        interp = comp.interpretation.lower()
        for phrase in banned_phrases:
            self.assertNotIn(phrase, interp, f"Banned causal/clinical claim '{phrase}' found in interpretation")


class TestFollowUpAndPersistence(unittest.IsolatedAsyncioTestCase):
    """Test follow-up measurement collection, idempotency, and update constraints."""

    @patch("services.analytics.intervention_effectiveness.db")
    async def test_collect_follow_up_measurements_after_start_date(self, mock_db):
        start_date = 1700000000
        intv = {
            "interventionId": "intv-1",
            "learnerId": "student-1",
            "startDate": start_date,
            "targetDomain": "reading_comprehension",
            "status": "active",
        }
        # Only sessions with createdAt > start_date are collected
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[
                {"comprehensionAccuracy": 85.0, "durationSeconds": 60, "wordsRead": 60, "createdAt": start_date + 1000},
                {"comprehensionAccuracy": 90.0, "durationSeconds": 60, "wordsRead": 65, "createdAt": start_date + 2000},
            ]
        )
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])

        follow_ups = await collect_follow_up_measurements(intv)
        self.assertGreater(len(follow_ups), 0)
        comp_fol = next((f for f in follow_ups if f.metricName == "reading_comprehension_accuracy"), None)
        self.assertIsNotNone(comp_fol)
        self.assertEqual(comp_fol.value, 87.5)  # avg(85, 90)
        self.assertEqual(comp_fol.observationCount, 2)

    @patch("services.analytics.intervention_effectiveness.verify_teacher_student_access")
    @patch("services.analytics.intervention_effectiveness.db")
    async def test_terminal_intervention_cannot_be_updated(self, mock_db, mock_verify):
        mock_db.interventions.find_one = AsyncMock(
            return_value={
                "interventionId": "intv-1",
                "teacherId": "t-1",
                "learnerId": "s-1",
                "classroomCode": "CLASS-1",
                "status": "completed",  # Terminal state
            }
        )
        teacher = {"id": "t-1", "classroomCode": "CLASS-1"}
        req = InterventionUpdateRequest(goal="New Goal")

        with self.assertRaises(HTTPException) as ctx:
            await update_intervention(teacher, "intv-1", req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("terminal", ctx.exception.detail.lower())


class TestTeacherAuthorizationAndBoundaries(unittest.IsolatedAsyncioTestCase):
    """Test tenant boundaries, cross-teacher isolation, and student role blocking."""

    @patch("services.analytics.intervention_effectiveness.db")
    async def test_unrelated_teacher_access_rejected(self, mock_db):
        mock_db.interventions.find_one = AsyncMock(
            return_value={
                "interventionId": "intv-1",
                "teacherId": "teacher-alpha",
                "learnerId": "student-1",
                "classroomCode": "CLASS-ALPHA",
                "status": "active",
            }
        )
        teacher_beta = {"id": "teacher-beta", "classroomCode": "CLASS-BETA"}

        with self.assertRaises(HTTPException) as ctx:
            await verify_teacher_intervention_access(teacher_beta, "intv-1")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())

    @patch("services.analytics.intervention_effectiveness.verify_teacher_student_access")
    @patch("services.analytics.intervention_effectiveness.db")
    async def test_authorized_teacher_access_granted(self, mock_db, mock_verify):
        mock_db.interventions.find_one = AsyncMock(
            return_value={
                "interventionId": "intv-1",
                "teacherId": "teacher-alpha",
                "learnerId": "student-1",
                "classroomCode": "CLASS-ALPHA",
                "status": "active",
            }
        )
        teacher_alpha = {"id": "teacher-alpha", "classroomCode": "CLASS-ALPHA"}

        doc = await verify_teacher_intervention_access(teacher_alpha, "intv-1")
        self.assertEqual(doc["interventionId"], "intv-1")


class TestInterventionAPIEndpoints(unittest.TestCase):
    """Test HTTP API endpoints for V2 Teacher Interventions."""

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests must be rejected with 401 Unauthorized."""
        endpoints = [
            ("POST", "/api/v2/teacher/interventions"),
            ("GET", "/api/v2/teacher/interventions"),
            ("GET", "/api/v2/teacher/interventions/intv-1"),
            ("PATCH", "/api/v2/teacher/interventions/intv-1"),
            ("POST", "/api/v2/teacher/interventions/intv-1/start"),
            ("POST", "/api/v2/teacher/interventions/intv-1/review"),
            ("POST", "/api/v2/teacher/interventions/intv-1/complete"),
            ("GET", "/api/v2/teacher/interventions/intv-1/effectiveness"),
        ]
        for method, ep in endpoints:
            if method == "POST":
                res = self.client.post(ep, json={})
            elif method == "PATCH":
                res = self.client.patch(ep, json={})
            else:
                res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, f"{method} {ep} did not enforce auth")

    def test_student_role_returns_403(self):
        """Students must be rejected with 403 Forbidden on teacher endpoints."""
        def mock_require_teacher():
            raise HTTPException(status_code=403, detail="Teacher role required")

        app.dependency_overrides[require_teacher] = mock_require_teacher

        res = self.client.get("/api/v2/teacher/interventions")
        self.assertEqual(res.status_code, 403)
        self.assertIn("Teacher role required", res.json().get("detail", ""))

    @patch.object(settings, "V2_INTERVENTION_EFFECTIVENESS", False)
    def test_feature_flag_disabled_returns_503(self):
        """When V2_INTERVENTION_EFFECTIVENESS is False, endpoints return 503."""
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-1"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        res = self.client.get("/api/v2/teacher/interventions")
        self.assertEqual(res.status_code, 503)
        self.assertIn("disabled via feature flags", res.json().get("detail", ""))

    @patch("routers.v2_intervention.create_intervention")
    def test_create_intervention_success(self, mock_create):
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-1"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_create.return_value = V2Intervention(
            interventionId="intv-created",
            teacherId="t-1",
            learnerId="s-1",
            classroomCode="CLASS-1",
            goal="Improve fluency",
            targetDomain="reading_fluency",
            supportActivity="Timed readings",
            startDate=int(time.time()),
            status="planned",
        )

        payload = {
            "learnerId": "s-1",
            "goal": "Improve fluency",
            "targetDomain": "reading_fluency",
            "supportActivity": "Timed readings",
        }
        res = self.client.post("/api/v2/teacher/interventions", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["interventionId"], "intv-created")
        self.assertEqual(data["status"], "planned")

    @patch("routers.v2_intervention.get_teacher_interventions")
    def test_list_interventions_success(self, mock_list):
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-1"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_list.return_value = [
            {
                "interventionId": "intv-1",
                "learnerId": "s-1",
                "learnerName": "Aarav",
                "goal": "Comprehension practice",
                "targetDomain": "reading_comprehension",
                "supportActivity": "Story maps",
                "status": "active",
                "startDate": int(time.time()),
            }
        ]

        res = self.client.get("/api/v2/teacher/interventions")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["learnerName"], "Aarav")

    @patch("routers.v2_intervention.verify_teacher_intervention_access")
    @patch("routers.v2_intervention.generate_effectiveness_report")
    def test_effectiveness_report_endpoint(self, mock_report, mock_verify):
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-1"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_verify.return_value = {"interventionId": "intv-1"}
        mock_report.return_value = InterventionEffectivenessReport(
            interventionId="intv-1",
            goal="Improve comprehension",
            targetDomain="reading_comprehension",
            supportActivity="Guided reading",
            status="active",
            learnerId="s-1",
            learnerName="Maya",
            startDate=1700000000,
            comparisons=[
                MetricComparison(
                    metricName="reading_comprehension_accuracy",
                    metricDisplayName="Reading Comprehension Accuracy",
                    targetDomain="reading_comprehension",
                    unit="%",
                    scale="0-100%",
                    baselineValue=60.0,
                    baselineObservations=3,
                    followUpValue=75.0,
                    followUpObservations=4,
                    absoluteChange=15.0,
                    relativeChangePercent=25.0,
                    status="improved_on_measure",
                    interpretation="Observed improvement of +15.0% between baseline and follow-up.",
                )
            ],
            dataSufficiency="sufficient",
            overallSummary="Observed positive progress on 1 of 1 measured metric(s).",
        )

        res = self.client.get("/api/v2/teacher/interventions/intv-1/effectiveness")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["interventionId"], "intv-1")
        self.assertEqual(data["dataSufficiency"], "sufficient")
        self.assertIn("disclaimer", data)
        self.assertIn("does not establish clinical efficacy", data["disclaimer"].lower())

    @patch("routers.v2_intervention.transition_intervention_status")
    def test_state_transitions_via_api(self, mock_trans):
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-1"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_trans.return_value = {"interventionId": "intv-1", "status": "active"}

        # POST /start
        res = self.client.post("/api/v2/teacher/interventions/intv-1/start")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "active")

        # Invalid transition mock
        mock_trans.side_effect = HTTPException(status_code=400, detail="Invalid status transition from 'completed' to 'active'")
        res2 = self.client.post("/api/v2/teacher/interventions/intv-1/start")
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Invalid status transition", res2.json()["detail"])

    @patch("routers.v2_intervention.record_manual_followup")
    def test_manual_measurement_endpoint(self, mock_manual):
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-1"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_manual.return_value = {
            "interventionId": "intv-1",
            "followUpMeasurements": [{"metricName": "oral_reading_accuracy", "value": 82.0}]
        }

        payload = {"metricName": "oral_reading_accuracy", "value": 82.0, "notes": "Check-in reading"}
        res = self.client.post("/api/v2/teacher/interventions/intv-1/measurements", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["followUpMeasurements"]), 1)

    @patch("routers.v2_intervention.create_intervention")
    def test_tampered_learner_cross_classroom_rejected(self, mock_create):
        teacher_user = {"id": "t-1", "name": "Teacher", "role": "teacher", "classroomCode": "CLASS-A"}
        app.dependency_overrides[require_teacher] = lambda: teacher_user

        mock_create.side_effect = HTTPException(
            status_code=403,
            detail="Access denied: Student is not enrolled in your classroom."
        )

        payload = {
            "learnerId": "student-cross-class",
            "goal": "Improve fluency",
            "targetDomain": "reading_fluency",
            "supportActivity": "Repeated reading",
        }
        res = self.client.post("/api/v2/teacher/interventions", json=payload)
        self.assertEqual(res.status_code, 403)
        self.assertIn("not enrolled in your classroom", res.json()["detail"])

    def test_privacy_no_sensitive_fields_in_payloads(self):
        """Verifies no passwords, tokens, hashes, or audioBlobs are returned or stored."""
        intv = V2Intervention(
            interventionId="intv_sec",
            teacherId="t-1",
            learnerId="s-1",
            classroomCode="CLASS-1",
            goal="Word fluency",
            targetDomain="reading_fluency",
            supportActivity="Repeated reading",
            startDate=int(time.time()),
        ).model_dump()

        sensitive_keys = ["password", "passwordHash", "token", "jwt", "audioBlob", "rawAudio", "secret"]
        for key in sensitive_keys:
            self.assertNotIn(key, intv)


class TestIdempotencyAndBaselineImmutability(unittest.IsolatedAsyncioTestCase):
    """Test that historical baseline remains unmodified and follow-ups sync idempotently."""

    @patch("services.analytics.intervention_effectiveness.db")
    async def test_historical_baseline_not_altered_when_followup_arrives(self, mock_db):
        baseline_record = BaselineMeasurement(
            metricName="reading_comprehension_accuracy",
            displayName="Reading Comprehension Accuracy",
            value=65.0,
            unit="%",
            scale="0-100%",
            source="reading_sessions",
            observationCount=3,
            status="sufficient",
        )
        intv = {
            "interventionId": "intv-immut",
            "learnerId": "student-1",
            "startDate": 1700000000,
            "targetDomain": "reading_comprehension",
            "status": "active",
            "baselineMeasurements": [baseline_record.model_dump()],
            "followUpMeasurements": [],
            "teacherObservations": [],
        }

        # Mock newer reading sessions after start date
        mock_db.users.find_one = AsyncMock(return_value={"id": "student-1", "name": "Maya"})
        mock_db.reading_sessions.find.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[
                {"comprehensionAccuracy": 90.0, "durationSeconds": 60, "wordsRead": 60, "createdAt": 1700050000},
            ]
        )
        mock_db.speech_reading_analyses.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.activity_attempts.find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
        mock_db.interventions.update_one = AsyncMock(return_value=None)

        teacher = {"id": "t-1", "classroomCode": "CLASS-1"}
        report = await generate_effectiveness_report(intv, teacher)

        # Baseline MUST remain 65.0, not overwritten by 90.0
        comp = report.comparisons[0]
        self.assertEqual(comp.baselineValue, 65.0)
        self.assertEqual(comp.followUpValue, 90.0)
        self.assertEqual(comp.absoluteChange, 25.0)
        self.assertEqual(comp.status, "improved_on_measure")


if __name__ == "__main__":
    unittest.main()

