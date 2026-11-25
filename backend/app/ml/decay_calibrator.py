"""
NeuroLearn Topic Decay Calibrator
=================================
Estimates topic-specific memory decay rate (lambda) using empirical revision history
and quiz attempt performance data.

Mathematical Formulation:
-------------------------
Given observation pairs (t_i, y_i) where:
  - t_i: elapsed days since previous study event (t_i > 0)
  - y_i: empirical retention / recall score in [0.0, 100.0]

Under the Ebbinghaus model, the theoretical retention is:
  y_hat(t; lambda) = 100.0 * exp(-lambda * t)

We formulate the calibration problem as a bounded nonlinear least-squares optimization:
  minimize_{lambda in [0.01, 0.30]} S(lambda) = sum_{i=1}^N w_i * (y_i - 100.0 * exp(-lambda * t_i))^2

Where:
  - w_i: observation sample weight (e.g. higher confidence for comprehensive quizzes)
  - Golden-section / Brent bounded line search is utilized for guaranteed convergence
    without requiring external C-extensions or heavy numerical toolkits.

Robust Fallback Rules:
----------------------
1. If data points N < MIN_OBSERVATIONS (default 2 valid samples), return DEFAULT_LAMBDA = 0.08.
2. If observations exhibit zero variance or invalid elapsed times (t <= 0), fallback safely.
3. If fitted lambda falls outside [0.01, 0.30], clamp to the nearest boundary.
"""

import math
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_LAMBDA: float = 0.08
MIN_LAMBDA: float = 0.01
MAX_LAMBDA: float = 0.30
MIN_OBSERVATIONS: int = 2


def objective_loss(
    lam: float,
    observations: List[Tuple[float, float, float]],
) -> float:
    """
    Computes weighted sum of squared residuals:
    loss(lam) = sum_{i} w_i * (score_i - 100 * exp(-lam * t_i))^2
    """
    total_loss = 0.0
    for t, score, weight in observations:
        pred = 100.0 * math.exp(-lam * t)
        residual = score - pred
        total_loss += weight * (residual ** 2)
    return total_loss


def golden_section_search(
    observations: List[Tuple[float, float, float]],
    a: float = MIN_LAMBDA,
    b: float = MAX_LAMBDA,
    tol: float = 1e-5,
    max_iter: int = 100,
) -> float:
    """
    Finds the minimizer of objective_loss on interval [a, b] using Golden-Section Search.
    Golden ratio phi = (1 + sqrt(5)) / 2 approx 1.6180339887...
    Guaranteed convergence for convex/quasiconvex bounded scalar optimization.
    """
    invphi = (math.sqrt(5.0) - 1.0) / 2.0  # approx 0.6180339887
    invphi2 = (3.0 - math.sqrt(5.0)) / 2.0  # approx 0.3819660113

    c = a + invphi2 * (b - a)
    d = a + invphi * (b - a)
    yc = objective_loss(c, observations)
    yd = objective_loss(d, observations)

    for _ in range(max_iter):
        if (b - a) < tol:
            break
        if yc < yd:
            b = d
            d = c
            yd = yc
            c = a + invphi2 * (b - a)
            yc = objective_loss(c, observations)
        else:
            a = c
            c = d
            yc = yd
            d = a + invphi * (b - a)
            yd = objective_loss(d, observations)

    best_lam = (a + b) / 2.0
    return max(MIN_LAMBDA, min(MAX_LAMBDA, best_lam))


class DecayCalibrator:
    """
    Calibrates topic decay rate lambda using historical revision and quiz data.
    """

    def __init__(
        self,
        default_lambda: float = DEFAULT_LAMBDA,
        min_lambda: float = MIN_LAMBDA,
        max_lambda: float = MAX_LAMBDA,
        min_observations: int = MIN_OBSERVATIONS,
    ) -> None:
        self.default_lambda = default_lambda
        self.min_lambda = min_lambda
        self.max_lambda = max_lambda
        self.min_observations = min_observations

    def calibrate_from_observations(
        self,
        observations: List[Tuple[float, float, float]],
    ) -> float:
        """
        Calibrates lambda from pre-filtered tuples of (elapsed_days, score, weight).

        Args:
            observations: List of (elapsed_days > 0, 0 <= score <= 100, weight > 0).

        Returns:
            Calibrated lambda bounded in [min_lambda, max_lambda].
        """
        valid_obs: List[Tuple[float, float, float]] = []
        for item in observations:
            if not isinstance(item, (tuple, list)) or len(item) < 2:
                continue
            t = float(item[0])
            score = float(item[1])
            weight = float(item[2]) if len(item) >= 3 else 1.0

            if t <= 0.0 or math.isnan(t) or math.isnan(score):
                continue
            score = max(0.0, min(100.0, score))
            weight = max(0.1, weight) if not math.isnan(weight) else 1.0
            valid_obs.append((t, score, weight))

        if len(valid_obs) < self.min_observations:
            return self.default_lambda

        # Check for degenerate scores (e.g. all 100% or all 0%)
        scores = [obs[1] for obs in valid_obs]
        if min(scores) == max(scores):
            # All scores identical
            if scores[0] >= 95.0:
                return self.min_lambda  # strong retention, slow decay
            elif scores[0] <= 10.0:
                return self.max_lambda  # severe forgetting, fast decay

        fitted_lambda = golden_section_search(
            valid_obs,
            a=self.min_lambda,
            b=self.max_lambda,
        )

        return max(self.min_lambda, min(self.max_lambda, fitted_lambda))

    def calibrate_from_history(
        self,
        revision_history: Optional[List[Dict[str, Any]]] = None,
        quiz_attempts: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """
        Extracts observations from raw entity dictionaries and estimates lambda.

        Args:
            revision_history: List of revision dicts (with 'interval_days'/'elapsed_days' & 'score').
            quiz_attempts: List of quiz attempt dicts (with 'elapsed_days' & 'score'/'accuracy').

        Returns:
            Calibrated lambda in [MIN_LAMBDA, MAX_LAMBDA].
        """
        observations: List[Tuple[float, float, float]] = []

        if revision_history:
            for rev in revision_history:
                if not isinstance(rev, dict):
                    continue
                # Support interval_days or elapsed_days
                t = rev.get("interval_days", rev.get("elapsed_days", 0))
                score = rev.get("score")
                if score is not None and t is not None:
                    try:
                        t_val = float(t)
                        s_val = float(score)
                        if t_val > 0:
                            observations.append((t_val, s_val, 1.0))
                    except (ValueError, TypeError):
                        continue

        if quiz_attempts:
            for q in quiz_attempts:
                if not isinstance(q, dict):
                    continue
                t = q.get("elapsed_days", 0)
                score = q.get("score", q.get("accuracy"))
                if score is not None and t is not None:
                    try:
                        t_val = float(t)
                        s_val = float(score)
                        if t_val > 0:
                            observations.append((t_val, s_val, 1.2))  # quizzes weighted slightly higher
                    except (ValueError, TypeError):
                        continue

        return self.calibrate_from_observations(observations)


decay_calibrator = DecayCalibrator()
