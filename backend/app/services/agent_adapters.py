"""
AI Agent Module Adapter Interface
=================================
Connects existing backend services and API controllers to the AI Orchestrator
and ML Retention Engine.
Maintains 100% public signature compatibility with existing adapter contracts.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.agents.orchestrator import ai_orchestrator
from app.agents.orchestrator_schemas import ExecutionMode
from app.agents.schemas import QuizAttemptContext
from app.ml.retention_model import retention_model
from app.ml.decay_calibrator import decay_calibrator


class AIAgentAdapter:
    """
    Adapter implementing the 4-Element Learning Agent interface via the central AI Orchestrator.
    """

    def generate_recommendations(
        self,
        user_id: str,
        student_history: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Invokes AI Orchestrator in RECOMMENDATION mode to produce prioritized study recommendations.
        """
        # If student_history contains a DB session, utilize it directly
        db = student_history.get("db")
        context = student_history.get("context")

        if db or context:
            orch_res = ai_orchestrator.run(
                db=db,
                user_id=user_id,
                context=context,
                mode=ExecutionMode.RECOMMENDATION,
            )
            return [rec.model_dump() for rec in orch_res.recommendations]

        # Deterministic fallback when only raw dictionary is passed
        return [
            {
                "subject_id": student_history.get("subject_id"),
                "topic_id": student_history.get("topic_id"),
                "agent_element": "Performance Element",
                "type": "pacing_optimization",
                "priority": "medium",
                "title": f"Study Task: {student_history.get('topic_name', 'Topic Review')}",
                "reason_type": "spaced_repetition",
                "reason_detail": "Scheduled study session to preserve memory consolidation.",
                "suggested_slot": "Flexible",
                "estimated_duration_minutes": 45,
            }
        ]

    def evaluate_quiz_critique(
        self,
        attempt_id: str,
        score: float,
        accuracy: float,
        topic_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Invokes Critic Agent to diagnose quiz results and formulate actionable notes.
        """
        quiz_ctx = QuizAttemptContext(
            id=attempt_id,
            topic_id=topic_context.get("topic_id", topic_context.get("id", "topic-unknown")),
            topic_name=topic_context.get("name", topic_context.get("topic_name", "Topic")),
            score=float(score),
            accuracy=float(accuracy),
            total_questions=topic_context.get("total_questions", 10),
            correct_answers=topic_context.get("correct_answers", int(round(score / 10.0))),
            attempted_at=datetime.now(timezone.utc),
            critic_evaluated=False,
        )

        critic_res = ai_orchestrator.critic.evaluate_quiz_attempt(quiz_ctx)
        return {
            "critic_notes": critic_res.critic_notes,
            "recommended_action": critic_res.recommended_action,
            "performance_category": critic_res.performance_category,
            "needs_practice": critic_res.needs_practice,
        }


class MLRetentionAdapter:
    """
    Adapter implementing ML Memory Retention & Decay Calibration interface.
    """

    def predict_retention(
        self,
        topic_id: str,
        elapsed_days: float,
        decay_lambda: float,
        repetition_count: int = 1,
    ) -> float:
        """
        Computes Ebbinghaus retention prediction: R(t) = 100 * e^(-lambda * t)
        """
        return retention_model.calculate_retention(
            elapsed_days=elapsed_days,
            decay_lambda=decay_lambda,
        )

    def calibrate_decay_rate(
        self,
        revision_history: List[Dict[str, Any]],
        quiz_scores: List[float],
    ) -> float:
        """
        Calibrates personalized decay rate parameter (decay_rate_lambda) in [0.01, 0.30].
        """
        quizzes = [{"elapsed_days": 3, "score": s} for s in quiz_scores] if quiz_scores else []
        return decay_calibrator.calibrate_from_history(
            revision_history=revision_history,
            quiz_attempts=quizzes,
        )


# Global adapter singletons
ai_agent_adapter = AIAgentAdapter()
ml_retention_adapter = MLRetentionAdapter()
