"""
backend/services/analytics/intervention_effectiveness.py — V2 Intervention Effectiveness Service.

Implements the educational measurement workflow:
1. Teacher records learning support activity & educational goal.
2. System establishes baseline measurements from real historical student practice data.
3. Learner completes educational sessions (reading coach, speech analysis, adaptive practice).
4. System collects subsequent follow-up measurements.
5. Baseline and follow-up are compared using defensible, documented thresholds.
6. Teacher reviews observed changes and makes pedagogical decisions.

IMPORTANT NON-CLINICAL NOTICE:
This is a descriptive educational measurement system. Observed changes represent
correlations/associations in longitudinal practice data, NOT proof of causal efficacy
or clinical/medical diagnosis.
"""
import time
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status

from database.database import db
from models.v2_intervention import (
    VALID_INTERVENTION_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    COMPARISON_STATUS_LABELS,
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
from services.analytics.teacher_analytics import (
    verify_teacher_student_access,
    get_teacher_classroom_code,
)
from services.learning.learner_profile_service import DOMAIN_METADATA

logger = logging.getLogger("dyslexaid.intervention_effectiveness")

# ─── Metric Definitions & Thresholds ──────────────────────────────────────────

# Explicit, defensible thresholds for "material change"
# Percentage metrics (comprehension, speech accuracy, activity scores): 3.0 percentage points
# Fluency metrics (WPM): 5.0 words per minute (normal variation across passages is 2-4 WPM)
# Domain mastery scores (0-100 scale): 3.0 scale points
METRIC_CONFIGS: Dict[str, Dict[str, Any]] = {
    "reading_comprehension_accuracy": {
        "displayName": "Reading Comprehension Accuracy",
        "unit": "%",
        "scale": "0-100%",
        "direction": "higher_is_better",
        "threshold": 3.0,
        "source": "reading_sessions",
    },
    "reading_fluency_wpm": {
        "displayName": "Reading Fluency (WPM)",
        "unit": "wpm",
        "scale": "words_per_minute",
        "direction": "higher_is_better",
        "threshold": 5.0,
        "source": "reading_sessions",
    },
    "speech_accuracy_rate": {
        "displayName": "Speech Word Reading Accuracy",
        "unit": "%",
        "scale": "0-100%",
        "direction": "higher_is_better",
        "threshold": 3.0,
        "source": "speech_reading_analyses",
    },
    "adaptive_activity_accuracy": {
        "displayName": "Adaptive Practice Accuracy",
        "unit": "%",
        "scale": "0-100%",
        "direction": "higher_is_better",
        "threshold": 3.0,
        "source": "activity_attempts",
    },
    "domain_mastery_score": {
        "displayName": "Domain Mastery Score",
        "unit": "score",
        "scale": "0-100",
        "direction": "higher_is_better",
        "threshold": 3.0,
        "source": "learner_profiles",
    },
}


# ─── Teacher & Intervention Access Verification ───────────────────────────────

async def verify_teacher_intervention_access(teacher: dict, intervention_id: str) -> dict:
    """
    Verifies that the intervention exists and the authenticated teacher is authorized to access it.
    Enforces strict classroom and teacher boundaries:
    - Intervention must belong to the teacher OR the teacher's active classroom.
    - Associated learner must be enrolled in the teacher's classroom.
    """
    doc = await db.interventions.find_one({"interventionId": intervention_id}, {"_id": 0})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intervention '{intervention_id}' not found."
        )

    teacher_id = teacher.get("id")
    teacher_code = await get_teacher_classroom_code(teacher)

    doc_teacher_id = doc.get("teacherId")
    doc_classroom = doc.get("classroomCode")

    # Authorization checks
    is_owner = (doc_teacher_id == teacher_id)
    is_same_classroom = (teacher_code is not None and doc_classroom == teacher_code)

    if not (is_owner or is_same_classroom):
        logger.warning(
            f"Unauthorized intervention access: Teacher {teacher_id} attempted access to "
            f"intervention {intervention_id} belonging to Teacher {doc_teacher_id} / Class {doc_classroom}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized to view or manage this intervention."
        )

    # Verify student is still in classroom
    learner_id = doc.get("learnerId")
    await verify_teacher_student_access(teacher, learner_id)

    return doc


# ─── Baseline Measurement Collection ──────────────────────────────────────────

