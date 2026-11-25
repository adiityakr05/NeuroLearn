"""
Tests for Milestone 8.4: Historical Analytics Engine
===================================================
1. Pre-window historical quiz replay: verifies pre-window attempts establish true starting mastery.
2. In-window EMA reconstruction: verifies subsequent attempts advance mastery with standard formula.
3. Topics with zero historical attempts: verifies fallback to 50.0 labeled initial_default_baseline.
4. Window filtering: verifies 14d, 30d, semester, and 7d properly filter time boundaries.
5. Retention history vs predicted decay separation: ensures continuous curve and discrete recall are separate.
6. Current decay rate lambda reporting: ensures lambda distribution reflects current state without inventing time series.
7. Mutually exclusive recommendation status partition: verifies total == pending + accepted + completed + dismissed.
8. Feedback helpful ratio denominator: ensures only non-null feedback rows count in denominator.
9. Study behavior analytics: ensures abandoned sessions are never counted as completed and legacy NULL actual duration is handled.
10. Tenant isolation: verifies student A cannot query or aggregate student B's historical metrics.
11. Empty student state: newly registered student receives clean 0/empty structure without 500 exceptions.
12. Frontend bundle compatibility: verifies frontend_bundle format matches all expectations of Analytics.jsx.
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.base import Base
from app.main import app
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import (
    User,
    Subject,
    Topic,
    QuizAttempt,
    RevisionHistory,
    StudySession,
    Recommendation,
)
from app.services.analytics_service import analytics_service


@pytest.fixture
def seeded_analytics_students(db_session):
    """Sets up two test students with curriculum and historical events."""
    now = datetime.now(timezone.utc)

    # Student 1 (Aditya)
    u1 = User(
        id="u_hist_1",
        email="aditya_hist@test.com",
        full_name="Aditya Kumar",
        hashed_password="pw",
    )
    # Student 2 (Isolator)
    u2 = User(
        id="u_hist_2",
        email="other_student@test.com",
        full_name="Other Student",
        hashed_password="pw",
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    # Subjects
    sub1 = Subject(id="s_algo_1", user_id=u1.id, name="Algorithms", code="CS301")
    sub2 = Subject(id="s_ml_1", user_id=u1.id, name="Machine Learning", code="CS302")
    sub_other = Subject(id="s_other_2", user_id=u2.id, name="Algorithms", code="CS301")
    db_session.add_all([sub1, sub2, sub_other])
    db_session.commit()

    # Topics for Student 1
    t_dp = Topic(
        id="top_dp_1",
        subject_id=sub1.id,
        name="Dynamic Programming",
        difficulty="Hard",
        mastery_score=68.3,
        retention_score=75.0,
        decay_rate_lambda=0.08,
        next_revision=now - timedelta(days=2),  # Overdue
    )
    t_svm = Topic(
        id="top_svm_1",
        subject_id=sub2.id,
        name="SVM Kernels",
        difficulty="Hard",
        mastery_score=50.0,
        retention_score=60.0,
        decay_rate_lambda=0.14,
        next_revision=now + timedelta(days=5),  # Upcoming
    )
    # Topic for Student 2
    t_other = Topic(
        id="top_other_2",
        subject_id=sub_other.id,
        name="Dynamic Programming",
        difficulty="Hard",
        mastery_score=95.0,
        retention_score=90.0,
        decay_rate_lambda=0.03,
    )
    db_session.add_all([t_dp, t_svm, t_other])
    db_session.commit()

    # Pre-window quiz attempt for Student 1 on DP (40 days ago: pre-30d window)
    # Initial 50 -> round((50 * 0.7) + (80 * 0.3), 1) = 59.0
    q_pre = QuizAttempt(
        id="q_pre_dp",
        user_id=u1.id,
        topic_id=t_dp.id,
        title="DP Diagnostic",
        score=80.0,
        accuracy=80.0,
        attempted_at=now - timedelta(days=40),
    )
    # In-window quiz attempt for Student 1 on DP (10 days ago)
    # Starting 59.0 -> round((59.0 * 0.7) + (90 * 0.3), 1) = 68.3
    q_in = QuizAttempt(
        id="q_in_dp",
        user_id=u1.id,
        topic_id=t_dp.id,
        title="DP Midterm Prep",
        score=90.0,
        accuracy=90.0,
        attempted_at=now - timedelta(days=10),
    )
    # Quiz attempt for Student 2
    q_other = QuizAttempt(
        id="q_other_dp",
        user_id=u2.id,
        topic_id=t_other.id,
        title="Other DP Quiz",
        score=100.0,
        accuracy=100.0,
        attempted_at=now - timedelta(days=5),
    )
    db_session.add_all([q_pre, q_in, q_other])

    # Revision History for Student 1
    rev1 = RevisionHistory(
        id="rev_hist_1",
        topic_id=t_dp.id,
        revision_date=(now - timedelta(days=12)).strftime("%Y-%m-%d"),
        score=85.0,
        interval_days=7,
        repetition_number=2,
        note="Active recall completed",
    )
    db_session.add(rev1)

    # Study Sessions for Student 1
    # 1. Completed session with measured actual duration
    s_comp = StudySession(
        id="sess_1",
        user_id=u1.id,
        subject_id=sub1.id,
        date=(now - timedelta(days=8)).strftime("%Y-%m-%d"),
        duration_minutes=45,
        actual_duration_minutes=50,
        status="completed",
    )
    # 2. Abandoned session
    s_aband = StudySession(
        id="sess_2",
        user_id=u1.id,
        subject_id=sub1.id,
        date=(now - timedelta(days=6)).strftime("%Y-%m-%d"),
        duration_minutes=60,
        actual_duration_minutes=15,
        status="abandoned",
    )
    # 3. Pending session
    s_pend = StudySession(
        id="sess_3",
        user_id=u1.id,
        subject_id=sub2.id,
        date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
        duration_minutes=30,
        status="pending",
    )
    # 4. Legacy completed session with missing actual duration
    s_legacy = StudySession(
        id="sess_4",
        user_id=u1.id,
        subject_id=sub2.id,
        date=(now - timedelta(days=15)).strftime("%Y-%m-%d"),
        duration_minutes=40,
        actual_duration_minutes=None,
        status="completed",
    )
    db_session.add_all([s_comp, s_aband, s_pend, s_legacy])

    # Recommendations for Student 1
    # Partition: 1 pending, 1 accepted, 1 completed, 1 dismissed (total = 4)
    r1 = Recommendation(
        id="rec_1",
        user_id=u1.id,
        subject_id=sub1.id,
        topic_id=t_dp.id,
        type="retention_decay",
        title="Revise DP",
        reason_type="decay",
        reason_detail="Decay threshold crossed",
        status="completed",
        feedback_helpful=True,
        updated_at=now - timedelta(days=11),
    )
    r2 = Recommendation(
        id="rec_2",
        user_id=u1.id,
        subject_id=sub2.id,
        topic_id=t_svm.id,
        type="diagnostic_probe",
        title="Probe SVM",
        reason_type="probe",
        reason_detail="Needs check",
        status="accepted",
        feedback_helpful=None,  # No feedback given
    )
    r3 = Recommendation(
        id="rec_3",
        user_id=u1.id,
        subject_id=sub1.id,
        type="pacing_optimization",
        title="Pacing Check",
        reason_type="pacing",
        reason_detail="Ahead of schedule",
        status="dismissed",
        feedback_helpful=False,
    )
    r4 = Recommendation(
        id="rec_4",
        user_id=u1.id,
        subject_id=sub2.id,
        type="exam_priority",
        title="Exam Focus",
        reason_type="exam",
        reason_detail="Upcoming finals",
        status="pending",
    )
    db_session.add_all([r1, r2, r3, r4])
    db_session.commit()

    return {
        "u1": u1,
        "u2": u2,
        "sub1": sub1,
        "sub2": sub2,
        "t_dp": t_dp,
        "t_svm": t_svm,
        "t_other": t_other,
    }


def test_1_pre_window_quiz_replay_and_starting_mastery(db_session, seeded_analytics_students):
    """1. Pre-window quiz attempt replays to establish true starting mastery (59.0, not reset to 50)."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    dp_traj = next((t for t in res.mastery_trajectories.topics if t.topic_id == "top_dp_1"), None)
    assert dp_traj is not None
    # Pre-window attempt (80%) on 50 baseline gave 59.0
    assert dp_traj.starting_mastery == 59.0
    assert dp_traj.starting_status == "prior_reconstructed_stable"


