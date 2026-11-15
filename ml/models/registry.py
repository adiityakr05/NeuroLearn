"""
Lightweight, Safe Model Registry and JSON Artifact Persistence for Retention Models.

Guarantees:
- Safe, explicit serialization strategy: Zero pickle or joblib usage to prevent RCE vulnerabilities.
- Human-readable JSON artifacts containing all preprocessor parameters, model weights/trees,
  calibrator slopes/intercepts, and metadata.
- Immutability: Prevents accidental overwriting of existing model versions.
- Deterministic, transparent model selection based on validation metrics.
"""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any, Final, Sequence
import numpy as np

from ml.data.preprocessor import RetentionFeaturePreprocessor
from ml.models.calibrator import PlattCalibrator
from ml.models.trainer import (
    NumpyHistGradientBoostingClassifier,
    ScipyLogisticRegression,
    _HistTreeNode,
)

DEFAULT_REGISTRY_DIR: Final[str] = "ml/registry"
INDEX_FILENAME: Final[str] = "registry_index.json"
ARTIFACTS_DIRNAME: Final[str] = "artifacts"
REGISTRY_FORMAT_VERSION: Final[str] = "1.0"


# -------------------------------------------------------------------------
# Serialization Helpers for Model Components
# -------------------------------------------------------------------------

def _serialize_tree_node(node: _HistTreeNode) -> dict[str, Any]:
    """Recursively serializes a decision tree node to a pure dictionary."""
    if node.is_leaf:
        return {
            "is_leaf": True,
            "leaf_value": float(node.leaf_value),
        }
    assert node.left_child is not None and node.right_child is not None
    return {
        "is_leaf": False,
        "split_feature": int(node.split_feature),
        "split_bin": int(node.split_bin),
        "left": _serialize_tree_node(node.left_child),
        "right": _serialize_tree_node(node.right_child),
    }


def _deserialize_tree_node(d: dict[str, Any]) -> _HistTreeNode:
    """Recursively reconstructs a decision tree node from a dictionary."""
    if d["is_leaf"]:
        return _HistTreeNode(
            is_leaf=True,
            leaf_value=float(d["leaf_value"]),
        )
    return _HistTreeNode(
        is_leaf=False,
        split_feature=int(d["split_feature"]),
        split_bin=int(d["split_bin"]),
        left_child=_deserialize_tree_node(d["left"]),
        right_child=_deserialize_tree_node(d["right"]),
    )


def serialize_preprocessor(prep: RetentionFeaturePreprocessor) -> dict[str, Any]:
    """Serializes a fitted RetentionFeaturePreprocessor to a dictionary."""
    if not prep.is_fitted_:
        raise ValueError("Cannot serialize an unfitted preprocessor.")
    return {
        "scale_features": prep.scale_features,
        "impute_last_rating": prep.impute_last_rating_,
        "impute_quiz_avg": prep.impute_quiz_avg_,
        "mean": prep.mean_.tolist() if prep.mean_ is not None else None,
        "scale": prep.scale_.tolist() if prep.scale_ is not None else None,
        "feature_names_out": prep.get_feature_names_out(),
    }


def deserialize_preprocessor(d: dict[str, Any]) -> RetentionFeaturePreprocessor:
    """Reconstructs a RetentionFeaturePreprocessor from a dictionary."""
    prep = RetentionFeaturePreprocessor(scale_features=bool(d["scale_features"]))
    prep.impute_last_rating_ = float(d["impute_last_rating"])
    prep.impute_quiz_avg_ = float(d["impute_quiz_avg"])
    prep.mean_ = np.array(d["mean"], dtype=np.float64) if d["mean"] is not None else None
    prep.scale_ = np.array(d["scale"], dtype=np.float64) if d["scale"] is not None else None
    prep.is_fitted_ = True
    return prep