async def establish_baseline_measurements(
    student_id: str,
    target_domain: str,
    start_date: int,
) -> List[BaselineMeasurement]:
    """
    Queries real existing learner practice data prior to or at start_date.
    Preserves source, scale, period, and observation counts.
    Never manufactures artificial baseline data or treats missing values as zero.
    """
    baselines: List[BaselineMeasurement] = []

    # 1. Reading Sessions (Comprehension & Fluency)
    r_query = {
        "learnerId": student_id,
        "completed": True,
        "createdAt": {"$lte": start_date},
    }
    reading_docs = await db.reading_sessions.find(r_query, {"_id": 0}).sort("createdAt", 1).to_list(100)

    if reading_docs:
        comp_scores = [float(r.get("comprehensionAccuracy", 0.0)) for r in reading_docs if r.get("comprehensionAccuracy") is not None]
        fluency_wpms: List[float] = []
        for r in reading_docs:
            dur = float(r.get("durationSeconds", 0))
            words = float(r.get("wordsRead", 0))
            if dur >= 10 and words > 0:
                fluency_wpms.append(round((words / dur) * 60.0, 1))

        first_ts = int(reading_docs[0].get("createdAt", start_date))
        last_ts = int(reading_docs[-1].get("createdAt", start_date))

        if comp_scores:
            avg_comp = round(sum(comp_scores) / len(comp_scores), 2)
            baselines.append(BaselineMeasurement(
                metricName="reading_comprehension_accuracy",
                displayName="Reading Comprehension Accuracy",
                value=avg_comp,
                unit="%",
                scale="0-100%",
                source="reading_sessions",
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(comp_scores),
                status="sufficient",
                metadata={"sessionCount": len(reading_docs), "minScore": min(comp_scores), "maxScore": max(comp_scores)},
            ))

        if fluency_wpms and ("fluency" in target_domain or target_domain == "reading_fluency"):
            avg_wpm = round(sum(fluency_wpms) / len(fluency_wpms), 1)
            baselines.append(BaselineMeasurement(
                metricName="reading_fluency_wpm",
                displayName="Reading Fluency (WPM)",
                value=avg_wpm,
                unit="wpm",
                scale="words_per_minute",
                source="reading_sessions",
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(fluency_wpms),
                status="sufficient",
                metadata={"observations": len(fluency_wpms)},
            ))
    else:
        # If target domain is reading comprehension or fluency and no sessions exist, add explicit insufficient baseline
        if "reading" in target_domain or "comprehension" in target_domain:
            baselines.append(BaselineMeasurement(
                metricName="reading_comprehension_accuracy",
                displayName="Reading Comprehension Accuracy",
                value=None,
                unit="%",
                scale="0-100%",
                source="reading_sessions",
                observationCount=0,
                status="insufficient_data",
                metadata={"reason": "No completed reading coach sessions prior to intervention start."},
            ))

    # 2. Speech Reading Analyses (Word Reading Accuracy)
    s_query = {
        "learnerId": student_id,
        "createdAt": {"$lte": start_date},
    }
    speech_docs = await db.speech_reading_analyses.find(s_query, {"_id": 0}).sort("createdAt", 1).to_list(100)

    if speech_docs:
        acc_rates = [float(s.get("accuracyRate", 0.0)) for s in speech_docs if s.get("accuracyRate") is not None]
        if acc_rates:
            avg_acc = round(sum(acc_rates) / len(acc_rates), 2)
            first_ts = int(speech_docs[0].get("createdAt", start_date))
            last_ts = int(speech_docs[-1].get("createdAt", start_date))
            baselines.append(BaselineMeasurement(
                metricName="speech_accuracy_rate",
                displayName="Speech Word Reading Accuracy",
                value=avg_acc,
                unit="%",
                scale="0-100%",
                source="speech_reading_analyses",
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(acc_rates),
                status="sufficient",
                metadata={"analysesCount": len(speech_docs)},
            ))
    elif "speech" in target_domain or "fluency" in target_domain or "phon" in target_domain:
        baselines.append(BaselineMeasurement(
            metricName="speech_accuracy_rate",
            displayName="Speech Word Reading Accuracy",
            value=None,
            unit="%",
            scale="0-100%",
            source="speech_reading_analyses",
            observationCount=0,
            status="insufficient_data",
            metadata={"reason": "No speech reading analyses recorded prior to intervention start."},
        ))

    # 3. Adaptive Activity Attempts
    a_query = {
        "learnerId": student_id,
        "completedAt": {"$lte": start_date},
    }
    # Filter by domain if specified and not generic
    if target_domain and target_domain in DOMAIN_METADATA:
        a_query["domain"] = target_domain

    act_docs = await db.activity_attempts.find(a_query, {"_id": 0}).sort("completedAt", 1).to_list(100)

    if act_docs:
        scores = [float(a.get("scorePercent", 0.0)) for a in act_docs if a.get("scorePercent") is not None]
        if scores:
            avg_score = round(sum(scores) / len(scores), 2)
            first_ts = int(act_docs[0].get("completedAt", start_date))
            last_ts = int(act_docs[-1].get("completedAt", start_date))
            baselines.append(BaselineMeasurement(
                metricName="adaptive_activity_accuracy",
                displayName=f"Adaptive Practice ({target_domain.replace('_', ' ').title()})",
                value=avg_score,
                unit="%",
                scale="0-100%",
                source="activity_attempts",
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(scores),
                status="sufficient",
                metadata={"attemptsCount": len(act_docs), "domain": target_domain},
            ))
    elif target_domain in DOMAIN_METADATA and target_domain not in ("reading_comprehension", "reading_fluency"):
        baselines.append(BaselineMeasurement(
            metricName="adaptive_activity_accuracy",
            displayName=f"Adaptive Practice ({target_domain.replace('_', ' ').title()})",
            value=None,
            unit="%",
            scale="0-100%",
            source="activity_attempts",
            observationCount=0,
            status="insufficient_data",
            metadata={"reason": f"No adaptive activity attempts recorded in '{target_domain}' before start date."},
        ))

    # 4. Domain Mastery from Learner Profile (if available)
    profile_doc = await db.learner_profiles.find_one({"learnerId": student_id}, {"_id": 0})
    if profile_doc:
        domain_scores = profile_doc.get("domainScores") or profile_doc.get("domain_scores") or {}
        domain_entry = domain_scores.get(target_domain)
        if isinstance(domain_entry, dict) and domain_entry.get("score") is not None:
            baselines.append(BaselineMeasurement(
                metricName="domain_mastery_score",
                displayName=f"Profile Domain Score ({target_domain.replace('_', ' ').title()})",
                value=round(float(domain_entry["score"]), 2),
                unit="score",
                scale="0-100",
                source="learner_profiles",
                periodStart=int(profile_doc.get("updatedAt", start_date)),
                periodEnd=int(profile_doc.get("updatedAt", start_date)),
                observationCount=1,
                status="sufficient",
                metadata={"domain": target_domain, "level": domain_entry.get("label")},
            ))

    return baselines