def test_2_in_window_ema_reconstruction(db_session, seeded_analytics_students):
    """2. In-window attempt (90%) updates mastery from 59.0 -> 68.3."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    dp_traj = next((t for t in res.mastery_trajectories.topics if t.topic_id == "top_dp_1"), None)
    assert dp_traj.current_mastery == 68.3
    assert len(dp_traj.data_points) >= 2
    # Find event point
    evt_point = next((p for p in dp_traj.data_points if p.label == "reconstructed_event"), None)
    assert evt_point is not None
    assert evt_point.mastery == 68.3
    assert evt_point.score == 90.0


def test_3_topic_with_zero_historical_attempts(db_session, seeded_analytics_students):
    """3. Topic with zero historical attempts defaults to baseline 50.0 labeled initial_default_baseline."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    svm_traj = next((t for t in res.mastery_trajectories.topics if t.topic_id == "top_svm_1"), None)
    assert svm_traj is not None
    assert svm_traj.starting_mastery == 50.0
    assert svm_traj.starting_status == "initial_default_baseline"
    assert svm_traj.current_mastery == 50.0


def test_4_window_filtering_boundaries(db_session, seeded_analytics_students):
    """4. Window filtering: in-window 10-day quiz appears in 14d and 30d, but NOT in 7d."""
    u1 = seeded_analytics_students["u1"]

    res_7d = analytics_service.get_historical_analytics(db_session, u1.id, time_range="7d")
    res_14d = analytics_service.get_historical_analytics(db_session, u1.id, time_range="14d")

    dp_7d = next(t for t in res_7d.mastery_trajectories.topics if t.topic_id == "top_dp_1")
    dp_14d = next(t for t in res_14d.mastery_trajectories.topics if t.topic_id == "top_dp_1")

    # In 7d, 10-day-old quiz is pre-window, so in-window points have no reconstructed events
    assert not any(p.label == "reconstructed_event" for p in dp_7d.data_points)
    # In 14d, 10-day-old quiz is inside the window
    assert any(p.label == "reconstructed_event" for p in dp_14d.data_points)


