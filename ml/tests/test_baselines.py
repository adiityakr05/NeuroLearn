"""
Unit tests for mathematical retention baselines and custom spaced repetition algorithms.
"""

import math
import unittest

from ml.config import (
    DEFAULT_INITIAL_STABILITY,
    DEFAULT_TARGET_RETENTION,
    MAX_DIFFICULTY,
    MAX_STABILITY_DAYS,
    MIN_DIFFICULTY,
    MIN_STABILITY_DAYS,
    RATING_AGAIN,
    RATING_EASY,
    RATING_GOOD,
    RATING_HARD,
)
from ml.core.baselines import (
    calculate_easiness_factor,
    calculate_half_life,
    calculate_remaining_days,
    calculate_retention,
    calculate_target_interval,
    is_recall_successful,
    is_retention_below_target,
    update_spaced_repetition_state,
)


class TestRetentionBaselines(unittest.TestCase):
    """Tests for pure mathematical Ebbinghaus exponential decay."""

    def test_retention_at_zero_elapsed_days(self):
        """At t=0, retention must be exactly 1.0."""
        self.assertEqual(calculate_retention(0.0, stability_days=5.0), 1.0)
        self.assertEqual(calculate_retention(-1.0, stability_days=5.0), 1.0)

    def test_retention_at_decay_constant(self):
        """At t=S, retention must equal 1/e (~0.367879)."""
        stability = 8.0
        retention = calculate_retention(elapsed_days=stability, stability_days=stability)
        expected = 1.0 / math.e
        self.assertAlmostEqual(retention, expected, places=5)

    def test_retention_at_half_life(self):
        """At t=half_life (S * ln 2), retention must equal exactly 0.5."""
        stability = 12.0
        half_life = calculate_half_life(stability)
        retention = calculate_retention(elapsed_days=half_life, stability_days=stability)
        self.assertAlmostEqual(retention, 0.5, places=5)

    def test_half_life_calculation(self):
        """Verifies half_life = S * ln(2)."""
        stability = 10.0
        expected = 10.0 * math.log(2.0)
        self.assertAlmostEqual(calculate_half_life(stability), expected, places=6)

    def test_retention_extreme_elapsed_time(self):
        """For very large t, retention approaches 0.0 without underflow errors."""
        retention = calculate_retention(elapsed_days=10000.0, stability_days=1.0)
        self.assertEqual(retention, 0.0)

    def test_retention_invalid_stability(self):
        """Stability <= 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_retention(elapsed_days=1.0, stability_days=0.0)
        with self.assertRaises(ValueError):
            calculate_retention(elapsed_days=1.0, stability_days=-2.5)

    def test_half_life_invalid_stability(self):
        """calculate_half_life with S <= 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_half_life(0.0)
        with self.assertRaises(ValueError):
            calculate_half_life(-5.0)


