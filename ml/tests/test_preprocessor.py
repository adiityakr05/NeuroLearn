"""
Unit tests for Leakage-Free Preprocessing Pipeline.
"""

import unittest
import numpy as np

from ml.data.preprocessor import (
    TRANSFORMED_FEATURE_NAMES,
    NotFittedError,
    RetentionFeaturePreprocessor,
    extract_features_and_target,
)
from ml.data.schemas import (
    METADATA_NAMES,
    MODEL_FEATURE_NAMES,
    ROUTING_KEYS,
    TARGET_NAME,
    ReviewEventRecord,
)


class TestRetentionFeaturePreprocessor(unittest.TestCase):
    """Unit tests for feature extraction, zero data leakage, and transformation safety."""

    def setUp(self):
        # Sample training records
        self.train_records = [
            ReviewEventRecord(
                event_id="evt_001",
                user_id="user_A",
                topic_id="topic_01",
                timestamp="2026-09-01T08:00:00Z",
                elapsed_days=1.0,
                stability_days_prior=2.0,
                repetition_count_prior=1,
                topic_difficulty_prior=0.30,
                last_rating_prior=3,
                user_prior_recall_rate=0.80,
                user_prior_reviews_count=5,
                topic_prior_quiz_avg=85.0,
                has_prior_quiz=1,
                recall_success=1,
                is_synthetic=1,
            ),
            ReviewEventRecord(
                event_id="evt_002",
                user_id="user_A",
                topic_id="topic_02",
                timestamp="2026-09-02T08:00:00Z",
                elapsed_days=3.0,
                stability_days_prior=1.0,
                repetition_count_prior=0,
                topic_difficulty_prior=0.60,
                last_rating_prior=None,  # Cold start for this topic
                user_prior_recall_rate=0.75,
                user_prior_reviews_count=6,
                topic_prior_quiz_avg=None,  # No prior quiz
                has_prior_quiz=0,
                recall_success=0,
                is_synthetic=1,
            ),
            ReviewEventRecord(
                event_id="evt_003",
                user_id="user_B",
                topic_id="topic_01",
                timestamp="2026-09-02T09:00:00Z",
                elapsed_days=2.0,
                stability_days_prior=4.0,
                repetition_count_prior=2,
                topic_difficulty_prior=0.40,
                last_rating_prior=4,
                user_prior_recall_rate=0.90,
                user_prior_reviews_count=12,
                topic_prior_quiz_avg=65.0,
                has_prior_quiz=1,
                recall_success=1,
                is_synthetic=1,
            ),
        ]

    def test_unfitted_transform_raises_error(self):
        """Calling transform or transform_record before fit must raise NotFittedError."""
        preprocessor = RetentionFeaturePreprocessor()
        with self.assertRaises(NotFittedError):
            preprocessor.transform(self.train_records)
        with self.assertRaises(NotFittedError):
            preprocessor.transform_record(self.train_records[0])

    def test_feature_and_target_extraction(self):
        """extract_features_and_target extracts aligned feature list and int32 target array."""
        features, y = extract_features_and_target(self.train_records)
        self.assertEqual(len(features), len(self.train_records))
        self.assertEqual(len(y), len(self.train_records))
        self.assertIsInstance(y, np.ndarray)
        self.assertEqual(y.dtype, np.int32)
        np.testing.assert_array_equal(y, [1, 0, 1])

    def test_routing_keys_and_metadata_exclusion(self):
        """Routing keys and metadata must never appear in output features."""
        preprocessor = RetentionFeaturePreprocessor()
        preprocessor.fit(self.train_records)
        out_features = preprocessor.get_feature_names_out()

        for key in ROUTING_KEYS:
            self.assertNotIn(key, out_features)
        for meta in METADATA_NAMES:
            self.assertNotIn(meta, out_features)
        self.assertNotIn(TARGET_NAME, out_features)

        # Confirm identity invariance: Changing routing IDs does not alter output features
        rec1 = self.train_records[0]
        rec2_diff_ids = ReviewEventRecord(
            event_id="DIFFERENT_ID_999",
            user_id="DIFFERENT_USER_999",
            topic_id="DIFFERENT_TOPIC_999",
            timestamp="2026-12-31T23:59:59Z",
            elapsed_days=rec1.elapsed_days,
            stability_days_prior=rec1.stability_days_prior,
            repetition_count_prior=rec1.repetition_count_prior,
            topic_difficulty_prior=rec1.topic_difficulty_prior,
            last_rating_prior=rec1.last_rating_prior,
            user_prior_recall_rate=rec1.user_prior_recall_rate,
            user_prior_reviews_count=rec1.user_prior_reviews_count,
            topic_prior_quiz_avg=rec1.topic_prior_quiz_avg,
            has_prior_quiz=rec1.has_prior_quiz,
            recall_success=rec1.recall_success,
            is_synthetic=0,  # different metadata
        )
        vec1 = preprocessor.transform_record(rec1)
        vec2 = preprocessor.transform_record(rec2_diff_ids)
        np.testing.assert_array_almost_equal(vec1, vec2)

    def test_output_matrix_dimensions(self):
        """Transformed matrix must have exact shape (N, 11)."""
        preprocessor = RetentionFeaturePreprocessor()
        X = preprocessor.fit_transform(self.train_records)
        self.assertEqual(X.shape, (3, 11))
        self.assertEqual(len(preprocessor.get_feature_names_out()), 11)

    def test_nullable_feature_imputation_and_indicators(self):
        """
        Unscaled preprocessor tests:
        Non-null ratings in train: [3, 4] -> median = 3.5.
        Non-null quiz avgs in train: [85.0, 65.0] -> mean = 75.0.
        """
        preprocessor = RetentionFeaturePreprocessor(scale_features=False)
        preprocessor.fit(self.train_records)

        self.assertAlmostEqual(preprocessor.impute_last_rating_, 3.5)
        self.assertAlmostEqual(preprocessor.impute_quiz_avg_, 75.0)

        # Transform second record which has cold start (last_rating=None, quiz=None)
        rec2 = self.train_records[1]
        vec = preprocessor.transform_record(rec2)

        # Check imputed values
        self.assertAlmostEqual(vec[4], 3.5)   # last_rating_prior imputed to 3.5
        self.assertAlmostEqual(vec[7], 75.0)  # topic_prior_quiz_avg imputed to 75.0
        # Check indicator flags
        self.assertEqual(vec[9], 1.0)   # is_cold_start == 1.0
        self.assertEqual(vec[10], 0.0)  # has_prior_quiz == 0.0

    def test_zero_leakage_from_validation_data(self):
        """Validation data must not alter fitted imputation or scaling statistics."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        preprocessor.fit(self.train_records)

        # Record fitted parameters
        initial_impute_rating = preprocessor.impute_last_rating_
        initial_impute_quiz = preprocessor.impute_quiz_avg_
        initial_mean = preprocessor.mean_.copy()
        initial_scale = preprocessor.scale_.copy()

        # Validation record with extreme values
        val_records = [
            ReviewEventRecord(
                event_id="val_001",
                user_id="user_Val",
                topic_id="topic_99",
                timestamp="2026-10-01T08:00:00Z",
                elapsed_days=99.0,
                stability_days_prior=100.0,
                repetition_count_prior=50,
                topic_difficulty_prior=1.0,
                last_rating_prior=1,
                user_prior_recall_rate=0.10,
                user_prior_reviews_count=500,
                topic_prior_quiz_avg=10.0,
                has_prior_quiz=1,
                recall_success=0,
                is_synthetic=1,
            )
        ]

        # Transforming validation records must NOT alter fitted statistics
        preprocessor.transform(val_records)

        self.assertEqual(preprocessor.impute_last_rating_, initial_impute_rating)
        self.assertEqual(preprocessor.impute_quiz_avg_, initial_impute_quiz)
        np.testing.assert_array_equal(preprocessor.mean_, initial_mean)
        np.testing.assert_array_equal(preprocessor.scale_, initial_scale)

    def test_deterministic_transformations(self):
        """Multiple transformations of identical input produce identical output."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        preprocessor.fit(self.train_records)

        X1 = preprocessor.transform(self.train_records)
        X2 = preprocessor.transform(self.train_records)
        np.testing.assert_array_equal(X1, X2)

    def test_inference_consistency(self):
        """transform_record(r) matches transform([r])[0]."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        preprocessor.fit(self.train_records)

        single_vec = preprocessor.transform_record(self.train_records[0])
        batch_vec = preprocessor.transform([self.train_records[0]])[0]
        np.testing.assert_array_equal(single_vec, batch_vec)

    def test_finite_values_no_nans(self):
        """All transformed elements must be finite with zero NaNs or Infs."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        X = preprocessor.fit_transform(self.train_records)
        self.assertTrue(np.all(np.isfinite(X)))
        self.assertFalse(np.any(np.isnan(X)))

    def test_empty_records_handling(self):
        """fit([]) raises ValueError; transform([]) on fitted preprocessor returns (0, 11)."""
        preprocessor = RetentionFeaturePreprocessor()
        with self.assertRaises(ValueError):
            preprocessor.fit([])

        preprocessor.fit(self.train_records)
        empty_matrix = preprocessor.transform([])
        self.assertEqual(empty_matrix.shape, (0, 11))

    def test_invalid_input_validation(self):
        """Out of bounds values raise descriptive ValueError."""
        preprocessor = RetentionFeaturePreprocessor()
        preprocessor.fit(self.train_records)

        # Negative elapsed days
        with self.assertRaises(ValueError):
            preprocessor.transform([{"elapsed_days": -1.0, "stability_days_prior": 1.0, "repetition_count_prior": 0, "topic_difficulty_prior": 0.5, "user_prior_recall_rate": 0.5, "user_prior_reviews_count": 0, "has_prior_quiz": 0}])

        # Stability <= 0
        with self.assertRaises(ValueError):
            preprocessor.transform([{"elapsed_days": 1.0, "stability_days_prior": 0.0, "repetition_count_prior": 0, "topic_difficulty_prior": 0.5, "user_prior_recall_rate": 0.5, "user_prior_reviews_count": 0, "has_prior_quiz": 0}])


if __name__ == "__main__":
    unittest.main()
