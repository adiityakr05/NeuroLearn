"""
NeuroLearn ML Retention Model
=============================
Mathematical formulation of cognitive memory retention based on Hermann Ebbinghaus's
forgetting curve and empirical spaced repetition stability dynamics.

Mathematical Principles:
-----------------------
1. Exponential Memory Decay:
   R(t) = 100.0 * exp(-lambda * t)
   Where:
     - R(t): Percentage memory retention at elapsed time t (bounded in [0.0, 100.0]).
     - t: Elapsed time in days since last study / revision session (t >= 0.0).
     - lambda: Topic-specific memory decay rate parameter (bounded in [0.01, 0.30]).

2. Memory Half-Life:
   t_{1/2} = ln(2) / lambda
   The time in days required for retention to decay to 50% of its initial value.

3. Stability Dynamics upon Revision / Quiz Performance:
   Memory stability is updated upon active recall based on recall score S in [0.0, 100.0]:
   - High performance (S >= 80%):
       Memory consolidation occurs; decay rate lambda decreases.
       lambda_{new} = lambda * (0.60 + 0.20 * (100.0 - S) / 100.0)
   - Moderate performance (60% <= S < 80%):
       Mild consolidation; minor reduction in lambda.
       lambda_{new} = lambda * (0.85 + 0.15 * (80.0 - S) / 20.0)
   - Failing / Poor performance (S < 60%):
       Forgetting risk triggers; decay rate increases (faster forgetting).
       lambda_{new} = lambda * (1.10 + 0.40 * (60.0 - S) / 60.0)
   All updated lambda values are clamped to [MIN_LAMBDA, MAX_LAMBDA].

4. Recommended Revision Interval:
   Determines the number of days until retention drops to a target threshold R_target (default 70%):
   t_{rev} = max(1, round(-ln(R_target / 100.0) / lambda))
"""

import math
from typing import Dict, Any, Optional

DEFAULT_LAMBDA: float = 0.08
MIN_LAMBDA: float = 0.01
MAX_LAMBDA: float = 0.30
DEFAULT_TARGET_RETENTION: float = 70.0


def clamp(val: float, min_val: float, max_val: float) -> float:
    """Clamps a floating point number within [min_val, max_val]."""
    return max(min_val, min(max_val, val))


class RetentionModel:
    """
    Mathematical cognitive retention engine implementing the Ebbinghaus forgetting curve
    and spaced repetition stability scaling.
    """

    def __init__(
        self,
        default_lambda: float = DEFAULT_LAMBDA,
        min_lambda: float = MIN_LAMBDA,
        max_lambda: float = MAX_LAMBDA,
    ) -> None:
        self.default_lambda = default_lambda
        self.min_lambda = min_lambda
        self.max_lambda = max_lambda

    def calculate_retention(
        self,
        elapsed_days: float,
        decay_lambda: Optional[float] = None,
    ) -> float:
        """
        Computes retention percentage R(t) = 100 * exp(-lambda * t).

        Args:
            elapsed_days: Non-negative elapsed time in days since last study/revision.
            decay_lambda: Decay rate parameter lambda in [0.01, 0.30]. Defaults to 0.08.

        Returns:
            Retention score bounded in [0.0, 100.0].
        """
        if elapsed_days < 0.0:
            elapsed_days = 0.0

        lam = self.sanitize_lambda(decay_lambda)
        decay = math.exp(-lam * elapsed_days)
        retention = 100.0 * decay

        return clamp(retention, 0.0, 100.0)

    def calculate_half_life(self, decay_lambda: Optional[float] = None) -> float:
        """
        Computes memory half-life in days: t_{1/2} = ln(2) / lambda.

        Args:
            decay_lambda: Decay rate parameter.

        Returns:
            Half-life in days (float > 0.0).
        """
        lam = self.sanitize_lambda(decay_lambda)
        return math.log(2.0) / lam

    def update_stability(
        self,
        current_lambda: Optional[float],
        performance_score: float,
        repetition_count: int = 1,
    ) -> float:
        """
        Updates topic decay rate lambda based on student's performance score (0-100).
        Successful revisions decrease lambda (increasing stability/half-life).
        Poor revisions increase lambda (reflecting faster decay / higher forgetting risk).

        Args:
            current_lambda: Current decay rate parameter.
            performance_score: Quiz or revision score in percentage [0.0, 100.0].
            repetition_count: Cumulative repetition cycle count (>= 1).

        Returns:
            Updated lambda clamped to [MIN_LAMBDA, MAX_LAMBDA].
        """
        lam = self.sanitize_lambda(current_lambda)
        score = clamp(performance_score, 0.0, 100.0)

        # Repetition damping factor: later repetitions solidify retention more stably
        rep_factor = max(1.0, math.log(repetition_count + 1, 2))

        if score >= 80.0:
            # Consolidation phase: lambda decreases
            # For 100% score: multiplier is ~0.60 / rep_factor
            decay_multiplier = 0.60 + 0.20 * ((100.0 - score) / 20.0)
            new_lam = lam * (decay_multiplier ** (1.0 / rep_factor))
        elif score >= 60.0:
            # Satisfactory recall: modest improvement
            decay_multiplier = 0.85 + 0.15 * ((80.0 - score) / 20.0)
            new_lam = lam * decay_multiplier
        else:
            # Memory failure / forgetting: lambda increases (faster decay)
            # For 0% score: multiplier is 1.50
            decay_multiplier = 1.10 + 0.40 * ((60.0 - score) / 60.0)
            new_lam = lam * decay_multiplier

        return self.sanitize_lambda(new_lam)

    def calculate_recommended_interval(
        self,
        decay_lambda: Optional[float] = None,
        target_retention: float = DEFAULT_TARGET_RETENTION,
    ) -> int:
        """
        Calculates recommended days until next revision before retention falls below target_retention.
        Formula: t = -ln(R_target / 100) / lambda

        Args:
            decay_lambda: Decay rate parameter.
            target_retention: Desired retention threshold (default 70.0%).

        Returns:
            Integer interval in days (minimum 1 day).
        """
        lam = self.sanitize_lambda(decay_lambda)
        target = clamp(target_retention, 1.0, 99.0)

        days = -math.log(target / 100.0) / lam
        return max(1, int(round(days)))

    def sanitize_lambda(self, decay_lambda: Optional[float]) -> float:
        """
        Validates and clamps lambda to [MIN_LAMBDA, MAX_LAMBDA].
        Returns default_lambda if decay_lambda is None, NaN, or non-positive.
        """
        if decay_lambda is None or not isinstance(decay_lambda, (int, float)) or math.isnan(decay_lambda):
            return self.default_lambda
        return clamp(float(decay_lambda), self.min_lambda, self.max_lambda)

    def predict_topic_state(
        self,
        elapsed_days: float,
        decay_lambda: Optional[float] = None,
        repetition_count: int = 1,
    ) -> Dict[str, Any]:
        """
        Convenience method returning comprehensive cognitive state for a topic.
        """
        lam = self.sanitize_lambda(decay_lambda)
        retention = self.calculate_retention(elapsed_days, lam)
        half_life = self.calculate_half_life(lam)
        recommended_interval = self.calculate_recommended_interval(lam)

        return {
            "decay_lambda": round(lam, 4),
            "elapsed_days": round(elapsed_days, 2),
            "retention_score": round(retention, 2),
            "half_life_days": round(half_life, 2),
            "recommended_interval_days": recommended_interval,
            "is_at_risk": retention < DEFAULT_TARGET_RETENTION,
        }


retention_model = RetentionModel()
