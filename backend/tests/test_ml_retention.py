"""
Unit Tests for NeuroLearn ML Retention Engine
=============================================
Tests:
- Retention calculation at 0 elapsed days
- Retention calculation after 1, 7, 14, and 30 days
- Memory half-life calculation: t_{1/2} = ln(2) / lambda
- Revision stability updates (successful recall vs poor recall)
- Lambda boundary conditions (0.01 to 0.30)
- Recommended revision interval calculation
- Decay calibration with synthetic historical data
- Insufficient data fallback (default lambda = 0.08)
- Feature extraction with valid, missing, and invalid records
"""

import math
from datetime import datetime, timezone, timedelta
import pytest

from app.ml.retention_model import (
    RetentionModel,
    retention_model,
    DEFAULT_LAMBDA,
    MIN_LAMBDA,
    MAX_LAMBDA,
)
from app.ml.decay_calibrator import (
    DecayCalibrator,
    decay_calibrator,
)
from app.ml.feature_extractor import (
    FeatureExtractor,
    feature_extractor,
    parse_datetime,
)


class TestRetentionModel:
    def test_retention_at_zero_elapsed_days(self):
        """At t=0, retention should be exactly 100%."""
        r = retention_model.calculate_retention(elapsed_days=0.0, decay_lambda=0.08)
        assert r == 100.0

    def test_retention_decay_curve(self):
        """Retention should decay exponentially over 1, 7, 14, and 30 days."""
        lam = 0.08
        r_1 = retention_model.calculate_retention(elapsed_days=1.0, decay_lambda=lam)
        r_7 = retention_model.calculate_retention(elapsed_days=7.0, decay_lambda=lam)
        r_14 = retention_model.calculate_retention(elapsed_days=14.0, decay_lambda=lam)
        r_30 = retention_model.calculate_retention(elapsed_days=30.0, decay_lambda=lam)

        # Theoretical values: 100 * exp(-0.08 * t)
        assert r_1 == pytest.approx(100.0 * math.exp(-0.08 * 1.0), rel=1e-3)
        assert r_7 == pytest.approx(100.0 * math.exp(-0.08 * 7.0), rel=1e-3)
        assert r_14 == pytest.approx(100.0 * math.exp(-0.08 * 14.0), rel=1e-3)
        assert r_30 == pytest.approx(100.0 * math.exp(-0.08 * 30.0), rel=1e-3)

        # Monotonically decreasing
        assert 100.0 > r_1 > r_7 > r_14 > r_30 > 0.0

    def test_negative_elapsed_days_handling(self):
        """Negative elapsed days should be treated as 0 (retention 100%)."""
        r = retention_model.calculate_retention(elapsed_days=-5.0, decay_lambda=0.08)
        assert r == 100.0

    def test_half_life_calculation(self):
        """Half-life must satisfy t_{1/2} = ln(2) / lambda."""
        lam = 0.08
        expected_half_life = math.log(2.0) / 0.08  # approx 8.664 days
        half_life = retention_model.calculate_half_life(lam)
        assert half_life == pytest.approx(expected_half_life, rel=1e-4)

        # At t = half_life, retention should be approx 50%
        r_half = retention_model.calculate_retention(elapsed_days=half_life, decay_lambda=lam)
        assert r_half == pytest.approx(50.0, rel=1e-3)

    def test_successful_revision_improves_stability(self):
        """A high score (>=80%) should decrease lambda (slower forgetting)."""
        current_lam = 0.10
        updated_lam = retention_model.update_stability(
            current_lambda=current_lam,
            performance_score=95.0,
            repetition_count=1,
        )
        assert updated_lam < current_lam
        assert updated_lam >= MIN_LAMBDA

    def test_failed_revision_increases_decay_rate(self):
        """A low score (<60%) should increase lambda (faster forgetting)."""
        current_lam = 0.08
        updated_lam = retention_model.update_stability(
            current_lambda=current_lam,
            performance_score=40.0,
            repetition_count=1,
        )
        assert updated_lam > current_lam
        assert updated_lam <= MAX_LAMBDA

    def test_lambda_boundary_enforcement(self):
        """Lambda must strictly remain within [0.01, 0.30]."""
        # Underflow attempt
        clamped_low = retention_model.sanitize_lambda(0.001)
        assert clamped_low == MIN_LAMBDA

        # Overflow attempt
        clamped_high = retention_model.sanitize_lambda(0.95)
        assert clamped_high == MAX_LAMBDA

        # Repeated 100% updates should not breach MIN_LAMBDA
        lam = 0.02
        for _ in range(10):
            lam = retention_model.update_stability(lam, 100.0)
        assert lam >= MIN_LAMBDA

        # Repeated 0% updates should not breach MAX_LAMBDA
        lam = 0.25
        for _ in range(10):
            lam = retention_model.update_stability(lam, 0.0)
        assert lam <= MAX_LAMBDA

    def test_recommended_interval(self):
        """Interval calculation should return positive integer days to reach target retention."""
        lam = 0.08
        target = 70.0
        expected_days = round(-math.log(0.70) / 0.08)  # ~ 4.45 -> 4 days
        interval = retention_model.calculate_recommended_interval(lam, target)
        assert interval == expected_days
        assert interval >= 1

    def test_invalid_and_nan_inputs(self):
        """Invalid or NaN lambda should gracefully fallback to default_lambda."""
        assert retention_model.sanitize_lambda(None) == DEFAULT_LAMBDA
        assert retention_model.sanitize_lambda(float("nan")) == DEFAULT_LAMBDA
        assert retention_model.sanitize_lambda("invalid") == DEFAULT_LAMBDA


