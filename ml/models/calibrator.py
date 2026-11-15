"""
Probability Calibration and Reliability Evaluation for Retention Models.

Implements Platt scaling calibration and reliability curve / ECE computation
using only NumPy and SciPy.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Final, Sequence
import numpy as np
from scipy.optimize import minimize

DEFAULT_CALIBRATOR_EPS: Final[float] = 1e-12


def _stable_sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid calculation preventing overflow/underflow."""
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


@dataclass(frozen=True)
class CalibrationBin:
    """Statistics for an individual probability reliability bin."""
    bin_index: int
    bin_lower: float
    bin_upper: float
    sample_count: int
    mean_predicted_prob: float | None
    observed_frequency: float | None
    is_empty: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationReport:
    """Comprehensive calibration and reliability diagram summary."""
    n_bins: int
    sample_count: int
    expected_calibration_error: float
    max_calibration_error: float
    brier_score: float
    bins: tuple[CalibrationBin, ...]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bins"] = [b.to_dict() for b in self.bins]
        return d


def compute_calibration_curve(
    y_true: np.ndarray | Sequence[int],
    y_prob: np.ndarray | Sequence[float],
    n_bins: int = 10,
) -> CalibrationReport:
    """
    Computes empirical reliability bins and Expected Calibration Error (ECE):
        ECE = sum_b (N_b / N) * |mean_prob_b - observed_freq_b|

    Args:
        y_true: Binary ground truth labels (0 or 1).
        y_prob: Predicted recall probabilities in [0.0, 1.0].
        n_bins: Number of equal-width probability intervals (default 10).

    Returns:
        CalibrationReport containing ECE, MCE, and per-bin statistics.

    Raises:
        ValueError: If inputs are invalid or n_bins < 2.
    """
    if n_bins < 2:
        raise ValueError(f"n_bins must be >= 2, got {n_bins}")

    y_t = np.asarray(y_true, dtype=np.int32).ravel()
    y_p = np.asarray(y_prob, dtype=np.float64).ravel()

    if len(y_t) == 0:
        raise ValueError("Cannot compute calibration curve on empty inputs.")
    if len(y_t) != len(y_p):
        raise ValueError(f"Length mismatch between y_true ({len(y_t)}) and y_prob ({len(y_p)}).")
    if not set(np.unique(y_t)).issubset({0, 1}):
        raise ValueError(f"y_true must contain only binary {0, 1}")
    if np.any(y_p < 0.0) or np.any(y_p > 1.0) or not np.all(np.isfinite(y_p)):
        raise ValueError("y_prob must be bounded in [0.0, 1.0] and finite.")

    n_total = len(y_t)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins_list: list[CalibrationBin] = []

    weighted_calibration_error = 0.0
    max_calibration_error = 0.0

    for b in range(n_bins):
        lower = float(bin_edges[b])
        upper = float(bin_edges[b + 1])

        # Last bin includes the upper edge 1.0
        if b == n_bins - 1:
            mask = (y_p >= lower) & (y_p <= upper)
        else:
            mask = (y_p >= lower) & (y_p < upper)

        count = int(np.sum(mask))
        if count > 0:
            mean_p = float(np.mean(y_p[mask]))
            obs_f = float(np.mean(y_t[mask]))
            err = abs(mean_p - obs_f)
            weighted_calibration_error += (count / n_total) * err
            if err > max_calibration_error:
                max_calibration_error = err
            bins_list.append(
                CalibrationBin(
                    bin_index=b,
                    bin_lower=lower,
                    bin_upper=upper,
                    sample_count=count,
                    mean_predicted_prob=mean_p,
                    observed_frequency=obs_f,
                    is_empty=False,
                )
            )
        else:
            bins_list.append(
                CalibrationBin(
                    bin_index=b,
                    bin_lower=lower,
                    bin_upper=upper,
                    sample_count=0,
                    mean_predicted_prob=None,
                    observed_frequency=None,
                    is_empty=True,
                )
            )

    brier = float(np.mean((y_p - y_t) ** 2))

    return CalibrationReport(
        n_bins=n_bins,
        sample_count=n_total,
        expected_calibration_error=float(weighted_calibration_error),
        max_calibration_error=float(max_calibration_error),
        brier_score=brier,
        bins=tuple(bins_list),
    )


