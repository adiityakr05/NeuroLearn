"""
Mathematical retention baselines and custom spaced repetition update algorithms.

All time parameters are measured in decimal days.
Stability (S) represents the exponential decay constant: R(t) = exp(-t / S).
"""

import math
from typing import Final

from ml.config import (
    DEFAULT_DIFFICULTY,
    DEFAULT_TARGET_RETENTION,
    DIFFICULTY_BONUS_EASY,
    DIFFICULTY_PENALTY_AGAIN,
    DIFFICULTY_PENALTY_HARD,
    EASY_STABILITY_BONUS,
    FAILURE_STABILITY_FACTOR,
    HARD_STABILITY_FACTOR,
    MAX_DIFFICULTY,
    MAX_EASINESS_FACTOR,
    MAX_STABILITY_DAYS,
    MIN_DIFFICULTY,
    MIN_EASINESS_FACTOR,
    MIN_STABILITY_DAYS,
    RATING_AGAIN,
    RATING_EASY,
    RATING_GOOD,
    RATING_HARD,
    RECALL_SUCCESS_RATINGS,
    VALID_RATINGS,
)

LN_2: Final[float] = math.log(2.0)  # ~0.693147


def calculate_retention(elapsed_days: float, stability_days: float) -> float:
    """
    Computes theoretical recall probability using Ebbinghaus exponential decay:
        R(t) = exp(-t / S)

    Args:
        elapsed_days: Time in decimal days since the last review (t >= 0).
        stability_days: Exponential decay constant in decimal days (S > 0).

    Returns:
        float in [0.0, 1.0], representing predicted recall probability.

    Raises:
        ValueError: If stability_days is not strictly positive.
    """
    if stability_days <= 0.0:
        raise ValueError(f"stability_days must be strictly positive (> 0.0), got {stability_days}")

    if elapsed_days <= 0.0:
        return 1.0

    exponent = -elapsed_days / stability_days
    # Prevent math underflow for very large ratios (e.g. t/S > 700)
    if exponent < -700.0:
        return 0.0

    retention = math.exp(exponent)
    return max(0.0, min(1.0, retention))


def calculate_half_life(stability_days: float) -> float:
    """
    Calculates the true mathematical half-life (t_1/2) where R(t_1/2) = 0.5:
        t_1/2 = S * ln(2)

    Args:
        stability_days: Exponential decay constant S in decimal days.

    Returns:
        Half-life in decimal days.

    Raises:
        ValueError: If stability_days is not strictly positive.
    """
    if stability_days <= 0.0:
        raise ValueError(f"stability_days must be strictly positive (> 0.0), got {stability_days}")

    return stability_days * LN_2


def calculate_target_interval(
    stability_days: float,
    target_retention: float = DEFAULT_TARGET_RETENTION,
) -> float:
    """
    Calculates the total time interval from the last review until retention drops to target_retention:
        t_target = -S * ln(R_target)

    Args:
        stability_days: Exponential decay constant S in decimal days.
        target_retention: Desired recall threshold (0.0 < target_retention < 1.0).

    Returns:
        Total interval in decimal days from the last review date.

    Raises:
        ValueError: If stability_days <= 0 or target_retention not in (0.0, 1.0).
    """
    if stability_days <= 0.0:
        raise ValueError(f"stability_days must be strictly positive (> 0.0), got {stability_days}")
    if not (0.0 < target_retention < 1.0):
        raise ValueError(
            f"target_retention must be strictly between 0.0 and 1.0, got {target_retention}"
        )

    return -stability_days * math.log(target_retention)


def calculate_remaining_days(
    elapsed_days: float,
    stability_days: float,
    target_retention: float = DEFAULT_TARGET_RETENTION,
) -> float:
    """
    Calculates the remaining time in decimal days from the current moment until retention
    reaches target_retention.

    When elapsed_days has already passed the target interval (retention <= target_retention),
    returns 0.0, signaling that an immediate review is overdue.

    Args:
        elapsed_days: Days already elapsed since the last review.
        stability_days: Exponential decay constant S in decimal days.
        target_retention: Desired recall threshold (0.0 < target_retention < 1.0).

    Returns:
        Remaining days from today (>= 0.0).
    """
    total_interval = calculate_target_interval(stability_days, target_retention)
    effective_elapsed = max(0.0, elapsed_days)
    remaining = total_interval - effective_elapsed
    return max(0.0, remaining)


def is_retention_below_target(
    elapsed_days: float,
    stability_days: float,
    target_retention: float = DEFAULT_TARGET_RETENTION,
) -> bool:
    """
    Checks whether current retention has degraded below the target threshold.
    """
    current_retention = calculate_retention(elapsed_days, stability_days)
    return current_retention < target_retention


