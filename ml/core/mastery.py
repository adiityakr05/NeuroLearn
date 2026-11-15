"""
Difficulty-Calibrated Bounded Mastery Update Engine.

Computes deterministic, bounded adjustments to cumulative topic mastery based on
quiz performance relative to question difficulty.
Topic mastery is strictly decoupled from transient memory retention decay.
"""

from ml.config import (
    MAX_DIFFICULTY,
    MAX_EXPECTED_SCORE,
    MAX_MASTERY,
    MAX_MASTERY_DELTA,
    MAX_QUIZ_SCORE,
    MASTERY_K_DOWN,
    MASTERY_K_UP,
    MIN_DIFFICULTY,
    MIN_EXPECTED_SCORE,
    MIN_MASTERY,
    MIN_MASTERY_DELTA,
    MIN_QUIZ_SCORE,
    THRESHOLD_DEVELOPING,
    THRESHOLD_MASTERED,
    THRESHOLD_PROFICIENT,
    TIER_DEVELOPING,
    TIER_MASTERED,
    TIER_NOVICE,
    TIER_PROFICIENT,
)


def _validate_mastery_inputs(
    mastery: float,
    difficulty: float,
    quiz_score: float | None = None,
) -> None:
    """
    Validates range constraints for mastery, difficulty, and optional quiz_score.

    Raises:
        ValueError: If any parameter falls outside its defined domain.
    """
    if not (MIN_MASTERY <= mastery <= MAX_MASTERY):
        raise ValueError(
            f"mastery must be in [{MIN_MASTERY}, {MAX_MASTERY}], got {mastery}"
        )
    if not (MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY):
        raise ValueError(
            f"difficulty must be in [{MIN_DIFFICULTY}, {MAX_DIFFICULTY}], got {difficulty}"
        )
    if quiz_score is not None and not (MIN_QUIZ_SCORE <= quiz_score <= MAX_QUIZ_SCORE):
        raise ValueError(
            f"quiz_score must be in [{MIN_QUIZ_SCORE}, {MAX_QUIZ_SCORE}], got {quiz_score}"
        )


def calculate_expected_quiz_score(mastery: float, difficulty: float) -> float:
    """
    Computes the expected quiz score percentage based on current mastery and difficulty:
        raw_expected = 100 * (mastery / 100) * (1.2 - 0.4 * difficulty)
        expected = clamp(raw_expected, 10, 95)

    Args:
        mastery: Existing topic mastery in [0.0, 100.0].
        difficulty: Average question difficulty in [0.1, 1.0].

    Returns:
        float in [10.0, 95.0], representing expected percentage score.

    Raises:
        ValueError: If mastery or difficulty violates bounds.
    """
    _validate_mastery_inputs(mastery, difficulty)

    raw_expected = 100.0 * (mastery / 100.0) * (1.2 - 0.4 * difficulty)
    clamped_expected = max(MIN_EXPECTED_SCORE, min(MAX_EXPECTED_SCORE, raw_expected))
    return round(clamped_expected, 4)


def calculate_mastery_delta(
    mastery: float,
    quiz_score: float,
    difficulty: float,
) -> float:
    """
    Calculates the bounded, asymmetric adjustment to topic mastery based on quiz performance:
        residual = quiz_score - expected_score
        If residual >= 0:
            delta = 0.15 * residual * difficulty
        If residual < 0:
            delta = 0.08 * residual * (1.1 - difficulty)
        delta_bounded = clamp(delta, -8.0, +12.0)

    Args:
        mastery: Existing topic mastery in [0.0, 100.0].
        quiz_score: Percentage score achieved on quiz in [0.0, 100.0].
        difficulty: Average question difficulty in [0.1, 1.0].

    Returns:
        float in [-8.0, +12.0], representing the bounded change in mastery.

    Raises:
        ValueError: If any input violates boundary constraints.
    """
    _validate_mastery_inputs(mastery, difficulty, quiz_score)

    expected = calculate_expected_quiz_score(mastery, difficulty)
    residual = quiz_score - expected

    if residual >= 0.0:
        raw_delta = MASTERY_K_UP * residual * difficulty
    else:
        raw_delta = MASTERY_K_DOWN * residual * (1.1 - difficulty)

    bounded_delta = max(MIN_MASTERY_DELTA, min(MAX_MASTERY_DELTA, raw_delta))
    return round(bounded_delta, 4)


def update_topic_mastery(
    mastery: float,
    quiz_score: float,
    difficulty: float,
) -> float:
    """
    Computes updated topic mastery by applying the bounded delta and clamping to [0.0, 100.0]:
        new_mastery = clamp(mastery + delta, 0.0, 100.0)

    Args:
        mastery: Existing topic mastery in [0.0, 100.0].
        quiz_score: Percentage score achieved in [0.0, 100.0].
        difficulty: Average question difficulty in [0.1, 1.0].

    Returns:
        float in [0.0, 100.0], representing the updated topic mastery.

    Raises:
        ValueError: If any input violates domain constraints.
    """
    delta = calculate_mastery_delta(mastery, quiz_score, difficulty)
    new_mastery = max(MIN_MASTERY, min(MAX_MASTERY, mastery + delta))
    return round(new_mastery, 4)


def classify_mastery_tier(mastery: float) -> str:
    """
    Maps topic mastery score to its qualitative proficiency tier:
        - Novice:      [0.0, 40.0)
        - Developing:  [40.0, 70.0)
        - Proficient:  [70.0, 85.0)
        - Mastered:    [85.0, 100.0]

    Args:
        mastery: Topic mastery score in [0.0, 100.0].

    Returns:
        One of "Novice", "Developing", "Proficient", "Mastered".

    Raises:
        ValueError: If mastery is outside [0.0, 100.0].
    """
    if not (MIN_MASTERY <= mastery <= MAX_MASTERY):
        raise ValueError(
            f"mastery must be in [{MIN_MASTERY}, {MAX_MASTERY}], got {mastery}"
        )

    if mastery < THRESHOLD_DEVELOPING:
        return TIER_NOVICE
    elif mastery < THRESHOLD_PROFICIENT:
        return TIER_DEVELOPING
    elif mastery < THRESHOLD_MASTERED:
        return TIER_PROFICIENT
    else:
        return TIER_MASTERED
