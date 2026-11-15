
"""Unit tests for NeuroLearn runtime inference service."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from ml.core.baselines import calculate_retention
from ml.service.contracts import (
    PredictionRequestItem,
    BatchPredictionRequest,
)
from ml.service.inference import RetentionInferenceService


class TestRetentionInferenceService(unittest.TestCase):

    def setUp(self):
        # Mock the model bundle
        self.bundle = Mock()

        self.bundle.predict_proba.return_value = np.array([
            [0.20, 0.80]
        ])

        self.bundle.calibrator = SimpleNamespace(
            is_fitted_=True
        )

        # Mock model metadata
        self.metadata = SimpleNamespace(
    model_version="1.0.0"
)

        # Mock model registry
        self.registry_patcher = patch(
            "ml.service.inference.ModelRegistry"
        )

        self.MockRegistry = self.registry_patcher.start()
        self.addCleanup(self.registry_patcher.stop)

        self.registry = self.MockRegistry.return_value

        self.registry.get_active_model.return_value = (
            self.metadata
        )

        self.registry.load_bundle.return_value = (
            self.bundle
        )

        # Initialize service
        self.service = RetentionInferenceService()

        # Valid sample request
        self.request = PredictionRequestItem(
            user_id="user_1",
            topic_id="topic_1",
            elapsed_days=1.0,
            stability_days_prior=5.0,
        )

    def test_single_prediction(self):
        result = self.service.predict_one(self.request)

        self.assertAlmostEqual(
            result.predicted_retention_prob,
            0.80,
        )

        self.assertFalse(result.is_fallback)
        self.assertEqual(result.model_version, "1.0.0")

    def test_batch_prediction(self):
        # Return one probability row per input record
        self.bundle.predict_proba.side_effect = (
            lambda records: np.tile(
                [[0.20, 0.80]],
                (len(records), 1),
            )
        )

        batch_request = BatchPredictionRequest(
            items=[
                self.request,
                self.request,
            ]
        )

        result = self.service.predict_batch(
            batch_request
        )

        self.assertEqual(result.count, 2)
        self.assertEqual(len(result.predictions), 2)
        self.assertFalse(result.is_fallback)

    def test_cold_start_detection(self):
        result = self.service.predict_one(self.request)

        self.assertTrue(result.is_cold_start)

    def test_health_check(self):
        result = self.service.health_check()

        self.assertEqual(result.status, "healthy")
        self.assertTrue(result.is_calibrated)
        self.assertFalse(result.is_fallback_mode)

    def test_fallback_when_model_unavailable(self):
        self.registry.get_active_model.return_value = None

        service = RetentionInferenceService()

        result = service.predict_one(self.request)

        expected = calculate_retention(
            elapsed_days=1.0,
            stability_days=5.0,
        )

        self.assertTrue(result.is_fallback)

        self.assertAlmostEqual(
            result.predicted_retention_prob,
            expected,
        )

    def test_invalid_request_rejected(self):
        invalid_request = PredictionRequestItem(
            user_id="user_1",
            topic_id="topic_1",
            elapsed_days=-1.0,
            stability_days_prior=5.0,
        )

        with self.assertRaises(ValueError):
            self.service.predict_one(invalid_request)


if __name__ == "__main__":
    unittest.main()