# ─── Follow-Up Measurement Collection ─────────────────────────────────────────

async def collect_follow_up_measurements(
    intervention: dict,
) -> List[FollowUpMeasurement]:
    """
    Gathers comparable subsequent measurements for the learner after intervention.startDate.
    Uses identical metrics and data sources.
    Idempotent: merges newly collected observations with existing follow-up records.
    """
    student_id = intervention.get("learnerId")
    start_date = int(intervention.get("startDate", 0))
    intv_id = intervention.get("interventionId")
    target_domain = intervention.get("targetDomain", "")

    # Look up end cutoff if completed or review
    end_cutoff = int(time.time())
    if intervention.get("status") in ("completed", "cancelled") and intervention.get("updatedAt"):
        end_cutoff = max(start_date, int(intervention.get("updatedAt")))

    follow_ups: List[FollowUpMeasurement] = []

    # 1. Reading Sessions
    r_query = {
        "learnerId": student_id,
        "completed": True,
        "createdAt": {"$gt": start_date, "$lte": end_cutoff},
    }
    r_docs = await db.reading_sessions.find(r_query, {"_id": 0}).sort("createdAt", 1).to_list(100)

    if r_docs:
        comp_scores = [float(r.get("comprehensionAccuracy", 0.0)) for r in r_docs if r.get("comprehensionAccuracy") is not None]
        fluency_wpms: List[float] = []
        for r in r_docs:
            dur = float(r.get("durationSeconds", 0))
            words = float(r.get("wordsRead", 0))
            if dur >= 10 and words > 0:
                fluency_wpms.append(round((words / dur) * 60.0, 1))

        first_ts = int(r_docs[0].get("createdAt", start_date))
        last_ts = int(r_docs[-1].get("createdAt", end_cutoff))

        if comp_scores:
            avg_comp = round(sum(comp_scores) / len(comp_scores), 2)
            follow_ups.append(FollowUpMeasurement(
                interventionId=intv_id,
                metricName="reading_comprehension_accuracy",
                displayName="Reading Comprehension Accuracy",
                value=avg_comp,
                unit="%",
                scale="0-100%",
                source="reading_sessions",
                timestamp=last_ts,
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(comp_scores),
                meetsComparisonRules=True,
                metadata={"sessionCount": len(r_docs)},
            ))

        if fluency_wpms and ("fluency" in target_domain or target_domain == "reading_fluency"):
            avg_wpm = round(sum(fluency_wpms) / len(fluency_wpms), 1)
            follow_ups.append(FollowUpMeasurement(
                interventionId=intv_id,
                metricName="reading_fluency_wpm",
                displayName="Reading Fluency (WPM)",
                value=avg_wpm,
                unit="wpm",
                scale="words_per_minute",
                source="reading_sessions",
                timestamp=last_ts,
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(fluency_wpms),
                meetsComparisonRules=True,
                metadata={"observations": len(fluency_wpms)},
            ))

    # 2. Speech Reading Analyses
    s_query = {
        "learnerId": student_id,
        "createdAt": {"$gt": start_date, "$lte": end_cutoff},
    }
    s_docs = await db.speech_reading_analyses.find(s_query, {"_id": 0}).sort("createdAt", 1).to_list(100)

    if s_docs:
        acc_rates = [float(s.get("accuracyRate", 0.0)) for s in s_docs if s.get("accuracyRate") is not None]
        if acc_rates:
            avg_acc = round(sum(acc_rates) / len(acc_rates), 2)
            first_ts = int(s_docs[0].get("createdAt", start_date))
            last_ts = int(s_docs[-1].get("createdAt", end_cutoff))
            follow_ups.append(FollowUpMeasurement(
                interventionId=intv_id,
                metricName="speech_accuracy_rate",
                displayName="Speech Word Reading Accuracy",
                value=avg_acc,
                unit="%",
                scale="0-100%",
                source="speech_reading_analyses",
                timestamp=last_ts,
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(acc_rates),
                meetsComparisonRules=True,
                metadata={"analysesCount": len(s_docs)},
            ))

    # 3. Adaptive Activity Attempts
    a_query = {
        "learnerId": student_id,
        "completedAt": {"$gt": start_date, "$lte": end_cutoff},
    }
    if target_domain and target_domain in DOMAIN_METADATA:
        a_query["domain"] = target_domain

    act_docs = await db.activity_attempts.find(a_query, {"_id": 0}).sort("completedAt", 1).to_list(100)

    if act_docs:
        scores = [float(a.get("scorePercent", 0.0)) for a in act_docs if a.get("scorePercent") is not None]
        if scores:
            avg_score = round(sum(scores) / len(scores), 2)
            first_ts = int(act_docs[0].get("completedAt", start_date))
            last_ts = int(act_docs[-1].get("completedAt", end_cutoff))
            follow_ups.append(FollowUpMeasurement(
                interventionId=intv_id,
                metricName="adaptive_activity_accuracy",
                displayName=f"Adaptive Practice ({target_domain.replace('_', ' ').title()})",
                value=avg_score,
                unit="%",
                scale="0-100%",
                source="activity_attempts",
                timestamp=last_ts,
                periodStart=first_ts,
                periodEnd=last_ts,
                observationCount=len(scores),
                meetsComparisonRules=True,
                metadata={"attemptsCount": len(act_docs)},
            ))

    # Include existing manual teacher measurements if any were recorded
    existing_manual = [
        FollowUpMeasurement(**m) if isinstance(m, dict) else m
        for m in intervention.get("followUpMeasurements", [])
        if (isinstance(m, dict) and m.get("source") == "teacher_observed_assessment")
        or (hasattr(m, "source") and m.source == "teacher_observed_assessment")
    ]
    follow_ups.extend(existing_manual)

    return follow_ups