def is_recall_successful(rating: int) -> bool:
    """
    Determines binary recall success based strictly on the 1-4 UI rating.
    Ratings 3 (Good) and 4 (Easy) count as success (1).
    Ratings 1 (Again) and 2 (Hard) count as failure (0).

    Raises:
        ValueError: If rating is outside {1, 2, 3, 4}.
    """
    if rating not in VALID_RATINGS:
        raise ValueError(f"rating must be one of {VALID_RATINGS}, got {rating}")
    return rating in RECALL_SUCCESS_RATINGS


def calculate_easiness_factor(difficulty: float) -> float:
    """
    Derives an Easiness Factor (EF) multiplier from topic difficulty D in [0.1, 1.0]:
        EF = 1.3 + (1.0 - D) * 1.5, bounded in [1.3, 2.8]
    """
    clamped_diff = max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, difficulty))
    ef = MIN_EASINESS_FACTOR + (1.0 - clamped_diff) * (MAX_EASINESS_FACTOR - MIN_EASINESS_FACTOR)
    return max(MIN_EASINESS_FACTOR, min(MAX_EASINESS_FACTOR, ef))


def update_spaced_repetition_state(
    repetition: int,
    stability_days: float,
    difficulty: float,
    rating: int,
) -> tuple[int, float, float]:
    """
    Performs a deterministic state transition for NeuroLearn's custom spaced repetition algorithm.

    State transition logic driven directly by UI rating (1-4):
    - Rating 1 (Again):
        Reset repetition to 0.
        Apply failure stability reduction: S_new = S_prev * 0.5.
        Increase topic difficulty (+0.15).
    - Rating 2 (Hard):
        Retain repetition count unchanged (repetition_new = repetition_prev).
        Apply conservative stability growth: S_new = S_prev * 1.2.
        Increase topic difficulty (+0.05).
    - Rating 3 (Good):
        Increment repetition count (repetition_new = repetition_prev + 1).
        Apply standard Good stability growth based on repetition and EF.
        Maintain difficulty unchanged.
    - Rating 4 (Easy):
        Increment repetition count (repetition_new = repetition_prev + 1).
        Apply accelerated Easy stability growth (Good growth * 1.3).
        Decrease topic difficulty (-0.08).

    Args:
        repetition: Current successful review streak count (>= 0).
        stability_days: Current memory stability constant in decimal days (> 0).
        difficulty: Current topic difficulty in [0.1, 1.0].
        rating: Review performance rating in {1, 2, 3, 4}.

    Returns:
        tuple of (new_repetition, new_stability_days, new_difficulty)

    Raises:
        ValueError: If any input parameters violate physical or domain constraints.
    """
    if repetition < 0:
        raise ValueError(f"repetition must be non-negative (>= 0), got {repetition}")
    if stability_days <= 0.0:
        raise ValueError(f"stability_days must be strictly positive (> 0.0), got {stability_days}")
    if not (MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY):
        raise ValueError(
            f"difficulty must be in [{MIN_DIFFICULTY}, {MAX_DIFFICULTY}], got {difficulty}"
        )
    if rating not in VALID_RATINGS:
        raise ValueError(f"rating must be one of {VALID_RATINGS}, got {rating}")

    ef = calculate_easiness_factor(difficulty)

    if rating == RATING_AGAIN:
        new_repetition = 0
        new_stability = stability_days * FAILURE_STABILITY_FACTOR
        new_difficulty = difficulty + DIFFICULTY_PENALTY_AGAIN

    elif rating == RATING_HARD:
        new_repetition = repetition  # Retain repetition count
        new_stability = stability_days * HARD_STABILITY_FACTOR  # previous * 1.2
        new_difficulty = difficulty + DIFFICULTY_PENALTY_HARD

    elif rating == RATING_GOOD:
        new_repetition = repetition + 1
        new_difficulty = difficulty  # Unchanged
        if new_repetition == 1:
            new_stability = max(1.0, 1.0 / new_difficulty)
        elif new_repetition == 2:
            new_stability = max(2.5, 3.0 / new_difficulty)
        else:
            new_stability = max(stability_days * 1.1, stability_days * ef)

    elif rating == RATING_EASY:
        new_repetition = repetition + 1
        new_difficulty = difficulty - DIFFICULTY_BONUS_EASY
        if new_repetition == 1:
            base = max(1.0, 1.0 / max(MIN_DIFFICULTY, new_difficulty))
            new_stability = base * EASY_STABILITY_BONUS
        elif new_repetition == 2:
            base = max(2.5, 3.0 / max(MIN_DIFFICULTY, new_difficulty))
            new_stability = base * EASY_STABILITY_BONUS
        else:
            new_stability = max(stability_days * 1.3, stability_days * ef * EASY_STABILITY_BONUS)

    # Apply global boundary clamping
    clamped_stability = max(MIN_STABILITY_DAYS, min(MAX_STABILITY_DAYS, new_stability))
    clamped_difficulty = max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, new_difficulty))

    return (new_repetition, round(clamped_stability, 4), round(clamped_difficulty, 4))
