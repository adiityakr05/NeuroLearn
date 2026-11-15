"""
Evaluation Metrics Engine for Retention Prediction.

Provides standardized, leakage-free evaluation for binary recall prediction:
- Brier Score (lower is better)
- Log Loss (lower is better, with safe clipping)
- ROC-AUC (higher is better, Wilcoxon-Mann-Whitney with tied-score handling)
- Classification Metrics: Accuracy, Precision, Recall at configurable threshold
- Cohort Descriptors: Sample counts, positive prevalence, single-class detection
"""

from dataclasses import asdict, dataclass
from typing import Any, Final, Sequence
import numpy as np
from scipy.stats import rankdata

DEFAULT_LOG_LOSS_EPS: Final[float] = 1e-15


@dataclass(frozen=True)
class EvaluationMetrics:
    """
    Standardized container for binary classification and probability calibration metrics.

    All metric directions:
    - Brier score: Lower is better (0.0 is perfect, 1.0 is complete error)
    - Log loss: Lower is better (0.0 is perfect cross-entropy)
    - ROC-AUC: Higher is better (1.0 is perfect ranking, 0.5 is random chance)
    - Accuracy: Higher is better (1.0 is perfect)
    - Precision: Higher is better
    - Recall: Higher is better
    """

    sample_count: int
    positive_count: int
    negative_count: int
    prevalence: float
    is_single_class: bool

    brier_score: float
    log_loss: float
    roc_auc: float | None

    accuracy: float
    precision: float | None
    recall: float | None
    threshold: float

    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serializes metrics to a dictionary."""
        d = asdict(self)
        d["warnings"] = list(self.warnings)
        return d


def validate_evaluation_inputs(
    y_true: np.ndarray | Sequence[int],
    y_prob: np.ndarray | Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """
    Validates input arrays for evaluation:
    - Must be non-empty 1D arrays of equal length.
    - y_true must contain only binary values (0 or 1).
    - y_prob must contain finite probabilities in [0.0, 1.0].
    """
    y_t = np.asarray(y_true, dtype=np.int32).ravel()
    y_p = np.asarray(y_prob, dtype=np.float64).ravel()

    if len(y_t) == 0:
        raise ValueError("Cannot evaluate empty target array.")
    if len(y_t) != len(y_p):
        raise ValueError(
            f"Length mismatch between y_true ({len(y_t)}) and y_prob ({len(y_p)})."
        )

    unique_vals = set(np.unique(y_t))
    if not unique_vals.issubset({0, 1}):
        raise ValueError(f"y_true must contain only binary {0, 1}, got {unique_vals}")

    if not np.all(np.isfinite(y_p)):
        raise ValueError("y_prob contains non-finite values (NaN or Inf).")

    if np.any(y_p < 0.0) or np.any(y_p > 1.0):
        raise ValueError("y_prob values must be bounded within [0.0, 1.0].")

    return y_t, y_p


def compute_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """
    Computes mean squared probability error (Brier Score):
        Brier = (1 / N) * sum((y_prob_i - y_true_i) ** 2)

    Direction: Lower is better. Range: [0.0, 1.0].
    """
    y_t, y_p = validate_evaluation_inputs(y_true, y_prob)
    return float(np.mean((y_p - y_t) ** 2))


def compute_log_loss(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    eps: float = DEFAULT_LOG_LOSS_EPS,
) -> float:
    """
    Computes binary cross-entropy (Log Loss) with safe clipping:
        LogLoss = - (1 / N) * sum(y * ln(p) + (1 - y) * ln(1 - p))

    Direction: Lower is better. Range: [0.0, inf).
    """
    y_t, y_p = validate_evaluation_inputs(y_true, y_prob)
    p_clipped = np.clip(y_p, eps, 1.0 - eps)
    loss = -np.mean(y_t * np.log(p_clipped) + (1 - y_t) * np.log(1.0 - p_clipped))
    return float(loss)


def compute_roc_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    """
    Computes Area Under the Receiver Operating Characteristic Curve (ROC-AUC)
    using the Wilcoxon-Mann-Whitney rank-sum statistic with average rank tied-score handling:
        AUC = (sum(R_pos) - N_pos * (N_pos + 1) / 2) / (N_pos * N_neg)

    Direction: Higher is better. Range: [0.0, 1.0].
    Returns None if the evaluation cohort contains only a single class (AUC is undefined).
    """
    y_t, y_p = validate_evaluation_inputs(y_true, y_prob)
    n_pos = int(np.sum(y_t == 1))
    n_neg = int(np.sum(y_t == 0))

    if n_pos == 0 or n_neg == 0:
        return None

    # Compute 1-based ranks with tied values receiving the average rank
    ranks = rankdata(y_p, method="average")
    sum_ranks_pos = float(np.sum(ranks[y_t == 1]))
    auc = (sum_ranks_pos - (n_pos * (n_pos + 1) / 2.0)) / (n_pos * n_neg)
    return float(np.clip(auc, 0.0, 1.0))


def evaluate_predictions(
    y_true: np.ndarray | Sequence[int],
    y_prob: np.ndarray | Sequence[float],
    threshold: float = 0.50,
    eps: float = DEFAULT_LOG_LOSS_EPS,
) -> EvaluationMetrics:
    """
    Comprehensive binary classification and probability evaluation.

    Args:
        y_true: Binary ground-truth labels (0 or 1).
        y_prob: Predicted recall probabilities in [0.0, 1.0].
        threshold: Decision threshold for discrete classification metrics (default 0.50).
        eps: Small epsilon for clipping log-loss probabilities.

    Returns:
        EvaluationMetrics instance containing all computed metrics, descriptors, and warnings.
    """
    if not (0.0 < threshold < 1.0):
        raise ValueError(f"threshold must be in (0.0, 1.0), got {threshold}")

    y_t, y_p = validate_evaluation_inputs(y_true, y_prob)
    n = len(y_t)
    n_pos = int(np.sum(y_t == 1))
    n_neg = int(np.sum(y_t == 0))
    prevalence = float(n_pos / n)
    is_single_class = bool(n_pos == 0 or n_neg == 0)

    warnings_list: list[str] = []

    # Probability calibration metrics
    brier = compute_brier_score(y_t, y_p)
    logloss = compute_log_loss(y_t, y_p, eps=eps)

    # Ranking metric
    if is_single_class:
        roc_auc = None
        warnings_list.append(
            f"ROC-AUC is undefined because cohort contains only class {1 if n_neg == 0 else 0}."
        )
    else:
        roc_auc = compute_roc_auc(y_t, y_p)

    # Discrete classification metrics
    y_pred = (y_p >= threshold).astype(np.int32)
    tp = int(np.sum((y_pred == 1) & (y_t == 1)))
    fp = int(np.sum((y_pred == 1) & (y_t == 0)))
    tn = int(np.sum((y_pred == 0) & (y_t == 0)))
    fn = int(np.sum((y_pred == 0) & (y_t == 1)))

    accuracy = float((tp + tn) / n)

    if (tp + fp) == 0:
        precision = None
        warnings_list.append("Precision is undefined because zero positive predictions were made.")
    else:
        precision = float(tp / (tp + fp))

    if (tp + fn) == 0:
        recall = None
        warnings_list.append("Recall is undefined because zero positive ground-truth samples exist.")
    else:
        recall = float(tp / (tp + fn))

    return EvaluationMetrics(
        sample_count=n,
        positive_count=n_pos,
        negative_count=n_neg,
        prevalence=prevalence,
        is_single_class=is_single_class,
        brier_score=brier,
        log_loss=logloss,
        roc_auc=roc_auc,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        threshold=threshold,
        warnings=tuple(warnings_list),
    )