def serialize_model(
    model: ScipyLogisticRegression | NumpyHistGradientBoostingClassifier,
) -> dict[str, Any]:
    """Serializes a supported retention model to a dictionary."""
    if not getattr(model, "is_fitted_", False):
        raise ValueError("Cannot serialize an unfitted model.")

    if isinstance(model, ScipyLogisticRegression):
        assert model.coef_ is not None and model.intercept_ is not None
        return {
            "model_type": "ScipyLogisticRegression",
            "C": float(model.C),
            "coef": model.coef_.tolist(),
            "intercept": model.intercept_.tolist(),
            "n_iter": int(model.n_iter_),
            "classes": model.classes_.tolist(),
        }
    elif isinstance(model, NumpyHistGradientBoostingClassifier):
        return {
            "model_type": "NumpyHistGradientBoostingClassifier",
            "max_iter": int(model.max_iter),
            "max_depth": int(model.max_depth),
            "learning_rate": float(model.learning_rate),
            "l2_regularization": float(model.l2_regularization),
            "min_samples_leaf": int(model.min_samples_leaf),
            "n_bins": int(model.n_bins),
            "init_raw_prediction": float(model.init_raw_prediction_),
            "bin_edges": [e.tolist() for e in model.bin_edges_],
            "trees": [_serialize_tree_node(t) for t in model.trees_],
            "classes": model.classes_.tolist(),
        }
    else:
        raise ValueError(f"Unsupported model type for serialization: {type(model)}")


def deserialize_model(
    d: dict[str, Any],
) -> ScipyLogisticRegression | NumpyHistGradientBoostingClassifier:
    """Reconstructs a retention model from a dictionary."""
    model_type = d.get("model_type")
    if model_type == "ScipyLogisticRegression":
        model = ScipyLogisticRegression(C=float(d["C"]))
        model.coef_ = np.array(d["coef"], dtype=np.float64)
        model.intercept_ = np.array(d["intercept"], dtype=np.float64)
        model.n_iter_ = int(d["n_iter"])
        model.classes_ = np.array(d["classes"], dtype=np.int32)
        model.is_fitted_ = True
        return model
    elif model_type == "NumpyHistGradientBoostingClassifier":
        gb = NumpyHistGradientBoostingClassifier(
            max_iter=int(d["max_iter"]),
            max_depth=int(d["max_depth"]),
            learning_rate=float(d["learning_rate"]),
            l2_regularization=float(d["l2_regularization"]),
            min_samples_leaf=int(d["min_samples_leaf"]),
            n_bins=int(d["n_bins"]),
        )
        gb.init_raw_prediction_ = float(d["init_raw_prediction"])
        gb.bin_edges_ = [np.array(e, dtype=np.float64) for e in d["bin_edges"]]
        gb.trees_ = [_deserialize_tree_node(t) for t in d["trees"]]
        gb.classes_ = np.array(d["classes"], dtype=np.int32)
        gb.is_fitted_ = True
        return gb
    else:
        raise ValueError(f"Unknown model_type in serialized artifact: {model_type}")


# -------------------------------------------------------------------------
# Bundle and Registry Metadata Containers
# -------------------------------------------------------------------------

@dataclass
class ModelArtifactBundle:
    """
    Complete bundle containing preprocessor, core model, optional calibrator,
    and associated evaluation metadata.
    """
    model_name: str
    model_version: str
    model_type: str
    preprocessor: RetentionFeaturePreprocessor
    model: ScipyLogisticRegression | NumpyHistGradientBoostingClassifier
    calibrator: PlattCalibrator | None
    training_dataset_id: str
    training_timestamp: str
    validation_metrics: dict[str, Any]
    test_metrics: dict[str, Any] | None = None
    is_synthetic: bool = True
    metadata: dict[str, Any] | None = None

    def predict_proba(self, records: Sequence[Any]) -> np.ndarray:
        """
        End-to-end inference convenience method:
        Records -> Preprocessor -> Model -> Calibrator (if present) -> Calibrated Probabilities.
        """
        X = self.preprocessor.transform(records)
        raw_probs = self.model.predict_proba(X)
        if self.calibrator is not None and self.calibrator.is_fitted_:
            return self.calibrator.predict_proba(raw_probs)
        return raw_probs


