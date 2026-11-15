"""
Unit tests for Platt Scaling Calibrator and Calibration Curve / ECE Evaluation.
"""

import unittest
import numpy as np

from ml.models.calibrator import (
    CalibrationReport,
    PlattCalibrator,
    compute_calibration_curve,
)


class TestPlattCalibrator(unittest.TestCase):
    """Verifies Platt scaling mathematics, monotonicity, single-class safeguards, and ECE calculation."""

    def setUp(self):
        # Deterministic sample dataset: overconfident raw probabilities
        np.random.seed(42)
        self.raw_probs = np.array([0.05, 0.15, 0.30, 0.45, 0.60, 0.75, 0.85, 0.95] * 10)
        # Ground truth where true probability is roughly p * 0.8
        self.targets = (np.random.rand(len(self.raw_probs)) < (self.raw_probs * 0.8)).astype(int)

    def test_platt_fitting_and_monotonicity(self):
        """Platt calibrator fits strictly positive slope A and preserves monotonic order."""
        calibrator = PlattCalibrator()
        calibrator.fit(self.raw_probs, self.targets)

        self.assertTrue(calibrator.is_fitted_)
        self.assertGreaterEqual(calibrator.A_, 0.0)
        self.assertIsNotNone(calibrator.B_)

        # Monotonicity test
        test_inputs = np.linspace(0.01, 0.99, 50)
        calibrated = calibrator.transform(test_inputs)

        # All values bounded in (0, 1)
        self.assertTrue(np.all(calibrated >= 0.0) and np.all(calibrated <= 1.0))
        # Strictly non-decreasing
        self.assertTrue(np.all(np.diff(calibrated) >= 0.0))

    def test_predict_proba_dimensions_and_sum(self):
        """predict_proba outputs (N, 2) array where columns sum to 1.0."""
        calibrator = PlattCalibrator()
        calibrator.fit(self.raw_probs, self.targets)

        probs_2d = calibrator.predict_proba(self.raw_probs[:5])
        self.assertEqual(probs_2d.shape, (5, 2))
        np.testing.assert_allclose(probs_2d.sum(axis=1), 1.0)
        np.testing.assert_allclose(probs_2d[:, 1], calibrator.transform(self.raw_probs[:5]))

    def test_single_class_safeguard(self):
        """When validation cohort contains only single class, calibrator defaults to identity pass-through."""
        calibrator = PlattCalibrator()
        all_ones = np.ones(20, dtype=int)
        calibrator.fit(np.linspace(0.1, 0.9, 20), all_ones)

        self.assertTrue(calibrator.is_fitted_)
        self.assertEqual(calibrator.A_, 1.0)
        self.assertEqual(calibrator.B_, 0.0)
        self.assertTrue(len(calibrator.warnings_) > 0)

        # Passes through original logits
        test_p = np.array([0.2, 0.5, 0.8])
        transformed = calibrator.transform(test_p)
        np.testing.assert_allclose(test_p, transformed, atol=1e-5)

    def test_unfitted_transform_raises_error(self):
        """Calling transform before fit raises RuntimeError."""
        calibrator = PlattCalibrator()
        with self.assertRaises(RuntimeError):
            calibrator.transform([0.5])

    def test_to_and_from_dict_serialization(self):
        """PlattCalibrator serializes to dict and reconstructs with identical parameters and predictions."""
        calibrator = PlattCalibrator()
        calibrator.fit(self.raw_probs, self.targets)

        d = calibrator.to_dict()
        reconstructed = PlattCalibrator.from_dict(d)

        self.assertTrue(reconstructed.is_fitted_)
        self.assertEqual(calibrator.A_, reconstructed.A_)
        self.assertEqual(calibrator.B_, reconstructed.B_)

        preds_orig = calibrator.transform(self.raw_probs[:10])
        preds_recon = reconstructed.transform(self.raw_probs[:10])
        np.testing.assert_array_equal(preds_orig, preds_recon)

    def test_calibration_curve_and_ece(self):
        """compute_calibration_curve computes ECE and correctly handles empty bins."""
        y_true = np.array([0, 0, 0, 1, 1, 1, 1])
        y_prob = np.array([0.05, 0.15, 0.25, 0.75, 0.85, 0.90, 0.95])

        report = compute_calibration_curve(y_true, y_prob, n_bins=10)

        self.assertIsInstance(report, CalibrationReport)
        self.assertEqual(report.n_bins, 10)
        self.assertEqual(report.sample_count, 7)
        self.assertGreaterEqual(report.expected_calibration_error, 0.0)
        self.assertLessEqual(report.expected_calibration_error, 1.0)

        # Check empty bin handling: bins in middle (e.g. [0.4, 0.5)) have count = 0
        empty_bins = [b for b in report.bins if b.is_empty]
        self.assertGreater(len(empty_bins), 0)
        for eb in empty_bins:
            self.assertEqual(eb.sample_count, 0)
            self.assertIsNone(eb.mean_predicted_prob)
            self.assertIsNone(eb.observed_frequency)

    def test_invalid_inputs_raise_errors(self):
        """Invalid arrays must raise descriptive ValueError."""
        calibrator = PlattCalibrator()
        with self.assertRaises(ValueError):
            calibrator.fit([], [])
        with self.assertRaises(ValueError):
            calibrator.fit([0.5], [1, 0])
        with self.assertRaises(ValueError):
            calibrator.fit([1.5], [1])
        with self.assertRaises(ValueError):
            calibrator.fit([0.5], [2])


if __name__ == "__main__":
    unittest.main()
