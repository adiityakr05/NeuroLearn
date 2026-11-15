"""
Unit tests for Spaced Repetition Study Scheduler.
"""

import unittest

from ml.config import (
    ACTION_IMMEDIATE_REVISION,
    ACTION_ON_TRACK,
    ACTION_PRACTICE_QUIZ,
    DEFAULT_EXAM_HORIZON_DAYS,
    DEFAULT_SESSION_BLOCK_MINUTES,
    MASTERY_PRACTICE_THRESHOLD,
    RETENTION_REVISION_THRESHOLD,
    WEIGHT_EXAM_PROXIMITY,
    WEIGHT_MASTERY_GAP,
    WEIGHT_RETENTION_URGENCY,
)
from ml.core.scheduler import (
    calculate_exam_proximity,
    calculate_mastery_gap,
    calculate_priority_score,
    calculate_retention_urgency,
    determine_recommended_action,
    schedule_study_sessions,
)


class TestUrgencyComponents(unittest.TestCase):
    """Analytical unit tests for individual normalized urgency components."""

    def test_retention_urgency_values(self):
        """Urgency = 1.0 - retention."""
        self.assertAlmostEqual(calculate_retention_urgency(1.0), 0.0)
        self.assertAlmostEqual(calculate_retention_urgency(0.0), 1.0)
        self.assertAlmostEqual(calculate_retention_urgency(0.75), 0.25)
        self.assertAlmostEqual(calculate_retention_urgency(0.30), 0.70)

    def test_retention_urgency_validation(self):
        """Retention outside [0.0, 1.0] must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_retention_urgency(-0.01)
        with self.assertRaises(ValueError):
            calculate_retention_urgency(1.01)

    def test_mastery_gap_values(self):
        """Mastery gap = (100 - mastery) / 100."""
        self.assertAlmostEqual(calculate_mastery_gap(100.0), 0.0)
        self.assertAlmostEqual(calculate_mastery_gap(0.0), 1.0)
        self.assertAlmostEqual(calculate_mastery_gap(70.0), 0.30)
        self.assertAlmostEqual(calculate_mastery_gap(40.0), 0.60)

    def test_mastery_gap_validation(self):
        """Mastery outside [0.0, 100.0] must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_mastery_gap(-0.1)
        with self.assertRaises(ValueError):
            calculate_mastery_gap(100.1)

    def test_exam_proximity_values(self):
        """Tests exam proximity across none, overdue, horizon, and midpoint cases."""
        # No exam scheduled
        self.assertEqual(calculate_exam_proximity(None), 0.0)
        # Exam is today or overdue
        self.assertEqual(calculate_exam_proximity(0.0), 1.0)
        self.assertEqual(calculate_exam_proximity(-3.0), 1.0)
        # Exam at or beyond 30-day horizon
        self.assertEqual(calculate_exam_proximity(30.0, horizon_days=30.0), 0.0)
        self.assertEqual(calculate_exam_proximity(45.0, horizon_days=30.0), 0.0)
        # Midpoint: 15 days out -> 1.0 - (15 / 30) = 0.50
        self.assertAlmostEqual(calculate_exam_proximity(15.0, horizon_days=30.0), 0.50)
        # 6 days out -> 1.0 - (6 / 30) = 0.80
        self.assertAlmostEqual(calculate_exam_proximity(6.0, horizon_days=30.0), 0.80)

    def test_exam_proximity_invalid_horizon(self):
        """Non-positive horizon must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_exam_proximity(10.0, horizon_days=0.0)
        with self.assertRaises(ValueError):
            calculate_exam_proximity(10.0, horizon_days=-5.0)


class TestPriorityScoreCalculation(unittest.TestCase):
    """Analytical unit tests for composite priority score."""

    def test_priority_score_midpoint(self):
        """
        R=0.60 -> u_r = 0.40
        M=50.0 -> u_m = 0.50
        days=15 -> u_e = 0.50 (horizon 30)
        U = 0.5 * 0.40 + 0.3 * 0.50 + 0.2 * 0.50 = 0.20 + 0.15 + 0.10 = 0.45
        """
        score = calculate_priority_score(retention=0.60, mastery=50.0, days_until_exam=15.0)
        self.assertAlmostEqual(score, 0.45, places=4)

    def test_priority_score_maximum_urgency(self):
        """Forgotten topic (R=0.0), novice mastery (M=0.0), exam today (days=0.0) -> U=1.0."""
        score = calculate_priority_score(retention=0.0, mastery=0.0, days_until_exam=0.0)
        self.assertAlmostEqual(score, 1.0, places=4)

    def test_priority_score_minimum_urgency(self):
        """Fresh memory (R=1.0), mastered (M=100.0), no exam -> U=0.0."""
        score = calculate_priority_score(retention=1.0, mastery=100.0, days_until_exam=None)
        self.assertAlmostEqual(score, 0.0, places=4)

    def test_high_mastery_low_retention_prioritization(self):
        """
        Verifies that high-mastery topics with low retention are prioritized higher
        than fresh topics with moderate mastery.
        """
        # Topic A: Mastered (M=95), but severely decayed retention (R=0.20), no exam
        # u_r = 0.80, u_m = 0.05, u_e = 0.0 -> U = 0.5 * 0.80 + 0.3 * 0.05 = 0.415
        score_a = calculate_priority_score(retention=0.20, mastery=95.0, days_until_exam=None)
        self.assertAlmostEqual(score_a, 0.415, places=4)

        # Topic B: Developing mastery (M=60), but very fresh retention (R=0.95), no exam
        # u_r = 0.05, u_m = 0.40, u_e = 0.0 -> U = 0.5 * 0.05 + 0.3 * 0.40 = 0.145
        score_b = calculate_priority_score(retention=0.95, mastery=60.0, days_until_exam=None)
        self.assertAlmostEqual(score_b, 0.145, places=4)

        self.assertGreater(score_a, score_b)


class TestRecommendedActionRules(unittest.TestCase):
    """Unit tests for discrete pedagogical action recommendations."""

    def test_immediate_revision_when_retention_below_threshold(self):
        """Any retention < 0.75 must recommend IMMEDIATE_REVISION, regardless of mastery."""
        self.assertEqual(
            determine_recommended_action(retention=0.749, mastery=100.0),
            ACTION_IMMEDIATE_REVISION,
        )
        self.assertEqual(
            determine_recommended_action(retention=0.50, mastery=20.0),
            ACTION_IMMEDIATE_REVISION,
        )
        self.assertEqual(
            determine_recommended_action(retention=0.0, mastery=90.0),
            ACTION_IMMEDIATE_REVISION,
        )

    def test_practice_quiz_when_retention_ok_and_mastery_below_70(self):
        """Retention >= 0.75 and mastery < 70.0 must recommend PRACTICE_QUIZ."""
        self.assertEqual(
            determine_recommended_action(retention=0.75, mastery=69.99),
            ACTION_PRACTICE_QUIZ,
        )
        self.assertEqual(
            determine_recommended_action(retention=0.90, mastery=45.0),
            ACTION_PRACTICE_QUIZ,
        )

    def test_on_track_when_both_retention_and_mastery_healthy(self):
        """Retention >= 0.75 and mastery >= 70.0 must classify as ON_TRACK."""
        self.assertEqual(
            determine_recommended_action(retention=0.75, mastery=70.0),
            ACTION_ON_TRACK,
        )
        self.assertEqual(
            determine_recommended_action(retention=0.90, mastery=85.0),
            ACTION_ON_TRACK,
        )
        self.assertEqual(
            determine_recommended_action(retention=1.0, mastery=100.0),
            ACTION_ON_TRACK,
        )

    def test_action_input_validation(self):
        """Out of bounds inputs must raise ValueError."""
        with self.assertRaises(ValueError):
            determine_recommended_action(retention=-0.1, mastery=50.0)
        with self.assertRaises(ValueError):
            determine_recommended_action(retention=0.8, mastery=105.0)


class TestScheduleStudySessions(unittest.TestCase):
    """Unit tests for multi-topic prioritization and discrete budget allocation."""

    def setUp(self):
        self.sample_topics = [
            {
                "topic_id": "T01",
                "topic_name": "Linear Algebra",
                "retention": 0.50,
                "mastery": 80.0,
                "days_until_exam": None,
            },
            {
                "topic_id": "T02",
                "topic_name": "Gradient Descent",
                "retention": 0.90,
                "mastery": 50.0,
                "days_until_exam": 5.0,  # Exam approaching soon
            },
            {
                "topic_id": "T03",
                "topic_name": "Backpropagation",
                "retention": 0.20,
                "mastery": 40.0,
                "days_until_exam": None,  # Severe retention drop & low mastery
            },
            {
                "topic_id": "T04",
                "topic_name": "Python Basics",
                "retention": 0.95,
                "mastery": 95.0,
                "days_until_exam": None,  # Healthy, on track
            },
        ]

    def test_budget_allocation_discrete_blocks(self):
        """
        With 60 available minutes and 25-minute blocks:
        Allowed sessions = 60 // 25 = 2.
        Top 2 topics must receive exactly 25 minutes each; total = 50 minutes (<= 60).
        Remaining topics receive 0 minutes.
        """
        scheduled = schedule_study_sessions(
            self.sample_topics,
            daily_available_minutes=60,
            session_block_minutes=25,
        )

        self.assertEqual(len(scheduled), 4)
        total_allocated = sum(t["allocated_minutes"] for t in scheduled)
        self.assertEqual(total_allocated, 50)

        # Top 2 get 25 minutes
        self.assertEqual(scheduled[0]["allocated_minutes"], 25)
        self.assertEqual(scheduled[1]["allocated_minutes"], 25)
        # 3rd and 4th get 0 minutes
        self.assertEqual(scheduled[2]["allocated_minutes"], 0)
        self.assertEqual(scheduled[3]["allocated_minutes"], 0)

    def test_sorting_order_highest_priority_first(self):
        """Verifies topics are ordered strictly in descending order of priority score."""
        scheduled = schedule_study_sessions(
            self.sample_topics,
            daily_available_minutes=100,
        )

        scores = [t["priority_score"] for t in scheduled]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # T03 (R=0.2, M=40 -> U = 0.5*0.8 + 0.3*0.6 = 0.58) must be rank 1
        self.assertEqual(scheduled[0]["topic_id"], "T03")
        self.assertEqual(scheduled[0]["recommended_action"], ACTION_IMMEDIATE_REVISION)

    def test_stable_deterministic_sorting_tiebreaker(self):
        """Tied priority scores must break ties deterministically by topic_id ascending."""
        tied_topics = [
            {"topic_id": "topic_Z", "topic_name": "Z", "retention": 0.80, "mastery": 70.0},
            {"topic_id": "topic_A", "topic_name": "A", "retention": 0.80, "mastery": 70.0},
            {"topic_id": "topic_M", "topic_name": "M", "retention": 0.80, "mastery": 70.0},
        ]

        scheduled = schedule_study_sessions(tied_topics, daily_available_minutes=50)
        ordered_ids = [t["topic_id"] for t in scheduled]
        self.assertEqual(ordered_ids, ["topic_A", "topic_M", "topic_Z"])

    def test_insufficient_budget_allocates_zero(self):
        """Budget smaller than one block size (e.g. 20 min < 25 min) allocates 0 minutes."""
        scheduled = schedule_study_sessions(
            self.sample_topics,
            daily_available_minutes=20,
            session_block_minutes=25,
        )
        total_allocated = sum(t["allocated_minutes"] for t in scheduled)
        self.assertEqual(total_allocated, 0)
        for t in scheduled:
            self.assertEqual(t["allocated_minutes"], 0)

    def test_zero_budget_and_empty_topics(self):
        """Handles empty topic lists and zero budget gracefully."""
        self.assertEqual(schedule_study_sessions([], daily_available_minutes=60), [])
        scheduled_zero = schedule_study_sessions(self.sample_topics, daily_available_minutes=0)
        self.assertEqual(sum(t["allocated_minutes"] for t in scheduled_zero), 0)

    def test_scheduler_input_validation(self):
        """Rejects negative daily budget, non-positive block size, or malformed dicts."""
        with self.assertRaises(ValueError):
            schedule_study_sessions(self.sample_topics, daily_available_minutes=-10)
        with self.assertRaises(ValueError):
            schedule_study_sessions(self.sample_topics, daily_available_minutes=60, session_block_minutes=0)
        with self.assertRaises(ValueError):
            # Missing 'retention' key
            schedule_study_sessions([{"topic_id": "X", "mastery": 50.0}], daily_available_minutes=60)


if __name__ == "__main__":
    unittest.main()
