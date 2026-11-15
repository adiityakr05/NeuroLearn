"""
Configuration constants and hyperparameter bounds for NeuroLearn ML and Spaced Repetition.
"""

from typing import Final

# -------------------------------------------------------------------------
# Spaced Repetition & Retention Defaults
# -------------------------------------------------------------------------

# Target retention threshold (R_target): the desired recall probability threshold.
# Default 0.90 means we schedule review when probability drops to 90%.
DEFAULT_TARGET_RETENTION: Final[float] = 0.90

# Default initial memory stability (S_0) in decimal days for a newly learned item.
DEFAULT_INITIAL_STABILITY: Final[float] = 1.0

# Minimum and maximum allowable stability in days.
MIN_STABILITY_DAYS: Final[float] = 0.1
MAX_STABILITY_DAYS: Final[float] = 3650.0  # 10 years upper bound

# Topic difficulty bounds (0.1 = easiest, 1.0 = most difficult)
MIN_DIFFICULTY: Final[float] = 0.1
MAX_DIFFICULTY: Final[float] = 1.0
DEFAULT_DIFFICULTY: Final[float] = 0.3

# -------------------------------------------------------------------------
# Review Ratings (1-4 scale)
# -------------------------------------------------------------------------
RATING_AGAIN: Final[int] = 1
RATING_HARD: Final[int] = 2
RATING_GOOD: Final[int] = 3
RATING_EASY: Final[int] = 4

VALID_RATINGS: Final[tuple[int, ...]] = (
    RATING_AGAIN,
    RATING_HARD,
    RATING_GOOD,
    RATING_EASY,
)

# Binary recall success is defined strictly as ratings 3 (Good) and 4 (Easy).
RECALL_SUCCESS_RATINGS: Final[tuple[int, ...]] = (
    RATING_GOOD,
    RATING_EASY,
)

# -------------------------------------------------------------------------
# Spaced Repetition State Update Multipliers
# -------------------------------------------------------------------------
# Failure (Rating 1) stability reduction factor
FAILURE_STABILITY_FACTOR: Final[float] = 0.5
DIFFICULTY_PENALTY_AGAIN: Final[float] = 0.15

# Hard (Rating 2) stability multiplier and difficulty penalty
HARD_STABILITY_FACTOR: Final[float] = 1.2
DIFFICULTY_PENALTY_HARD: Final[float] = 0.05

# Easy (Rating 4) stability bonus multiplier and difficulty reward
EASY_STABILITY_BONUS: Final[float] = 1.3
DIFFICULTY_BONUS_EASY: Final[float] = 0.08

# Easiness Factor bounds
MIN_EASINESS_FACTOR: Final[float] = 1.3
MAX_EASINESS_FACTOR: Final[float] = 2.8

# -------------------------------------------------------------------------
# Topic Mastery Constants
# -------------------------------------------------------------------------
MIN_MASTERY: Final[float] = 0.0
MAX_MASTERY: Final[float] = 100.0
DEFAULT_MASTERY: Final[float] = 0.0

MIN_QUIZ_SCORE: Final[float] = 0.0
MAX_QUIZ_SCORE: Final[float] = 100.0

MIN_EXPECTED_SCORE: Final[float] = 10.0
MAX_EXPECTED_SCORE: Final[float] = 95.0

# Asymmetric learning rate multipliers
MASTERY_K_UP: Final[float] = 0.15
MASTERY_K_DOWN: Final[float] = 0.08

# Bounded step delta limits
MIN_MASTERY_DELTA: Final[float] = -8.0
MAX_MASTERY_DELTA: Final[float] = 12.0

# Mastery tier labels
TIER_NOVICE: Final[str] = "Novice"
TIER_DEVELOPING: Final[str] = "Developing"
TIER_PROFICIENT: Final[str] = "Proficient"
TIER_MASTERED: Final[str] = "Mastered"

# Mastery tier thresholds (left-closed, right-open intervals, except Mastered which includes 100.0)
THRESHOLD_DEVELOPING: Final[float] = 40.0
THRESHOLD_PROFICIENT: Final[float] = 70.0
THRESHOLD_MASTERED: Final[float] = 85.0

# -------------------------------------------------------------------------
# Study Scheduler Constants
# -------------------------------------------------------------------------
# Priority score linear weights (sum to 1.0)
WEIGHT_RETENTION_URGENCY: Final[float] = 0.5
WEIGHT_MASTERY_GAP: Final[float] = 0.3
WEIGHT_EXAM_PROXIMITY: Final[float] = 0.2

# Exam horizon in days (exams beyond this horizon have zero proximity urgency)
DEFAULT_EXAM_HORIZON_DAYS: Final[float] = 30.0

# Action recommendation thresholds
RETENTION_REVISION_THRESHOLD: Final[float] = 0.75
MASTERY_PRACTICE_THRESHOLD: Final[float] = 70.0

# Action recommendation labels
ACTION_IMMEDIATE_REVISION: Final[str] = "IMMEDIATE_REVISION"
ACTION_PRACTICE_QUIZ: Final[str] = "PRACTICE_QUIZ"
ACTION_ON_TRACK: Final[str] = "ON_TRACK"

# Scheduling session block defaults (in minutes)
DEFAULT_SESSION_BLOCK_MINUTES: Final[int] = 25
MIN_SESSION_BLOCK_MINUTES: Final[int] = 10
MAX_SESSION_BLOCK_MINUTES: Final[int] = 120

MIN_DAILY_BUDGET_MINUTES: Final[int] = 0
MAX_DAILY_BUDGET_MINUTES: Final[int] = 1440  # 24 hours


