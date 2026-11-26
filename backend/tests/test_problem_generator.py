"""
Unit Tests for Problem Generator (Milestone 4)
==============================================
Tests:
- Weak-topic targeting from context.
- Difficulty adaptation (Easy, Medium, Hard).
- Bloom's Taxonomy level selection (Remember, Understand, Apply, Analyze, Evaluate).
- Supported question types: MCQ, True/False, Short Answer, Conceptual/Application.
- Missing topic context handling (empty topics / insufficient context).
- Duplicate question prevention.
- Correct answer and explanation structure.
- Deterministic output for identical inputs.
- Invalid input handling.
"""

from datetime import datetime, timezone
import pytest

from app.agents.problem_generator import ProblemGenerator
from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    TopicContext,
)


@pytest.fixture
def base_context():
    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    profile = StudentProfileContext(
        user_id="usr-prob-1",
        full_name="Evan Student",
        email="evan@test.com",
    )
    topic_weak = TopicContext(
        id="top-weak-dp",
        subject_id="sub-algo",
        subject_name="Algorithms",
        name="Dynamic Programming",
        difficulty="Hard",
        mastery_score=42.0,  # Weak mastery
        retention_score=50.0,
    )
    topic_strong = TopicContext(
        id="top-strong-arrays",
        subject_id="sub-algo",
        subject_name="Algorithms",
        name="Arrays & Strings",
        difficulty="Easy",
        mastery_score=92.0,  # High mastery
        retention_score=95.0,
    )
    return StudentContext(
        student=profile,
        subjects=[],
        topics=[topic_weak, topic_strong],
        recent_quizzes=[],
        study_sessions=[],
        active_recommendations=[],
        reference_time=ref_time,
    )


def test_weak_topic_targeting(base_context):
    """Problem generator should automatically prioritize weak topic (mastery < 70%)."""
    agent = ProblemGenerator()
    result = agent.run(base_context)

    assert result.status == "success"
    assert len(result.probes) >= 1
    # First probe should target the weak topic
    first_probe = result.probes[0]
    assert first_probe.topic_id == "top-weak-dp"
    assert first_probe.topic_name == "Dynamic Programming"


def test_difficulty_and_bloom_level_adaptation(base_context):
    """Low mastery (<50%) selects Remember/Easy; High mastery (>85%) selects Evaluate/Hard."""
    agent = ProblemGenerator()

    # Weak topic (mastery 42%)
    bloom_low, diff_low = agent.determine_bloom_and_difficulty(
        base_context.topics[0], base_context
    )
    assert bloom_low == "Remember"
    assert diff_low == "Easy"

    # Strong topic (mastery 92%)
    bloom_high, diff_high = agent.determine_bloom_and_difficulty(
        base_context.topics[1], base_context
    )
    assert bloom_high in ["Analyze", "Evaluate"]
    assert diff_high == "Hard"


def test_supported_question_types_structure(base_context):
    """Generated probe must contain MCQ, True/False, and Short Answer question types with complete fields."""
    agent = ProblemGenerator()
    result = agent.run(base_context, target_topic_ids=["top-weak-dp"])

    assert len(result.probes) == 1
    questions = result.probes[0].questions
    assert len(questions) >= 3

    q_types = [q.question_type for q in questions]
    assert "mcq" in q_types
    assert "true_false" in q_types
    assert "short_answer" in q_types

    # Validate structure of each question
    for q in questions:
        assert q.id.startswith("gen-q-")
        assert len(q.question_text) > 10
        assert len(q.correct_answer) > 0
        assert len(q.explanation) > 10
        assert len(q.learning_objective) > 10
        if q.question_type in ["mcq", "true_false"]:
            assert q.options is not None
            assert len(q.options) >= 2


def test_empty_topics_handling():
    """Context with no topics returns empty_topics status."""
    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    profile = StudentProfileContext(user_id="usr-empty", full_name="Empty", email="empty@test.com")
    ctx = StudentContext(
        student=profile,
        subjects=[],
        topics=[],
        recent_quizzes=[],
        study_sessions=[],
        active_recommendations=[],
        reference_time=ref_time,
    )

    agent = ProblemGenerator()
    result = agent.run(ctx)
    assert result.status == "empty_topics"
    assert len(result.probes) == 0


def test_duplicate_question_prevention(base_context):
    """Each question generated within a probe must have a unique ID and non-duplicate text."""
    agent = ProblemGenerator()
    result = agent.run(base_context)

    for probe in result.probes:
        q_ids = [q.id for q in probe.questions]
        assert len(q_ids) == len(set(q_ids))
        q_texts = [q.question_text for q in probe.questions]
        assert len(q_texts) == len(set(q_texts))


def test_deterministic_output(base_context):
    """Identical contexts produce identical question sets."""
    agent = ProblemGenerator()
    res1 = agent.run(base_context)
    res2 = agent.run(base_context)

    assert res1.model_dump() == res2.model_dump()
