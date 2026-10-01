# DyslexAid V2 — Phase 8: Intervention Effectiveness & Learning Support

## 1. Executive Summary

Phase 8 introduces **Intervention Effectiveness**, an educational measurement and teacher-directed pedagogical decision-support system for DyslexAid V2.

The system empowers classroom teachers to:
1. **Document targeted learning support activities** (e.g. structured guided reading, phonological sound segmentation, syllable pacing).
2. **Establish quantitative baselines** automatically derived from historical learner practice sessions (reading sessions, speech analysis records, adaptive activity attempts).
3. **Track longitudinal follow-up measurements** collected automatically during active intervention periods alongside interim teacher-observed assessments.
4. **Review observed changes over time** using directional, threshold-aware metric comparisons.
5. **Make teacher-directed pedagogical decisions** (continue, complete, adjust support, or cancel) backed by structured longitudinal evidence.

> [!IMPORTANT]
> **Non-Clinical & Descriptive Architecture Standard**:  
> DyslexAid V2 is an educational measurement and support platform. It **does not provide medical diagnoses, clinical efficacy evaluations, or claim direct causality**. All progress indicators represent observed associations in practice performance over time and must never claim that an intervention caused observed changes.

---

## 2. Architectural Overview

The Phase 8 implementation integrates cleanly into the V2 architecture without altering existing V1 or V2 services:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Frontend (React + Vite)                         │
│  ┌─────────────────────────┐  ┌───────────────────────┐  ┌───────────────┐  │
│  │    InterventionsPage    │  │ CreateSupportActivity │  │ Detail & Review│ │
│  └───────────┬─────────────┘  └───────────┬───────────┘  └───────┬───────┘  │
│              └────────────────────────────┼──────────────────────┘          │
│                                           ▼                                 │
│                        interventionV2API (client.js)                        │
└───────────────────────────────────────────┬─────────────────────────────────┘
                                            │ HTTP / JSON
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend (FastAPI / Motor)                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Router: /api/v2/teacher/interventions (routers/v2_intervention.py)   │  │
│  │  • require_teacher Dependency (403 for Students)                      │  │
│  │  • V2_INTERVENTION_EFFECTIVENESS Flag Check (503 if Disabled)         │  │
│  │  • Classroom-Tenant Authorization Boundary Check                      │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Core Service: intervention_effectiveness.py                         │  │
│  │  • Baseline Aggregator (reading_sessions, activity_attempts, speech)   │  │
│  │  • Follow-Up Collector (post-startDate practice sessions)              │  │
│  │  • Directional Comparison Engine & Material Change Thresholds         │  │
│  │  • State Machine Validator & Idempotent Sync                          │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MongoDB: dyslexaid.interventions                                     │  │
│  │  • Indexes: interventionId, teacherId, learnerId, classroomCode       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Intervention Lifecycle & State Machine

Every intervention follows a strictly validated, directional state machine:

```
                 ┌───────────┐
                 │  PLANNED  │
                 └─────┬─────┘
                       │
         ┌─────────────┼─────────────┐
         │ (Start)     │             │ (Cancel)
         ▼             │             ▼
    ┌──────────┐       │       ┌───────────┐
    │  ACTIVE  │◄──────┤       │ CANCELLED │ [Terminal]
    └────┬─────┘       │       └───────────┘
         │             │
   ┌─────┴─────┐       │
   │           │       │
   ▼           ▼       ▼
┌────────┐   ┌───────────┐
│ REVIEW │   │ COMPLETED │ [Terminal]
└────┬───┘   └───────────┘
     │             ▲
     └─────────────┘ (Complete / Adjust / Re-activate)
```

### Transition Rules & Semantics:
- **`planned`**: Initial state upon creation. Historical practice sessions prior to `startDate` are gathered into immutable baseline measurements. May transition to `active` or `cancelled`.
- **`active`**: Support activity is actively taking place. Automated practice sessions and manual teacher observations post-`startDate` accumulate in follow-up records. May transition to `review`, `completed`, or `cancelled`.
- **`review`**: Scheduled or teacher-initiated checkpoint. Automated follow-up measurements are synced; comparative report is generated. Teacher records a decision to return to `active`, mark `completed`, or mark `cancelled`.
- **`completed`**: Terminal state. Support activity concluded with documented pedagogical observations and next steps. Immutable against further updates.
- **`cancelled`**: Terminal state. Support activity aborted prior to completion with teacher rationale. Immutable against further updates.

---

## 4. Baseline Establishment & Follow-Up Methodology

### 4.1 Baseline Gatherer (`calculate_baseline_metrics`)
When an intervention is created, the system inspects the target student's existing activity in the authorized classroom:
- **Reading Sessions (`db.reading_sessions`)**: Gathers completed sessions prior to `startDate`. Derives mean comprehension accuracy (%) and reading fluency (WPM).
- **Speech Reading Analyses (`db.speech_analyses`)**: Gathers speech evaluations prior to `startDate` to extract hesitation metrics and pronunciation accuracy.
- **Adaptive Practice (`db.activity_attempts`)**: Gathers domain-specific attempts prior to `startDate` to determine baseline skill accuracy.
- **Sample Sufficiency**: If fewer than 2 data points are found, the baseline is flagged with `insufficient_data`, preventing false comparisons.
- **Immutability Guarantee**: Once saved to `db.interventions`, baseline measurements are immutable. Subsequent practice sessions post-`startDate` do not alter the historical baseline.

