"""
Retention Model Training and Initial Evaluation Pipeline.

Implements leakage-free training, baseline models, L-BFGS logistic regression,
and genuine histogram gradient tree boosting using only NumPy and SciPy.
"""

import csv
from dataclasses import dataclass
from typing import Any, Callable, Final, Sequence
import numpy as np
from scipy.optimize import minimize

from ml.core.baselines import calculate_retention
from ml.data.preprocessor import RetentionFeaturePreprocessor, extract_features_and_target
from ml.data.schemas import ReviewEventRecord
from ml.models.evaluator import EvaluationMetrics, evaluate_predictions

DEFAULT_RANDOM_STATE: Final[int] = 42
DEFAULT_TRAIN_RATIO: Final[float] = 0.70
DEFAULT_VAL_RATIO: Final[float] = 0.15
DEFAULT_TEST_RATIO: Final[float] = 0.15


# -------------------------------------------------------------------------
# Evaluation Split Utilities
# -------------------------------------------------------------------------

def temporal_split(
    records: Sequence[ReviewEventRecord | dict[str, Any]],
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    val_ratio: float = DEFAULT_VAL_RATIO,
    test_ratio: float = DEFAULT_TEST_RATIO,
) -> tuple[
    list[ReviewEventRecord | dict[str, Any]],
    list[ReviewEventRecord | dict[str, Any]],
    list[ReviewEventRecord | dict[str, Any]],
    dict[str, Any],
]:
    """
    Partitions review events chronologically without random shuffling.
    Guarantees that training records strictly precede validation and test records in time.

    Args:
        records: Sequence of review event records or dictionaries.
        train_ratio: Fraction of records for training (default 0.70).
        val_ratio: Fraction of records for validation (default 0.15).
        test_ratio: Fraction of records for holdout test (default 0.15).

    Returns:
        tuple of (train_records, val_records, test_records, metadata_dict).

    Raises:
        ValueError: If ratios do not sum to 1.0 or records is empty.
    """
    if not records:
        raise ValueError("Cannot perform temporal split on empty records sequence.")
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError(
            f"Split ratios must sum to 1.0, got {train_ratio} + {val_ratio} + {test_ratio} = {train_ratio + val_ratio + test_ratio}"
        )
    if train_ratio <= 0.0 or val_ratio <= 0.0 or test_ratio <= 0.0:
        raise ValueError("All split ratios must be strictly positive (> 0.0).")

    # Sort strictly by timestamp string (ISO-8601 UTC strings sort lexicographically)
    def _get_ts(r: ReviewEventRecord | dict[str, Any]) -> str:
        return r.timestamp if isinstance(r, ReviewEventRecord) else str(r["timestamp"])

    sorted_records = sorted(records, key=_get_ts)
    total_n = len(sorted_records)

    n_train = int(total_n * train_ratio)
    n_val = int(total_n * val_ratio)

    train_records = sorted_records[:n_train]
    val_records = sorted_records[n_train : n_train + n_val]
    test_records = sorted_records[n_train + n_val :]

    metadata = {
        "strategy": "temporal_holdout",
        "total_records": total_n,
        "train_count": len(train_records),
        "val_count": len(val_records),
        "test_count": len(test_records),
        "train_start_timestamp": _get_ts(train_records[0]),
        "train_end_timestamp": _get_ts(train_records[-1]),
        "val_start_timestamp": _get_ts(val_records[0]),
        "val_end_timestamp": _get_ts(val_records[-1]),
        "test_start_timestamp": _get_ts(test_records[0]),
        "test_end_timestamp": _get_ts(test_records[-1]),
    }
    return train_records, val_records, test_records, metadata