# ─── Comparison Logic & Observed Change ───────────────────────────────────────

def calculate_metric_comparison(
    baseline: Optional[BaselineMeasurement],
    follow_up: Optional[FollowUpMeasurement],
    target_domain: str,
) -> MetricComparison:
    """
    Computes absolute and relative changes between compatible baseline and follow-up metrics.
    Enforces rules:
    - Never treat missing data as zero.
    - If either baseline or follow-up is missing or insufficient -> 'insufficient_data'.
    - If units or scales mismatch -> 'not_comparable'.
    - If baseline is zero -> relative change percent is None (undefined).
    - Threshold-based material change evaluation.
    - Strictly neutral, non-clinical interpretation.
    """
    metric_name = baseline.metricName if baseline else (follow_up.metricName if follow_up else "unknown_metric")
    config = METRIC_CONFIGS.get(metric_name, {
        "displayName": metric_name.replace("_", " ").title(),
        "unit": baseline.unit if baseline else (follow_up.unit if follow_up else "%"),
        "scale": baseline.scale if baseline else (follow_up.scale if follow_up else "0-100%"),
        "direction": "higher_is_better",
        "threshold": 3.0,
    })

    display_name = baseline.displayName if baseline else (follow_up.displayName if follow_up else config["displayName"])
    unit = baseline.unit if baseline else (follow_up.unit if follow_up else config["unit"])
    scale = baseline.scale if baseline else (follow_up.scale if follow_up else config["scale"])
    direction = config.get("direction", "higher_is_better")
    threshold = config.get("threshold", 3.0)

    base_val = baseline.value if (baseline and baseline.status == "sufficient") else None
    base_obs = baseline.observationCount if baseline else 0
    base_period = f"{base_obs} observation(s)" if base_obs > 0 else "No historical observations"

    fol_val = follow_up.value if follow_up else None
    fol_obs = follow_up.observationCount if follow_up else 0
    fol_period = f"{fol_obs} observation(s)" if fol_obs > 0 else "No follow-up observations"

    # Case 1: Missing or insufficient baseline or follow-up
    if base_val is None or fol_val is None or base_obs < 1 or fol_obs < 1:
        if base_val is None and fol_val is None:
            reason = "Neither baseline data nor follow-up practice sessions have been recorded yet."
        elif base_val is None:
            reason = "A historical baseline could not be established from prior student activity."
        else:
            reason = "Follow-up practice sessions have not yet been recorded since the support activity began."

        return MetricComparison(
            metricName=metric_name,
            metricDisplayName=display_name,
            targetDomain=target_domain,
            unit=unit,
            scale=scale,
            direction=direction,
            baselineValue=base_val,
            baselineObservations=base_obs,
            baselinePeriod=base_period,
            baselineStatus="sufficient" if (base_val is not None and base_obs >= 1) else "insufficient_data",
            followUpValue=fol_val,
            followUpObservations=fol_obs,
            followUpPeriod=fol_period,
            followUpStatus="sufficient" if (fol_val is not None and fol_obs >= 1) else "insufficient_data",
            absoluteChange=None,
            relativeChangePercent=None,
            status="insufficient_data",
            thresholdUsed=threshold,
            interpretation=f"Insufficient data to calculate observed change on {display_name}. {reason}",
        )

    # Case 2: Incompatible scales or sources
    if baseline.unit != follow_up.unit or baseline.scale != follow_up.scale:
        return MetricComparison(
            metricName=metric_name,
            metricDisplayName=display_name,
            targetDomain=target_domain,
            unit=unit,
            scale=scale,
            direction=direction,
            baselineValue=base_val,
            baselineObservations=base_obs,
            baselinePeriod=base_period,
            baselineStatus="sufficient",
            followUpValue=fol_val,
            followUpObservations=fol_obs,
            followUpPeriod=fol_period,
            followUpStatus="sufficient",
            absoluteChange=None,
            relativeChangePercent=None,
            status="not_comparable",
            thresholdUsed=threshold,
            interpretation=f"Baseline ({baseline.unit}, {baseline.scale}) and follow-up ({follow_up.unit}, {follow_up.scale}) use incompatible measurement scales.",
        )

    # Case 3: Compatible comparison
    abs_change = round(fol_val - base_val, 2)

    # Relative change: only calculate when baseline is nonzero
    rel_change: Optional[float] = None
    if abs(base_val) > 0.0001:
        rel_change = round(((fol_val - base_val) / abs(base_val)) * 100.0, 1)

    # Direction-aware material change classification
    if abs(abs_change) < threshold:
        change_status = "no_material_change"
        direction_label = "stable within normal fluctuation limits"
    else:
        if direction == "higher_is_better":
            if abs_change >= threshold:
                change_status = "improved_on_measure"
                direction_label = "positive improvement"
            else:
                change_status = "declined_on_measure"
                direction_label = "decline on measure"
        else:
            # lower_is_better
            if abs_change <= -threshold:
                change_status = "improved_on_measure"
                direction_label = "positive reduction (lower is better)"
            else:
                change_status = "declined_on_measure"
                direction_label = "increase on measure (lower is better)"

    sign = "+" if abs_change > 0 else ""
    rel_text = f" ({sign}{rel_change}%)" if rel_change is not None else ""

    interp = (
        f"Observed change of {sign}{abs_change} {unit}{rel_text} "
        f"from baseline ({base_val} {unit}, {base_obs} observation(s)) to follow-up ({fol_val} {unit}, {fol_obs} observation(s)). "
        f"This indicates a {direction_label} (threshold: {threshold} {unit}). "
        f"Note: This reflects an observed association in student activity data and does not prove causal efficacy."
    )

    return MetricComparison(
        metricName=metric_name,
        metricDisplayName=display_name,
        targetDomain=target_domain,
        unit=unit,
        scale=scale,
        direction=direction,
        baselineValue=base_val,
        baselineObservations=base_obs,
        baselinePeriod=base_period,
        baselineStatus="sufficient",
        followUpValue=fol_val,
        followUpObservations=fol_obs,
        followUpPeriod=fol_period,
        followUpStatus="sufficient",
        absoluteChange=abs_change,
        relativeChangePercent=rel_change,
        status=change_status,
        thresholdUsed=threshold,
        interpretation=interp,
    )


