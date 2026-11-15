
"""
Runtime inference service for NeuroLearn retention predictions.

Supports:
- Single-topic prediction
- Batch prediction
- Model health monitoring
- Deterministic Ebbinghaus fallback
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ml.core.baselines import calculate_retention
from ml.models.registry import ModelRegistry, DEFAULT_REGISTRY_DIR
from ml.service.contracts import (
    PredictionRequestItem,
    PredictionResponseItem,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ServiceHealthResponse,
)


FALLBACK_MODEL_NAME = "ebbinghaus_baseline"
FALLBACK_MODEL_VERSION = "baseline-v1"


class RetentionInferenceService:
    """Runtime inference service for NeuroLearn retention predictions."""

    def __init__(
        self,
        registry_dir: str | Path = DEFAULT_REGISTRY_DIR,
        model_name: str = "retention_hist_gradient_boosting",
    ) -> None:
        self.registry = ModelRegistry(registry_dir)
        self.registry_path = str(registry_dir)
        self.model_name = model_name

        self.model_metadata = None
        self.model_bundle = None
        self.is_fallback_mode = False
        self.fallback_reason = None

        try:
            self.model_metadata = self.registry.get_active_model(model_name)

            if self.model_metadata is None:
                raise RuntimeError(
                    f"No active model found for '{model_name}'."
                )

            self.model_bundle = self.registry.load_bundle(model_name)

            if self.model_bundle is None:
                raise RuntimeError(
                    f"Failed to load model bundle for '{model_name}'."
                )

        except Exception as exc:
            self.is_fallback_mode = True
            self.fallback_reason = (
                f"ML model unavailable: {type(exc).__name__}: {exc}"
            )

    @property
    def model_version(self) -> str:
        """Return the version of the currently serving model."""
        if self.is_fallback_mode:
            return FALLBACK_MODEL_VERSION

        return self.model_metadata.model_version

    @property
    def active_model_name(self) -> str:
        """Return the model currently serving predictions."""
        if self.is_fallback_mode:
            return FALLBACK_MODEL_NAME

        return self.model_name

    def _fallback_probabilities(
        self,
        requests: list[PredictionRequestItem],
    ) -> list[float]:
        """Calculate deterministic Ebbinghaus fallback probabilities."""
        return [
            calculate_retention(
                elapsed_days=item.elapsed_days,
                stability_days=item.stability_days_prior,
            )
            for item in requests
        ]

    def _predict_probabilities(
        self,
        requests: list[PredictionRequestItem],
    ) -> tuple[list[float], bool, str | None]:
        """Predict probabilities using ML or the fallback baseline."""

        if self.is_fallback_mode:
            return (
                self._fallback_probabilities(requests),
                True,
                self.fallback_reason,
            )

        try:
            records = [
                item.to_feature_dict()
                for item in requests
            ]

            probabilities = np.asarray(
                self.model_bundle.predict_proba(records),
                dtype=np.float64,
            )

            if probabilities.shape != (len(requests), 2):
                raise ValueError(
                    f"Unexpected probability shape: {probabilities.shape}"
                )

            if (
                not np.all(np.isfinite(probabilities))
                or np.any(probabilities < 0.0)
                or np.any(probabilities > 1.0)
            ):
                raise ValueError(
                    "Model returned invalid probabilities."
                )

            return probabilities[:, 1].tolist(), False, None

        except Exception as exc:
            reason = (
                f"ML inference failed: {type(exc).__name__}: {exc}"
            )

            return (
                self._fallback_probabilities(requests),
                True,
                reason,
            )

    def _build_prediction(
        self,
        request: PredictionRequestItem,
        probability: float,
        is_fallback: bool,
        fallback_reason: str | None,
    ) -> PredictionResponseItem:
        """Build a standardized prediction response."""

        return PredictionResponseItem(
            user_id=request.user_id,
            topic_id=request.topic_id,
            predicted_retention_prob=float(probability),
            is_cold_start=request.user_prior_reviews_count == 0,
            model_name=(
                FALLBACK_MODEL_NAME
                if is_fallback
                else self.model_name
            ),
            model_version=(
                FALLBACK_MODEL_VERSION
                if is_fallback
                else self.model_version
            ),
            is_fallback=is_fallback,
            fallback_reason=fallback_reason,
            is_synthetic_model=not is_fallback,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def predict_one(
        self,
        request: PredictionRequestItem,
    ) -> PredictionResponseItem:
        """Predict calibrated recall probability for one topic."""

        request.validate()

        probabilities, is_fallback, reason = (
            self._predict_probabilities([request])
        )

        return self._build_prediction(
            request=request,
            probability=probabilities[0],
            is_fallback=is_fallback,
            fallback_reason=reason,
        )

    def predict_batch(
        self,
        request: BatchPredictionRequest | list[PredictionRequestItem],
    ) -> BatchPredictionResponse:
        """Predict calibrated recall probabilities for multiple topics.

        Accepts either a BatchPredictionRequest object or a list of
        PredictionRequestItem objects for compatibility with callers.
        """

        # Normalize list input into the expected DTO.
        if isinstance(request, list):
            request = BatchPredictionRequest(items=request)

        if not isinstance(request, BatchPredictionRequest):
            raise TypeError(
                "request must be a BatchPredictionRequest "
                "or list[PredictionRequestItem]."
            )

        # Validate the batch container and every individual item.
        request.validate()

        probabilities, is_fallback, reason = (
            self._predict_probabilities(request.items)
        )

        predictions = [
            self._build_prediction(
                request=item,
                probability=probabilities[index],
                is_fallback=is_fallback,
                fallback_reason=reason,
            )
            for index, item in enumerate(request.items)
        ]

        return BatchPredictionResponse(
            predictions=predictions,
            count=len(predictions),
            model_name=(
                FALLBACK_MODEL_NAME
                if is_fallback
                else self.model_name
            ),
            model_version=(
                FALLBACK_MODEL_VERSION
                if is_fallback
                else self.model_version
            ),
            is_fallback=is_fallback,
        )

    def health_check(self) -> ServiceHealthResponse:
        """Return runtime service and model health information."""

        is_calibrated = (
            not self.is_fallback_mode
            and self.model_bundle.calibrator is not None
            and self.model_bundle.calibrator.is_fitted_
        )

        if self.is_fallback_mode:
            status = "fallback"
        elif is_calibrated:
            status = "healthy"
        else:
            status = "degraded"

        return ServiceHealthResponse(
            status=status,
            active_model_name=self.active_model_name,
            active_model_version=self.model_version,
            is_calibrated=is_calibrated,
            is_fallback_mode=self.is_fallback_mode,
            registry_path=self.registry_path,
            notice=(
                "SYNTHETIC MODEL NOTICE: "
                "Trained on simulated interaction telemetry."
                if not self.is_fallback_mode
                else "FALLBACK NOTICE: "
                "Using deterministic Ebbinghaus retention baseline."
            ),
        )
