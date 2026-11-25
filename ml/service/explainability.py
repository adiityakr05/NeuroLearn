
"""
Explainability service for NeuroLearn retention predictions.

Supports:
- Logistic regression feature contributions.
- Gradient boosting decision-path explanations.
- Ebbinghaus fallback explanations.
- Raw and calibrated probability reporting.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ml.data.preprocessor import TRANSFORMED_FEATURE_NAMES
from ml.models.trainer import (
    ScipyLogisticRegression,
    NumpyHistGradientBoostingClassifier,
)
from ml.service.inference import (
    RetentionInferenceService,
    FALLBACK_MODEL_NAME,
    FALLBACK_MODEL_VERSION,
)


class RetentionExplainabilityService:
    """Generate transparent explanations for retention predictions."""

    def __init__(
        self,
        inference_service: RetentionInferenceService,
    ) -> None:
        if not isinstance(inference_service, RetentionInferenceService):
            raise TypeError(
                "inference_service must be a "
                "RetentionInferenceService instance."
            )

        self.inference_service = inference_service

    @property
    def feature_names(self) -> list[str]:
        return list(TRANSFORMED_FEATURE_NAMES)

    @property
    def active_model_name(self) -> str:
        return self.inference_service.active_model_name

    @property
    def active_model_version(self) -> str:
        return self.inference_service.model_version

    def _explain_fallback(
        self,
        request: Any,
        probability: float,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        """Explain a deterministic Ebbinghaus fallback prediction."""

        elapsed_days = float(request.elapsed_days)
        stability_days = float(request.stability_days_prior)

        return {
            "explanation_type": "ebbinghaus_baseline",
            "model_name": FALLBACK_MODEL_NAME,
            "model_version": FALLBACK_MODEL_VERSION,
            "is_fallback": True,
            "fallback_reason": fallback_reason,
            "predicted_retention_probability": float(probability),
            "formula": "R(t) = exp(-t / S)",
            "inputs": {
                "elapsed_days": elapsed_days,
                "stability_days": stability_days,
            },
            "disclaimer": (
                "This is a deterministic mathematical baseline, "
                "not an ML feature-attribution explanation."
            ),
        }

    def _explain_logistic_regression(
        self,
        transformed_features: np.ndarray,
        final_probability: float,
    ) -> dict[str, Any]:
        """Explain logistic regression using exact log-odds contributions."""

        bundle = self.inference_service.model_bundle
        model = bundle.model

        if not isinstance(model, ScipyLogisticRegression):
            raise TypeError("Active model is not logistic regression.")

        if (
            not model.is_fitted_
            or model.coef_ is None
            or model.intercept_ is None
        ):
            raise RuntimeError("Logistic regression model is not fitted.")

        values = np.asarray(
            transformed_features,
            dtype=np.float64,
        ).reshape(-1)

        if len(values) != len(self.feature_names):
            raise ValueError("Unexpected transformed feature count.")

        coefficients = model.coef_[0]
        intercept = float(model.intercept_[0])

        contributions = values * coefficients
        raw_log_odds = float(intercept + np.sum(contributions))

        raw_probability = float(
            model.predict_proba(values.reshape(1, -1))[0, 1]
        )

        feature_contributions = []

        for index, feature_name in enumerate(self.feature_names):
            contribution = float(contributions[index])

            feature_contributions.append({
                "feature": feature_name,
                "transformed_value": float(values[index]),
                "coefficient": float(coefficients[index]),
                "log_odds_contribution": contribution,
                "direction": (
                    "increases"
                    if contribution > 0
                    else "decreases"
                    if contribution < 0
                    else "neutral"
                ),
            })

        feature_contributions.sort(
            key=lambda item: abs(item["log_odds_contribution"]),
            reverse=True,
        )

        calibrator = bundle.calibrator
        is_calibrated = (
            calibrator is not None
            and calibrator.is_fitted_
        )

        return {
            "explanation_type": "logistic_regression",
            "model_name": self.active_model_name,
            "model_version": self.active_model_version,
            "is_fallback": False,
            "predicted_retention_probability": float(final_probability),
            "raw_probability": raw_probability,
            "calibrated_probability": float(final_probability),
            "is_calibrated": is_calibrated,
            "raw_log_odds": raw_log_odds,
            "intercept": intercept,
            "feature_contributions": feature_contributions,
            "contribution_scale": "raw_log_odds",
            "disclaimer": (
                "Feature contributions are additive in raw log-odds "
                "space, not direct probability changes."
            ),
        }

    def _explain_gradient_boosting(
        self,
        transformed_features: np.ndarray,
        final_probability: float,
    ) -> dict[str, Any]:
        """Explain a gradient boosting prediction through actual tree paths."""

        bundle = self.inference_service.model_bundle
        model = bundle.model

        if not isinstance(model, NumpyHistGradientBoostingClassifier):
            raise TypeError(
                "Active model is not gradient boosting."
            )

        if (
            not model.is_fitted_
            or model.bin_edges_ is None
            or model.init_raw_prediction_ is None
        ):
            raise RuntimeError(
                "Gradient boosting model is not fitted."
            )

        values = np.asarray(
            transformed_features,
            dtype=np.float64,
        ).reshape(-1)

        if len(values) != len(self.feature_names):
            raise ValueError(
                "Unexpected transformed feature count."
            )

        binned = model._bin_features(
            values.reshape(1, -1)
        )[0]

        raw_score = float(model.init_raw_prediction_)
        initial_raw_score = raw_score
        tree_paths = []

        for tree_index, tree in enumerate(model.trees_):
            node = tree
            splits = []

            while not node.is_leaf:
                feature_index = int(node.split_feature)
                split_bin = int(node.split_bin)

                if not 0 <= feature_index < len(self.feature_names):
                    raise RuntimeError(
                        "Tree contains an invalid feature index."
                    )

                observed_bin = int(binned[feature_index])
                edges = model.bin_edges_[feature_index]
                go_left = observed_bin <= split_bin

                if 0 <= split_bin < len(edges):
                    threshold = float(edges[split_bin])
                    operator = "<" if go_left else ">="
                else:
                    threshold = None
                    operator = (
                        "left_bin" if go_left else "right_bin"
                    )

                splits.append({
                    "feature": self.feature_names[feature_index],
                    "transformed_value": float(values[feature_index]),
                    "observed_bin": observed_bin,
                    "split_bin": split_bin,
                    "threshold": threshold,
                    "operator": operator,
                    "branch": "left" if go_left else "right",
                })

                node = (
                    node.left_child
                    if go_left
                    else node.right_child
                )

                if node is None:
                    raise RuntimeError(
                        "Invalid gradient boosting tree structure."
                    )

            leaf_value = float(node.leaf_value)
            tree_update = float(
                model.learning_rate * leaf_value
            )

            raw_score += tree_update

            tree_paths.append({
                "tree_index": tree_index,
                "splits": splits,
                "leaf_value": leaf_value,
                "learning_rate": float(model.learning_rate),
                "raw_score_contribution": tree_update,
            })

        clipped_score = float(
            np.clip(raw_score, -709.0, 709.0)
        )

        raw_probability = float(
            1.0 / (1.0 + np.exp(-clipped_score))
        )

        calibrator = bundle.calibrator
        is_calibrated = (
            calibrator is not None
            and calibrator.is_fitted_
        )

        return {
            "explanation_type": "gradient_boosting_tree_paths",
            "model_name": self.active_model_name,
            "model_version": self.active_model_version,
            "is_fallback": False,
            "predicted_retention_probability": float(final_probability),
            "raw_probability": raw_probability,
            "calibrated_probability": float(final_probability),
            "is_calibrated": is_calibrated,
            "initial_raw_score": initial_raw_score,
            "final_raw_score": raw_score,
            "tree_count": len(tree_paths),
            "tree_paths": tree_paths,
            "disclaimer": (
                "These are the actual decision paths and leaf updates "
                "for this prediction. They are not SHAP values or "
                "unique additive feature attributions."
            ),
        }
    def explain_one(
        self,
        request: Any,
    ) -> dict[str, Any]:
        """Generate an explanation matching the actual inference result."""

        request.validate()

        probabilities, is_fallback, fallback_reason = (
            self.inference_service._predict_probabilities([request])
        )

        final_probability = float(probabilities[0])

        if is_fallback:
            explanation = self._explain_fallback(
                request=request,
                probability=final_probability,
                fallback_reason=fallback_reason,
            )
        else:
            bundle = self.inference_service.model_bundle

            records = [request.to_feature_dict()]

            transformed = bundle.preprocessor.transform(records)[0]

            if isinstance(bundle.model, ScipyLogisticRegression):
                explanation = self._explain_logistic_regression(
                    transformed_features=transformed,
                    final_probability=final_probability,
                )

            elif isinstance(
                bundle.model,
                NumpyHistGradientBoostingClassifier,
            ):
                explanation = self._explain_gradient_boosting(
                    transformed_features=transformed,
                    final_probability=final_probability,
                )

            else:
                raise NotImplementedError(
                    "Explanations are not supported for model type "
                    f"{type(bundle.model).__name__}."
                )

        explanation["user_id"] = request.user_id
        explanation["topic_id"] = request.topic_id

        return explanation