# ─── Comprehensive Effectiveness Report Generator ────────────────────────────

async def generate_effectiveness_report(
    intervention: dict,
    teacher: dict,
) -> InterventionEffectivenessReport:
    """
    Synchronizes follow-up measurements, calculates multi-metric comparisons,
    and returns a structured, non-clinical effectiveness report for the teacher.
    """
    intv_id = intervention.get("interventionId")
    learner_id = intervention.get("learnerId")
    target_domain = intervention.get("targetDomain", "general")

    # Fetch student name for clear teacher context
    student_doc = await db.users.find_one({"id": learner_id}, {"_id": 0, "name": 1})
    learner_name = student_doc.get("name", "Student") if student_doc else "Student"

    # Sync follow-up data from DB
    follow_up_list = await collect_follow_up_measurements(intervention)

    # Persist synced follow-up measurements back into intervention doc (idempotent)
    serialized_follow_ups = [
        f.model_dump() if hasattr(f, "model_dump") else f
        for f in follow_up_list
    ]
    await db.interventions.update_one(
        {"interventionId": intv_id},
        {"$set": {"followUpMeasurements": serialized_follow_ups, "updatedAt": int(time.time())}}
    )

    # Map existing baseline measurements
    baselines_by_metric: Dict[str, BaselineMeasurement] = {}
    for b in intervention.get("baselineMeasurements", []):
        b_model = BaselineMeasurement(**b) if isinstance(b, dict) else b
        baselines_by_metric[b_model.metricName] = b_model

    # Map follow-up measurements
    follow_ups_by_metric: Dict[str, FollowUpMeasurement] = {}
    for f in follow_up_list:
        f_model = FollowUpMeasurement(**f) if isinstance(f, dict) else f
        follow_ups_by_metric[f_model.metricName] = f_model

    # Gather all metric names across baselines, follow-ups, and target domain
    all_metrics = set(baselines_by_metric.keys()).union(set(follow_ups_by_metric.keys()))

    comparisons: List[MetricComparison] = []
    sufficient_comparisons = 0
    improved_count = 0
    declined_count = 0
    stable_count = 0

    for m_name in sorted(list(all_metrics)):
        base_obj = baselines_by_metric.get(m_name)
        fol_obj = follow_ups_by_metric.get(m_name)
        comp = calculate_metric_comparison(base_obj, fol_obj, target_domain)
        comparisons.append(comp)

        if comp.status in ("improved_on_measure", "declined_on_measure", "no_material_change"):
            sufficient_comparisons += 1
            if comp.status == "improved_on_measure":
                improved_count += 1
            elif comp.status == "declined_on_measure":
                declined_count += 1
            else:
                stable_count += 1

    # Overall data sufficiency
    has_sufficient_base = any(b.status == "sufficient" for b in baselines_by_metric.values())
    has_sufficient_fol = any(f.observationCount >= 1 for f in follow_up_list)

    if has_sufficient_base and has_sufficient_fol and sufficient_comparisons > 0:
        data_sufficiency = "sufficient"
        if improved_count > declined_count:
            summary = (
                f"Observed positive progress on {improved_count} of {sufficient_comparisons} measured metric(s) "
                f"since the support activity began. The teacher may review whether to continue or consolidate practice."
            )
        elif declined_count > improved_count:
            summary = (
                f"Observed decline on {declined_count} of {sufficient_comparisons} measured metric(s). "
                f"The teacher may consider adjusting the difficulty level, pacing, or modality of the support activity."
            )
        else:
            summary = (
                f"Observed steady performance across {sufficient_comparisons} measured metric(s). "
                f"Measurements show consistent stability within normal day-to-day score variations."
            )
    elif not has_sufficient_base and not has_sufficient_fol:
        data_sufficiency = "insufficient_data"
        summary = (
            "Insufficient practice data available for both baseline and follow-up periods. "
            "Prompt the learner to complete reading passages or adaptive practice activities to establish evidence."
        )
    elif not has_sufficient_base:
        data_sufficiency = "insufficient_baseline"
        summary = (
            "A historical baseline could not be established from prior student records. "
            "Subsequent practice has been recorded, but cannot be compared against a valid pre-support baseline."
        )
    else:
        data_sufficiency = "insufficient_followup"
        summary = (
            "A baseline has been established, but additional student practice sessions are needed "
            "since the support activity started to evaluate observed changes."
        )

    observations = [
        TeacherObservation(**o) if isinstance(o, dict) else o
        for o in intervention.get("teacherObservations", [])
    ]

    return InterventionEffectivenessReport(
        interventionId=intv_id,
        goal=intervention.get("goal", ""),
        targetDomain=target_domain,
        supportActivity=intervention.get("supportActivity", ""),
        status=intervention.get("status", "planned"),
        learnerId=learner_id,
        learnerName=learner_name,
        startDate=int(intervention.get("startDate", 0)),
        plannedReviewDate=intervention.get("plannedReviewDate"),
        comparisons=comparisons,
        dataSufficiency=data_sufficiency,
        overallSummary=summary,
        teacherObservations=observations,
    )