def test_5_retention_predicted_vs_actual_separation(db_session, seeded_analytics_students):
    """5. Predicted retention curve is continuous while actual recall appears only on discrete days."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    curve = res.retention_analytics.predicted_vs_actual
    assert len(curve) > 0

    # Predicted is non-null everywhere
    for pt in curve:
        assert pt.predicted > 0.0
        assert pt.baseline_without_repetition > 0.0

    # Actual recall test occurs on the day corresponding to the in-window quiz
    has_actual = any(pt.actual is not None for pt in curve)
    assert has_actual is True


def test_6_decay_rate_lambda_reported_from_current_state(db_session, seeded_analytics_students):
    """6. Current lambda distribution reflects active topic states without claiming historical trends."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    dist = res.retention_analytics.current_decay_distribution
    # top_dp_1 has lambda=0.08 (moderate), top_svm_1 has lambda=0.14 (fast decay)
    assert dist.moderate_decay_count == 1
    assert dist.fast_decay_count == 1
    assert dist.high_stability_count == 0


def test_7_recommendation_mutually_exclusive_status_partition(db_session, seeded_analytics_students):
    """7. Recommendation status counts strictly sum to total: pending + accepted + completed + dismissed == total."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    recs = res.recommendation_effectiveness
    assert recs.total_recommendations == 4
    counts = recs.status_counts
    assert counts.pending + counts.accepted + counts.completed + counts.dismissed == recs.total_recommendations

    rates = recs.rates
    # 1 pending, 1 accepted, 1 completed, 1 dismissed
    assert rates.currently_accepted_rate == 25.0
    assert rates.completion_rate == 25.0
    assert rates.dismissal_rate == 25.0
    assert rates.pending_rate == 25.0
    assert rates.adoption_rate == 50.0
    assert rates.acceptance_rate == 50.0  # Backward-compatible alias


def test_8_recommendation_feedback_denominator_accuracy(db_session, seeded_analytics_students):
    """8. Feedback helpful ratio denominator only counts rows where feedback was provided."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    fb = res.recommendation_effectiveness.feedback
    # 2 recommendations had feedback (rec_1: True, rec_3: False)
    assert fb.total_with_feedback == 2
    assert fb.helpful_count == 1
    assert fb.unhelpful_count == 1
    assert fb.helpful_ratio == 50.0


def test_9_study_behavior_abandoned_session_exclusion_and_legacy_handling(db_session, seeded_analytics_students):
    """9. Study behavior excludes abandoned sessions from completed count and separates legacy NULL durations."""
    u1 = seeded_analytics_students["u1"]
    res = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")

    sb = res.study_behavior
    assert sb.total_sessions == 4
    assert sb.completed_sessions == 2
    assert sb.abandoned_sessions == 1
    assert sb.pending_sessions == 1

    # Completed measured actual minutes = 50 (from sess_1)
    assert sb.completed_actual_minutes == 50
    assert sb.measured_actual_minutes == 50  # Backward-compatible alias
    # Legacy estimated minutes = 40 (from sess_4)
    assert sb.legacy_estimated_minutes == 40
    # Abandoned minutes = 15 (from sess_2)
    assert sb.abandoned_minutes == 15
    # Total elapsed = 50 + 15 = 65
    assert sb.total_elapsed_minutes == 65
    # Total completed = 50 + 40 = 90
    assert sb.total_completed_minutes == 90
    # Average actual duration is strictly based on measured completed sessions: 50 / 1 = 50.0
    assert sb.average_actual_duration_minutes == 50.0

    # Summary KPI: actual_study_minutes includes both measured and legacy completed time (50 + 40 = 90)
    assert res.summary.actual_study_minutes == 90
    assert res.summary.measured_actual_minutes == 50
    assert res.summary.legacy_estimated_minutes == 40


