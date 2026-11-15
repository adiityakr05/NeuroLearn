"""
Deterministic Spaced Repetition Study Scheduler.

Combines memory retention urgency, cumulative mastery gaps, and exam proximity
into prioritized daily study recommendations with 25-minute session block allocation.
Retention and mastery remain strictly decoupled input signals.
"""

from typing import Any, Final

from ml.config import (
    ACTION_IMMEDIATE_REVISION,
    ACTION_ON_TRACK,
    ACTION_PRACTICE_QUIZ,
    DEFAULT_EXAM_HORIZON_DAYS,
    DEFAULT_SESSION_BLOCK_MINUTES,
    MASTERY_PRACTICE_THRESHOLD,
    MAX_DAILY_BUDGET_MINUTES,
    MAX_MASTERY,
    MAX_SESSION_BLOCK_MINUTES,
    MIN_DAILY_BUDGET_MINUTES,
    MIN_MASTERY,
    MIN_SESSION_BLOCK_MINUTES,
    RETENTION_REVISION_THRESHOLD,
    WEIGHT_EXAM_PROXIMITY,
    WEIGHT_MASTERY_GAP,
    WEIGHT_RETENTION_URGENCY,
)


def calculate_retention_urgency(retention: float) -> float:
    """
    Computes normalized retention urgency in [0.0, 1.0]:
        urgency = 1.0 - retention

    Assumptions:
        - When recall probability is 1.0 (fresh memory), retention urgency is 0.0.
        - When recall probability drops to 0.0 (forgotten), retention urgency is 1.0.

    Args:
        retention: Estimated recall probability in [0.0, 1.0].

    Returns:
        float in [0.0, 1.0].

    Raises:
        ValueError: If retention is outside [0.0, 1.0].
    """
    if not (0.0 <= retention <= 1.0):
        raise ValueError(f"retention must be in [0.0, 1.0], got {retention}")

    urgency = 1.0 - retention
    return round(max(0.0, min(1.0, urgency)), 4)


def calculate_mastery_gap(mastery: float) -> float:
    """
    Computes normalized mastery gap in [0.0, 1.0]:
        gap = (100.0 - mastery) / 100.0

    Assumptions:
        - When topic mastery is 100.0 (mastered), the gap is 0.0.
        - When topic mastery is 0.0 (novice), the gap is 1.0.

    Args:
        mastery: Cumulative topic mastery in [0.0, 100.0].

    Returns:
        float in [0.0, 1.0].

    Raises:
        ValueError: If mastery is outside [0.0, 100.0].
    """
    if not (MIN_MASTERY <= mastery <= MAX_MASTERY):
        raise ValueError(
            f"mastery must be in [{MIN_MASTERY}, {MAX_MASTERY}], got {mastery}"
        )

    gap = (MAX_MASTERY - mastery) / MAX_MASTERY
    return round(max(0.0, min(1.0, gap)), 4)


def calculate_exam_proximity(
    days_until_exam: float | None,
    horizon_days: float = DEFAULT_EXAM_HORIZON_DAYS,
) -> float:
    """
    Computes normalized exam proximity urgency in [0.0, 1.0].

    Assumptions:
        - If days_until_exam is None, no exam is scheduled -> proximity urgency is 0.0.
        - If days_until_exam <= 0.0, exam is today or overdue -> maximum urgency 1.0.
        - If days_until_exam >= horizon_days, exam is beyond planning horizon -> urgency is 0.0.
        - Within the horizon, urgency scales linearly: 1.0 - (days_until_exam / horizon_days).

    Args:
        days_until_exam: Days remaining until the scheduled exam, or None.
        horizon_days: Planning horizon threshold in days (> 0.0).

    Returns:
        float in [0.0, 1.0].

    Raises:
        ValueError: If horizon_days is not strictly positive.
    """
    if horizon_days <= 0.0:
        raise ValueError(f"horizon_days must be strictly positive (> 0.0), got {horizon_days}")

    if days_until_exam is None:
        return 0.0

    if days_until_exam <= 0.0:
        return 1.0

    if days_until_exam >= horizon_days:
        return 0.0

    proximity = 1.0 - (days_until_exam / horizon_days)
    return round(max(0.0, min(1.0, proximity)), 4)


def calculate_priority_score(
    retention: float,
    mastery: float,
    days_until_exam: float | None = None,
    horizon_days: float = DEFAULT_EXAM_HORIZON_DAYS,
) -> float:
    """
    Computes composite normalized study priority score U in [0.0, 1.0]:
        U = 0.5 * retention_urgency + 0.3 * mastery_gap + 0.2 * exam_proximity

    Args:
        retention: Memory recall probability in [0.0, 1.0].
        mastery: Cumulative topic mastery in [0.0, 100.0].
        days_until_exam: Optional days remaining until exam.
        horizon_days: Planning horizon in days.

    Returns:
        float in [0.0, 1.0].
    """
    u_retention = calculate_retention_urgency(retention)
    u_mastery = calculate_mastery_gap(mastery)
    u_exam = calculate_exam_proximity(days_until_exam, horizon_days=horizon_days)

    score = (
        WEIGHT_RETENTION_URGENCY * u_retention
        + WEIGHT_MASTERY_GAP * u_mastery
        + WEIGHT_EXAM_PROXIMITY * u_exam
    )
    return round(max(0.0, min(1.0, score)), 4)


