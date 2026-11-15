"""
Unit tests for Difficulty-Calibrated Bounded Mastery Update Engine.
"""

import unittest

from ml.config import (
    MAX_DIFFICULTY,
    MAX_EXPECTED_SCORE,
    MAX_MASTERY,
    MAX_MASTERY_DELTA,
    MAX_QUIZ_SCORE,
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
from ml.core.mastery import (
    calculate_expected_quiz_score,
    calculate_mastery_delta,
    classify_mastery_tier,
    update_topic_mastery,
)


class TestExpectedQuizScore(unittest.TestCase):
    """Analytical unit tests for expected quiz score calculation."""

    def test_expected_score_standard_midpoint(self):
        """M=50.0, D=0.5: raw expected = 100 * 0.5 * (1.2 - 0.2) = 50.0."""
        expected = calculate_expected_quiz_score(mastery=50.0, difficulty=0.5)
        self.assertAlmostEqual(expected, 50.0, places=4)

    def test_expected_score_high_mastery_easy_quiz(self):
        """M=80.0, D=0.25: raw = 100 * 0.8 * (1.2 - 0.1) = 88.0."""
        expected = calculate_expected_quiz_score(mastery=80.0, difficulty=0.25)
        self.assertAlmostEqual(expected, 88.0, places=4)

    def test_expected_score_floor_clamping(self):
        """Low mastery (e.g. M=0.0) must clamp to MIN_EXPECTED_SCORE (10.0)."""
        expected = calculate_expected_quiz_score(mastery=0.0, difficulty=1.0)
        self.assertEqual(expected, MIN_EXPECTED_SCORE)

        # M=5.0, D=1.0 -> raw = 100 * 0.05 * 0.8 = 4.0 -> clamped to 10.0
        expected_low = calculate_expected_quiz_score(mastery=5.0, difficulty=1.0)
        self.assertEqual(expected_low, MIN_EXPECTED_SCORE)

    def test_expected_score_ceiling_clamping(self):
        """High mastery with very easy quiz must clamp to MAX_EXPECTED_SCORE (95.0)."""
        # M=100.0, D=0.1 -> raw = 100 * 1.0 * (1.2 - 0.04) = 116.0 -> clamped to 95.0
        expected = calculate_expected_quiz_score(mastery=100.0, difficulty=0.1)
        self.assertEqual(expected, MAX_EXPECTED_SCORE)

    def test_expected_score_input_validation(self):
        """Out of bounds inputs must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_expected_quiz_score(mastery=-0.1, difficulty=0.5)
        with self.assertRaises(ValueError):
            calculate_expected_quiz_score(mastery=100.1, difficulty=0.5)
        with self.assertRaises(ValueError):
            calculate_expected_quiz_score(mastery=50.0, difficulty=0.05)
        with self.assertRaises(ValueError):
            calculate_expected_quiz_score(mastery=50.0, difficulty=1.05)


class TestMasteryDelta(unittest.TestCase):
    """Analytical unit tests for bounded mastery delta calculations."""

    def test_positive_residual_calculation(self):
        """
        When quiz_score > expected_score:
        M=50.0, D=0.50 -> expected = 50.0
        quiz_score = 80.0 -> residual = +30.0
        delta = 0.15 * 30.0 * 0.50 = 2.25
        """
        delta = calculate_mastery_delta(mastery=50.0, quiz_score=80.0, difficulty=0.50)
        self.assertAlmostEqual(delta, 2.25, places=4)

    def test_negative_residual_calculation(self):
        """
        When quiz_score < expected_score:
        M=50.0, D=0.50 -> expected = 50.0
        quiz_score = 30.0 -> residual = -20.0
        delta = 0.08 * (-20.0) * (1.1 - 0.50) = 0.08 * (-20.0) * 0.60 = -0.96
        """
        delta = calculate_mastery_delta(mastery=50.0, quiz_score=30.0, difficulty=0.50)
        self.assertAlmostEqual(delta, -0.96, places=4)

    def test_zero_residual_calculation(self):
        """When quiz_score == expected_score, delta must be exactly 0.0."""
        # M=50.0, D=0.50 -> expected = 50.0
        delta = calculate_mastery_delta(mastery=50.0, quiz_score=50.0, difficulty=0.50)
        self.assertEqual(delta, 0.0)

    def test_positive_delta_upper_bound(self):
        """
        Large positive residual must be capped at MAX_MASTERY_DELTA (+12.0):
        M=10.0, D=1.0 -> expected = 10.0 (clamped)
        quiz_score = 100.0 -> residual = 90.0
        raw_delta = 0.15 * 90.0 * 1.0 = 13.50 -> clamped to 12.0
        """
        delta = calculate_mastery_delta(mastery=10.0, quiz_score=100.0, difficulty=1.0)
        self.assertEqual(delta, MAX_MASTERY_DELTA)

    def test_negative_delta_bounded_within_floor(self):
        """
        Negative delta must never fall below MIN_MASTERY_DELTA (-8.0):
        M=95.0, D=0.10 -> expected = 95.0
        quiz_score = 0.0 -> residual = -95.0
        raw_delta = 0.08 * (-95.0) * (1.1 - 0.10) = -7.60
        Result is bounded above -8.0.
        """
        delta = calculate_mastery_delta(mastery=95.0, quiz_score=0.0, difficulty=0.10)
        self.assertGreaterEqual(delta, MIN_MASTERY_DELTA)
        self.assertAlmostEqual(delta, -7.60, places=4)

    def test_delta_input_validation(self):
        """Invalid quiz score must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_mastery_delta(mastery=50.0, quiz_score=-1.0, difficulty=0.5)
        with self.assertRaises(ValueError):
            calculate_mastery_delta(mastery=50.0, quiz_score=100.5, difficulty=0.5)


class TestUpdateTopicMastery(unittest.TestCase):
    """Unit tests for final mastery updates and global clamping."""

    def test_standard_upward_update(self):
        """M=50.0, delta=2.25 -> new_mastery=52.25."""
        new_mastery = update_topic_mastery(mastery=50.0, quiz_score=80.0, difficulty=0.50)
        self.assertAlmostEqual(new_mastery, 52.25, places=4)

    def test_standard_downward_update(self):
        """M=50.0, delta=-0.96 -> new_mastery=49.04."""
        new_mastery = update_topic_mastery(mastery=50.0, quiz_score=30.0, difficulty=0.50)
        self.assertAlmostEqual(new_mastery, 49.04, places=4)

    def test_mastery_ceiling_clamping(self):
        """Mastery must not exceed MAX_MASTERY (100.0)."""
        # M=98.0, D=1.0 -> expected = 78.4 -> residual = 21.6 -> delta = 3.24 -> 98.0 + 3.24 = 101.24 -> clamped to 100.0
        new_mastery = update_topic_mastery(mastery=98.0, quiz_score=100.0, difficulty=1.0)
        self.assertEqual(new_mastery, MAX_MASTERY)

    def test_mastery_floor_clamping(self):
        """Mastery must not fall below MIN_MASTERY (0.0)."""
        # M=0.5, D=0.1 -> expected = 10.0 (floor clamped) -> residual = -10.0 -> delta = -0.80 -> 0.5 - 0.80 = -0.30 -> clamped to 0.0
        new_mastery = update_topic_mastery(mastery=0.5, quiz_score=0.0, difficulty=0.10)
        self.assertEqual(new_mastery, MIN_MASTERY)


class TestMasteryTierClassification(unittest.TestCase):
    """Unit tests for qualitative mastery tier classification and boundary conditions."""

    def test_novice_tier_range(self):
        """Novice range: [0.0, 40.0)."""
        self.assertEqual(classify_mastery_tier(0.0), TIER_NOVICE)
        self.assertEqual(classify_mastery_tier(20.0), TIER_NOVICE)
        self.assertEqual(classify_mastery_tier(39.999), TIER_NOVICE)

    def test_developing_tier_range(self):
        """Developing range: [40.0, 70.0). Boundary at 40.0 must be Developing."""
        self.assertEqual(classify_mastery_tier(THRESHOLD_DEVELOPING), TIER_DEVELOPING)  # 40.0
        self.assertEqual(classify_mastery_tier(55.0), TIER_DEVELOPING)
        self.assertEqual(classify_mastery_tier(69.999), TIER_DEVELOPING)

    def test_proficient_tier_range(self):
        """Proficient range: [70.0, 85.0). Boundary at 70.0 must be Proficient."""
        self.assertEqual(classify_mastery_tier(THRESHOLD_PROFICIENT), TIER_PROFICIENT)  # 70.0
        self.assertEqual(classify_mastery_tier(78.5), TIER_PROFICIENT)
        self.assertEqual(classify_mastery_tier(84.999), TIER_PROFICIENT)

    def test_mastered_tier_range(self):
        """Mastered range: [85.0, 100.0]. Boundary at 85.0 and 100.0 must be Mastered."""
        self.assertEqual(classify_mastery_tier(THRESHOLD_MASTERED), TIER_MASTERED)      # 85.0
        self.assertEqual(classify_mastery_tier(92.0), TIER_MASTERED)
        self.assertEqual(classify_mastery_tier(MAX_MASTERY), TIER_MASTERED)             # 100.0

    def test_tier_input_validation(self):
        """Mastery outside [0.0, 100.0] must raise ValueError."""
        with self.assertRaises(ValueError):
            classify_mastery_tier(-0.01)
        with self.assertRaises(ValueError):
            classify_mastery_tier(100.01)


if __name__ == "__main__":
    unittest.main()
