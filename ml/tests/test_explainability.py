"""Unit tests for NeuroLearn retention explainability service."""

import unittest
from types import SimpleNamespace

import numpy as np
from ml.data.schemas import ReviewEventRecord

from ml.data.preprocessor import (
    RetentionFeaturePreprocessor,
    extract_features_and_target,
)
from ml.models.trainer import (
    ScipyLogisticRegression,
    NumpyHistGradientBoostingClassifier,
)
from ml.service.contracts import PredictionRequestItem
from ml.service.explainability import RetentionExplainabilityService
from ml.service.inference import RetentionInferenceService
from ml.models.registry import ModelArtifactBundle
from ml.models.calibrator import PlattCalibrator


class TestRetentionExplainabilityService(unittest.TestCase):

    def setUp(self):
        self.request = PredictionRequestItem(
            user_id="user_1",
            topic_id="topic_1",
            elapsed_days=1.0,
            stability_days_prior=5.0,
            repetition_count_prior=2,
            topic_difficulty_prior=0.4,
            last_rating_prior=3,
            user_prior_recall_rate=0.7,
            user_prior_reviews_count=10,
            topic_prior_quiz_avg=80.0,
            has_prior_quiz=1,
        )

        self.inference_service = RetentionInferenceService.__new__(
            RetentionInferenceService
        )

        self.inference_service.is_fallback_mode = True
        self.inference_service.fallback_reason = "Test fallback"

        self.inference_service.model_name = "test_model"
        self.inference_service.model_metadata = SimpleNamespace(
            model_version="1.0.0"
        )

        self.inference_service.model_bundle = None

        self.service = RetentionExplainabilityService(
            self.inference_service
        )
    def _build_training_records(self):
        records = []

        for i in range(100):
            day = i // 2 + 1
            hour = (i % 2) * 8 + 8

            records.append(
                ReviewEventRecord(
                    event_id=f"evt_{i:03d}",
                    user_id=f"user_{(i % 5) + 1}",
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

        return records
    def _build_logistic_service(self):
        records = self._build_training_records()

        preprocessor = RetentionFeaturePreprocessor(
            scale_features=True
        )
        X = preprocessor.fit_transform(records)

        _, y = extract_features_and_target(records)

        model = ScipyLogisticRegression(
            C=1.0,
            max_iter=200,
            tol=1e-7,
        )
        model.fit(X, y)

        bundle = ModelArtifactBundle(
            model_name="test_logistic",
            model_version="1.0.0",
            model_type="logistic_regression",
            preprocessor=preprocessor,
            model=model,
            calibrator=None,
            training_dataset_id="test_dataset",
            training_timestamp="2026-11-17T00:00:00Z",
            validation_metrics={},
        )

        inference = RetentionInferenceService.__new__(
            RetentionInferenceService
        )
        inference.is_fallback_mode = False
        inference.fallback_reason = None
        inference.model_name = "test_logistic"
        inference.model_metadata = SimpleNamespace(
            model_version="1.0.0"
        )
        inference.model_bundle = bundle

        return RetentionExplainabilityService(inference)
    def test_ebbinghaus_fallback_explanation(self):
        explanation = self.service.explain_one(self.request)

        expected_probability = np.exp(
            -self.request.elapsed_days
            / self.request.stability_days_prior
        )

        self.assertEqual(
            explanation["explanation_type"],
            "ebbinghaus_baseline",
        )

        self.assertTrue(explanation["is_fallback"])

        self.assertAlmostEqual(
            explanation["predicted_retention_probability"],
            expected_probability,
        )

        self.assertEqual(
            explanation["user_id"],
            "user_1",
        )

        self.assertEqual(
            explanation["topic_id"],
            "topic_1",
        )
    def test_logistic_regression_explanation(self):
        service = self._build_logistic_service()

        explanation = service.explain_one(self.request)

        self.assertEqual(
            explanation["explanation_type"],
            "logistic_regression",
        )

        self.assertFalse(explanation["is_fallback"])

        contributions = explanation["feature_contributions"]

        self.assertEqual(len(contributions), 11)

        reconstructed_log_odds = (
            explanation["intercept"]
            + sum(
                item["log_odds_contribution"]
                for item in contributions
            )
        )

        self.assertAlmostEqual(
            reconstructed_log_odds,
            explanation["raw_log_odds"],
            places=7,
        )

        self.assertAlmostEqual(
            explanation["predicted_retention_probability"],
            explanation["raw_probability"],
            places=7,
        )

        self.assertEqual(
            explanation["contribution_scale"],
            "raw_log_odds",
        )
    def _build_gradient_boosting_service(self):
        records = self._build_training_records()

        preprocessor = RetentionFeaturePreprocessor(
            scale_features=True
        )
        X = preprocessor.fit_transform(records)

        _, y = extract_features_and_target(records)

        model = NumpyHistGradientBoostingClassifier(
            max_iter=15,
            max_depth=2,
            learning_rate=0.10,
            min_samples_leaf=5,
            n_bins=16,
        )
        model.fit(X, y)

        bundle = ModelArtifactBundle(
            model_name="test_gradient_boosting",
            model_version="1.0.0",
            model_type="hist_gradient_boosting",
            preprocessor=preprocessor,
            model=model,
            calibrator=None,
            training_dataset_id="test_dataset",
            training_timestamp="2026-11-17T00:00:00Z",
            validation_metrics={},
        )

        inference = RetentionInferenceService.__new__(
            RetentionInferenceService
        )
        inference.is_fallback_mode = False
        inference.fallback_reason = None
        inference.model_name = "test_gradient_boosting"
        inference.model_metadata = SimpleNamespace(
            model_version="1.0.0"
        )
        inference.model_bundle = bundle

        return RetentionExplainabilityService(inference)

    def test_gradient_boosting_explanation(self):
        service = self._build_gradient_boosting_service()

        explanation = service.explain_one(self.request)

        model = service.inference_service.model_bundle.model
        preprocessor = service.inference_service.model_bundle.preprocessor

        transformed = preprocessor.transform(
            [self.request.to_feature_dict()]
        )

        expected_probability = model.predict_proba(transformed)[0, 1]

        self.assertEqual(
            explanation["explanation_type"],
            "gradient_boosting_tree_paths",
        )

        self.assertFalse(explanation["is_fallback"])

        self.assertEqual(
            explanation["tree_count"],
            len(model.trees_),
        )

        self.assertEqual(
            len(explanation["tree_paths"]),
            len(model.trees_),
        )

        self.assertAlmostEqual(
            explanation["raw_probability"],
            expected_probability,
            places=7,
        )

        self.assertAlmostEqual(
            explanation["predicted_retention_probability"],
            expected_probability,
            places=7,
        )
    def test_logistic_calibration_explanation(self):
        service = self._build_logistic_service()

        calibrator = PlattCalibrator()
        calibrator.fit(
            np.array([0.10, 0.20, 0.30, 0.70, 0.80, 0.90]),
            np.array([0, 0, 1, 0, 1, 1]),
        )

        bundle = service.inference_service.model_bundle
        bundle.calibrator = calibrator

        explanation = service.explain_one(self.request)

        self.assertTrue(explanation["is_calibrated"])

        self.assertAlmostEqual(
            explanation["calibrated_probability"],
            explanation["predicted_retention_probability"],
            places=7,
        )

        self.assertAlmostEqual(
            explanation["calibrated_probability"],
            float(
                calibrator.transform(
                    np.array([explanation["raw_probability"]])
                )[0]
            ),
            places=7,
        )

        self.assertEqual(
            explanation["contribution_scale"],
            "raw_log_odds",
        )

        self.assertNotIn(
            "calibration_parameters",
            explanation,
        )