### 4.2 Follow-Up Measurement Collector (`collect_follow_up_measurements`)
- Queries practice records with timestamps strictly **after** `startDate` up to the current timestamp or terminal `updatedAt`.
- Supports manual teacher interim checks (`oral_reading_check`, observational rubrics).
- Executes idempotently: re-evaluating follow-up data updates aggregates without duplicating measurements.

---

## 5. Metric Comparability, Directionality & Material Change Thresholds

### 5.1 Comparability Rules
To prevent misleading comparisons, two measurements are only compared if:
1. `scale` matches exactly (e.g. `0-100%` vs `0-100%`, or `wpm` vs `wpm`).
2. `unit` matches exactly (e.g. `%` vs `%`, or `wpm` vs `wpm`).
3. Both have sufficient observations (`sampleCount >= 2` or valid teacher check).

If scales or units differ, status is marked `not_comparable`.

### 5.2 Metric Directionality
- **`higher_is_better`**: Comprehension accuracy, reading fluency WPM, phonological accuracy.
  - Positive change beyond threshold $\rightarrow$ `improved_on_measure`
  - Negative change beyond threshold $\rightarrow$ `declined_on_measure`
- **`lower_is_better`**: Reading hesitation duration, error count, latency.
  - Negative change beyond threshold $\rightarrow$ `improved_on_measure`
  - Positive change beyond threshold $\rightarrow$ `declined_on_measure`

### 5.3 Material Change Thresholds
To avoid interpreting trivial day-to-day noise as meaningful change, explicit thresholds are applied:
- **Accuracy / Comprehension**: **3.0%** threshold. Absolute changes within $[-3.0\%, +3.0\%]$ are classified as `no_material_change`.
- **Reading Fluency**: **5.0 WPM** threshold. Absolute changes within $[-5.0, +5.0\text{ wpm}]$ are classified as `no_material_change`.
- **Hesitation Duration**: **0.5 seconds** threshold.

---

## 6. Associative vs. Causal Attribution

DyslexAid explicitly enforces descriptive, non-causal language across all models, services, UI text, and documentation:

> [!WARNING]
> **Why Changes Are Associative, Not Causal**:
> 1. **Concurrent Maturation**: Students naturally develop reading skills as part of overall cognitive development.
> 2. **Uncontrolled Class Instruction**: Students participate in general classroom reading, peer reading, and home reading simultaneously.
> 3. **Environmental Variances**: Time of day, student fatigue, test anxiety, or difficulty of specific reading passages introduce variation.
> 4. **Scientific Integrity**: Without a randomized controlled trial (RCT), educational software cannot infer causation.
> 
> Therefore, report summaries state: *"During the support period, observed comprehension accuracy was 82.5%, compared to a baseline of 75.0% (+7.5% observed difference)."*

---

## 7. Security, Tenant Isolation & Privacy

1. **Role-Based Access Control**:
   - All `/api/v2/teacher/interventions` endpoints depend on `require_teacher`.
   - Students attempting access receive `403 Forbidden`.
   - Unauthenticated requests receive `401 Unauthorized`.
2. **Classroom Tenant Boundaries**:
   - `verify_teacher_intervention_access` verifies the student belongs to the teacher's classroom (`classroomCode`).
   - Requests for students in other classrooms are rejected with `403 Forbidden`.
3. **Student Privacy**:
   - No raw audio recordings, audio URLs, hashed passwords, or private parent notes are included in intervention schemas.
4. **Feature Flag**:
   - Governed by `V2_INTERVENTION_EFFECTIVENESS` in `Settings`. If disabled, endpoints return `503 Service Unavailable`.

---

## 8. API Reference

All routes are mounted under `/api/v2/teacher/interventions`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v2/teacher/interventions` | Create support activity, calculate baseline, set `planned` |
| `GET` | `/api/v2/teacher/interventions` | List activities for classroom with optional `status` filter |
| `GET` | `/api/v2/teacher/interventions/{id}` | Retrieve activity details, baselines, and observations |
| `PATCH` | `/api/v2/teacher/interventions/{id}` | Update goal, activity description, or planned review date |
| `POST` | `/api/v2/teacher/interventions/{id}/start` | Transition from `planned` $\rightarrow$ `active` |
| `POST` | `/api/v2/teacher/interventions/{id}/review` | Transition from `active` $\rightarrow$ `review` and sync follow-ups |
| `POST` | `/api/v2/teacher/interventions/{id}/complete` | Transition to terminal `completed` with pedagogical notes |
| `POST` | `/api/v2/teacher/interventions/{id}/cancel` | Transition to terminal `cancelled` with cancellation reason |
| `GET` | `/api/v2/teacher/interventions/{id}/effectiveness` | Generate comparative before-and-after report |
| `POST` | `/api/v2/teacher/interventions/{id}/measurements` | Record manual teacher interim observation |

---

## 9. Test Verification Summary

Comprehensive automated tests cover all Phase 8 components:
- **Phase 8 Tests**: `backend/test_phase8_intervention_effectiveness.py` (32 tests, 100% pass).
- **Regression Suite**: Phases 1 through 8 (`test_phase2_endpoints.py`, `test_phase2_learner_profile.py`, `test_phase3_adaptive_engine.py`, `test_phase4_reading_coach.py`, `test_phase5_speech_analysis.py`, `test_phase6_ai_tutor.py`, `test_phase7_teacher_analytics.py`, `test_phase8_intervention_effectiveness.py`).
- **Total Passing Tests**: **182 passed out of 182 (0 regressions)** in 3.19s.
- **Frontend Build**: `vite build` completed cleanly in 9.13s with 0 errors.