def user_disjoint_split(
    records: Sequence[ReviewEventRecord | dict[str, Any]],
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    val_ratio: float = DEFAULT_VAL_RATIO,
    test_ratio: float = DEFAULT_TEST_RATIO,
    seed: int = DEFAULT_RANDOM_STATE,
) -> tuple[
    list[ReviewEventRecord | dict[str, Any]],
    list[ReviewEventRecord | dict[str, Any]],
    list[ReviewEventRecord | dict[str, Any]],
    dict[str, Any],
]:
    """
    Partitions review events such that no user_id appears in more than one partition.
    Evaluates model generalization to completely unseen learners.

    Args:
        records: Sequence of review event records or dictionaries.
        train_ratio: Fraction of unique users for training.
        val_ratio: Fraction of unique users for validation.
        test_ratio: Fraction of unique users for test.
        seed: Random seed for deterministic user partition assignment.

    Returns:
        tuple of (train_records, val_records, test_records, metadata_dict).
    """
    if not records:
        raise ValueError("Cannot perform user-disjoint split on empty records sequence.")
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("Split ratios must sum to 1.0.")

    def _get_user(r: ReviewEventRecord | dict[str, Any]) -> str:
        return r.user_id if isinstance(r, ReviewEventRecord) else str(r["user_id"])

    def _get_ts(r: ReviewEventRecord | dict[str, Any]) -> str:
        return r.timestamp if isinstance(r, ReviewEventRecord) else str(r["timestamp"])

    unique_users = sorted(list({_get_user(r) for r in records}))
    rng = np.random.RandomState(seed)
    shuffled_users = rng.permutation(unique_users)

    n_users = len(shuffled_users)
    n_train_u = int(n_users * train_ratio)
    n_val_u = int(n_users * val_ratio)

    train_user_set = set(shuffled_users[:n_train_u])
    val_user_set = set(shuffled_users[n_train_u : n_train_u + n_val_u])
    test_user_set = set(shuffled_users[n_train_u + n_val_u :])

    train_records = [r for r in records if _get_user(r) in train_user_set]
    val_records = [r for r in records if _get_user(r) in val_user_set]
    test_records = [r for r in records if _get_user(r) in test_user_set]

    # Preserve internal chronological ordering within each split
    train_records.sort(key=_get_ts)
    val_records.sort(key=_get_ts)
    test_records.sort(key=_get_ts)

    metadata = {
        "strategy": "user_disjoint",
        "total_records": len(records),
        "total_users": n_users,
        "train_user_count": len(train_user_set),
        "val_user_count": len(val_user_set),
        "test_user_count": len(test_user_set),
        "train_record_count": len(train_records),
        "val_record_count": len(val_records),
        "test_record_count": len(test_records),
    }
    return train_records, val_records, test_records, metadata


# -------------------------------------------------------------------------
# Baseline Estimators
# -------------------------------------------------------------------------

class PopulationPrevalenceBaseline:
    """
    Dummy population baseline that predicts the empirical training recall prevalence.
    Provides the null-hypothesis reference point for calibration and classification metrics.
    """

    def __init__(self) -> None:
        self.prevalence_: float | None = None
        self.classes_: np.ndarray = np.array([0, 1], dtype=np.int32)
        self.is_fitted_: bool = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray | Sequence[int],
    ) -> "PopulationPrevalenceBaseline":
        """Fits prevalence strictly using training labels."""
        y_arr = np.asarray(y, dtype=np.int32).ravel()
        if len(y_arr) == 0:
            raise ValueError("Cannot fit baseline on empty target array.")
        prev = float(np.mean(y_arr))
        self.prevalence_ = float(np.clip(prev, 1e-6, 1.0 - 1e-6))
        self.is_fitted_ = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Returns constant training prevalence for all samples: shape (N, 2)."""
        if not self.is_fitted_:
            raise RuntimeError("PopulationPrevalenceBaseline is not fitted.")
        n = len(X)
        assert self.prevalence_ is not None
        p1 = np.full(n, self.prevalence_, dtype=np.float64)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray, threshold: float = 0.50) -> np.ndarray:
        """Returns binary predictions based on prevalence threshold."""
        return (self.predict_proba(X)[:, 1] >= threshold).astype(np.int32)


class EbbinghausBaseline:
    """
    Theoretical exponential retention baseline: R(t) = exp(-t / S).
    Uses ml/core/baselines.calculate_retention as a mathematical anchor.

    Note: Theoretical retention represents expected memory trace decay,
    not an empirically fitted probability distribution.
    """

    def __init__(self) -> None:
        self.classes_: np.ndarray = np.array([0, 1], dtype=np.int32)
        self.is_fitted_: bool = True

    def fit(
        self,
        X: Any = None,
        y: Any = None,
    ) -> "EbbinghausBaseline":
        """Theoretical baseline requires no training parameter fitting."""
        return self

    def predict_proba_from_records(
        self,
        records: Sequence[ReviewEventRecord | dict[str, Any]],
    ) -> np.ndarray:
        """
        Computes retention probabilities directly from review event records:
            R = exp(-elapsed_days / stability_days_prior)
        """
        if not records:
            return np.empty((0, 2), dtype=np.float64)

        probs: list[float] = []
        for r in records:
            if isinstance(r, ReviewEventRecord):
                elapsed = r.elapsed_days
                stability = r.stability_days_prior
            else:
                elapsed = float(r["elapsed_days"])
                stability = float(r["stability_days_prior"])
            probs.append(calculate_retention(elapsed, stability))

        p1 = np.array(probs, dtype=np.float64)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict_from_records(
        self,
        records: Sequence[ReviewEventRecord | dict[str, Any]],
        threshold: float = 0.50,
    ) -> np.ndarray:
        """Returns binary recall predictions based on retention threshold."""
        return (self.predict_proba_from_records(records)[:, 1] >= threshold).astype(np.int32)


# -------------------------------------------------------------------------
# ScipyLogisticRegression (L-BFGS-B with L2 Regularization)
# -------------------------------------------------------------------------

def _stable_sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid calculation preventing overflow/underflow."""
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