# ─── Intervention CRUD & Lifecycle Operations ─────────────────────────────────

async def create_intervention(
    teacher: dict,
    req: InterventionCreateRequest,
) -> V2Intervention:
    """
    Creates a new learning support activity / intervention record:
    1. Verifies teacher-student authorization.
    2. Gathers historical baseline measurements from real practice data.
    3. Initializes controlled status to 'planned' (or 'active' if startDate <= now).
    4. Persists record in db.interventions.
    """
    teacher_id = teacher.get("id")
    teacher_code = await get_teacher_classroom_code(teacher)
    if not teacher_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher does not have an active classroom assigned."
        )

    # Verify student is in teacher's classroom
    await verify_teacher_student_access(teacher, req.learnerId)

    now = int(time.time())
    start_ts = req.startDate if req.startDate is not None else now

    if req.plannedReviewDate is not None and req.plannedReviewDate < start_ts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planned review date cannot be earlier than start date."
        )

    # Establish baseline from existing data prior to start_ts
    baselines = await establish_baseline_measurements(
        student_id=req.learnerId,
        target_domain=req.targetDomain,
        start_date=start_ts,
    )

    intv_id = f"intv_{uuid.uuid4().hex[:10]}"

    obs_list: List[TeacherObservation] = []
    if req.initialNotes:
        obs_list.append(TeacherObservation(
            teacherId=teacher_id,
            stage="planning",
            notes=req.initialNotes,
            timestamp=now,
        ))

    initial_status = "planned"

    intervention = V2Intervention(
        interventionId=intv_id,
        teacherId=teacher_id,
        learnerId=req.learnerId,
        classroomCode=teacher_code,
        goal=req.goal,
        targetDomain=req.targetDomain,
        supportActivity=req.supportActivity,
        startDate=start_ts,
        plannedReviewDate=req.plannedReviewDate,
        status=initial_status,
        baselineMeasurements=baselines,
        followUpMeasurements=[],
        teacherObservations=obs_list,
        createdAt=now,
        updatedAt=now,
    )

    doc = intervention.model_dump()
    await db.interventions.insert_one(doc)
    logger.info(f"Created intervention {intv_id} for learner {req.learnerId} by teacher {teacher_id}")

    return intervention


