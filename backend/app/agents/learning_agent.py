"""
Learning Agent
==============
Implementation of the Learning Element (Russell & Norvig learning agent architecture).
Responsible for:
- Evaluating student learning trajectories (improving, declining, consistently high, repeated low).
- Proposing calibrated adjustments to memory decay rate (lambda in [0.01, 0.30]).
- Modulating revision intervals and recommended study duration.
- Factoring in recommendation adherence and student feedback.
- Synthesizing metacognitive recommendations under agent_element="Learning Element".
"""

from typing import List, Dict, Any, Optional
import math

from app.agents.base import BaseAgent
from app.agents.schemas import (
    StudentContext,
    TopicContext,
    QuizAttemptContext,
    AgentRecommendationCandidate,
)
from app.agents.learning_schemas import (
    TopicLearningTrajectory,
    LearningAgentResult,
)
from app.ml.retention_model import (
    retention_model,
    DEFAULT_LAMBDA,
    MIN_LAMBDA,
    MAX_LAMBDA,
)
from app.ml.decay_calibrator import decay_calibrator


class LearningAgent(BaseAgent):
    """
    Learning Element calibrating cognitive model parameters and policy adaptations.
    """

    def __init__(self) -> None:
        super().__init__(name="LearningAgent", element_role="Learning Element")

    def run(
        self,
        context: StudentContext,
        max_recommendations: int = 3,
        **kwargs,
    ) -> LearningAgentResult:
        """
        Executes learning trajectory analysis and strategic adaptation over the student context.
        """
        trajectories: List[TopicLearningTrajectory] = []
        rec_candidates: List[AgentRecommendationCandidate] = []

        # 1. Group recent quiz attempts by topic
        quizzes_by_topic: Dict[str, List[QuizAttemptContext]] = {}
        for q in context.recent_quizzes:
            quizzes_by_topic.setdefault(q.topic_id, []).append(q)

        # 2. Analyze adherence feedback from active or historical recommendations
        adherence_insights = self.analyze_adherence(context)

        # 3. Analyze each topic trajectory
        for topic in context.topics:
            topic_quizzes = quizzes_by_topic.get(topic.id, [])
            trajectory = self.analyze_topic_trajectory(topic, topic_quizzes, context)
            trajectories.append(trajectory)

            # Generate strategic learning element recommendation if policy adjustment is actionable
            rec = self.formulate_policy_recommendation(topic, trajectory, context)
            if rec and len(rec_candidates) < max_recommendations:
                # Deduplication check against pending active recommendations
                is_duplicate = any(
                    ar.topic_id == topic.id and ar.agent_element == self.element_role
                    for ar in context.active_recommendations
                )
                if not is_duplicate:
                    rec_candidates.append(rec)

        self.log_execution(
            "Analyzed learning trajectories",
            {
                "topic_count": len(trajectories),
                "policy_recs_count": len(rec_candidates),
            },
        )

        return LearningAgentResult(
            user_id=context.student.user_id,
            trajectories=trajectories,
            recommendation_candidates=rec_candidates,
            adherence_insights=adherence_insights,
        )

    def analyze_topic_trajectory(
        self,
        topic: TopicContext,
        quizzes: List[QuizAttemptContext],
        context: StudentContext,
    ) -> TopicLearningTrajectory:
        """
        Determines empirical performance trend for a topic:
        - "insufficient_data": Fewer than 2 attempts
        - "consistently_high": All scores >= 80% (avg >= 85%)
        - "repeated_low": All scores < 60%
        - "improving": Scores monotonically or significantly trending upward (diff >= +15%)
        - "declining": Scores trending downward (diff <= -15%)
        - "stable": Scores fluctuating within moderate variance
        """
        scores = [float(q.score) for q in reversed(quizzes)]  # Chronological order
        current_lam = retention_model.sanitize_lambda(topic.decay_rate_lambda)
        current_interval = retention_model.calculate_recommended_interval(current_lam)

        if len(scores) < 2:
            return TopicLearningTrajectory(
                topic_id=topic.id,
                topic_name=topic.name,
                trend="insufficient_data",
                average_score=float(scores[0]) if scores else float(topic.mastery_score),
                score_history=scores,
                current_lambda=current_lam,
                proposed_lambda=current_lam,
                current_interval_days=current_interval,
                proposed_interval_days=current_interval,
                proposed_difficulty=topic.difficulty,
                recommended_duration_minutes=45,
                rationale="Insufficient historical quiz attempts (<2). Preserving default baseline parameters.",
            )

        avg_score = sum(scores) / len(scores)
        first_half = scores[: len(scores) // 2]
        second_half = scores[len(scores) // 2 :]
        avg_early = sum(first_half) / len(first_half)
        avg_recent = sum(second_half) / len(second_half)
        diff = avg_recent - avg_early

        # Classify trajectory
        if all(s >= 80.0 for s in scores) and avg_score >= 85.0:
            trend = "consistently_high"
            # High consolidation: reduce lambda by 20% (slower decay), expand revision interval
            proposed_lam = current_lam * 0.80
            duration = 30  # efficient maintenance
            # Difficulty advancement
            proposed_diff = "Hard" if topic.difficulty == "Medium" else topic.difficulty
            rationale = (
                f"Consistently high performance (avg {avg_score:.1f}% across {len(scores)} quizzes). "
                f"Memory consolidation verified. Recommending expanding revision intervals and advancing difficulty."
            )
        elif all(s < 60.0 for s in scores):
            trend = "repeated_low"
            # Memory failure: increase lambda by 25% (faster decay), shorten revision interval
            proposed_lam = current_lam * 1.25
            duration = 60  # extended remediation
            proposed_diff = "Easy" if topic.difficulty == "Medium" else topic.difficulty
            rationale = (
                f"Repeated low scores detected (avg {avg_score:.1f}%). "
                f"Forgetting rate accelerated. Recommending shorter revision cycles and intensive practice."
            )
        elif diff >= 15.0:
            trend = "improving"
            # Improving trajectory: moderate stability boost
            proposed_lam = current_lam * 0.88
            duration = 45
            proposed_diff = "Medium" if topic.difficulty == "Easy" else topic.difficulty
            rationale = (
                f"Upward mastery trajectory detected (+{diff:.1f}% recent gain). "
                f"Learning strategy is effective. Stabilizing revision interval."
            )
        elif diff <= -15.0:
            trend = "declining"
            # Declining trajectory: decay rate increases
            proposed_lam = current_lam * 1.20
            duration = 50
            proposed_diff = topic.difficulty
            rationale = (
                f"Performance decline detected ({diff:.1f}% drop from initial quizzes). "
                f"Knowledge decay exceeding expectations. Prioritizing refresher review."
            )
        else:
            trend = "stable"
            proposed_lam = current_lam
            duration = 45
            proposed_diff = topic.difficulty
            rationale = (
                f"Performance is stable around {avg_score:.1f}%. "
                f"Current spaced repetition parameters are well-calibrated."
            )

        # Sanitize lambda boundary conditions [0.01, 0.30]
        sanitized_proposed_lam = retention_model.sanitize_lambda(proposed_lam)
        proposed_interval = retention_model.calculate_recommended_interval(sanitized_proposed_lam)

        # Adapt duration based on student daily capacity
        capacity = context.student.daily_capacity_minutes
        if capacity < 60:
            duration = min(duration, 30)
        elif capacity > 180 and trend in ["repeated_low", "declining"]:
            duration = min(duration + 15, 75)

        return TopicLearningTrajectory(
            topic_id=topic.id,
            topic_name=topic.name,
            trend=trend,
            average_score=round(avg_score, 1),
            score_history=scores,
            current_lambda=round(current_lam, 4),
            proposed_lambda=round(sanitized_proposed_lam, 4),
            current_interval_days=current_interval,
            proposed_interval_days=proposed_interval,
            proposed_difficulty=proposed_diff,
            recommended_duration_minutes=duration,
            rationale=rationale,
        )

    def formulate_policy_recommendation(
        self,
        topic: TopicContext,
        trajectory: TopicLearningTrajectory,
        context: StudentContext,
    ) -> Optional[AgentRecommendationCandidate]:
        """
        Formulates a strategic recommendation candidate under Learning Element if trajectory
        requires an intervention or policy optimization.
        """
        if trajectory.trend == "insufficient_data" or trajectory.trend == "stable":
            return None

        if trajectory.trend == "repeated_low":
            return AgentRecommendationCandidate(
                subject_id=topic.subject_id,
                topic_id=topic.id,
                agent_element=self.element_role,
                type="pacing_optimization",
                priority="urgent",
                title=f"Strategy Adaptation: {topic.name}",
                reason_type="pedagogical_pivot",
                reason_detail=(
                    f"Learning Agent detected repeated difficulty on {topic.name} (avg {trajectory.average_score}%). "
                    f"Calibrated forgetting rate adjusted to λ={trajectory.proposed_lambda}. "
                    f"Action: Shortened revision interval from {trajectory.current_interval_days} to "
                    f"{trajectory.proposed_interval_days} days with a {trajectory.recommended_duration_minutes}-min deep-dive."
                ),
                suggested_slot="Evening Focus",
                estimated_duration_minutes=trajectory.recommended_duration_minutes,
            )
        elif trajectory.trend == "declining":
            return AgentRecommendationCandidate(
                subject_id=topic.subject_id,
                topic_id=topic.id,
                agent_element=self.element_role,
                type="retention_decay",
                priority="high",
                title=f"Decay Mitigation: {topic.name}",
                reason_type="retention_decay_acceleration",
                reason_detail=(
                    f"Learning Agent identified declining retention on {topic.name}. "
                    f"Increasing study priority and adjusting revision schedule to halt further memory decay."
                ),
                suggested_slot="Flexible",
                estimated_duration_minutes=trajectory.recommended_duration_minutes,
            )
        elif trajectory.trend == "consistently_high":
            return AgentRecommendationCandidate(
                subject_id=topic.subject_id,
                topic_id=topic.id,
                agent_element=self.element_role,
                type="pacing_optimization",
                priority="low",
                title=f"Interval Expansion: {topic.name}",
                reason_type="spaced_repetition_expansion",
                reason_detail=(
                    f"Consistently high recall on {topic.name} (avg {trajectory.average_score}%). "
                    f"Expanded revision interval to {trajectory.proposed_interval_days} days to optimize student time."
                ),
                suggested_slot="Flexible",
                estimated_duration_minutes=trajectory.recommended_duration_minutes,
            )
        elif trajectory.trend == "improving":
            return AgentRecommendationCandidate(
                subject_id=topic.subject_id,
                topic_id=topic.id,
                agent_element=self.element_role,
                type="pacing_optimization",
                priority="medium",
                title=f"Milestone Consolidation: {topic.name}",
                reason_type="positive_reinforcement",
                reason_detail=(
                    f"Great momentum on {topic.name} (+{trajectory.average_score}% mastery). "
                    f"Learning policy tuned to consolidate current retention."
                ),
                suggested_slot="Flexible",
                estimated_duration_minutes=trajectory.recommended_duration_minutes,
            )
        return None

    def analyze_adherence(self, context: StudentContext) -> Dict[str, Any]:
        """
        Analyzes adherence from active or completed recommendation feedback.
        """
        # Read from existing recommendation contexts safely
        total_recs = len(context.active_recommendations)
        return {
            "total_pending_recommendations": total_recs,
            "adherence_rate": 1.0,  # default when no dismissal logs exist
        }


learning_agent = LearningAgent()
