"""
NeuroLearn Multi-Agent System Package
=====================================
Exports agent interfaces, schemas, and element instances.
"""

from app.agents.schemas import (
    StudentContext,
    StudentProfileContext,
    SubjectContext,
    TopicContext,
    QuizAttemptContext,
    StudySessionContext,
    ExistingRecommendationContext,
    AgentRecommendationCandidate,
    CriticEvaluationResult,
)
from app.agents.learning_schemas import (
    TopicLearningTrajectory,
    LearningAgentResult,
)
from app.agents.problem_schemas import (
    GeneratedQuestion,
    DiagnosticProbeSet,
    ProblemGeneratorResult,
)
from app.agents.orchestrator_schemas import (
    ExecutionMode,
    OrchestratorExecutionMetadata,
    OrchestratorResult,
)
from app.agents.base import BaseAgent
from app.agents.context import StudentContextBuilder, student_context_builder
from app.agents.performance_agent import PerformanceAgent, performance_agent
from app.agents.critic_agent import CriticAgent, critic_agent
from app.agents.learning_agent import LearningAgent, learning_agent
from app.agents.problem_generator import ProblemGenerator, problem_generator
from app.agents.orchestrator import AIOrchestrator, ai_orchestrator

__all__ = [
    "BaseAgent",
    "StudentContextBuilder",
    "student_context_builder",
    "PerformanceAgent",
    "performance_agent",
    "CriticAgent",
    "critic_agent",
    "LearningAgent",
    "learning_agent",
    "ProblemGenerator",
    "problem_generator",
    "AIOrchestrator",
    "ai_orchestrator",
    "StudentContext",
    "StudentProfileContext",
    "SubjectContext",
    "TopicContext",
    "QuizAttemptContext",
    "StudySessionContext",
    "ExistingRecommendationContext",
    "AgentRecommendationCandidate",
    "CriticEvaluationResult",
    "TopicLearningTrajectory",
    "LearningAgentResult",
    "GeneratedQuestion",
    "DiagnosticProbeSet",
    "ProblemGeneratorResult",
    "ExecutionMode",
    "OrchestratorExecutionMetadata",
    "OrchestratorResult",
]