class TestDecayCalibrator:
    def test_insufficient_data_fallback(self):
        """When fewer than 2 valid observations exist, return default lambda (0.08)."""
        calibrator = DecayCalibrator()
        assert calibrator.calibrate_from_observations([]) == DEFAULT_LAMBDA
        assert calibrator.calibrate_from_observations([(3.0, 80.0, 1.0)]) == DEFAULT_LAMBDA

    def test_decay_calibration_with_synthetic_data(self):
        """Calibrator should accurately fit lambda from synthetic Ebbinghaus data."""
        true_lambda = 0.12
        # Generate synthetic points: t = 2, 5, 10 days
        observations = [
            (2.0, 100.0 * math.exp(-true_lambda * 2.0), 1.0),
            (5.0, 100.0 * math.exp(-true_lambda * 5.0), 1.0),
            (10.0, 100.0 * math.exp(-true_lambda * 10.0), 1.0),
        ]

        calibrator = DecayCalibrator()
        fitted_lambda = calibrator.calibrate_from_observations(observations)
        assert fitted_lambda == pytest.approx(true_lambda, rel=1e-2)

    def test_calibration_clamping_to_boundaries(self):
        """Extremely steep decay should clamp to MAX_LAMBDA (0.30)."""
        # Very steep decay: score drops to 1% by day 2
        observations = [
            (1.0, 10.0, 1.0),
            (2.0, 1.0, 1.0),
        ]
        calibrator = DecayCalibrator()
        fitted = calibrator.calibrate_from_observations(observations)
        assert fitted <= MAX_LAMBDA

    def test_calibration_from_history_dicts(self):
        """Verify calibration directly from entity history dicts."""
        history = [
            {"interval_days": 3, "score": 75.0},
            {"interval_days": 7, "score": 55.0},
        ]
        quizzes = [
            {"elapsed_days": 5, "score": 65.0},
        ]
        calibrator = DecayCalibrator()
        calibrated_lam = calibrator.calibrate_from_history(history, quizzes)
        assert MIN_LAMBDA <= calibrated_lam <= MAX_LAMBDA


class TestFeatureExtractor:
    def test_extract_elapsed_days_with_valid_dates(self):
        ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        past_time = ref_time - timedelta(days=3, hours=12)  # 3.5 days

        elapsed = feature_extractor.extract_elapsed_days(past_time, ref_time)
        assert elapsed == pytest.approx(3.5, rel=1e-4)

    def test_extract_elapsed_days_with_none_or_future(self):
        ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
        future_time = ref_time + timedelta(days=2)

        # None should yield 0.0
        assert feature_extractor.extract_elapsed_days(None, ref_time) == 0.0
        # Future should be clamped to 0.0
        assert feature_extractor.extract_elapsed_days(future_time, ref_time) == 0.0

    def test_extract_topic_features(self):
        topic_dict = {
            "id": "top-123",
            "name": "Bayesian Networks",
            "difficulty": "Hard",
            "mastery_score": 85.0,
            "retention_score": 68.0,
            "decay_rate_lambda": 0.09,
            "last_revised": "2026-11-20T12:00:00Z",
            "completed": True,
        }
        ref_time = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

        features = feature_extractor.extract_topic_features(topic_dict, ref_time)
        assert features["topic_id"] == "top-123"
        assert features["name"] == "Bayesian Networks"
        assert features["mastery_score"] == 85.0
        assert features["retention_score"] == 68.0
        assert features["decay_lambda"] == 0.09
        assert features["elapsed_days"] == pytest.approx(5.0, rel=1e-2)
        assert features["completed"] is True

    def test_extract_topic_features_missing_data_fallbacks(self):
        # Empty dict should yield clean safe defaults
        features = feature_extractor.extract_topic_features({})
        assert features["mastery_score"] == 50.0
        assert features["retention_score"] == 70.0
        assert features["decay_lambda"] == 0.08
        assert features["elapsed_days"] == 0.0