def test_10_cross_user_isolation(db_session, seeded_analytics_students):
    """10. Tenant isolation: student 1 cannot see student 2's high quiz scores or topics."""
    u1 = seeded_analytics_students["u1"]
    u2 = seeded_analytics_students["u2"]

    res1 = analytics_service.get_historical_analytics(db_session, u1.id, time_range="30d")
    res2 = analytics_service.get_historical_analytics(db_session, u2.id, time_range="30d")

    # u1 topics do not include u2's top_other_2
    u1_topic_ids = [t.topic_id for t in res1.mastery_trajectories.topics]
    assert "top_other_2" not in u1_topic_ids

    # u2 topics only include top_other_2
    u2_topic_ids = [t.topic_id for t in res2.mastery_trajectories.topics]
    assert "top_dp_1" not in u2_topic_ids
    assert "top_other_2" in u2_topic_ids


def test_11_empty_student_state_safety(db_session):
    """11. Newly registered student with zero data receives a valid structure without 500 or division by zero."""
    new_user = User(
        id="u_empty_student",
        email="empty_student@test.com",
        full_name="New Student",
        hashed_password="pw",
    )
    db_session.add(new_user)
    db_session.commit()

    res = analytics_service.get_historical_analytics(db_session, new_user.id, time_range="30d")
    assert res.summary.average_quiz_accuracy == 0.0
    assert res.mastery_trajectories.topics == []
    assert res.study_behavior.total_sessions == 0
    assert res.study_behavior.completion_percentage == 0.0
    assert res.recommendation_effectiveness.total_recommendations == 0
    assert res.recommendation_effectiveness.rates.acceptance_rate == 0.0
    assert res.recommendation_effectiveness.rates.currently_accepted_rate == 0.0
    assert res.recommendation_effectiveness.rates.adoption_rate == 0.0
    assert res.study_behavior.completed_actual_minutes == 0
    assert res.study_behavior.total_elapsed_minutes == 0
    assert res.summary.actual_study_minutes == 0


def test_12_fastapi_endpoint_and_frontend_bundle_format(db_session, seeded_analytics_students):
    """12. Verifies GET /api/analytics/history HTTP endpoint and frontend_bundle structure."""
    u1 = seeded_analytics_students["u1"]
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: u1

    client = TestClient(app)
    try:
        res = client.get("/api/analytics/history?timeRange=30d")
        assert res.status_code == 200
        data = res.json()

        assert "frontend_bundle" in data
        bundle = data["frontend_bundle"]
        assert "summary" in bundle
        assert "retentionDecayCurve" in bundle
        assert "quizTrends" in bundle
        assert "topicQuizPerformance" in bundle
        assert "subjectMasteryComparison" in bundle
        assert "revisionFrequency" in bundle
        assert "overdueList" in bundle

        # Check overdue list populated from top_dp_1
        assert len(bundle["overdueList"]) >= 1
        assert bundle["overdueList"][0]["topic"] == "Dynamic Programming"
    finally:
        app.dependency_overrides.clear()


def test_13_direct_pending_to_completed_recommendation_adoption_rate(db_session, seeded_analytics_students):
    """13. Tests adoption rate when a recommendation moves directly from pending to completed."""
    now = datetime.now(timezone.utc)
    u_new = User(
        id="u_direct_comp",
        email="direct_comp@test.com",
        full_name="Direct Complete Student",
        hashed_password="pw",
    )
    db_session.add(u_new)
    db_session.commit()

    # Create 2 recommendations: 1 pending, 1 completed directly
    r_pend = Recommendation(
        id="rec_dir_1",
        user_id=u_new.id,
        type="exam_priority",
        title="Direct 1",
        reason_type="exam",
        reason_detail="Exam",
        status="pending",
    )
    r_direct_done = Recommendation(
        id="rec_dir_2",
        user_id=u_new.id,
        type="exam_priority",
        title="Direct 2",
        reason_type="exam",
        reason_detail="Exam",
        status="completed",
    )
    db_session.add_all([r_pend, r_direct_done])
    db_session.commit()

    res = analytics_service.get_historical_analytics(db_session, u_new.id, time_range="30d")
    rates = res.recommendation_effectiveness.rates

    # 0 accepted, 1 completed out of 2
    assert rates.currently_accepted_rate == 0.0
    assert rates.completion_rate == 50.0
    assert rates.adoption_rate == 50.0
    assert rates.acceptance_rate == 50.0

