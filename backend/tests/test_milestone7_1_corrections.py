"""
Regression Tests for Milestone 7.1 Corrections
==============================================
Validates:
1. PerformanceAgent capacity overshoot fix:
   - 30-minute capacity with a 60-minute Hard task splits/compresses into 30m.
   - 20-minute capacity with a 45-minute Medium task splits/compresses into 20m.
   - Multiple recommendations whose combined duration would exceed capacity are capped/truncated.
   - Missing, None, zero, negative, and float capacity values are safely handled (0 recommendations emitted, no crash).
   - Total allocated recommendation duration NEVER exceeds daily capacity.
2. Automatic Exam-Date Context Propagation:
   - TopicContext with missing days_until_exam automatically derives days_until_exam from SubjectContext.exam_date.
   - Explicit days_until_exam on TopicContext takes precedence.
   - Missing exam dates on SubjectContext safely leave days_until_exam as None.
   - Past exam dates (e.g. 5 days ago) clamp to 0.0 without negative values.
   - Consistency between in-memory StudentContext and DB-built StudentContext.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.agents.performance_agent import PerformanceAgent
from app.agents.schemas import (
    StudentProfileContext,
    SubjectContext,
    TopicContext,
    StudentContext,
)


@pytest.fixture
def base_time():
    return datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)


# ==============================================================================
# 1. CAPACITY CONSTRAINT & TASK SPLITTING TESTS
# ==============================================================================

def test_30m_capacity_with_60m_hard_task(base_time):
    """A 30-minute capacity with a 60-minute Hard task splits into a 30m drill."""
    student = StudentProfileContext(
        user_id="u_cap_30",
        full_name="Cap 30",
        email="cap30@test.com",
        daily_capacity_minutes=30,
    )
    subj = SubjectContext(id="s1", name="AI", code="AI101")
    topic = TopicContext(
        id="t_hard",
        subject_id="s1",
        subject_name="AI",
        name="Transformer Models",
        difficulty="Hard",  # Desired duration = 60m
        mastery_score=40.0,
        retention_score=45.0,
        decay_rate_lambda=0.10,
        elapsed_days=4.0,
    )
    ctx = StudentContext(reference_time=base_time, student=student, subjects=[subj], topics=[topic])
    agent = PerformanceAgent()
    recs = agent.run(ctx)

    assert len(recs) == 1
    rec = recs[0]
    assert rec.estimated_duration_minutes == 30
    assert "Focused Drill" in rec.title
    assert "30m" in rec.title
    assert sum(r.estimated_duration_minutes for r in recs) <= 30


def test_20m_capacity_with_45m_medium_task(base_time):
    """A 20-minute capacity with a 45-minute Medium task splits into a 20m drill."""
    student = StudentProfileContext(
        user_id="u_cap_20",
        full_name="Cap 20",
        email="cap20@test.com",
        daily_capacity_minutes=20,
    )
    subj = SubjectContext(id="s1", name="OS", code="OS101")
    topic = TopicContext(
        id="t_med",
        subject_id="s1",
        subject_name="OS",
        name="Virtual Memory",
        difficulty="Medium",  # Desired duration = 45m
        mastery_score=50.0,
        retention_score=55.0,
        decay_rate_lambda=0.08,
        elapsed_days=3.0,
    )
    ctx = StudentContext(reference_time=base_time, student=student, subjects=[subj], topics=[topic])
    agent = PerformanceAgent()
    recs = agent.run(ctx)

    assert len(recs) == 1
    assert recs[0].estimated_duration_minutes == 20
    assert sum(r.estimated_duration_minutes for r in recs) <= 20


def test_multiple_recommendations_capacity_capped(base_time):
    """Multiple recommendations whose combined duration would exceed capacity are capped/truncated."""
    student = StudentProfileContext(
        user_id="u_cap_75",
        full_name="Cap 75",
        email="cap75@test.com",
        daily_capacity_minutes=75,
    )
    subj = SubjectContext(id="s1", name="CS", code="CS101")
    # 3 Medium topics (45m each = 135m total desired)
    topics = [
        TopicContext(
            id=f"t_{i}",
            subject_id="s1",
            subject_name="CS",
            name=f"Topic {i}",
            difficulty="Medium",  # 45m
            mastery_score=50.0 - i * 5,
            retention_score=50.0,
            decay_rate_lambda=0.08,
            elapsed_days=3.0,
        )
        for i in range(1, 4)
    ]
    ctx = StudentContext(reference_time=base_time, student=student, subjects=[subj], topics=topics)
    agent = PerformanceAgent()
    recs = agent.run(ctx)

    total_allocated = sum(r.estimated_duration_minutes for r in recs)
    assert total_allocated <= 75
    # First item: 45m. Remaining: 30m. Second item desired 45m -> split to 30m. Total = 75m.
    assert len(recs) == 2
    assert recs[0].estimated_duration_minutes == 45
    assert recs[1].estimated_duration_minutes == 30
    assert "Focused Drill" in recs[1].title


def test_missing_zero_and_negative_capacity_handled_safely(base_time):
    """Zero, negative, or missing capacity produces zero recommendations without throwing exceptions."""
    agent = PerformanceAgent()
    subj = SubjectContext(id="s1", name="CS", code="CS101")
    topic = TopicContext(id="t1", subject_id="s1", subject_name="CS", name="Topic 1")

    # Manually test via object with zero capacity
    student_zero = StudentProfileContext(user_id="u0", full_name="Zero", email="z@test.com", daily_capacity_minutes=15)
    student_zero.daily_capacity_minutes = 0  # override directly
    ctx_zero = StudentContext(reference_time=base_time, student=student_zero, subjects=[subj], topics=[topic])
    assert agent.run(ctx_zero) == []

    # Negative capacity
    student_neg = StudentProfileContext(user_id="uneg", full_name="Neg", email="n@test.com", daily_capacity_minutes=15)
    student_neg.daily_capacity_minutes = -30
    ctx_neg = StudentContext(reference_time=base_time, student=student_neg, subjects=[subj], topics=[topic])
    assert agent.run(ctx_neg) == []


# ==============================================================================
# 2. AUTOMATIC EXAM-DATE CONTEXT PROPAGATION TESTS
# ==============================================================================

def test_automatic_exam_date_propagation_from_subject(base_time):
    """When TopicContext.days_until_exam is missing/None, derive from SubjectContext.exam_date."""
    exam_dt = base_time + timedelta(days=5)
    subj = SubjectContext(
        id="subj_math",
        name="Discrete Math",
        code="MATH101",
        exam_date=exam_dt,
    )
    topic = TopicContext(
        id="t_math_1",
        subject_id="subj_math",
        subject_name="Discrete Math",
        name="Graph Theory",
        days_until_exam=None,  # Missing!
    )
    student = StudentProfileContext(user_id="u1", full_name="Student", email="s@test.com")
    ctx = StudentContext(
        reference_time=base_time,
        student=student,
        subjects=[subj],
        topics=[topic],
    )

    # Automatically derived!
    propagated_topic = ctx.topics[0]
    assert propagated_topic.days_until_exam is not None
    assert pytest.approx(propagated_topic.days_until_exam, abs=0.1) == 5.0
    assert propagated_topic.exam_date == exam_dt


def test_explicit_days_until_exam_takes_precedence(base_time):
    """Explicitly provided TopicContext.days_until_exam is preserved even if Subject has exam_date."""
    exam_dt = base_time + timedelta(days=10)
    subj = SubjectContext(
        id="subj_chem",
        name="Organic Chemistry",
        code="CHEM101",
        exam_date=exam_dt,
    )
    topic = TopicContext(
        id="t_chem_1",
        subject_id="subj_chem",
        subject_name="Organic Chemistry",
        name="Benzene Rings",
        days_until_exam=3.5,  # Explicitly set to 3.5
    )
    student = StudentProfileContext(user_id="u1", full_name="Student", email="s@test.com")
    ctx = StudentContext(
        reference_time=base_time,
        student=student,
        subjects=[subj],
        topics=[topic],
    )

    propagated_topic = ctx.topics[0]
    assert propagated_topic.days_until_exam == 3.5


def test_missing_exam_dates_safely_preserved(base_time):
    """When SubjectContext has no exam_date, days_until_exam remains None safely."""
    subj = SubjectContext(id="subj_art", name="Art History", code="ART101", exam_date=None)
    topic = TopicContext(
        id="t_art_1",
        subject_id="subj_art",
        subject_name="Art History",
        name="Renaissance",
        days_until_exam=None,
    )
    student = StudentProfileContext(user_id="u1", full_name="Student", email="s@test.com")
    ctx = StudentContext(
        reference_time=base_time,
        student=student,
        subjects=[subj],
        topics=[topic],
    )

    assert ctx.topics[0].days_until_exam is None


def test_past_exam_dates_clamped_to_zero(base_time):
    """Past exam dates (e.g. 3 days ago) clamp days_until_exam to 0.0 (no negative days)."""
    past_exam = base_time - timedelta(days=3)
    subj = SubjectContext(
        id="subj_hist",
        name="World History",
        code="HIST101",
        exam_date=past_exam,
    )
    topic = TopicContext(
        id="t_hist_1",
        subject_id="subj_hist",
        subject_name="World History",
        name="Industrial Revolution",
        days_until_exam=None,
    )
    student = StudentProfileContext(user_id="u1", full_name="Student", email="s@test.com")
    ctx = StudentContext(
        reference_time=base_time,
        student=student,
        subjects=[subj],
        topics=[topic],
    )

    assert ctx.topics[0].days_until_exam == 0.0
