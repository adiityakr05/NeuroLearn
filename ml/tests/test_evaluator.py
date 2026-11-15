"""
Unit tests for the Retention Evaluation Metrics Engine.
"""

import math
import unittest
import numpy as np

from ml.models.evaluator import (
    EvaluationMetrics,
    compute_brier_score,
    compute_log_loss,
    compute_roc_auc,
    evaluate_predictions,
)


class TestEvaluatorMetrics(unittest.TestCase):
    """Verifies mathematical correctness, tied-score handling, and safeguards of the evaluation engine."""

    def test_brier_score_known_values(self):
        """Verifies exact Brier score calculation against analytical targets."""
        # Perfect predictions -> 0.0
        self.assertAlmostEqual(compute_brier_score([1, 0], [1.0, 0.0]), 0.0)
        # Inverted predictions -> 1.0
        self.assertAlmostEqual(compute_brier_score([1, 0], [0.0, 1.0]), 1.0)
        # Midpoint predictions -> 0.25
        self.assertAlmostEqual(compute_brier_score([1, 1], [0.5, 0.5]), 0.25)
        # Known float vector: (0.8-1)^2 + (0.2-0)^2 = 0.04 + 0.04 = 0.08 / 2 = 0.04
        self.assertAlmostEqual(compute_brier_score([1, 0], [0.8, 0.2]), 0.04)

    def test_log_loss_known_values(self):
        """Verifies log-loss calculations against analytical targets."""
        # 50/50 prediction on [1, 0] -> -ln(0.5) ~ 0.693147
        expected = -math.log(0.5)
        self.assertAlmostEqual(compute_log_loss([1, 0], [0.5, 0.5]), expected, places=5)

        # Near perfect prediction clamped to eps -> near 0.0
        loss_perf = compute_log_loss([1, 0], [1.0, 0.0])
        self.assertLess(loss_perf, 1e-10)

    def test_roc_auc_known_values_and_ties(self):
        """Verifies ROC-AUC across perfect, inverted, tied, and partial rankings."""
        # Perfect separation -> 1.0
        self.assertAlmostEqual(
            compute_roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0
        )
        # Complete inversion -> 0.0
        self.assertAlmostEqual(
            compute_roc_auc([0, 0, 1, 1], [0.8, 0.9, 0.1, 0.2]), 0.0
        )
        # Tied probabilities -> 0.5
        self.assertAlmostEqual(
            compute_roc_auc([0, 1], [0.5, 0.5]), 0.5
        )
        # Mixed ranking with tied pairs:
        # y = [0, 0, 1, 1], p = [0.2, 0.5, 0.5, 0.8]
        # ranks: 1, 2.5, 2.5, 4. Pos ranks: 2.5 + 4 = 6.5.
        # AUC = (6.5 - 2*3/2) / (2*2) = (6.5 - 3) / 4 = 3.5 / 4 = 0.875
        self.assertAlmostEqual(
            compute_roc_auc([0, 0, 1, 1], [0.2, 0.5, 0.5, 0.8]), 0.875
        )

    def test_roc_auc_single_class_safeguard(self):
        """ROC-AUC must return None when cohort contains only positive or only negative samples."""
        self.assertIsNone(compute_roc_auc([1, 1, 1], [0.2, 0.5, 0.8]))
        self.assertIsNone(compute_roc_auc([0, 0, 0, 0], [0.1, 0.4, 0.6, 0.9]))

        # evaluate_predictions must flag is_single_class and record warning
        res = evaluate_predictions([1, 1, 1], [0.2, 0.5, 0.8])
        self.assertTrue(res.is_single_class)
        self.assertIsNone(res.roc_auc)
        self.assertTrue(any("undefined" in w.lower() for w in res.warnings))

    def test_discrete_classification_metrics(self):
        """Verifies accuracy, precision, and recall at decision threshold."""
        # y = [1, 0, 1, 0], p = [0.8, 0.2, 0.3, 0.1], threshold = 0.5
        # preds = [1, 0, 0, 0] -> TP=1, FP=0, TN=2, FN=1
        metrics = evaluate_predictions([1, 0, 1, 0], [0.8, 0.2, 0.3, 0.1], threshold=0.5)
        self.assertAlmostEqual(metrics.accuracy, 0.75)
        self.assertAlmostEqual(metrics.precision, 1.0)
        self.assertAlmostEqual(metrics.recall, 0.50)
        self.assertEqual(metrics.positive_count, 2)
        self.assertEqual(metrics.negative_count, 2)
        self.assertAlmostEqual(metrics.prevalence, 0.50)

    def test_zero_positive_predictions_precision_safeguard(self):
        """When TP + FP == 0, precision must safely return None with an explicit warning."""
        metrics = evaluate_predictions([1, 0, 1], [0.1, 0.2, 0.3], threshold=0.5)
        self.assertIsNone(metrics.precision)
        self.assertTrue(any("precision is undefined" in w.lower() for w in metrics.warnings))

    def test_invalid_evaluation_inputs_raise_errors(self):
        """Invalid arrays must raise descriptive ValueError."""
        # Empty array
        with self.assertRaises(ValueError):
            compute_brier_score([], [])

        # Length mismatch
        with self.assertRaises(ValueError):
            compute_brier_score([1, 0], [0.5])

        # Non-binary y_true
        with self.assertRaises(ValueError):
            compute_brier_score([1, 2], [0.5, 0.5])

        # Out of bounds y_prob
        with self.assertRaises(ValueError):
            compute_brier_score([1, 0], [1.5, 0.5])
        with self.assertRaises(ValueError):
            compute_brier_score([1, 0], [-0.1, 0.5])

        # Non-finite y_prob
        with self.assertRaises(ValueError):
            compute_brier_score([1, 0], [np.nan, 0.5])
        with self.assertRaises(ValueError):
            compute_brier_score([1, 0], [np.inf, 0.5])

        # Invalid threshold
        with self.assertRaises(ValueError):
            evaluate_predictions([1, 0], [0.8, 0.2], threshold=1.0)
        with self.assertRaises(ValueError):
            evaluate_predictions([1, 0], [0.8, 0.2], threshold=0.0)


if __name__ == "__main__":
    unittest.main()
