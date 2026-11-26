"""
Unit Tests for Central AI Orchestrator (Milestone 5)
====================================================
Tests:
- Full pipeline execution coordinating all agents.
- Individual execution modes (Quiz Evaluation, Diagnostic, Recommendation).
- Recommendation merging, conflict resolution, and deduplication.
- Priority ordering (urgent > high > medium > low).
- Configurable recommendation limits and capacity constraints.
- Agent failure and fallback behavior (per-agent error isolation).
- Topic retention states via ML Retention Engine.
- Deterministic reproducibility.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.agents.orchestrator import AIOrchestrator
from app.agents.orchestrator_schemas import ExecutionMode
from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    TopicContext,
    SubjectContext,
    QuizAttemptContext,
    AgentRecommendationCandidate,
)


@pytest.fixture
def complex_context():
    ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    profile = StudentProfileContext(
        user_id="usr-orch-1",
        full_name="Fiona Student",
        email="fiona@test.com",
        daily_capacity_minutes=150,
    )
    topics = [
        TopicContext(
            id="top-1",
            subject_id="sub-1",
            subject_name="Algorithms",
            name="Graph Traversals",
            difficulty="Hard",
            mastery_score=40.0,
            retention_score=35.0,
            decay_rate_lambda=0.10,
            elapsed_days=8.0,
            days_until_exam=5.0,
        ),
        TopicContext(
            id="top-2",
            subject_id="sub-1",
            subject_name="Algorithms",
            name="Divide & Conquer",
            difficulty="Medium",
            mastery_score=85.0,
            retention_score=88.0,
            decay_rate_lambda=0.06,
            elapsed_days=1.0,
            days_until_exam=5.0,
        ),
    ]
    quizzes = [
        QuizAttemptContext(
            id="q-orch-1",
            topic_id="top-1",
            topic_name="Graph Traversals",
            score=30.0,
            accuracy=30.0,
            critic_evaluated=False,
        ),
    ]
    return StudentContext(
        student=profile,
        subjects=[],
        topics=topics,
        recent_quizzes=quizzes,
        study_sessions=[],
        active_recommendations=[],
        reference_time=ref_time,
    )


def test_full_pipeline_execution(complex_context):
    """Full mode should execute Critic, Learning, Problem Generator, and Performance agents."""
    orchestrator = AIOrchestrator()
    result = orchestrator.run(context=complex_context, mode=ExecutionMode.FULL)

    assert result.user_id == "usr-orch-1"
    assert len(result.metadata.executed_agents) == 4
    assert "CriticAgent" in result.metadata.executed_agents
    assert "LearningAgent" in result.metadata.executed_agents
    assert "ProblemGenerator" in result.metadata.executed_agents
    assert "PerformanceAgent" in result.metadata.executed_agents

    assert len(result.critic_evaluations) == 1
    assert result.critic_evaluations[0].performance_category == "High Concern"

    assert len(result.diagnostic_probes) >= 1
    assert len(result.recommendations) >= 1
    assert "top-1" in result.topic_retention_states


def test_quiz_evaluation_mode(complex_context):
    """Quiz evaluation mode executes CriticAgent only."""
    orchestrator = AIOrchestrator()
    result = orchestrator.run(context=complex_context, mode=ExecutionMode.QUIZ_EVALUATION)

    assert result.metadata.executed_agents == ["CriticAgent"]
    assert len(result.critic_evaluations) == 1
    assert len(result.diagnostic_probes) == 0


def test_diagnostic_mode(complex_context):
    """Diagnostic mode executes ProblemGenerator only."""
    orchestrator = AIOrchestrator()
    result = orchestrator.run(context=complex_context, mode=ExecutionMode.DIAGNOSTIC)

    assert result.metadata.executed_agents == ["ProblemGenerator"]
    assert len(result.diagnostic_probes) >= 1
    assert len(result.critic_evaluations) == 0


def test_recommendation_merging_and_deduplication(complex_context):
    """Multiple agents proposing recommendations for the same topic must resolve to highest priority."""
    orchestrator = AIOrchestrator()
    candidates = [
        AgentRecommendationCandidate(
            topic_id="top-1",
            agent_element="Problem Generator",
            type="diagnostic_probe",
            priority="medium",
            title="Probe",
            reason_type="probe",
            reason_detail="detail",
            estimated_duration_minutes=30,
        ),
        AgentRecommendationCandidate(
            topic_id="top-1",
            agent_element="Critic",
            type="retention_decay",
            priority="urgent",  # Higher priority
            title="Urgent Remediation",
            reason_type="critic_gap",
            reason_detail="detail",
            estimated_duration_minutes=45,
        ),
    ]

    coordinated = orchestrator.coordinate_recommendations(
        candidates, complex_context, max_limit=5
    )

    # Exactly 1 recommendation should survive for top-1
    assert len(coordinated) == 1
    assert coordinated[0].priority == "urgent"
    assert coordinated[0].agent_element == "Critic"


def test_recommendation_limit_enforcement(complex_context):
    """Recommendations should not exceed max_limit."""
    orchestrator = AIOrchestrator()
    candidates = [
        AgentRecommendationCandidate(
            topic_id=f"top-{i}",
            agent_element="Performance Element",
            type="pacing_optimization",
            priority="medium",
            title=f"Task {i}",
            reason_type="pacing",
            reason_detail="detail",
            estimated_duration_minutes=20,
        )
        for i in range(10)
    ]

    coordinated = orchestrator.coordinate_recommendations(
        candidates, complex_context, max_limit=3
    )
    assert len(coordinated) == 3


def test_agent_failure_isolation(complex_context):
    """If an individual agent raises an exception, the orchestrator records it and continues safely."""
    orchestrator = AIOrchestrator()

    # Mock failing critic agent
    class BrokenCritic:
        name = "BrokenCritic"
        def run(self, *args, **kwargs):
            raise RuntimeError("Database connection timed out in Critic")

    orchestrator.critic = BrokenCritic()
    result = orchestrator.run(context=complex_context, mode=ExecutionMode.FULL)

    # Pipeline still finishes successfully
    assert "BrokenCritic" in result.metadata.failed_agents
    assert len(result.metadata.warnings) >= 1
    assert "PerformanceAgent" in result.metadata.executed_agents
    assert len(result.recommendations) >= 1
