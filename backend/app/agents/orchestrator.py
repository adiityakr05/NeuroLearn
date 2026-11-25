"""
AI Orchestrator
===============
Central coordinating engine for NeuroLearn's 4-Element Learning Agent Architecture:
1. Performance Agent (study scheduling & priority planning)
2. Critic Agent (quiz diagnosis & knowledge gap evaluation)
3. Learning Agent (decay calibration & policy adjustment)
4. Problem Generator (Bloom's diagnostic probes)
5. ML Retention Engine (Ebbinghaus decay & stability)

Features:
- Multi-mode execution: full, quiz_evaluation, diagnostic, recommendation.
- Recommendation merging, conflict resolution, priority normalization, and deduplication.
- Per-agent failure isolation with deterministic fallbacks.
- Tenant isolation and safety guarantees (LearningAgent does not silently overwrite DB).
"""

import time
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.schemas import (
    StudentContext,
    TopicContext,
    AgentRecommendationCandidate,
    CriticEvaluationResult,
)
from app.agents.context import StudentContextBuilder, student_context_builder
from app.agents.performance_agent import PerformanceAgent, performance_agent
from app.agents.critic_agent import CriticAgent, critic_agent
from app.agents.learning_agent import LearningAgent, learning_agent
from app.agents.problem_generator import ProblemGenerator, problem_generator
from app.agents.orchestrator_schemas import (
    ExecutionMode,
    OrchestratorExecutionMetadata,
    OrchestratorResult,
)
from app.ml.retention_model import retention_model

logger = logging.getLogger("neurolearn.orchestrator")