class ScipyLogisticRegression:
    """
    Binary Logistic Regression fitted via SciPy's L-BFGS-B quasi-Newton optimizer.
    Uses exact analytical gradients and L2 regularization.

    Guarantees:
    - Numerically stable log-loss and sigmoid computation.
    - Intercept is strictly excluded from L2 regularization.
    - Scikit-learn duck-typed API (fit, predict_proba, predict, classes_, coef_, intercept_).
    """

    def __init__(
        self,
        C: float = 1.0,
        max_iter: int = 1000,
        tol: float = 1e-7,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        if C <= 0.0:
            raise ValueError(f"C must be strictly positive (> 0.0), got {C}")
        self.C = C
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

        self.coef_: np.ndarray | None = None
        self.intercept_: np.ndarray | None = None
        self.classes_: np.ndarray = np.array([0, 1], dtype=np.int32)
        self.n_iter_: int = 0
        self.is_fitted_: bool = False

    def fit(self, X: np.ndarray, y: np.ndarray | Sequence[int]) -> "ScipyLogisticRegression":
        """
        Fits weights and intercept by minimizing L2-regularized binary cross-entropy.

        Args:
            X: 2D array of shape (N, D).
            y: Binary target array of shape (N,).
        """
        X_arr = np.asarray(X, dtype=np.float64)
        y_arr = np.asarray(y, dtype=np.float64).ravel()

        if X_arr.ndim != 2:
            raise ValueError(f"X must be 2D, got shape {X_arr.shape}")
        if len(X_arr) != len(y_arr):
            raise ValueError(f"X ({len(X_arr)}) and y ({len(y_arr)}) must have equal length.")
        if len(y_arr) == 0:
            raise ValueError("Cannot fit on empty dataset.")

        n_samples, n_features = X_arr.shape
        inv_c = 1.0 / self.C

        def _objective_and_grad(theta: np.ndarray) -> tuple[float, np.ndarray]:
            w = theta[:n_features]
            b = theta[n_features]

            z = X_arr @ w + b
            p = _stable_sigmoid(z)

            # Log-loss with log-sum-exp formulation for stability
            # Loss = (1/N) * sum( max(z, 0) - z*y + ln(1 + exp(-|z|)) ) + (1 / 2C) * ||w||^2
            sample_loss = np.maximum(z, 0.0) - z * y_arr + np.log1p(np.exp(-np.abs(z)))
            loss = float(np.mean(sample_loss) + 0.5 * inv_c * np.sum(w ** 2))

            # Gradients
            err = p - y_arr  # shape (N,)
            grad_w = (X_arr.T @ err) / n_samples + inv_c * w
            grad_b = float(np.mean(err))  # Note: Intercept is NOT regularized

            grad = np.empty(n_features + 1, dtype=np.float64)
            grad[:n_features] = grad_w
            grad[n_features] = grad_b

            return loss, grad

        theta_init = np.zeros(n_features + 1, dtype=np.float64)

        res = minimize(
            _objective_and_grad,
            theta_init,
            method="L-BFGS-B",
            jac=True,
            options={"maxiter": self.max_iter, "ftol": self.tol, "gtol": self.tol},
        )

        self.coef_ = res.x[:n_features].reshape(1, -1)
        self.intercept_ = np.array([res.x[n_features]])
        self.n_iter_ = int(res.nit)
        self.is_fitted_ = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Computes predicted class probabilities: shape (N, 2)."""
        if not self.is_fitted_ or self.coef_ is None or self.intercept_ is None:
            raise RuntimeError("ScipyLogisticRegression is not fitted.")

        X_arr = np.asarray(X, dtype=np.float64)
        z = X_arr @ self.coef_[0] + self.intercept_[0]
        p1 = _stable_sigmoid(z)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray, threshold: float = 0.50) -> np.ndarray:
        """Predicts discrete binary labels: shape (N,)."""
        return (self.predict_proba(X)[:, 1] >= threshold).astype(np.int32)


# -------------------------------------------------------------------------
# NumpyHistGradientBoostingClassifier
# -------------------------------------------------------------------------

@dataclass
class _HistTreeNode:
    """Internal node or leaf in a histogram gradient boosted tree."""
    is_leaf: bool
    leaf_value: float = 0.0
    split_feature: int = 0
    split_bin: int = 0
    left_child: "_HistTreeNode | None" = None
    right_child: "_HistTreeNode | None" = None


def _predict_tree(node: _HistTreeNode, X_binned: np.ndarray) -> np.ndarray:
    """Vectorized prediction across all samples for a single tree."""
    out = np.empty(X_binned.shape[0], dtype=np.float64)

    def _traverse(curr: _HistTreeNode, indices: np.ndarray) -> None:
        if len(indices) == 0:
            return
        if curr.is_leaf:
            out[indices] = curr.leaf_value
            return
        mask_left = X_binned[indices, curr.split_feature] <= curr.split_bin
        assert curr.left_child is not None and curr.right_child is not None
        _traverse(curr.left_child, indices[mask_left])
        _traverse(curr.right_child, indices[~mask_left])

    _traverse(node, np.arange(X_binned.shape[0]))
    return out


class NumpyHistGradientBoostingClassifier:
    """
    Genuine Histogram-Based Gradient Boosted Decision Tree Classifier in pure NumPy.

    Implements:
    - Deterministic quantile binning fitted strictly on training data.
    - Negative gradient and Hessian aggregation into 1D histograms.
    - Split selection maximizing Newton gain reduction:
        Gain = (G_L^2 / (H_L + lambda)) + (G_R^2 / (H_R + lambda)) - (G_node^2 / (H_node + lambda))
    - Newton-Raphson leaf updates:
        gamma = - (sum g_i) / (sum h_i + lambda)
    - Learning rate shrinkage.
    - Scikit-learn duck-typed API (fit, predict_proba, predict, classes_).
    """

    def __init__(
        self,
        max_iter: int = 30,
        max_depth: int = 3,
        learning_rate: float = 0.10,
        l2_regularization: float = 1.0,
        min_samples_leaf: int = 20,
        n_bins: int = 32,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        if max_iter < 1:
            raise ValueError(f"max_iter must be >= 1, got {max_iter}")
        if max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {max_depth}")
        if learning_rate <= 0.0:
            raise ValueError(f"learning_rate must be > 0.0, got {learning_rate}")
        if l2_regularization < 0.0:
            raise ValueError(f"l2_regularization must be >= 0.0, got {l2_regularization}")
        if min_samples_leaf < 1:
            raise ValueError(f"min_samples_leaf must be >= 1, got {min_samples_leaf}")
        if n_bins < 4:
            raise ValueError(f"n_bins must be >= 4, got {n_bins}")

        self.max_iter = max_iter
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.l2_regularization = l2_regularization
        self.min_samples_leaf = min_samples_leaf
        self.n_bins = n_bins
        self.random_state = random_state

        self.bin_edges_: list[np.ndarray] = []
        self.init_raw_prediction_: float = 0.0
        self.trees_: list[_HistTreeNode] = []
        self.classes_: np.ndarray = np.array([0, 1], dtype=np.int32)
        self.is_fitted_: bool = False

    def _bin_features(self, X: np.ndarray) -> np.ndarray:
        """Discretizes continuous features into integer bin indices using fitted quantile edges."""
        n_samples, n_features = X.shape
        X_binned = np.empty((n_samples, n_features), dtype=np.int32)
        for j in range(n_features):
            edges = self.bin_edges_[j]
            if len(edges) == 0:
                X_binned[:, j] = 0
            else:
                X_binned[:, j] = np.digitize(X[:, j], edges)
        return X_binned

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray | Sequence[int],
    ) -> "NumpyHistGradientBoostingClassifier":
        """
        Fits the histogram gradient boosted ensemble.

        Args:
            X: 2D array of shape (N, D).
            y: Binary target array of shape (N,).
        """
        X_arr = np.asarray(X, dtype=np.float64)
        y_arr = np.asarray(y, dtype=np.float64).ravel()

        if X_arr.ndim != 2:
            raise ValueError(f"X must be 2D, got shape {X_arr.shape}")
        if len(X_arr) != len(y_arr):
            raise ValueError(f"X ({len(X_arr)}) and y ({len(y_arr)}) must have equal length.")
        if len(y_arr) == 0:
            raise ValueError("Cannot fit on empty dataset.")

        n_samples, n_features = X_arr.shape

        # 1. Deterministic quantile binning fitted EXCLUSIVELY on training data
        self.bin_edges_ = []
        quantiles = np.linspace(0.0, 1.0, self.n_bins + 1)[1:-1]
        for j in range(n_features):
            col = X_arr[:, j]
            edges = np.unique(np.quantile(col, quantiles))
            self.bin_edges_.append(edges)

        X_binned = self._bin_features(X_arr)

        # 2. Initial base prediction (prior log-odds)
        p_mean = float(np.clip(np.mean(y_arr), 1e-4, 1.0 - 1e-4))
        self.init_raw_prediction_ = float(np.log(p_mean / (1.0 - p_mean)))
        raw_predictions = np.full(n_samples, self.init_raw_prediction_, dtype=np.float64)

        self.trees_ = []
        l2_reg = self.l2_regularization
        min_leaf = self.min_samples_leaf

        # 3. Boosting iterations
        for _ in range(self.max_iter):
            p = _stable_sigmoid(raw_predictions)
            # Binary log-loss gradient and hessian:
            # g = p - y, h = p * (1 - p)
            g = p - y_arr
            h = np.maximum(p * (1.0 - p), 1e-12)

            # Build decision tree of depth <= self.max_depth
            def _build_node(sample_indices: np.ndarray, depth: int) -> _HistTreeNode:
                n_node = len(sample_indices)
                g_node = float(np.sum(g[sample_indices]))
                h_node = float(np.sum(h[sample_indices]))

                # Stop conditions: max depth or insufficient samples
                if depth >= self.max_depth or n_node < 2 * min_leaf:
                    val = -g_node / (h_node + l2_reg)
                    return _HistTreeNode(is_leaf=True, leaf_value=float(np.clip(val, -5.0, 5.0)))

                score_node = (g_node ** 2) / (h_node + l2_reg)
                best_gain = -1.0
                best_feat = -1
                best_bin = -1

                # Search best split across all features and histogram bins
                for j in range(n_features):
                    k_bins = len(self.bin_edges_[j]) + 1
                    col_b = X_binned[sample_indices, j]

                    g_bin = np.bincount(col_b, weights=g[sample_indices], minlength=k_bins)
                    h_bin = np.bincount(col_b, weights=h[sample_indices], minlength=k_bins)
                    count_bin = np.bincount(col_b, minlength=k_bins)

                    gl_arr = np.cumsum(g_bin)[:-1]
                    hl_arr = np.cumsum(h_bin)[:-1]
                    count_l = np.cumsum(count_bin)[:-1]

                    gr_arr = g_node - gl_arr
                    hr_arr = h_node - hl_arr
                    count_r = n_node - count_l

                    valid_splits = (count_l >= min_leaf) & (count_r >= min_leaf) & (hl_arr > 0) & (hr_arr > 0)
                    if not np.any(valid_splits):
                        continue

                    gains = np.where(
                        valid_splits,
                        (gl_arr ** 2) / (hl_arr + l2_reg) + (gr_arr ** 2) / (hr_arr + l2_reg) - score_node,
                        -1.0,
                    )
                    max_idx = int(np.argmax(gains))
                    if gains[max_idx] > best_gain:
                        best_gain = float(gains[max_idx])
                        best_feat = j
                        best_bin = max_idx

                if best_gain <= 1e-10:
                    val = -g_node / (h_node + l2_reg)
                    return _HistTreeNode(is_leaf=True, leaf_value=float(np.clip(val, -5.0, 5.0)))

                # Split node samples
                mask_left = X_binned[sample_indices, best_feat] <= best_bin
                left_indices = sample_indices[mask_left]
                right_indices = sample_indices[~mask_left]

                left_child = _build_node(left_indices, depth + 1)
                right_child = _build_node(right_indices, depth + 1)

                return _HistTreeNode(
                    is_leaf=False,
                    split_feature=best_feat,
                    split_bin=best_bin,
                    left_child=left_child,
                    right_child=right_child,
                )

            tree_root = _build_node(np.arange(n_samples), depth=0)
            tree_updates = _predict_tree(tree_root, X_binned)
            raw_predictions += self.learning_rate * tree_updates
            self.trees_.append(tree_root)

        self.is_fitted_ = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Computes predicted class probabilities: shape (N, 2)."""
        if not self.is_fitted_:
            raise RuntimeError("NumpyHistGradientBoostingClassifier is not fitted.")

        X_arr = np.asarray(X, dtype=np.float64)
        X_binned = self._bin_features(X_arr)
        raw_pred = np.full(len(X_arr), self.init_raw_prediction_, dtype=np.float64)

        for tree in self.trees_:
            raw_pred += self.learning_rate * _predict_tree(tree, X_binned)

        p1 = _stable_sigmoid(raw_pred)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray, threshold: float = 0.50) -> np.ndarray:
        """Predicts discrete binary labels: shape (N,)."""
        return (self.predict_proba(X)[:, 1] >= threshold).astype(np.int32)


