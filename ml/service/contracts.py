"""
Data Transfer Objects (DTOs) and API Contracts for Retention Inference Service.

Designed for seamless integration with Member 3's backend:
- Standard library dataclasses with dict/JSON serialization.
- Fully compatible with FastAPI request/response schema specifications.
- Strict input validation against domain physical constraints.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Any, Final, Sequence

from ml.config import (
    DEFAULT_DIFFICULTY,
    MAX_DIFFICULTY,
    MAX_MASTERY,
    MIN_DIFFICULTY,
    MIN_MASTERY,
    VALID_RATINGS,
)
from ml.data.schemas import MODEL_FEATURE_NAMES


@dataclass
class PredictionRequestItem:
    """
    Request payload representing a student's review interaction state for a topic.
    Provides all historical features strictly prior to the scheduled review.
    """

    user_id: str
    topic_id: str

    elapsed_days: float
    stability_days_prior: float
    repetition_count_prior: int = 0
    topic_difficulty_prior: float = DEFAULT_DIFFICULTY
    last_rating_prior: int | None = None

    user_prior_recall_rate: float = 0.0
    user_prior_reviews_count: int = 0
    topic_prior_quiz_avg: float | None = None
    has_prior_quiz: int = 0

    def validate(self) -> None:
        """
        Validates data types and physical boundaries.

        Raises:
            ValueError: If any input field is invalid or out of bounds.
        """
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError(f"user_id must be a non-empty string, got {self.user_id!r}")
        if not self.topic_id or not isinstance(self.topic_id, str):
            raise ValueError(f"topic_id must be a non-empty string, got {self.topic_id!r}")

        # Elapsed days must be non-negative and finite
        if not isinstance(self.elapsed_days, (int, float)) or not math.isfinite(self.elapsed_days) or self.elapsed_days < 0.0:
            raise ValueError(f"elapsed_days must be finite and >= 0.0, got {self.elapsed_days}")

        # Stability days must be strictly positive and finite
        if not isinstance(self.stability_days_prior, (int, float)) or not math.isfinite(self.stability_days_prior) or self.stability_days_prior <= 0.0:
            raise ValueError(f"stability_days_prior must be finite and > 0.0, got {self.stability_days_prior}")

        # Repetition count non-negative int
        if not isinstance(self.repetition_count_prior, int) or self.repetition_count_prior < 0:
            raise ValueError(f"repetition_count_prior must be an int >= 0, got {self.repetition_count_prior}")

        # Topic difficulty in [0.1, 1.0]
        if not isinstance(self.topic_difficulty_prior, (int, float)) or not (MIN_DIFFICULTY <= self.topic_difficulty_prior <= MAX_DIFFICULTY):
            raise ValueError(f"topic_difficulty_prior must be in [{MIN_DIFFICULTY}, {MAX_DIFFICULTY}], got {self.topic_difficulty_prior}")

        # Last rating prior (nullable)
        if self.last_rating_prior is not None:
            if self.last_rating_prior not in VALID_RATINGS:
                raise ValueError(f"last_rating_prior must be None or in {VALID_RATINGS}, got {self.last_rating_prior}")

        # User prior recall rate in [0.0, 1.0]
        if not isinstance(self.user_prior_recall_rate, (int, float)) or not (0.0 <= self.user_prior_recall_rate <= 1.0):
            raise ValueError(f"user_prior_recall_rate must be in [0.0, 1.0], got {self.user_prior_recall_rate}")

        # User prior reviews count non-negative int
        if not isinstance(self.user_prior_reviews_count, int) or self.user_prior_reviews_count < 0:
            raise ValueError(f"user_prior_reviews_count must be an int >= 0, got {self.user_prior_reviews_count}")

        # Prior quiz average and flag
        if self.has_prior_quiz not in (0, 1):
            raise ValueError(f"has_prior_quiz must be 0 or 1, got {self.has_prior_quiz}")
        if self.has_prior_quiz == 1:
            if self.topic_prior_quiz_avg is None or not (MIN_MASTERY <= self.topic_prior_quiz_avg <= MAX_MASTERY):
                raise ValueError(
                    f"When has_prior_quiz=1, topic_prior_quiz_avg must be in [{MIN_MASTERY}, {MAX_MASTERY}], got {self.topic_prior_quiz_avg}"
                )
        else:
            if self.topic_prior_quiz_avg is not None:
                raise ValueError(
                    f"When has_prior_quiz=0, topic_prior_quiz_avg must be None, got {self.topic_prior_quiz_avg}"
                )

    def to_feature_dict(self) -> dict[str, Any]:
        """Converts request to feature dictionary format expected by RetentionFeaturePreprocessor."""
        return {
            "elapsed_days": float(self.elapsed_days),
            "stability_days_prior": float(self.stability_days_prior),
            "repetition_count_prior": int(self.repetition_count_prior),
            "topic_difficulty_prior": float(self.topic_difficulty_prior),
            "last_rating_prior": self.last_rating_prior,
            "user_prior_recall_rate": float(self.user_prior_recall_rate),
            "user_prior_reviews_count": int(self.user_prior_reviews_count),
            "topic_prior_quiz_avg": float(self.topic_prior_quiz_avg) if self.topic_prior_quiz_avg is not None else None,
            "has_prior_quiz": int(self.has_prior_quiz),
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionRequestItem":
        item = cls(
            user_id=str(data["user_id"]),
            topic_id=str(data["topic_id"]),
            elapsed_days=float(data["elapsed_days"]),
            stability_days_prior=float(data["stability_days_prior"]),
            repetition_count_prior=int(data.get("repetition_count_prior", 0)),
            topic_difficulty_prior=float(data.get("topic_difficulty_prior", DEFAULT_DIFFICULTY)),
            last_rating_prior=(
                int(data["last_rating_prior"])
                if data.get("last_rating_prior") is not None and str(data["last_rating_prior"]).strip() != ""
                else None
            ),
            user_prior_recall_rate=float(data.get("user_prior_recall_rate", 0.0)),
            user_prior_reviews_count=int(data.get("user_prior_reviews_count", 0)),
            topic_prior_quiz_avg=(
                float(data["topic_prior_quiz_avg"])
                if data.get("topic_prior_quiz_avg") is not None and str(data["topic_prior_quiz_avg"]).strip() != ""
                else None
            ),
            has_prior_quiz=int(data.get("has_prior_quiz", 0)),
        )
        item.validate()
        return item


@dataclass
class BatchPredictionRequest:
    """Batch prediction request container."""
    items: list[PredictionRequestItem]

    def validate(self) -> None:
        if not self.items:
            raise ValueError("Batch prediction request items list cannot be empty.")
        for item in self.items:
            item.validate()

    def to_dict(self) -> dict[str, Any]:
        return {"items": [item.to_dict() for item in self.items]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchPredictionRequest":
        items = [PredictionRequestItem.from_dict(d) for d in data.get("items", [])]
        req = cls(items=items)
        req.validate()
        return req


@dataclass(frozen=True)
class PredictionResponseItem:
    """
    Response payload for a single topic recall prediction.
    Contains calibrated retention probability alongside provenance and fallback metadata.
    """
    user_id: str
    topic_id: str
    predicted_retention_prob: float
    is_cold_start: bool
    model_name: str
    model_version: str
    is_fallback: bool
    fallback_reason: str | None
    is_synthetic_model: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BatchPredictionResponse:
    """Batch prediction response container."""
    predictions: list[PredictionResponseItem]
    count: int
    model_name: str
    model_version: str
    is_fallback: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "predictions": [p.to_dict() for p in self.predictions],
            "count": self.count,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "is_fallback": self.is_fallback,
        }


@dataclass(frozen=True)
class ServiceHealthResponse:
    """Service status and champion model telemetry."""
    status: str  # "healthy", "degraded", "fallback"
    active_model_name: str
    active_model_version: str
    is_calibrated: bool
    is_fallback_mode: bool
    registry_path: str
    notice: str = "SYNTHETIC MODEL NOTICE: Trained on simulated interaction telemetry."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
