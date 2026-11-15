"""
Unit tests for Retention Model Training, Baselines, and Evaluation Splitters.
"""

import unittest
import numpy as np

from ml.data.preprocessor import RetentionFeaturePreprocessor, extract_features_and_target
from ml.data.schemas import ReviewEventRecord
from ml.models.trainer import (
    EbbinghausBaseline,
    NumpyHistGradientBoostingClassifier,
    PopulationPrevalenceBaseline,
    ScipyLogisticRegression,
    temporal_split,
    user_disjoint_split,
)


class TestTrainerAndModels(unittest.TestCase):
    """Verifies temporal splitting, baseline models, logistic regression, and histogram gradient boosting."""

    def setUp(self):
        # Create deterministic synthetic records with clear temporal ordering
        self.records: list[ReviewEventRecord] = []
        for i in range(100):
            day = i // 2 + 1
            hour = (i % 2) * 8 + 8
            user_idx = (i % 5) + 1  # 5 distinct users
            self.records.append(
                ReviewEventRecord(
                    event_id=f"evt_{i:03d}",
                    user_id=f"user_{user_idx}",
                    topic_id="topic_A",
                    timestamp=f"2026-09-{day:02d}T{hour:02d}:00:00Z",
                    elapsed_days=float(day * 0.5),
                    stability_days_prior=2.0 + (i % 3),
                    repetition_count_prior=i % 4,
                    topic_difficulty_prior=0.40,
                    last_rating_prior=3 if i > 0 else None,
                    user_prior_recall_rate=0.70,
                    user_prior_reviews_count=i,
                    topic_prior_quiz_avg=80.0 if i > 5 else None,
                    has_prior_quiz=1 if i > 5 else 0,
                    recall_success=1 if (i % 3 != 0) else 0,
                    is_synthetic=1,
                )
            )

    def test_temporal_split_chronological_ordering_and_disjointness(self):
        """Temporal split must maintain strict chronological ordering with zero ID overlap."""
        train, val, test, meta = temporal_split(
            self.records, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15
        )

        self.assertEqual(len(train), 70)
        self.assertEqual(len(val), 15)
        self.assertEqual(len(test), 15)
        self.assertEqual(len(train) + len(val) + len(test), 100)

        # Zero ID overlap
        train_ids = {r.event_id for r in train}
        val_ids = {r.event_id for r in val}
        test_ids = {r.event_id for r in test}
        self.assertTrue(train_ids.isdisjoint(val_ids))
        self.assertTrue(val_ids.isdisjoint(test_ids))
        self.assertTrue(train_ids.isdisjoint(test_ids))

        # Chronological boundary assertions
        self.assertLessEqual(train[-1].timestamp, val[0].timestamp)
        self.assertLessEqual(val[-1].timestamp, test[0].timestamp)
        self.assertEqual(meta["train_end_timestamp"], train[-1].timestamp)
        self.assertEqual(meta["val_start_timestamp"], val[0].timestamp)

    def test_user_disjoint_split_strict_user_isolation(self):
        """User-disjoint split must ensure no user_id appears in multiple partitions."""
        train, val, test, meta = user_disjoint_split(
            self.records, train_ratio=0.60, val_ratio=0.20, test_ratio=0.20, seed=42
        )

        train_users = {r.user_id for r in train}
        val_users = {r.user_id for r in val}
        test_users = {r.user_id for r in test}

        self.assertTrue(train_users.isdisjoint(val_users))
        self.assertTrue(val_users.isdisjoint(test_users))
        self.assertTrue(train_users.isdisjoint(test_users))
        self.assertEqual(len(train_users) + len(val_users) + len(test_users), 5)

    def test_population_prevalence_baseline(self):
        """Population baseline fits empirical training prevalence and outputs constant probabilities."""
        X_dummy = np.zeros((10, 5))
        y = np.array([1, 1, 1, 0])  # prevalence = 0.75
        model = PopulationPrevalenceBaseline()
        model.fit(X_dummy[:4], y)

        self.assertAlmostEqual(model.prevalence_, 0.75)
        probs = model.predict_proba(X_dummy)
        self.assertEqual(probs.shape, (10, 2))
        np.testing.assert_allclose(probs[:, 1], 0.75)
        np.testing.assert_allclose(probs[:, 0], 0.25)

        preds = model.predict(X_dummy)
        np.testing.assert_array_equal(preds, np.ones(10, dtype=np.int32))

    def test_ebbinghaus_baseline(self):
        """Ebbinghaus baseline generates valid exponential retention probabilities in [0, 1]."""
        model = EbbinghausBaseline()
        sub_records = self.records[:10]
        probs = model.predict_proba_from_records(sub_records)

        self.assertEqual(probs.shape, (10, 2))
        self.assertTrue(np.all(probs >= 0.0) and np.all(probs <= 1.0))
        np.testing.assert_allclose(probs.sum(axis=1), 1.0)

        # Check first record specifically
        r0 = sub_records[0]
        expected_r = np.exp(-r0.elapsed_days / r0.stability_days_prior)
        self.assertAlmostEqual(probs[0, 1], expected_r)

    def test_scipy_logistic_regression_fit_and_predict(self):
        """ScipyLogisticRegression converges and outputs valid calibrated probabilities."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        X = preprocessor.fit_transform(self.records)
        _, y = extract_features_and_target(self.records)

        model = ScipyLogisticRegression(C=1.0, max_iter=200, tol=1e-7)
        model.fit(X, y)

        self.assertTrue(model.is_fitted_)
        self.assertGreater(model.n_iter_, 0)
        self.assertEqual(model.coef_.shape, (1, 11))
        self.assertEqual(model.intercept_.shape, (1,))

        probs = model.predict_proba(X)
        self.assertEqual(probs.shape, (100, 2))
        self.assertTrue(np.all(probs >= 0.0) and np.all(probs <= 1.0))
        np.testing.assert_allclose(probs.sum(axis=1), 1.0)

        preds = model.predict(X)
        self.assertEqual(preds.shape, (100,))
        self.assertTrue(set(np.unique(preds)).issubset({0, 1}))

    def test_scipy_logistic_regression_unfitted_raises_error(self):
        """Calling predict_proba or predict on unfitted model raises RuntimeError."""
        model = ScipyLogisticRegression()
        with self.assertRaises(RuntimeError):
            model.predict_proba(np.zeros((5, 11)))

    def test_numpy_hist_gradient_boosting_fit_and_predict(self):
        """NumpyHistGradientBoostingClassifier builds trees and outputs valid probabilities."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        X = preprocessor.fit_transform(self.records)
        _, y = extract_features_and_target(self.records)

        model = NumpyHistGradientBoostingClassifier(
            max_iter=15,
            max_depth=2,
            learning_rate=0.10,
            min_samples_leaf=5,
            n_bins=16,
        )
        model.fit(X, y)

        self.assertTrue(model.is_fitted_)
        self.assertEqual(len(model.trees_), 15)
        self.assertEqual(len(model.bin_edges_), 11)

        probs = model.predict_proba(X)
        self.assertEqual(probs.shape, (100, 2))
        self.assertTrue(np.all(probs >= 0.0) and np.all(probs <= 1.0))
        np.testing.assert_allclose(probs.sum(axis=1), 1.0)

        preds = model.predict(X)
        self.assertEqual(preds.shape, (100,))
        self.assertTrue(set(np.unique(preds)).issubset({0, 1}))

    def test_numpy_hist_gradient_boosting_deterministic(self):
        """Identical inputs produce identical gradient boosting predictions."""
        preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        X = preprocessor.fit_transform(self.records)
        _, y = extract_features_and_target(self.records)

        m1 = NumpyHistGradientBoostingClassifier(max_iter=5, max_depth=2, random_state=42)
        m2 = NumpyHistGradientBoostingClassifier(max_iter=5, max_depth=2, random_state=42)

        m1.fit(X, y)
        m2.fit(X, y)

        p1 = m1.predict_proba(X)
        p2 = m2.predict_proba(X)
        np.testing.assert_array_almost_equal(p1, p2)

    def test_invalid_parameters_raise_errors(self):
        """Invalid hyperparameters and inputs must raise ValueError."""
        with self.assertRaises(ValueError):
            temporal_split([], train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
        with self.assertRaises(ValueError):
            temporal_split(self.records, train_ratio=0.5, val_ratio=0.2, test_ratio=0.1)

        with self.assertRaises(ValueError):
            ScipyLogisticRegression(C=-1.0)

        with self.assertRaises(ValueError):
            NumpyHistGradientBoostingClassifier(max_iter=0)
        with self.assertRaises(ValueError):
            NumpyHistGradientBoostingClassifier(learning_rate=-0.1)
        with self.assertRaises(ValueError):
            NumpyHistGradientBoostingClassifier(n_bins=2)


if __name__ == "__main__":
    unittest.main()