# -------------------------------------------------------------------------
# Full Training & Evaluation Orchestration
# -------------------------------------------------------------------------

def load_review_events_from_csv(csv_path: str) -> list[ReviewEventRecord]:
    """Loads and validates ReviewEventRecord instances from a CSV file."""
    records: list[ReviewEventRecord] = []
    with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(ReviewEventRecord.from_dict(row))
    return records


def run_phase_2_4_4a_experiment(
    csv_path: str = "datasets/synthetic_review_events.csv",
) -> dict[str, Any]:
    """
    Executes the complete Phase 2.4.4A model training and initial evaluation benchmark.

    Procedure:
    1. Loads the synthetic review event records.
    2. Performs temporal split (70% Train, 15% Val, 15% Test).
    3. Fits RetentionFeaturePreprocessor strictly on Train partition.
    4. Transforms Train, Val, and Test records into feature matrices.
    5. Fits and evaluates:
       - PopulationPrevalenceBaseline
       - EbbinghausBaseline
       - ScipyLogisticRegression
       - NumpyHistGradientBoostingClassifier
    6. Performs Model Selection on Validation Set.
    7. Evaluates all models on the preserved Final Test Set.
    8. Executes User-Disjoint Split benchmark to assess generalization to unseen learners.
    9. Returns full experimental report.
    """
    records = load_review_events_from_csv(csv_path)

    # 1. Temporal Holdout Split
    train_recs, val_recs, test_recs, temp_split_meta = temporal_split(records)

    # 2. Extract features and target
    _, y_train = extract_features_and_target(train_recs)
    _, y_val = extract_features_and_target(val_recs)
    _, y_test = extract_features_and_target(test_recs)

    # 3. Fit preprocessor STRICTLY on training partition
    preprocessor = RetentionFeaturePreprocessor(scale_features=True)
    X_train = preprocessor.fit_transform(train_recs)
    X_val = preprocessor.transform(val_recs)
    X_test = preprocessor.transform(test_recs)

    # 4. Instantiate models
    dummy_model = PopulationPrevalenceBaseline().fit(X_train, y_train)
    ebbinghaus_model = EbbinghausBaseline()

    lr_model = ScipyLogisticRegression(C=1.0, max_iter=1000, tol=1e-7)
    lr_model.fit(X_train, y_train)

    gb_model = NumpyHistGradientBoostingClassifier(
        max_iter=30,
        max_depth=3,
        learning_rate=0.10,
        l2_regularization=1.0,
        min_samples_leaf=20,
        n_bins=32,
    )
    gb_model.fit(X_train, y_train)

    # 5. Evaluate on Validation Set
    val_dummy_prob = dummy_model.predict_proba(X_val)[:, 1]
    val_ebbinghaus_prob = ebbinghaus_model.predict_proba_from_records(val_recs)[:, 1]
    val_lr_prob = lr_model.predict_proba(X_val)[:, 1]
    val_gb_prob = gb_model.predict_proba(X_val)[:, 1]

    val_metrics = {
        "dummy": evaluate_predictions(y_val, val_dummy_prob).to_dict(),
        "ebbinghaus": evaluate_predictions(y_val, val_ebbinghaus_prob).to_dict(),
        "logistic_regression": evaluate_predictions(y_val, val_lr_prob).to_dict(),
        "hist_gradient_boosting": evaluate_predictions(y_val, val_gb_prob).to_dict(),
    }

    # 6. Evaluate on Preserved Final Test Set
    test_dummy_prob = dummy_model.predict_proba(X_test)[:, 1]
    test_ebbinghaus_prob = ebbinghaus_model.predict_proba_from_records(test_recs)[:, 1]
    test_lr_prob = lr_model.predict_proba(X_test)[:, 1]
    test_gb_prob = gb_model.predict_proba(X_test)[:, 1]

    test_metrics = {
        "dummy": evaluate_predictions(y_test, test_dummy_prob).to_dict(),
        "ebbinghaus": evaluate_predictions(y_test, test_ebbinghaus_prob).to_dict(),
        "logistic_regression": evaluate_predictions(y_test, test_lr_prob).to_dict(),
        "hist_gradient_boosting": evaluate_predictions(y_test, test_gb_prob).to_dict(),
    }

    # 7. User-Disjoint Split Generalization Benchmark
    u_train_recs, u_val_recs, u_test_recs, user_split_meta = user_disjoint_split(records)
    _, u_y_train = extract_features_and_target(u_train_recs)
    _, u_y_test = extract_features_and_target(u_test_recs)

    u_preprocessor = RetentionFeaturePreprocessor(scale_features=True)
    u_X_train = u_preprocessor.fit_transform(u_train_recs)
    u_X_test = u_preprocessor.transform(u_test_recs)

    u_lr = ScipyLogisticRegression(C=1.0).fit(u_X_train, u_y_train)
    u_gb = NumpyHistGradientBoostingClassifier(max_iter=30, max_depth=3).fit(u_X_train, u_y_train)

    user_disjoint_test_metrics = {
        "dummy": evaluate_predictions(
            u_y_test,
            PopulationPrevalenceBaseline().fit(u_X_train, u_y_train).predict_proba(u_X_test)[:, 1],
        ).to_dict(),
        "ebbinghaus": evaluate_predictions(
            u_y_test,
            EbbinghausBaseline().predict_proba_from_records(u_test_recs)[:, 1],
        ).to_dict(),
        "logistic_regression": evaluate_predictions(
            u_y_test,
            u_lr.predict_proba(u_X_test)[:, 1],
        ).to_dict(),
        "hist_gradient_boosting": evaluate_predictions(
            u_y_test,
            u_gb.predict_proba(u_X_test)[:, 1],
        ).to_dict(),
    }

    return {
        "dataset_notice": "ALL DATA AND RESULTS ARE STRICTLY SYNTHETIC SIMULATION BENCHMARKS.",
        "temporal_split_metadata": temp_split_meta,
        "user_disjoint_split_metadata": user_split_meta,
        "validation_metrics": val_metrics,
        "final_test_metrics": test_metrics,
        "user_disjoint_test_metrics": user_disjoint_test_metrics,
        "model_convergence": {
            "logistic_regression_iterations": lr_model.n_iter_,
            "gradient_boosting_trees": len(gb_model.trees_),
        },
    }