PRIORITY_RANKS = {
    "urgent": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


class AIOrchestrator:
    """
    Central AI Orchestrator coordinating all learning agents and ML prediction models.
    """

    def __init__(
        self,
        performance: Optional[PerformanceAgent] = None,
        critic: Optional[CriticAgent] = None,
        learning: Optional[LearningAgent] = None,
        problem_gen: Optional[ProblemGenerator] = None,
        context_builder: Optional[StudentContextBuilder] = None,
    ) -> None:
        self.performance = performance or performance_agent
        self.critic = critic or critic_agent
        self.learning = learning or learning_agent
        self.problem_gen = problem_gen or problem_generator
        self.context_builder = context_builder or student_context_builder
        self.logger = logging.getLogger("neurolearn.orchestrator")

    def run(
        self,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
        context: Optional[StudentContext] = None,
        mode: ExecutionMode = ExecutionMode.FULL,
        max_recommendations: int = 5,
        target_topic_ids: Optional[List[str]] = None,
        unevaluated_quizzes_only: bool = True,
        **kwargs,
    ) -> OrchestratorResult:
        """
        Executes orchestrated pipeline with per-agent safety and isolated fallback handling.
        """
        start_time = time.perf_counter()
        executed_agents: List[str] = []
        failed_agents: List[str] = []
        warnings: List[str] = []

        # Ensure mode is an ExecutionMode enum instance
        if isinstance(mode, str):
            try:
                mode = ExecutionMode(mode.lower())
            except ValueError:
                mode = ExecutionMode.FULL

        # 1. Load or validate StudentContext
        if context is None:
            if db is None or user_id is None:
                raise ValueError("Either 'context' or both 'db' and 'user_id' must be provided.")
            context = self.context_builder.build_from_db(db, user_id=user_id)
            if context is None:
                warnings.append(f"User {user_id} not found.")
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return OrchestratorResult(
                    user_id=user_id,
                    metadata=OrchestratorExecutionMetadata(
                        user_id=user_id,
                        execution_mode=mode.value,
                        executed_agents=[],
                        failed_agents=[],
                        warnings=warnings,
                        duration_ms=round(duration_ms, 2),
                    ),
                )

        effective_user_id = context.student.user_id

        # 2. Compute topic retention states via ML Retention Engine
        topic_states: Dict[str, Dict[str, Any]] = {}
        for topic in context.topics:
            state = retention_model.predict_topic_state(
                elapsed_days=topic.elapsed_days,
                decay_lambda=topic.decay_rate_lambda,
            )
            topic_states[topic.id] = state

        critic_evaluations: List[CriticEvaluationResult] = []
        learning_trajectories = []
        diagnostic_probes = []
        raw_candidates: List[AgentRecommendationCandidate] = []

        # 3. Execution: Critic Agent
        if mode in [ExecutionMode.FULL, ExecutionMode.QUIZ_EVALUATION]:
            try:
                critic_evaluations = self.critic.run(
                    context, unevaluated_only=unevaluated_quizzes_only
                )
                executed_agents.append(self.critic.name)
                # Collect any remedial candidates generated by Critic
                for eval_res in critic_evaluations:
                    if eval_res.recommendation_candidate:
                        raw_candidates.append(eval_res.recommendation_candidate)
            except Exception as e:
                self.logger.error("CriticAgent execution failed: %s", str(e), exc_info=True)
                failed_agents.append(self.critic.name)
                warnings.append(f"CriticAgent failed: {str(e)}")

        # 4. Execution: Learning Agent
        if mode in [ExecutionMode.FULL, ExecutionMode.RECOMMENDATION]:
            try:
                learn_res = self.learning.run(context, max_recommendations=max_recommendations)
                executed_agents.append(self.learning.name)
                learning_trajectories = learn_res.trajectories
                raw_candidates.extend(learn_res.recommendation_candidates)
            except Exception as e:
                self.logger.error("LearningAgent execution failed: %s", str(e), exc_info=True)
                failed_agents.append(self.learning.name)
                warnings.append(f"LearningAgent failed: {str(e)}")

        # 5. Execution: Problem Generator
        if mode in [ExecutionMode.FULL, ExecutionMode.DIAGNOSTIC]:
            try:
                prob_res = self.problem_gen.run(context, target_topic_ids=target_topic_ids)
                executed_agents.append(self.problem_gen.name)
                diagnostic_probes = prob_res.probes
                raw_candidates.extend(prob_res.recommendation_candidates)
            except Exception as e:
                self.logger.error("ProblemGenerator execution failed: %s", str(e), exc_info=True)
                failed_agents.append(self.problem_gen.name)
                warnings.append(f"ProblemGenerator failed: {str(e)}")

        # 6. Execution: Performance Agent
        if mode in [ExecutionMode.FULL, ExecutionMode.RECOMMENDATION]:
            try:
                perf_recs = self.performance.run(context, max_recommendations=max_recommendations)
                executed_agents.append(self.performance.name)
                raw_candidates.extend(perf_recs)
            except Exception as e:
                self.logger.error("PerformanceAgent execution failed: %s", str(e), exc_info=True)
                failed_agents.append(self.performance.name)
                warnings.append(f"PerformanceAgent failed: {str(e)}")

        # 7. Merge, Deduplicate, Resolve Conflicts, and Cap Recommendations
        final_recommendations = self.coordinate_recommendations(
            candidates=raw_candidates,
            context=context,
            max_limit=max_recommendations,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = OrchestratorExecutionMetadata(
            user_id=effective_user_id,
            execution_mode=mode.value,
            executed_agents=executed_agents,
            failed_agents=failed_agents,
            warnings=warnings,
            duration_ms=round(duration_ms, 2),
        )

        return OrchestratorResult(
            user_id=effective_user_id,
            recommendations=final_recommendations,
            critic_evaluations=critic_evaluations,
            learning_trajectories=learning_trajectories,
            diagnostic_probes=diagnostic_probes,
            topic_retention_states=topic_states,
            metadata=metadata,
        )

    def coordinate_recommendations(
        self,
        candidates: List[AgentRecommendationCandidate],
        context: StudentContext,
        max_limit: int = 5,
    ) -> List[AgentRecommendationCandidate]:
        """
        Coordinates candidates across agents:
        - Deduplication key: (topic_id, type)
        - Conflict resolution: If multiple agents target the same topic, higher priority wins.
          If priority tied, Critic/Performance take precedence over exploratory probes.
        - Suppresses topics with active pending recommendations in DB.
        - Normalizes priority ordering: urgent > high > medium > low.
        - Respects student daily capacity constraints.
        """
        if not candidates:
            return []

        active_db_keys = {
            (r.topic_id, r.type)
            for r in context.active_recommendations
            if r.topic_id
        }

        # Deduplicate & resolve conflicts: Best candidate per (topic_id)
        best_by_topic: Dict[str, AgentRecommendationCandidate] = {}

        # Element tie-breaking weight
        element_weight = {
            "Critic": 4,
            "Performance Element": 3,
            "Learning Element": 2,
            "Problem Generator": 1,
        }

        for cand in candidates:
            if not cand.topic_id:
                continue

            # Skip if exact (topic_id, type) is already pending in DB
            if (cand.topic_id, cand.type) in active_db_keys:
                continue

            if cand.topic_id not in best_by_topic:
                best_by_topic[cand.topic_id] = cand
            else:
                existing = best_by_topic[cand.topic_id]
                existing_prio = PRIORITY_RANKS.get(existing.priority, 1)
                cand_prio = PRIORITY_RANKS.get(cand.priority, 1)

                # Higher priority wins
                if cand_prio > existing_prio:
                    best_by_topic[cand.topic_id] = cand
                elif cand_prio == existing_prio:
                    # Tie-break by element weight
                    cand_ew = element_weight.get(cand.agent_element, 0)
                    exist_ew = element_weight.get(existing.agent_element, 0)
                    if cand_ew > exist_ew:
                        best_by_topic[cand.topic_id] = cand

        # Sort remaining candidates by priority descending
        resolved = list(best_by_topic.values())
        resolved.sort(
            key=lambda c: (
                PRIORITY_RANKS.get(c.priority, 1),
                element_weight.get(c.agent_element, 0),
            ),
            reverse=True,
        )

        # Enforce capacity & max limit
        final_list: List[AgentRecommendationCandidate] = []
        allocated_minutes = 0
        capacity = context.student.daily_capacity_minutes

        for cand in resolved:
            if len(final_list) >= max_limit:
                break
            if allocated_minutes + cand.estimated_duration_minutes > capacity and len(final_list) > 0:
                continue
            final_list.append(cand)
            allocated_minutes += cand.estimated_duration_minutes

        return final_list


ai_orchestrator = AIOrchestrator()
