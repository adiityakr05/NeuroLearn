"""
Unit tests for Model Registry, Safe JSON Serialization, and Model Promotion.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

from ml.data.preprocessor import RetentionFeaturePreprocessor
from ml.data.schemas import ReviewEventRecord
from ml.models.calibrator import PlattCalibrator
from ml.models.registry import (
    ModelArtifactBundle,
    ModelMetadata,
    ModelRegistry,
)
from ml.models.trainer import (
    NumpyHistGradientBoostingClassifier,
    ScipyLogisticRegression,
)


class TestModelRegistry(unittest.TestCase):
    """Verifies safe JSON persistence, round-trip numerical equality, version uniqueness, and promotion."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(registry_dir=self.temp_dir)

        # Create small synthetic records
        self.records: list[ReviewEventRecord] = []
        for i in range(40):
            self.records.append(
                ReviewEventRecord(
                    event_id=f"evt_{i:03d}",
                    user_id=f"u_{i % 3}",
                    topic_id="topic_1",
                    timestamp="2026-09-01T08:00:00Z",
                    elapsed_days=float(i * 0.2 + 0.1),
                    stability_days_prior=1.5 + (i % 2),
                    repetition_count_prior=i % 3,
                    topic_difficulty_prior=0.35,
                    last_rating_prior=3 if i > 0 else None,
                    user_prior_recall_rate=0.75,
                    user_prior_reviews_count=i,
                    topic_prior_quiz_avg=82.0 if i > 2 else None,
                    has_prior_quiz=1 if i > 2 else 0,
                    recall_success=1 if (i % 2 == 0) else 0,
                    is_synthetic=1,
                )
            )

        self.preprocessor = RetentionFeaturePreprocessor(scale_features=True)
        self.X = self.preprocessor.fit_transform(self.records)
        self.y = np.array([r.recall_success for r in self.records], dtype=int)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_version_uniqueness_prevents_overwriting(self):
        """Attempting to register an already existing (model_name, model_version) raises ValueError."""
        lr = ScipyLogisticRegression(C=1.0).fit(self.X, self.y)
        bundle = ModelArtifactBundle(
            model_name="retention_lr",
            model_version="1.0.0",
            model_type="ScipyLogisticRegression",
            preprocessor=self.preprocessor,
            model=lr,
            calibrator=None,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:00:00Z",
            validation_metrics={"brier_score": 0.12},
        )

        self.registry.register_model(bundle)

        # Second registration with identical version must fail
        with self.assertRaises(ValueError):
            self.registry.register_model(bundle)

    def test_round_trip_logistic_regression_numerical_equivalence(self):
        """Saved and loaded Logistic Regression model produces numerically identical predictions."""
        lr = ScipyLogisticRegression(C=0.5).fit(self.X, self.y)
        calibrator = PlattCalibrator().fit(lr.predict_proba(self.X)[:, 1], self.y)

        bundle = ModelArtifactBundle(
            model_name="retention_lr",
            model_version="1.0.0",
            model_type="ScipyLogisticRegression",
            preprocessor=self.preprocessor,
            model=lr,
            calibrator=calibrator,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:00:00Z",
            validation_metrics={"brier_score": 0.14, "log_loss": 0.45},
            test_metrics={"brier_score": 0.13},
        )

        orig_preds = bundle.predict_proba(self.records)
        self.registry.register_model(bundle)

        loaded_bundle = self.registry.load_bundle("retention_lr", "1.0.0")
        loaded_preds = loaded_bundle.predict_proba(self.records)

        # Exact numerical equivalence
        np.testing.assert_allclose(orig_preds, loaded_preds, rtol=1e-12, atol=1e-12)

    def test_round_trip_gradient_boosting_numerical_equivalence(self):
        """Saved and loaded Histogram Gradient Boosting model produces numerically identical predictions."""
        gb = NumpyHistGradientBoostingClassifier(max_iter=5, max_depth=2).fit(self.X, self.y)
        calibrator = PlattCalibrator().fit(gb.predict_proba(self.X)[:, 1], self.y)

        bundle = ModelArtifactBundle(
            model_name="retention_gbdt",
            model_version="1.0.0",
            model_type="NumpyHistGradientBoostingClassifier",
            preprocessor=self.preprocessor,
            model=gb,
            calibrator=calibrator,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:00:00Z",
            validation_metrics={"brier_score": 0.08, "log_loss": 0.32},
        )

        orig_preds = bundle.predict_proba(self.records)
        self.registry.register_model(bundle)

        loaded_bundle = self.registry.load_bundle("retention_gbdt", "1.0.0")
        loaded_preds = loaded_bundle.predict_proba(self.records)

        # Exact numerical equivalence
        np.testing.assert_allclose(orig_preds, loaded_preds, rtol=1e-12, atol=1e-12)

    def test_active_model_selection_and_promotion(self):
        """Setting active model promotes specified version and archives prior active version."""
        lr1 = ScipyLogisticRegression(C=1.0).fit(self.X, self.y)
        lr2 = ScipyLogisticRegression(C=0.1).fit(self.X, self.y)

        b1 = ModelArtifactBundle(
            model_name="retention_lr",
            model_version="1.0.0",
            model_type="ScipyLogisticRegression",
            preprocessor=self.preprocessor,
            model=lr1,
            calibrator=None,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:00:00Z",
            validation_metrics={"brier_score": 0.15, "log_loss": 0.50},
        )
        b2 = ModelArtifactBundle(
            model_name="retention_lr",
            model_version="1.1.0",
            model_type="ScipyLogisticRegression",
            preprocessor=self.preprocessor,
            model=lr2,
            calibrator=None,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:30:00Z",
            validation_metrics={"brier_score": 0.11, "log_loss": 0.42},
        )

        self.registry.register_model(b1, status="active")
        self.registry.register_model(b2, status="candidate")

        active_meta = self.registry.get_active_model("retention_lr")
        self.assertEqual(active_meta.model_version, "1.0.0")

        # Promote 1.1.0
        self.registry.set_active_model("retention_lr", "1.1.0")

        active_new = self.registry.get_active_model("retention_lr")
        self.assertEqual(active_new.model_version, "1.1.0")

        v1_meta = self.registry.get_model_metadata("retention_lr", "1.0.0")
        self.assertEqual(v1_meta.status, "archived")

    def test_deterministic_best_model_promotion(self):
        """select_and_promote_best_model deterministically promotes the lowest validation Brier score model."""
        lr = ScipyLogisticRegression(C=1.0).fit(self.X, self.y)
        gb = NumpyHistGradientBoostingClassifier(max_iter=5).fit(self.X, self.y)

        b_lr = ModelArtifactBundle(
            model_name="retention_models",
            model_version="1.0.0",
            model_type="ScipyLogisticRegression",
            preprocessor=self.preprocessor,
            model=lr,
            calibrator=None,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:00:00Z",
            validation_metrics={"brier_score": 0.15, "log_loss": 0.50},
        )
        b_gb = ModelArtifactBundle(
            model_name="retention_models",
            model_version="1.1.0",
            model_type="NumpyHistGradientBoostingClassifier",
            preprocessor=self.preprocessor,
            model=gb,
            calibrator=None,
            training_dataset_id="test_ds",
            training_timestamp="2026-11-14T10:30:00Z",
            validation_metrics={"brier_score": 0.07, "log_loss": 0.28},
        )

        self.registry.register_model(b_lr)
        self.registry.register_model(b_gb)

        promoted = self.registry.select_and_promote_best_model("retention_models", metric="brier_score")
        self.assertEqual(promoted.model_version, "1.1.0")
        self.assertEqual(promoted.model_type, "NumpyHistGradientBoostingClassifier")
        self.assertEqual(promoted.status, "active")

    def test_missing_or_corrupted_artifact_raises_error(self):
        """Attempting to load a nonexistent model or corrupt artifact raises proper exception."""
        with self.assertRaises(KeyError):
            self.registry.load_bundle("nonexistent_model")

        # Manually alter artifact path in index to non-existent
        index_data = self.registry._load_index()
        index_data["models"].append({
            "model_name": "corrupt_model",
            "model_version": "1.0.0",
            "model_type": "ScipyLogisticRegression",
            "created_at": "2026-11-14T10:00:00Z",
            "dataset_id": "ds",
            "is_synthetic": True,
            "is_calibrated": False,
            "status": "candidate",
            "brier_score_val": 0.2,
            "log_loss_val": 0.5,
            "roc_auc_val": 0.8,
            "artifact_path": str(Path(self.temp_dir) / "does_not_exist.json"),
        })
        self.registry._save_index(index_data)

        with self.assertRaises(FileNotFoundError):
            self.registry.load_bundle("corrupt_model", "1.0.0")


if __name__ == "__main__":
    unittest.main()
