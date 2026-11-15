"""
Unit tests for Review Event Schemas and Synthetic Review Generator.
"""

import csv
import os
import random
import tempfile
import unittest
from datetime import datetime

from ml.data.schemas import (
    MODEL_FEATURE_NAMES,
    ROUTING_KEYS,
    TARGET_NAME,
    ReviewEventRecord,
)
from ml.data.synthetic_generator import (
    MAX_LEARNER_ABILITY_MULT,
    MIN_LEARNER_ABILITY_MULT,
    GeneratorConfig,
    SyntheticReviewGenerator,
    export_synthetic_dataset_to_csv,
)


class TestReviewEventSchema(unittest.TestCase):
    """Unit tests for ReviewEventRecord validation and schema integrity."""

    def setUp(self):
        self.valid_data = {
            "event_id": "evt_test_001",
            "user_id": "user_001",
            "topic_id": "topic_01",
            "timestamp": "2026-09-01T08:30:00Z",
            "elapsed_days": 2.5,
            "stability_days_prior": 3.0,
            "repetition_count_prior": 1,
            "topic_difficulty_prior": 0.45,
            "last_rating_prior": 3,
            "user_prior_recall_rate": 0.85,
            "user_prior_reviews_count": 10,
            "topic_prior_quiz_avg": 78.5,
            "has_prior_quiz": 1,
            "recall_success": 1,
            "is_synthetic": 1,
        }

    def test_valid_record_instantiation(self):
        """A properly formatted record validates without error."""
        record = ReviewEventRecord(**self.valid_data)
        record.validate()
        self.assertEqual(record.event_id, "evt_test_001")
        self.assertEqual(record.recall_success, 1)

    def test_routing_keys_separation(self):
        """Ensures routing keys and model features are strictly disjoint."""
        intersection = set(ROUTING_KEYS).intersection(set(MODEL_FEATURE_NAMES))
        self.assertEqual(len(intersection), 0)
        self.assertNotIn(TARGET_NAME, ROUTING_KEYS)
        self.assertNotIn(TARGET_NAME, MODEL_FEATURE_NAMES)

    def test_from_and_to_dict_serialization(self):
        """Serialization to/from dict preserves types and values."""
        record = ReviewEventRecord.from_dict(self.valid_data)
        dict_rep = record.to_dict()
        self.assertEqual(dict_rep["event_id"], "evt_test_001")
        self.assertEqual(dict_rep["topic_prior_quiz_avg"], 78.5)

    def test_invalid_timestamp_raises_error(self):
        """Malformed timestamp strings must raise ValueError."""
        data = self.valid_data.copy()
        data["timestamp"] = "invalid-date-format"
        record = ReviewEventRecord(**data)
        with self.assertRaises(ValueError):
            record.validate()

    def test_invalid_boundary_values_raise_error(self):
        """Negative elapsed time or negative stability must raise ValueError."""
        # Negative elapsed days
        data_neg_elapsed = self.valid_data.copy()
        data_neg_elapsed["elapsed_days"] = -0.5
        with self.assertRaises(ValueError):
            ReviewEventRecord(**data_neg_elapsed).validate()

        # Non-positive stability
        data_zero_stab = self.valid_data.copy()
        data_zero_stab["stability_days_prior"] = 0.0
        with self.assertRaises(ValueError):
            ReviewEventRecord(**data_zero_stab).validate()

        # Non-binary target
        data_bad_target = self.valid_data.copy()
        data_bad_target["recall_success"] = 2
        with self.assertRaises(ValueError):
            ReviewEventRecord(**data_bad_target).validate()

    def test_quiz_flag_consistency(self):
        """has_prior_quiz flag must be consistent with topic_prior_quiz_avg."""
        # has_prior_quiz=0 but average is provided
        data_inconsistent = self.valid_data.copy()
        data_inconsistent["has_prior_quiz"] = 0
        data_inconsistent["topic_prior_quiz_avg"] = 80.0
        with self.assertRaises(ValueError):
            ReviewEventRecord(**data_inconsistent).validate()

        # has_prior_quiz=1 but average is None
        data_inconsistent_2 = self.valid_data.copy()
        data_inconsistent_2["has_prior_quiz"] = 1
        data_inconsistent_2["topic_prior_quiz_avg"] = None
        with self.assertRaises(ValueError):
            ReviewEventRecord(**data_inconsistent_2).validate()


