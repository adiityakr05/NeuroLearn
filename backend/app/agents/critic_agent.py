"""
Critic Agent
============
Implementation of the Critic Element (Russell & Norvig learning agent architecture).
Responsible for:
- Evaluating student quiz performance.
- Diagnosing knowledge gaps and misconceptions.
- Categorizing scores into High Concern (<60%), Moderate Concern (60-80%), or Reinforcement (>80%).
- Formulating qualitative, explainable critique notes and structured feedback.
- Generating diagnostic recommendation candidates for urgent review when severe gaps are identified.
"""

from typing import List, Dict, Any, Optional

from app.agents.base import BaseAgent
from app.agents.schemas import (
    StudentContext,
    QuizAttemptContext,
    CriticEvaluationResult,
    AgentRecommendationCandidate,
)


class CriticAgent(BaseAgent):
    """
    Critic Element assessing student recall accuracy and providing diagnostic feedback.
    """

    def __init__(self) -> None:
        super().__init__(name="CriticAgent", element_role="Critic")

    def run(
        self,
        context: StudentContext,
        unevaluated_only: bool = True,
        **kwargs,
    ) -> List[CriticEvaluationResult]:
        """
        Evaluates quiz attempts present in the student context.

        Args:
            context: StudentContext snapshot.
            unevaluated_only: If True, filters only attempts where critic_evaluated is False.

        Returns:
            List of CriticEvaluationResult objects.
        """
        results: List[CriticEvaluationResult] = []
        quizzes = context.recent_quizzes

        if unevaluated_only:
            quizzes = [q for q in quizzes if not q.critic_evaluated]

        for quiz in quizzes:
            eval_res = self.evaluate_quiz_attempt(quiz, context)
            results.append(eval_res)

        self.log_execution(
            "Completed quiz evaluations",
            {"evaluated_count": len(results)},
        )
        return results

    def evaluate_quiz_attempt(
        self,
        quiz: QuizAttemptContext,
        context: Optional[StudentContext] = None,
    ) -> CriticEvaluationResult:
        """
        Evaluates an individual quiz attempt according to strict performance tiers:
        - Below 60%: High concern
        - 60% to 80%: Moderate concern
        - Above 80%: Reinforcement
        """
        score = float(quiz.score)
        topic_name = quiz.topic_name or "Topic"

        # Determine topic context if available
        topic_ctx = None
        if context and context.topics:
            for t in context.topics:
                if t.id == quiz.topic_id:
                    topic_ctx = t
                    topic_name = t.name
                    break

        # Tier classification
        if score < 60.0:
            category = "High Concern"
            concern_level = "high"
            needs_practice = True
            action = f"Immediate review required. Focus on foundational concepts in {topic_name}."
            notes = (
                f"Diagnostic Evaluation: High Concern ({score:.1f}% score, {quiz.correct_answers}/{quiz.total_questions} correct). "
                f"Student demonstrated significant comprehension gaps or recall failure on {topic_name}. "
                f"Recommended Action: Halt progression to advanced topics until core principles are revisited."
            )
            rec_candidate = AgentRecommendationCandidate(
                subject_id=topic_ctx.subject_id if topic_ctx else None,
                topic_id=quiz.topic_id,
                agent_element=self.element_role,
                type="retention_decay",
                priority="urgent",
                title=f"Remedial Focus: {topic_name}",
                reason_type="diagnostic_gap",
                reason_detail=notes,
                suggested_slot="Immediate",
                estimated_duration_minutes=45,
            )
        elif 60.0 <= score <= 80.0:
            category = "Moderate Concern"
            concern_level = "moderate"
            needs_practice = True
            action = f"Targeted practice recommended to solidify borderline mastery in {topic_name}."
            notes = (
                f"Diagnostic Evaluation: Moderate Concern ({score:.1f}% score, {quiz.correct_answers}/{quiz.total_questions} correct). "
                f"Core concepts are partially understood, but inconsistent application was detected in {topic_name}. "
                f"Recommended Action: Solve 5-10 targeted problem probes to reinforce weak subtopics."
            )
            rec_candidate = AgentRecommendationCandidate(
                subject_id=topic_ctx.subject_id if topic_ctx else None,
                topic_id=quiz.topic_id,
                agent_element=self.element_role,
                type="pacing_optimization",
                priority="medium",
                title=f"Reinforce Understanding: {topic_name}",
                reason_type="partial_mastery",
                reason_detail=notes,
                suggested_slot="Flexible",
                estimated_duration_minutes=30,
            )
        else:
            category = "Reinforcement"
            concern_level = "low"
            needs_practice = False
            action = f"Mastery achieved on {topic_name}. Maintain spaced revision schedule."
            notes = (
                f"Diagnostic Evaluation: Reinforcement ({score:.1f}% score, {quiz.correct_answers}/{quiz.total_questions} correct). "
                f"Excellent recall and conceptual fluency demonstrated on {topic_name}. "
                f"Recommended Action: Proceed to next syllabus module; schedule maintenance review in next cycle."
            )
            rec_candidate = None

        return CriticEvaluationResult(
            attempt_id=quiz.id,
            topic_id=quiz.topic_id,
            topic_name=topic_name,
            score=score,
            accuracy=float(quiz.accuracy),
            performance_category=category,
            concern_level=concern_level,
            critic_notes=notes,
            recommended_action=action,
            needs_practice=needs_practice,
            recommendation_candidate=rec_candidate,
        )


critic_agent = CriticAgent()
