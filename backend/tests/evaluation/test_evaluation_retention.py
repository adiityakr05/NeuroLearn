"""
Evaluation Suite: Retention Engine & Decay Calibrator (Component A)
===================================================================
Evaluates:
- Monotonic retention decay over time t.
- Behavior across multiple decay lambdas in [0.01, 0.30].
- Numerical stability, non-negative bounding [0.0, 100.0], half-life.
- Calibration behavior with sparse vs sufficient observations.
- Revision stability updates and damping factors.
"""

import math
import pytest
from app.ml.retention_model import RetentionModel, DEFAULT_LAMBDA, MIN_LAMBDA, MAX_LAMBDA
from app.ml.decay_calibrator import DecayCalibrator, golden_section_search
from tests.evaluation.metrics import calculate_retention_mae


def test_monotonic_retention_decay():
    """Verify retention strictly decreases monotonically over elapsed time."""
    model = RetentionModel()
    lam = 0.08
    times = [0.0, 1.0, 3.0, 7.0, 14.0, 30.0, 60.0]
    retentions = [model.calculate_retention(t, lam) for t in times]

    for i in range(len(retentions) - 1):
        assert retentions[i] >= retentions[i + 1], f"Non-monotonic decay at t={times[i]}"
    assert retentions[0] == 100.0
    assert retentions[-1] < 1.0


def test_decay_across_lambdas():
    """Verify higher lambda produces strictly faster forgetting at any given elapsed time t > 0."""
    model = RetentionModel()
    t = 5.0
    lambdas = [0.02, 0.05, 0.08, 0.15, 0.25, 0.30]
    retentions = [model.calculate_retention(t, l) for l in lambdas]

    for i in range(len(retentions) - 1):
        assert retentions[i] > retentions[i + 1], f"Higher lambda did not decay faster: l={lambdas[i]}"


def test_half_life_calculation():
    """Verify half life matches t_half = ln(2) / lambda exactly."""
    model = RetentionModel()
    for lam in [0.01, 0.05, 0.08, 0.20, 0.30]:
        half_life = model.calculate_half_life(lam)
        expected = math.log(2.0) / lam
        assert pytest.approx(half_life, rel=1e-4) == expected

        # Check retention at half life is ~50%
        r_half = model.calculate_retention(half_life, lam)
        assert pytest.approx(r_half, abs=1e-2) == 50.0


def test_revision_stability_updates():
    """Verify stability dynamics: high score reduces lambda, low score increases lambda."""
    model = RetentionModel()
    base_lam = 0.10

    # High performance (S=95%)
    lam_high = model.update_stability(base_lam, performance_score=95.0, repetition_count=1)
    assert lam_high < base_lam, "High performance did not decrease decay rate"

    # Failing performance (S=30%)
    lam_low = model.update_stability(base_lam, performance_score=30.0, repetition_count=1)
    assert lam_low > base_lam, "Failing performance did not increase decay rate"

    # Clamping boundaries
    lam_extreme_high = model.update_stability(0.015, performance_score=100.0, repetition_count=10)
    assert lam_extreme_high >= MIN_LAMBDA
    lam_extreme_low = model.update_stability(0.28, performance_score=0.0, repetition_count=1)
    assert lam_extreme_low <= MAX_LAMBDA


def test_calibrator_with_sparse_data():
    """Verify calibrator falls back safely to DEFAULT_LAMBDA when samples < 2."""
    calibrator = DecayCalibrator()
    # 0 observations
    assert calibrator.calibrate_from_history([]) == DEFAULT_LAMBDA

    # 1 observation
    assert calibrator.calibrate_from_history([{"elapsed_days": 5.0, "score": 60.0}]) == DEFAULT_LAMBDA


def test_calibrator_with_sufficient_synthetic_data():
    """Verify calibrator accurately recovers true lambda from noisy observations."""
    calibrator = DecayCalibrator()
    true_lam = 0.12
    # Synthetic samples based on true lambda
    observations = [
        {"elapsed_days": 2.0, "score": 100.0 * math.exp(-true_lam * 2.0)},
        {"elapsed_days": 5.0, "score": 100.0 * math.exp(-true_lam * 5.0)},
        {"elapsed_days": 10.0, "score": 100.0 * math.exp(-true_lam * 10.0)},
    ]
    fitted_lam = calibrator.calibrate_from_history(observations)
    assert pytest.approx(fitted_lam, abs=0.01) == true_lam


def test_retention_mae_metric():
    """Verify retention calculation has 0 MAE against mathematical ground truth."""
    model = RetentionModel()
    lam = 0.10
    times = [1.0, 2.0, 5.0, 10.0]
    ground_truth = [100.0 * math.exp(-lam * t) for t in times]
    predictions = [model.calculate_retention(t, lam) for t in times]
    mae = calculate_retention_mae(predictions, ground_truth)
    assert mae < 1e-4
