"""
Retention Models, Calibration, Training Pipelines, and Model Registry for NeuroLearn ML.
"""

from ml.models.calibrator import (
    CalibrationBin,
    CalibrationReport,
    PlattCalibrator,
    compute_calibration_curve,
)
from ml.models.evaluator import (
    EvaluationMetrics,
    compute_brier_score,
    compute_log_loss,
    compute_roc_auc,
    evaluate_predictions,
)
from ml.models.registry import (
    ModelArtifactBundle,
    ModelMetadata,
    ModelRegistry,
)
from ml.models.trainer import (
    EbbinghausBaseline,
    NumpyHistGradientBoostingClassifier,
    PopulationPrevalenceBaseline,
    ScipyLogisticRegression,
    run_phase_2_4_4a_experiment,
    temporal_split,
    user_disjoint_split,
)

__all__ = [
    # Evaluator
    "EvaluationMetrics",
    "compute_brier_score",
    "compute_log_loss",
    "compute_roc_auc",
    "evaluate_predictions",
    # Calibrator
    "CalibrationBin",
    "CalibrationReport",
    "PlattCalibrator",
    "compute_calibration_curve",
    # Trainer & Models
    "temporal_split",
    "user_disjoint_split",
    "PopulationPrevalenceBaseline",
    "EbbinghausBaseline",
    "ScipyLogisticRegression",
    "NumpyHistGradientBoostingClassifier",
    "run_phase_2_4_4a_experiment",
    # Registry
    "ModelArtifactBundle",
    "ModelMetadata",
    "ModelRegistry",
]