@dataclass(frozen=True)
class ModelMetadata:
    """Registry record entry stored in index."""
    model_name: str
    model_version: str
    model_type: str
    created_at: str
    dataset_id: str
    is_synthetic: bool
    is_calibrated: bool
    status: str  # "candidate", "active", "archived"
    brier_score_val: float
    log_loss_val: float
    roc_auc_val: float | None
    artifact_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# -------------------------------------------------------------------------
# Model Registry Engine
# -------------------------------------------------------------------------

class ModelRegistry:
    """
    File-based, safe Model Registry managing versioning, JSON artifacts,
    and active model promotion.
    """

    def __init__(self, registry_dir: str = DEFAULT_REGISTRY_DIR) -> None:
        self.registry_dir = Path(registry_dir)
        self.artifacts_dir = self.registry_dir / ARTIFACTS_DIRNAME
        self.index_path = self.registry_dir / INDEX_FILENAME

        # Ensure directories exist
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        if not self.index_path.exists():
            self._save_index({"format_version": REGISTRY_FORMAT_VERSION, "models": []})

    def _load_index(self) -> dict[str, Any]:
        with open(self.index_path, mode="r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, data: dict[str, Any]) -> None:
        with open(self.index_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register_model(
        self,
        bundle: ModelArtifactBundle,
        status: str = "candidate",
    ) -> ModelMetadata:
        """
        Registers a new model bundle and saves its JSON artifact.

        Raises:
            ValueError: If a model with identical name and version is already registered.
        """
        if status not in ("candidate", "active", "archived"):
            raise ValueError(f"Invalid status '{status}', must be candidate/active/archived.")

        index_data = self._load_index()
        existing = [
            m for m in index_data["models"]
            if m["model_name"] == bundle.model_name and m["model_version"] == bundle.model_version
        ]
        if existing:
            raise ValueError(
                f"Model '{bundle.model_name}' version '{bundle.model_version}' is already registered. "
                "Overwriting existing model versions is strictly prohibited."
            )

        # Build clean JSON artifact
        artifact_filename = f"{bundle.model_name}_{bundle.model_version}.json"
        artifact_full_path = self.artifacts_dir / artifact_filename

        artifact_payload = {
            "format_version": REGISTRY_FORMAT_VERSION,
            "model_name": bundle.model_name,
            "model_version": bundle.model_version,
            "model_type": bundle.model_type,
            "training_dataset_id": bundle.training_dataset_id,
            "training_timestamp": bundle.training_timestamp,
            "is_synthetic": bundle.is_synthetic,
            "preprocessor": serialize_preprocessor(bundle.preprocessor),
            "model": serialize_model(bundle.model),
            "calibrator": bundle.calibrator.to_dict() if bundle.calibrator is not None else None,
            "validation_metrics": bundle.validation_metrics,
            "test_metrics": bundle.test_metrics,
            "metadata": bundle.metadata or {},
        }

        with open(artifact_full_path, mode="w", encoding="utf-8") as f:
            json.dump(artifact_payload, f, indent=2)

        # Extract validation metrics for index
        val_metrics = bundle.validation_metrics or {}
        brier_val = float(val_metrics.get("brier_score", 1.0))
        log_loss_val = float(val_metrics.get("log_loss", float("inf")))
        roc_auc_val = val_metrics.get("roc_auc")
        if roc_auc_val is not None:
            roc_auc_val = float(roc_auc_val)

        meta = ModelMetadata(
            model_name=bundle.model_name,
            model_version=bundle.model_version,
            model_type=bundle.model_type,
            created_at=bundle.training_timestamp,
            dataset_id=bundle.training_dataset_id,
            is_synthetic=bundle.is_synthetic,
            is_calibrated=bool(bundle.calibrator is not None and bundle.calibrator.is_fitted_),
            status=status,
            brier_score_val=brier_val,
            log_loss_val=log_loss_val,
            roc_auc_val=roc_auc_val,
            artifact_path=str(artifact_full_path.as_posix()),
        )

        index_data["models"].append(meta.to_dict())
        self._save_index(index_data)
        return meta

    def list_models(self, model_name: str | None = None) -> list[ModelMetadata]:
        """Lists all registered models, optionally filtered by model_name."""
        index_data = self._load_index()
        records: list[ModelMetadata] = []
        for m in index_data["models"]:
            if model_name is None or m["model_name"] == model_name:
                records.append(ModelMetadata(**m))
        return records

    def get_model_metadata(
        self,
        model_name: str,
        version: str | None = None,
    ) -> ModelMetadata:
        """
        Retrieves metadata for a model.
        If version is omitted, returns the active version, or latest registered if none active.
        """
        models = self.list_models(model_name)
        if not models:
            raise KeyError(f"No models registered with name '{model_name}'.")

        if version is not None:
            for m in models:
                if m.model_version == version:
                    return m
            raise KeyError(f"Model '{model_name}' has no version '{version}'.")

        # Find active model first
        for m in models:
            if m.status == "active":
                return m
        # Default to latest registered
        return models[-1]

    def set_active_model(self, model_name: str, version: str) -> ModelMetadata:
        """
        Sets the specified model version to 'active' and marks all other versions
        of this model as 'archived'.
        """
        index_data = self._load_index()
        found = False
        target_meta: ModelMetadata | None = None

        for m in index_data["models"]:
            if m["model_name"] == model_name:
                if m["model_version"] == version:
                    m["status"] = "active"
                    found = True
                    target_meta = ModelMetadata(**m)
                else:
                    m["status"] = "archived"

        if not found or target_meta is None:
            raise KeyError(f"Model '{model_name}' with version '{version}' not found in registry.")

        self._save_index(index_data)
        return target_meta

    def get_active_model(self, model_name: str | None = None) -> ModelMetadata | None:
        """Returns the currently active model metadata, if any."""
        models = self.list_models(model_name)
        for m in models:
            if m.status == "active":
                return m
        return None

    def load_bundle(
        self,
        model_name: str,
        version: str | None = None,
    ) -> ModelArtifactBundle:
        """
        Loads and reconstructs the complete ModelArtifactBundle from its JSON artifact.
        Guarantees zero use of pickle or arbitrary code execution.
        """
        meta = self.get_model_metadata(model_name, version)
        artifact_path = Path(meta.artifact_path)

        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact file not found at: {artifact_path}")

        with open(artifact_path, mode="r", encoding="utf-8") as f:
            payload = json.load(f)

        preprocessor = deserialize_preprocessor(payload["preprocessor"])
        model = deserialize_model(payload["model"])

        calibrator: PlattCalibrator | None = None
        if payload.get("calibrator") is not None:
            calibrator = PlattCalibrator.from_dict(payload["calibrator"])

        return ModelArtifactBundle(
            model_name=payload["model_name"],
            model_version=payload["model_version"],
            model_type=payload["model_type"],
            preprocessor=preprocessor,
            model=model,
            calibrator=calibrator,
            training_dataset_id=payload["training_dataset_id"],
            training_timestamp=payload["training_timestamp"],
            validation_metrics=payload["validation_metrics"],
            test_metrics=payload.get("test_metrics"),
            is_synthetic=bool(payload.get("is_synthetic", True)),
            metadata=payload.get("metadata"),
        )

    def select_and_promote_best_model(
        self,
        model_name: str | None = None,
        metric: str = "brier_score",
    ) -> ModelMetadata:
        """
        Deterministic model promotion:
        Evaluates registered models by validation score (lowest Brier score or log loss)
        and sets the champion model to 'active'.
        """
        candidates = self.list_models(model_name)
        if not candidates:
            raise ValueError("No candidates available for model promotion.")

        if metric == "brier_score":
            best = min(candidates, key=lambda m: m.brier_score_val)
        elif metric == "log_loss":
            best = min(candidates, key=lambda m: m.log_loss_val)
        elif metric == "roc_auc":
            best = max(candidates, key=lambda m: m.roc_auc_val or -1.0)
        else:
            raise ValueError(f"Unsupported selection metric: '{metric}'")

        return self.set_active_model(best.model_name, best.model_version)