class TestTargetIntervalAndRemaining(unittest.TestCase):
    """Tests for target interval and remaining days calculation."""

    def test_target_interval_formula(self):
        """Verifies t_target = -S * ln(R_target)."""
        stability = 10.0
        target_retention = 0.90
        expected = -10.0 * math.log(0.90)  # ~1.0536 days
        self.assertAlmostEqual(
            calculate_target_interval(stability, target_retention), expected, places=4
        )

    def test_target_interval_validation(self):
        """Invalid target_retention (< 0, == 0, >= 1) must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_target_interval(10.0, target_retention=0.0)
        with self.assertRaises(ValueError):
            calculate_target_interval(10.0, target_retention=1.0)
        with self.assertRaises(ValueError):
            calculate_target_interval(10.0, target_retention=-0.1)
        with self.assertRaises(ValueError):
            calculate_target_interval(10.0, target_retention=1.5)

    def test_remaining_days_before_target(self):
        """When elapsed_days < target_interval, remaining days = target - elapsed."""
        stability = 10.0
        target_retention = 0.90
        total_target = calculate_target_interval(stability, target_retention)
        elapsed = 0.5  # Less than ~1.0536
        remaining = calculate_remaining_days(elapsed, stability, target_retention)
        self.assertAlmostEqual(remaining, total_target - elapsed, places=5)

    def test_remaining_days_when_past_target(self):
        """When elapsed_days >= target_interval, remaining days must return 0.0."""
        stability = 10.0
        target_retention = 0.90
        # Elapsed 5 days is well past the ~1.05 day threshold
        remaining = calculate_remaining_days(5.0, stability, target_retention)
        self.assertEqual(remaining, 0.0)

    def test_is_retention_below_target(self):
        """Verifies boolean threshold detection."""
        stability = 5.0
        target_retention = 0.85
        # At t=0, retention=1.0 >= 0.85 -> False
        self.assertFalse(is_retention_below_target(0.0, stability, target_retention))
        # At t=10, retention = exp(-2) ~ 0.135 < 0.85 -> True
        self.assertTrue(is_retention_below_target(10.0, stability, target_retention))


class TestRecallSuccessRule(unittest.TestCase):
    """Tests that recall success is determined strictly by UI rating."""

    def test_rating_recall_mapping(self):
        """Ratings 3 & 4 count as success; ratings 1 & 2 count as failure."""
        self.assertFalse(is_recall_successful(RATING_AGAIN))  # 1 -> False
        self.assertFalse(is_recall_successful(RATING_HARD))   # 2 -> False
        self.assertTrue(is_recall_successful(RATING_GOOD))    # 3 -> True
        self.assertTrue(is_recall_successful(RATING_EASY))    # 4 -> True

    def test_invalid_ratings_raise_error(self):
        """Out of range ratings must raise ValueError."""
        for invalid in [0, 5, -1, 10]:
            with self.assertRaises(ValueError):
                is_recall_successful(invalid)


class TestCustomSpacedRepetitionTransitions(unittest.TestCase):
    """Tests for the custom spaced repetition state update rules."""

    def test_rating_again_failure_transition(self):
        """Rating 1: resets repetition to 0, reduces stability by 50%, increases difficulty."""
        repetition = 4
        stability = 12.0
        difficulty = 0.40

        new_rep, new_stab, new_diff = update_spaced_repetition_state(
            repetition, stability, difficulty, rating=RATING_AGAIN
        )

        self.assertEqual(new_rep, 0)
        self.assertAlmostEqual(new_stab, 6.0, places=3)
        self.assertAlmostEqual(new_diff, 0.55, places=3)  # 0.40 + 0.15

    def test_rating_again_clamping_bounds(self):
        """Rating 1 respect stability floor (0.1) and difficulty ceiling (1.0)."""
        new_rep, new_stab, new_diff = update_spaced_repetition_state(
            repetition=1, stability_days=0.15, difficulty=0.95, rating=RATING_AGAIN
        )
        self.assertEqual(new_rep, 0)
        self.assertGreaterEqual(new_stab, MIN_STABILITY_DAYS)
        self.assertEqual(new_diff, MAX_DIFFICULTY)  # 0.95 + 0.15 clamped to 1.0

    def test_rating_hard_transition(self):
        """Rating 2: retains repetition count, stability = prev * 1.2, increases difficulty."""
        repetition = 3
        stability = 5.0
        difficulty = 0.50

        new_rep, new_stab, new_diff = update_spaced_repetition_state(
            repetition, stability, difficulty, rating=RATING_HARD
        )

        # Repetition MUST be retained
        self.assertEqual(new_rep, 3)
        # Stability MUST grow conservatively by 1.2x
        self.assertAlmostEqual(new_stab, 6.0, places=3)  # 5.0 * 1.2
        # Difficulty increases slightly (+0.05)
        self.assertAlmostEqual(new_diff, 0.55, places=3)

    def test_rating_good_transition(self):
        """Rating 3: increments repetition, applies Good growth, difficulty unchanged."""
        repetition = 2
        stability = 4.0
        difficulty = 0.35

        new_rep, new_stab, new_diff = update_spaced_repetition_state(
            repetition, stability, difficulty, rating=RATING_GOOD
        )

        self.assertEqual(new_rep, 3)
        self.assertEqual(new_diff, 0.35)  # Difficulty unchanged
        self.assertGreater(new_stab, stability)  # Stability must grow

    def test_rating_good_initial_repetitions(self):
        """Rating 3 handles repetition 0 -> 1 and 1 -> 2 initialization."""
        # Initial review: 0 -> 1
        rep1, stab1, diff1 = update_spaced_repetition_state(
            repetition=0, stability_days=1.0, difficulty=0.5, rating=RATING_GOOD
        )
        self.assertEqual(rep1, 1)
        self.assertGreaterEqual(stab1, 1.0)

        # Second review: 1 -> 2
        rep2, stab2, diff2 = update_spaced_repetition_state(
            repetition=1, stability_days=stab1, difficulty=0.5, rating=RATING_GOOD
        )
        self.assertEqual(rep2, 2)
        self.assertGreaterEqual(stab2, 2.5)

    def test_rating_easy_transition(self):
        """Rating 4: increments repetition, accelerated stability growth, decreases difficulty."""
        repetition = 2
        stability = 4.0
        difficulty = 0.40

        new_rep, new_stab, new_diff = update_spaced_repetition_state(
            repetition, stability, difficulty, rating=RATING_EASY
        )

        self.assertEqual(new_rep, 3)
        self.assertAlmostEqual(new_diff, 0.32, places=3)  # 0.40 - 0.08

        # Compare Easy growth against Good growth for identical starting state
        _, good_stab, _ = update_spaced_repetition_state(
            repetition, stability, difficulty, rating=RATING_GOOD
        )
        self.assertGreater(new_stab, good_stab)

    def test_easiness_factor_range(self):
        """Verifies EF is bounded within [1.3, 2.8]."""
        ef_easy = calculate_easiness_factor(0.1)
        ef_hard = calculate_easiness_factor(1.0)
        self.assertLessEqual(ef_easy, 2.8)
        self.assertGreaterEqual(ef_hard, 1.3)
        self.assertGreater(ef_easy, ef_hard)

    def test_invalid_parameters_raise_error(self):
        """Verifies input validation on spaced repetition state updates."""
        with self.assertRaises(ValueError):
            update_spaced_repetition_state(-1, 2.0, 0.3, RATING_GOOD)
        with self.assertRaises(ValueError):
            update_spaced_repetition_state(0, 0.0, 0.3, RATING_GOOD)
        with self.assertRaises(ValueError):
            update_spaced_repetition_state(0, 2.0, 0.05, RATING_GOOD)  # diff < 0.1
        with self.assertRaises(ValueError):
            update_spaced_repetition_state(0, 2.0, 1.2, RATING_GOOD)   # diff > 1.0
        with self.assertRaises(ValueError):
            update_spaced_repetition_state(0, 2.0, 0.3, rating=5)      # invalid rating


if __name__ == "__main__":
    unittest.main()