async def get_teacher_interventions(
    teacher: dict,
    learner_id: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves interventions for the teacher's classroom with optional learner or status filtering.
    """
    teacher_code = await get_teacher_classroom_code(teacher)
    if not teacher_code:
        return []

    query: Dict[str, Any] = {"classroomCode": teacher_code}
    if learner_id:
        # Verify access to this specific learner
        await verify_teacher_student_access(teacher, learner_id)
        query["learnerId"] = learner_id
    if status_filter:
        if status_filter not in VALID_INTERVENTION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter '{status_filter}'."
            )
        query["status"] = status_filter

    cursor = db.interventions.find(query, {"_id": 0}).sort("createdAt", -1).limit(100)
    interventions = await cursor.to_list(100)

    # Attach student names for teacher convenience
    student_ids = list({i.get("learnerId") for i in interventions if i.get("learnerId")})
    if student_ids:
        students = await db.users.find(
            {"id": {"$in": student_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(len(student_ids))
        s_map = {s["id"]: s.get("name", "Student") for s in students}
        for i in interventions:
            i["learnerName"] = s_map.get(i.get("learnerId"), "Student")

    return interventions


async def update_intervention(
    teacher: dict,
    intervention_id: str,
    req: InterventionUpdateRequest,
) -> Dict[str, Any]:
    """
    Applies partial updates to goal, supportActivity, plannedReviewDate, or notes.
    Rejects modifications on terminal states (completed/cancelled).
    """
    doc = await verify_teacher_intervention_access(teacher, intervention_id)

    curr_status = doc.get("status")
    if curr_status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update intervention in terminal '{curr_status}' state."
        )

    updates: Dict[str, Any] = {"updatedAt": int(time.time())}
    if req.goal is not None:
        updates["goal"] = req.goal
    if req.targetDomain is not None:
        updates["targetDomain"] = req.targetDomain
    if req.supportActivity is not None:
        updates["supportActivity"] = req.supportActivity
    if req.plannedReviewDate is not None:
        start_date = int(doc.get("startDate", 0))
        if req.plannedReviewDate < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Planned review date cannot be earlier than start date."
            )
        updates["plannedReviewDate"] = req.plannedReviewDate

    if req.notes:
        new_obs = TeacherObservation(
            teacherId=teacher.get("id"),
            stage="active_checkin",
            notes=req.notes,
            timestamp=int(time.time()),
        ).model_dump()
        await db.interventions.update_one(
            {"interventionId": intervention_id},
            {"$push": {"teacherObservations": new_obs}}
        )

    await db.interventions.update_one(
        {"interventionId": intervention_id},
        {"$set": updates}
    )

    updated_doc = await db.interventions.find_one({"interventionId": intervention_id}, {"_id": 0})
    return updated_doc


async def transition_intervention_status(
    teacher: dict,
    intervention_id: str,
    target_status: str,
    req: Optional[InterventionTransitionRequest] = None,
) -> Dict[str, Any]:
    """
    Transitions the intervention to a new status subject to valid lifecycle rules.
    Allowed transitions:
    - planned -> active | cancelled
    - active  -> review | completed | cancelled
    - review  -> active | completed | cancelled
    - completed/cancelled -> terminal (none allowed)
    """
    doc = await verify_teacher_intervention_access(teacher, intervention_id)
    curr_status = doc.get("status")

    if target_status not in VALID_INTERVENTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target status '{target_status}'. Allowed: {sorted(list(VALID_INTERVENTION_STATUSES))}"
        )

    allowed = ALLOWED_STATUS_TRANSITIONS.get(curr_status, set())
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{curr_status}' to '{target_status}'. Allowed: {sorted(list(allowed)) or 'None (terminal state)'}"
        )

    now = int(time.time())
    updates: Dict[str, Any] = {
        "status": target_status,
        "updatedAt": now,
    }

    # If transitioning to active and startDate is in the future, activate starting now
    if target_status == "active" and curr_status == "planned":
        updates["startDate"] = now

    notes = req.notes if req else None
    if notes:
        obs = TeacherObservation(
            teacherId=teacher.get("id"),
            stage=target_status,
            notes=notes,
            timestamp=now,
        ).model_dump()
        await db.interventions.update_one(
            {"interventionId": intervention_id},
            {"$push": {"teacherObservations": obs}}
        )

    await db.interventions.update_one(
        {"interventionId": intervention_id},
        {"$set": updates}
    )

    # Automatically sync follow-up data if moving to review or completed
    updated_doc = await db.interventions.find_one({"interventionId": intervention_id}, {"_id": 0})
    if target_status in ("review", "completed"):
        await collect_follow_up_measurements(updated_doc)

    return await db.interventions.find_one({"interventionId": intervention_id}, {"_id": 0})


async def record_manual_followup(
    teacher: dict,
    intervention_id: str,
    req: ManualFollowUpRequest,
) -> Dict[str, Any]:
    """
    Allows a teacher to record an interim assessment observation (e.g. oral reading check).
    """
    doc = await verify_teacher_intervention_access(teacher, intervention_id)
    if doc.get("status") in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add measurements to a completed or cancelled intervention."
        )

    now = int(time.time())
    measurement = FollowUpMeasurement(
        interventionId=intervention_id,
        metricName=req.metricName,
        displayName=req.metricName.replace("_", " ").title(),
        value=round(req.value, 2),
        unit=req.unit or "%",
        scale=req.scale or "0-100%",
        source=req.source or "teacher_observed_assessment",
        timestamp=now,
        periodStart=now,
        periodEnd=now,
        observationCount=1,
        meetsComparisonRules=True,
        metadata={"notes": req.notes} if req.notes else {},
    ).model_dump()

    await db.interventions.update_one(
        {"interventionId": intervention_id},
        {
            "$push": {"followUpMeasurements": measurement},
            "$set": {"updatedAt": now}
        }
    )

    return await db.interventions.find_one({"interventionId": intervention_id}, {"_id": 0})
