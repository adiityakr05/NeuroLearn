"""
AI Orchestrator Schemas
=======================
Pydantic v2 schemas defining input modes, structured results,
metadata, and execution modes for the central AI Orchestrator.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from app.agents.schemas import (
    AgentRecommendationCandidate,
    CriticEvaluationResult,
    TopicContext,
)
from app.agents.learning_schemas import TopicLearningTrajectory
from app.agents.problem_schemas import DiagnosticProbeSet


class ExecutionMode(str, Enum):
    FULL = "full"
    QUIZ_EVALUATION = "quiz_evaluation"
    DIAGNOSTIC = "diagnostic"
    RECOMMENDATION = "recommendation"


class OrchestratorExecutionMetadata(BaseModel):
    user_id: str
    execution_mode: str
    executed_agents: List[str] = []
    failed_agents: List[str] = []
    warnings: List[str] = []
    duration_ms: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class OrchestratorResult(BaseModel):
    """
    Unified structured response produced by the central AI Orchestrator.
    """
    user_id: str
    recommendations: List[AgentRecommendationCandidate] = []
    critic_evaluations: List[CriticEvaluationResult] = []
    learning_trajectories: List[TopicLearningTrajectory] = []
    diagnostic_probes: List[DiagnosticProbeSet] = []
    topic_retention_states: Dict[str, Dict[str, Any]] = {}
    metadata: OrchestratorExecutionMetadata

    model_config = ConfigDict(from_attributes=True)
