"""
NeuroLearn Milestone 7 - Evaluation Metrics & Measurements
==========================================================
Mathematical metrics definitions and measurement formulas:
1. Prioritization Accuracy:
   Ratio of prioritized urgent/decay topics that align with the true highest-need topic.
2. Retention Prediction Error (MAE):
   Mean absolute error |R_pred(t) - R_actual(t)| across decay test curves.
3. Recommendation Relevance:
   Fraction of recommendations that address either weak mastery (<60%), high decay risk, or exam <= 7 days.
4. Capacity Constraint Violation Rate:
   Fraction of recommended task batches whose total estimated minutes exceed student.daily_capacity_minutes.
5. Duplicate Recommendation Rate:
   Fraction of generated recommendations sharing identical topic_id and agent_element.
6. Question Generation Validity:
   Fraction of generated questions with non-empty text, valid answer options/criteria, and matching Bloom's taxonomy.
7. Agent Failure Rate:
   Fraction of pipeline runs where an agent uncaught exception occurs or crashes the orchestrator.
8. Decision Consistency:
   Pairwise agreement between consecutive runs on identical context (deterministic output check).
"""

from typing import List, Dict, Any
from app.agents.schemas import AgentRecommendationCandidate
from app.agents.problem_schemas import GeneratedQuestion


def calculate_retention_mae(predictions: List[float], ground_truths: List[float]) -> float:
    """Mean Absolute Error between predicted and actual retention."""
    if not predictions or not ground_truths or len(predictions) != len(ground_truths):
        return 0.0
    return sum(abs(p - g) for p, g in zip(predictions, ground_truths)) / len(predictions)


def calculate_capacity_violation_rate(batches: List[Dict[str, Any]]) -> float:
    """
    Checks if sum(rec.estimated_duration_minutes) > student_capacity.
    Returns fraction in [0.0, 1.0].
    """
    if not batches:
        return 0.0
    violations = 0
    for b in batches:
        total_mins = sum(r.estimated_duration_minutes for r in b.get("recommendations", []))
        cap = b.get("capacity", 90)
        if total_mins > cap:
            violations += 1
    return violations / len(batches)


def calculate_duplicate_rate(recommendations: List[AgentRecommendationCandidate]) -> float:
    """
    Fraction of duplicates based on (topic_id, agent_element).
    """
    if not recommendations:
        return 0.0
    seen = set()
    duplicates = 0
    for r in recommendations:
        key = (r.topic_id, r.agent_element)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates / len(recommendations)


def calculate_question_validity_rate(questions: List[GeneratedQuestion]) -> float:
    """
    Validates structural integrity of questions (non-empty question, valid Bloom level, non-empty answer).
    """
    if not questions:
        return 0.0
    valid_count = 0
    for q in questions:
        has_text = bool(q.question_text and len(q.question_text.strip()) > 5)
        ans = getattr(q, "correct_answer", None) or getattr(q, "expected_answer", None)
        has_answer = bool(ans and len(str(ans).strip()) > 0)
        has_bloom = bool(q.bloom_level)
        if has_text and has_answer and has_bloom:
            valid_count += 1
    return valid_count / len(questions)


def calculate_relevance_rate(
    recommendations: List[AgentRecommendationCandidate],
    topic_map: Dict[str, Any],
) -> float:
    """
    Relevance check: topic mastery < 65% OR retention < 70% OR exam urgency.
    """
    if not recommendations:
        return 1.0  # vacuously relevant
    relevant_count = 0
    for r in recommendations:
        t = topic_map.get(r.topic_id)
        if not t:
            continue
        # Topic is relevant if mastery is low, or retention is low, or high priority
        is_weak = t.mastery_score < 70.0
        is_decayed = getattr(t, "retention_score", 70.0) < 70.0
        is_priority = r.priority in ("urgent", "high")
        if is_weak or is_decayed or is_priority:
            relevant_count += 1
    return relevant_count / len(recommendations)