class PlattCalibrator:
    """
    Platt Scaling Calibrator (Platt, 1999).

    Transforms uncalibrated probabilities into calibrated probabilities via scalar
    logistic regression over raw log-odds (logits):
        s = logit(clip(p, eps, 1 - eps))
        P_calibrated = sigmoid(A * s + B)

    Guarantees:
    - Fits exclusively on validation predictions and validation targets.
    - Utilizes target smoothing (Platt's Bayesian prior) to prevent overfitting.
    - Enforces monotonicity (A >= 0).
    - Safely handles single-class cohorts with identity pass-through (A=1.0, B=0.0).
    - Fully serializable to/from JSON dictionary.
    """

    def __init__(self, eps: float = DEFAULT_CALIBRATOR_EPS) -> None:
        self.eps = eps
        self.A_: float | None = None
        self.B_: float | None = None
        self.is_fitted_: bool = False
        self.warnings_: list[str] = []

    def fit(
        self,
        y_val_probs: np.ndarray | Sequence[float],
        y_val_targets: np.ndarray | Sequence[int],
    ) -> "PlattCalibrator":
        """
        Fits calibration parameters A and B strictly on validation predictions and targets.

        Args:
            y_val_probs: Uncalibrated predicted probabilities on validation set.
            y_val_targets: Ground truth binary outcomes on validation set.

        Returns:
            self: Fitted PlattCalibrator instance.
        """
        p_arr = np.asarray(y_val_probs, dtype=np.float64).ravel()
        y_arr = np.asarray(y_val_targets, dtype=np.int32).ravel()

        if len(p_arr) == 0:
            raise ValueError("Cannot fit calibrator on empty predictions.")
        if len(p_arr) != len(y_arr):
            raise ValueError(f"Length mismatch: {len(p_arr)} probs vs {len(y_arr)} targets.")
        if not set(np.unique(y_arr)).issubset({0, 1}):
            raise ValueError(f"y_val_targets must be binary {0, 1}")
        if np.any(p_arr < 0.0) or np.any(p_arr > 1.0) or not np.all(np.isfinite(p_arr)):
            raise ValueError("y_val_probs must be in [0.0, 1.0] and finite.")

        n_samples = len(y_arr)
        n_pos = int(np.sum(y_arr == 1))
        n_neg = int(np.sum(y_arr == 0))

        # Single-class safeguard: if validation cohort lacks one class, cannot fit slope
        if n_pos == 0 or n_neg == 0:
            self.warnings_.append(
                "Single-class validation cohort detected. Platt scaling defaulted to identity (A=1.0, B=0.0)."
            )
            self.A_ = 1.0
            self.B_ = 0.0
            self.is_fitted_ = True
            return self

        # Platt target smoothing:
        # t_pos = (N_pos + 1) / (N_pos + 2), t_neg = 1 / (N_neg + 2)
        t_pos = (n_pos + 1.0) / (n_pos + 2.0)
        t_neg = 1.0 / (n_neg + 2.0)
        target_smoothed = np.where(y_arr == 1, t_pos, t_neg)

        # Logit transformation of raw probabilities
        p_clipped = np.clip(p_arr, self.eps, 1.0 - self.eps)
        s = np.log(p_clipped / (1.0 - p_clipped))

        def _objective_and_grad(params: np.ndarray) -> tuple[float, np.ndarray]:
            a, b = params[0], params[1]
            z = a * s + b
            q = _stable_sigmoid(z)

            # Log-sum-exp binary cross-entropy loss:
            # Loss = (1/N) * sum( max(z, 0) - z*t + ln(1 + exp(-|z|)) )
            sample_loss = np.maximum(z, 0.0) - z * target_smoothed + np.log1p(np.exp(-np.abs(z)))
            loss = float(np.mean(sample_loss))

            err = q - target_smoothed
            grad_a = float(np.mean(err * s))
            grad_b = float(np.mean(err))

            return loss, np.array([grad_a, grad_b], dtype=np.float64)

        # Initialize at A=1.0, B=0.0 (identity mapping)
        init_params = np.array([1.0, 0.0], dtype=np.float64)

        # Constraint: A >= 0.0 to enforce monotonicity
        res = minimize(
            _objective_and_grad,
            init_params,
            method="L-BFGS-B",
            jac=True,
            bounds=[(0.0, None), (None, None)],
            options={"maxiter": 500, "ftol": 1e-9, "gtol": 1e-7},
        )

        self.A_ = float(res.x[0])
        self.B_ = float(res.x[1])
        self.is_fitted_ = True
        return self

    def transform(self, y_probs: np.ndarray | Sequence[float]) -> np.ndarray:
        """
        Calibrates raw 1D probabilities into calibrated 1D probabilities.

        Args:
            y_probs: 1D array of uncalibrated probabilities in [0.0, 1.0].

        Returns:
            1D float64 array of calibrated probabilities.
        """
        if not self.is_fitted_ or self.A_ is None or self.B_ is None:
            raise RuntimeError("PlattCalibrator is not fitted. Call fit() before transform().")

        p_arr = np.asarray(y_probs, dtype=np.float64).ravel()
        if len(p_arr) == 0:
            return np.empty(0, dtype=np.float64)

        p_clipped = np.clip(p_arr, self.eps, 1.0 - self.eps)
        s = np.log(p_clipped / (1.0 - p_clipped))
        z = self.A_ * s + self.B_
        calibrated_p = _stable_sigmoid(z)
        return np.asarray(calibrated_p, dtype=np.float64)

    def predict_proba(self, y_probs: np.ndarray) -> np.ndarray:
        """
        Computes calibrated (N, 2) probability matrix.
        Accepts either 1D probability vector or (N, 2) array where column 1 is P(y=1).
        """
        p_arr = np.asarray(y_probs, dtype=np.float64)
        if p_arr.ndim == 2 and p_arr.shape[1] == 2:
            p_1 = p_arr[:, 1]
        elif p_arr.ndim == 1 or (p_arr.ndim == 2 and p_arr.shape[1] == 1):
            p_1 = p_arr.ravel()
        else:
            raise ValueError(f"Expected 1D or (N, 2) probabilities, got shape {p_arr.shape}")

        cal_p1 = self.transform(p_1)
        cal_p0 = 1.0 - cal_p1
        return np.column_stack([cal_p0, cal_p1])

    def to_dict(self) -> dict[str, Any]:
        """Serializes calibrator state to a dictionary."""
        return {
            "method": "platt_scaling",
            "is_fitted": self.is_fitted_,
            "A": self.A_,
            "B": self.B_,
            "eps": self.eps,
            "warnings": list(self.warnings_),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlattCalibrator":
        """Reconstructs a PlattCalibrator from a dictionary."""
        calibrator = cls(eps=float(data.get("eps", DEFAULT_CALIBRATOR_EPS)))
        calibrator.is_fitted_ = bool(data.get("is_fitted", False))
        calibrator.A_ = float(data["A"]) if data.get("A") is not None else None
        calibrator.B_ = float(data["B"]) if data.get("B") is not None else None
        calibrator.warnings_ = list(data.get("warnings", []))
        return calibrator
