"""
Performance Agent
=================
Implementation of the Performance Element (Russell & Norvig learning agent architecture).
Responsible for:
- Prioritizing topics by memory decay risk, exam urgency, topic difficulty, and mastery gap.
- Formulating tactical study tasks and revision schedule candidates.
- Respecting daily study capacity constraints.
- Suppressing duplicate or conflicting recommendations.
"""

from typing import List, Dict, Any, Optional
import math

from app.agents.base import BaseAgent
from app.agents.schemas import (
    StudentContext,
    TopicContext,
    AgentRecommendationCandidate,
)
from app.ml.retention_model import retention_model

# Mathematical weights for multi-factor priority scoring
WEIGHT_FORGETTING_RISK: float = 0.40
WEIGHT_EXAM_URGENCY: float = 0.30
WEIGHT_MASTERY_GAP: float = 0.20
WEIGHT_DIFFICULTY: float = 0.10

DIFFICULTY_FACTORS = {
    "Easy": 0.5,
    "Medium": 1.0,
    "Hard": 1.5,
}


class PerformanceAgent(BaseAgent):
    """
    Performance Element generating concrete study tasks based on tactical learning goals.
    """

    def __init__(self) -> None:
        super().__init__(name="PerformanceAgent", element_role="Performance Element")

    def run(
        self,
        context: StudentContext,
        max_recommendations: int = 5,
        **kwargs,
    ) -> List[AgentRecommendationCandidate]:
        """
        Executes prioritization and task synthesis over the student's context.

        Args:
            context: Synthesized StudentContext.
            max_recommendations: Maximum recommendation candidates to produce.

        Returns:
            List of prioritized, non-duplicate AgentRecommendationCandidate objects.
        """
        if not context.topics:
            self.log_execution("No topics available in context to prioritize.")
            return []

        # 1. Calculate dynamic current retention and priority score for each topic
        scored_topics: List[Dict[str, Any]] = []
        for topic in context.topics:
            # Predict current retention R(t) using Milestone 1 retention engine
            current_retention = retention_model.calculate_retention(
                elapsed_days=topic.elapsed_days,
                decay_lambda=topic.decay_rate_lambda,
            )

            score, components = self.compute_priority_score(topic, current_retention)
            scored_topics.append({
                "topic": topic,
                "current_retention": current_retention,
                "priority_score": score,
                "components": components,
            })

        # 2. Sort topics by composite priority score (highest need first)
        scored_topics.sort(key=lambda x: x["priority_score"], reverse=True)

        # 3. Identify topics that already have an active pending recommendation
        active_rec_topic_ids = {
            r.topic_id for r in context.active_recommendations if r.topic_id
        }

        # 4. Generate recommendations respecting daily study capacity
        recommendations: List[AgentRecommendationCandidate] = []
        allocated_minutes = 0
        raw_capacity = getattr(context.student, "daily_capacity_minutes", None)
        # Safe capacity handling: handle zero, negative, missing, or float
        if raw_capacity is None or not isinstance(raw_capacity, (int, float)) or raw_capacity <= 0:
            max_capacity = 0
        else:
            max_capacity = int(raw_capacity)

        if max_capacity <= 0:
            self.log_execution("Daily study capacity is zero or invalid. Generating no recommendations.")
            return []

        for item in scored_topics:
            if len(recommendations) >= max_recommendations:
                break

            topic: TopicContext = item["topic"]
            retention: float = item["current_retention"]
            priority_score: float = item["priority_score"]
            components: Dict[str, float] = item["components"]

            # Suppress duplicate recommendation if already pending for this topic
            if topic.id in active_rec_topic_ids:
                continue

            # Remaining available time for student today
            remaining_capacity = max_capacity - allocated_minutes
            if remaining_capacity <= 0:
                break

            # Determine baseline task duration based on difficulty and retention deficit
            desired_duration = self.determine_study_duration(topic.difficulty, retention)

            # Capacity constraint & splitting check:
            # If the desired duration exceeds remaining capacity:
            # Split into a targeted shorter study drill matching remaining time (if meaningful >= 15m),
            # or cap at remaining capacity. If remaining capacity is too small (< 15m) and we already have tasks, skip.
            if desired_duration > remaining_capacity:
                if remaining_capacity < 15 and len(recommendations) > 0:
                    continue
                # Split / compress task into a targeted drill
                duration = remaining_capacity
                is_split = True
            else:
                duration = desired_duration
                is_split = False

            # Map priority score to discrete label
            priority_label = self.map_priority_level(priority_score, components)

            # Determine recommendation type and title
            rec_type, title, reason_detail = self.formulate_rationale(
                topic=topic,
                retention=retention,
                components=components,
                recommended_duration=duration,
            )

            # If task was split/shortened to fit daily capacity, adjust title & reason
            if is_split:
                title = f"Focused Drill: {topic.name} ({duration}m)"
                reason_detail += (
                    f" (Split to fit remaining daily study capacity of {remaining_capacity} minutes "
                    f"from standard {desired_duration}-minute session)."
                )

            candidate = AgentRecommendationCandidate(
                subject_id=topic.subject_id,
                topic_id=topic.id,
                agent_element=self.element_role,
                type=rec_type,
                priority=priority_label,
                title=title,
                reason_type="decay_risk" if components["forgetting_risk"] > 0.5 else "exam_urgency",
                reason_detail=reason_detail,
                suggested_slot="Evening (07:00 PM - 08:30 PM)" if duration > 45 else "Flexible",
                estimated_duration_minutes=duration,
            )

            recommendations.append(candidate)
            active_rec_topic_ids.add(topic.id)  # prevent duplicate in same batch
            allocated_minutes += duration

        self.log_execution(
            "Synthesized recommendations",
            {"count": len(recommendations), "allocated_minutes": allocated_minutes},
        )
        return recommendations

    def compute_priority_score(
        self,
        topic: TopicContext,
        current_retention: float,
    ) -> (float, Dict[str, float]):
        """
        Mathematical composite priority formula:
        Priority = w_forget * (1 - R/100)
                 + w_exam * Urgency(days_to_exam)
                 + w_mastery * (1 - Mastery/100)
                 + w_diff * DiffFactor
        """
        # 1. Forgetting Risk component: normalized [0.0, 1.0]
        forgetting_risk = max(0.0, min(1.0, (100.0 - current_retention) / 100.0))

        # 2. Exam Urgency component: exponential urgency curve as exam approaches
        if topic.days_until_exam is not None:
            # Days <= 0 is exam day (1.0 urgency), days = 7 is ~0.7, days > 30 drops to near 0.1
            d = max(0.0, topic.days_until_exam)
            exam_urgency = math.exp(-0.06 * d)  # half-life ~11.5 days
        else:
            exam_urgency = 0.15  # baseline mild priority

        # 3. Mastery Gap component: normalized [0.0, 1.0]
        mastery_gap = max(0.0, min(1.0, (100.0 - topic.mastery_score) / 100.0))

        # 4. Difficulty component: normalized [0.0, 1.0]
        diff_raw = DIFFICULTY_FACTORS.get(topic.difficulty, 1.0)
        diff_norm = diff_raw / 1.5  # maps [0.5, 1.5] -> [0.33, 1.0]

        composite = (
            WEIGHT_FORGETTING_RISK * forgetting_risk
            + WEIGHT_EXAM_URGENCY * exam_urgency
            + WEIGHT_MASTERY_GAP * mastery_gap
            + WEIGHT_DIFFICULTY * diff_norm
        )

        components = {
            "forgetting_risk": forgetting_risk,
            "exam_urgency": exam_urgency,
            "mastery_gap": mastery_gap,
            "difficulty_norm": diff_norm,
        }
        return composite, components

    def determine_study_duration(self, difficulty: str, retention: float) -> int:
        """Determines recommended duration in minutes based on difficulty and retention."""
        base = 45
        if difficulty == "Hard":
            base = 60
        elif difficulty == "Easy":
            base = 30

        if retention < 50.0:
            base += 15  # add deep review buffer
        return base

    def map_priority_level(self, composite_score: float, components: Dict[str, float]) -> str:
        """Categorizes priority into low, medium, high, urgent."""
        if composite_score >= 0.70 or components["exam_urgency"] >= 0.85:
            return "urgent"
        elif composite_score >= 0.50:
            return "high"
        elif composite_score >= 0.35:
            return "medium"
        return "low"

    def formulate_rationale(
        self,
        topic: TopicContext,
        retention: float,
        components: Dict[str, float],
        recommended_duration: int,
    ) -> (str, str, str):
        """Generates explainable, deterministic rationale string and recommendation type."""
        if components["exam_urgency"] >= 0.70 and topic.days_until_exam is not None:
            rec_type = "exam_priority"
            title = f"High Exam Priority: {topic.name}"
            days_str = f"{round(topic.days_until_exam, 1)} days"
            detail = (
                f"{topic.subject_name} examination is in {days_str}. Topic '{topic.name}' has "
                f"current retention estimated at {round(retention, 1)}% and mastery at {round(topic.mastery_score, 1)}%. "
                f"Schedule a {recommended_duration}-minute revision session to secure target mastery."
            )
        elif components["forgetting_risk"] >= 0.40:
            rec_type = "retention_decay"
            title = f"Review Alert: {topic.name}"
            detail = (
                f"Memory decay simulation shows retention for '{topic.name}' has decayed to {round(retention, 1)}% "
                f"(last revised {round(topic.elapsed_days, 1)} days ago). Reviewing now takes advantage of "
                f"the spaced repetition window before memory consolidation drops further."
            )
        else:
            rec_type = "pacing_optimization"
            title = f"Pacing Practice: {topic.name}"
            detail = (
                f"Keep regular study momentum on '{topic.name}' ({topic.difficulty} difficulty) "
                f"to steadily elevate current mastery of {round(topic.mastery_score, 1)}% towards target."
            )

        return rec_type, title, detail


performance_agent = PerformanceAgent()