class TestSyntheticReviewGenerator(unittest.TestCase):
    """Unit tests for the synthetic interaction simulator."""

    def setUp(self):
        # Lightweight test config: 15 learners, 5 topics, 14 days
        self.test_config = GeneratorConfig(
            num_learners=15,
            num_topics=5,
            simulation_days=14,
            seed=123,
        )

    def test_seed_reproducibility(self):
        """Identical seeds must generate identical event lists."""
        gen1 = SyntheticReviewGenerator(self.test_config)
        events1 = gen1.generate()

        gen2 = SyntheticReviewGenerator(self.test_config)
        events2 = gen2.generate()

        self.assertEqual(len(events1), len(events2))
        self.assertGreater(len(events1), 0)
        for e1, e2 in zip(events1, events2):
            self.assertEqual(e1.event_id, e2.event_id)
            self.assertEqual(e1.timestamp, e2.timestamp)
            self.assertEqual(e1.recall_success, e2.recall_success)

    def test_unique_event_ids(self):
        """All generated event IDs must be distinct."""
        gen = SyntheticReviewGenerator(self.test_config)
        events = gen.generate()
        event_ids = [e.event_id for e in events]
        self.assertEqual(len(event_ids), len(set(event_ids)))

    def test_valid_timestamps_and_targets(self):
        """All timestamps must be valid ISO-8601 UTC and targets binary."""
        gen = SyntheticReviewGenerator(self.test_config)
        events = gen.generate()
        for e in events:
            # Parses without exception
            dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            self.assertIsNotNone(dt)
            self.assertIn(e.recall_success, (0, 1))
            self.assertEqual(e.is_synthetic, 1)

    def test_first_review_cold_start_behavior(self):
        """First review for each user-topic pair must contain no fabricated prior outcomes."""
        gen = SyntheticReviewGenerator(self.test_config)
        events = gen.generate()

        seen_user_topics = set()
        for e in events:
            key = (e.user_id, e.topic_id)
            if key not in seen_user_topics:
                seen_user_topics.add(key)
                # First time reviewing this topic:
                self.assertIsNone(e.last_rating_prior)
                self.assertEqual(e.repetition_count_prior, 0)
                self.assertEqual(e.stability_days_prior, 1.0)

    def test_historical_features_strict_point_in_time_causality(self):
        """Historical statistics for user reviews must be computed strictly from preceding events."""
        gen = SyntheticReviewGenerator(self.test_config)
        events = gen.generate()

        # Track user events chronologically
        user_events: dict[str, list[ReviewEventRecord]] = {}
        for e in events:
            user_events.setdefault(e.user_id, []).append(e)

        for user_id, u_list in user_events.items():
            running_success = 0
            for idx, e in enumerate(u_list):
                # Preceding count must equal exact number of prior events for this user
                self.assertEqual(e.user_prior_reviews_count, idx)
                if idx > 0:
                    expected_rate = round(running_success / idx, 4)
                    self.assertAlmostEqual(e.user_prior_recall_rate, expected_rate, places=4)

                # Target must not leak into prior count or prior rate
                running_success += e.recall_success

    def test_dataset_export_and_readback(self):
        """Tests that export_synthetic_dataset_to_csv writes valid, readable CSV records."""
        gen = SyntheticReviewGenerator(self.test_config)
        events = gen.generate()

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_csv = os.path.join(tmp_dir, "test_events.csv")
            export_synthetic_dataset_to_csv(events, temp_csv)
            self.assertTrue(os.path.exists(temp_csv))
            self.assertGreater(os.path.getsize(temp_csv), 0)

            # Read back and verify line count
            with open(temp_csv, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 1 header line + N event lines
                self.assertEqual(len(lines), len(events) + 1)

    def test_learner_ability_multiplier_bounds(self):
        """Verifies that every generated learner has an ability multiplier strictly in [0.50, 1.50]."""
        gen = SyntheticReviewGenerator(self.test_config)
        rng = random.Random(self.test_config.seed)
        topic_ids = [f"topic_{t:02d}" for t in range(self.test_config.num_topics)]
        learners = gen.generate_learners(rng, topic_ids)

        self.assertEqual(len(learners), self.test_config.num_learners)
        for user_id, learner_data in learners.items():
            mult = learner_data["ability_multiplier"]
            self.assertGreaterEqual(
                mult,
                MIN_LEARNER_ABILITY_MULT,
                f"Learner {user_id} multiplier {mult} below minimum {MIN_LEARNER_ABILITY_MULT}",
            )
            self.assertLessEqual(
                mult,
                MAX_LEARNER_ABILITY_MULT,
                f"Learner {user_id} multiplier {mult} above maximum {MAX_LEARNER_ABILITY_MULT}",
            )

    def test_csv_deserialization_round_trip(self):
        """
        Exports ReviewEventRecord rows to CSV, reads them back, reconstructs
        records using ReviewEventRecord.from_dict(), and asserts full integrity.
        """
        gen = SyntheticReviewGenerator(self.test_config)
        original_events = gen.generate()

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_csv = os.path.join(tmp_dir, "round_trip_test.csv")
            export_synthetic_dataset_to_csv(original_events, temp_csv)
            self.assertTrue(os.path.exists(temp_csv))

            reconstructed_events: list[ReviewEventRecord] = []
            with open(temp_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    reconstructed = ReviewEventRecord.from_dict(row)
                    reconstructed_events.append(reconstructed)

            self.assertEqual(len(reconstructed_events), len(original_events))

            # Compare every reconstructed record with the original
            for orig, recon in zip(original_events, reconstructed_events):
                self.assertEqual(orig.event_id, recon.event_id)
                self.assertEqual(orig.user_id, recon.user_id)
                self.assertEqual(orig.topic_id, recon.topic_id)
                self.assertEqual(orig.timestamp, recon.timestamp)
                self.assertAlmostEqual(orig.elapsed_days, recon.elapsed_days, places=2)
                self.assertAlmostEqual(orig.stability_days_prior, recon.stability_days_prior, places=4)
                self.assertEqual(orig.repetition_count_prior, recon.repetition_count_prior)
                self.assertAlmostEqual(orig.topic_difficulty_prior, recon.topic_difficulty_prior, places=2)
                self.assertEqual(orig.last_rating_prior, recon.last_rating_prior)
                self.assertAlmostEqual(orig.user_prior_recall_rate, recon.user_prior_recall_rate, places=4)
                self.assertEqual(orig.user_prior_reviews_count, recon.user_prior_reviews_count)
                if orig.topic_prior_quiz_avg is None:
                    self.assertIsNone(recon.topic_prior_quiz_avg)
                else:
                    self.assertAlmostEqual(orig.topic_prior_quiz_avg, recon.topic_prior_quiz_avg, places=2)
                self.assertEqual(orig.has_prior_quiz, recon.has_prior_quiz)
                self.assertEqual(orig.recall_success, recon.recall_success)
                self.assertEqual(orig.is_synthetic, 1)

    def test_invalid_config_raises_error(self):
        """Invalid generator configuration must raise ValueError."""
        with self.assertRaises(ValueError):
            GeneratorConfig(num_learners=0).validate()
        with self.assertRaises(ValueError):
            GeneratorConfig(num_topics=-1).validate()
        with self.assertRaises(ValueError):
            GeneratorConfig(simulation_days=0).validate()
        with self.assertRaises(ValueError):
            export_synthetic_dataset_to_csv([])


if __name__ == "__main__":
    unittest.main()