def determine_recommended_action(retention: float, mastery: float) -> str:
    """
    Determines pedagogical action recommendation based on independent retention and mastery:
        - If retention < 0.75: "IMMEDIATE_REVISION"
        - If retention >= 0.75 and mastery < 70.0: "PRACTICE_QUIZ"
        - Otherwise: "ON_TRACK"

    Args:
        retention: Recall probability in [0.0, 1.0].
        mastery: Topic mastery score in [0.0, 100.0].

    Returns:
        One of "IMMEDIATE_REVISION", "PRACTICE_QUIZ", "ON_TRACK".

    Raises:
        ValueError: If retention or mastery violates bounds.
    """
    if not (0.0 <= retention <= 1.0):
        raise ValueError(f"retention must be in [0.0, 1.0], got {retention}")
    if not (MIN_MASTERY <= mastery <= MAX_MASTERY):
        raise ValueError(
            f"mastery must be in [{MIN_MASTERY}, {MAX_MASTERY}], got {mastery}"
        )

    if retention < RETENTION_REVISION_THRESHOLD:
        return ACTION_IMMEDIATE_REVISION
    elif mastery < MASTERY_PRACTICE_THRESHOLD:
        return ACTION_PRACTICE_QUIZ
    else:
        return ACTION_ON_TRACK


def schedule_study_sessions(
    topics: list[dict[str, Any]],
    daily_available_minutes: int,
    session_block_minutes: int = DEFAULT_SESSION_BLOCK_MINUTES,
    horizon_days: float = DEFAULT_EXAM_HORIZON_DAYS,
) -> list[dict[str, Any]]:
    """
    Prioritizes candidate topics and allocates study sessions in discrete blocks
    without exceeding the daily study budget.

    Sorting is deterministic: topics are ordered by (-priority_score, topic_id).

    Args:
        topics: List of topic dictionaries, each containing:
            - 'topic_id': str (unique identifier)
            - 'topic_name': str (display name)
            - 'retention': float in [0.0, 1.0]
            - 'mastery': float in [0.0, 100.0]
            - 'days_until_exam': float | None (optional)
        daily_available_minutes: Total study budget in minutes (>= 0).
        session_block_minutes: Discrete duration per session block in minutes (> 0).
        horizon_days: Exam planning horizon threshold in days (> 0.0).

    Returns:
        List of enriched topic dictionaries ordered by priority descending,
        each with allocated_minutes (session_block_minutes or 0).

    Raises:
        ValueError: If daily budget is negative, block size <= 0, or topic records are invalid.
    """
    if daily_available_minutes < MIN_DAILY_BUDGET_MINUTES:
        raise ValueError(
            f"daily_available_minutes must be non-negative (>= 0), got {daily_available_minutes}"
        )
    if session_block_minutes <= 0:
        raise ValueError(
            f"session_block_minutes must be strictly positive (> 0), got {session_block_minutes}"
        )

    if not topics:
        return []

    evaluated_topics: list[dict[str, Any]] = []

    for idx, item in enumerate(topics):
        if not isinstance(item, dict):
            raise ValueError(f"Each topic must be a dict, got {type(item)} at index {idx}")

        topic_id = str(item.get("topic_id", f"topic_{idx}"))
        topic_name = str(item.get("topic_name", topic_id))

        if "retention" not in item:
            raise ValueError(f"Missing required key 'retention' in topic '{topic_id}'")
        if "mastery" not in item:
            raise ValueError(f"Missing required key 'mastery' in topic '{topic_id}'")

        retention = float(item["retention"])
        mastery = float(item["mastery"])
        days_until_exam = (
            float(item["days_until_exam"])
            if item.get("days_until_exam") is not None
            else None
        )

        u_retention = calculate_retention_urgency(retention)
        u_mastery = calculate_mastery_gap(mastery)
        u_exam = calculate_exam_proximity(days_until_exam, horizon_days=horizon_days)
        priority_score = calculate_priority_score(
            retention, mastery, days_until_exam, horizon_days=horizon_days
        )
        action = determine_recommended_action(retention, mastery)

        evaluated_topics.append(
            {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "retention": retention,
                "mastery": mastery,
                "days_until_exam": days_until_exam,
                "retention_urgency": u_retention,
                "mastery_gap": u_mastery,
                "exam_proximity": u_exam,
                "priority_score": priority_score,
                "recommended_action": action,
                "allocated_minutes": 0,
            }
        )

    # Stable deterministic sorting: highest priority first; tie-breaker: topic_id ascending
    evaluated_topics.sort(key=lambda t: (-t["priority_score"], t["topic_id"]))

    # Discrete session block allocation within daily budget
    total_allowed_sessions = daily_available_minutes // session_block_minutes
    for i in range(min(total_allowed_sessions, len(evaluated_topics))):
        evaluated_topics[i]["allocated_minutes"] = session_block_minutes

    return evaluated_topics
