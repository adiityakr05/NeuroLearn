"""
NeuroLearn Feature Extractor
============================
Transforms raw database entities (Topic, QuizAttempt, RevisionHistory) into clean,
validated feature dictionaries and observation vectors for ML retention modeling.
"""

import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple


def parse_datetime(dt_val: Any) -> Optional[datetime]:
    """Safely converts an ISO string or datetime object into an aware UTC datetime."""
    if dt_val is None:
        return None
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(timezone.utc)
    if isinstance(dt_val, str):
        try:
            # Handle standard ISO formats
            clean_str = dt_val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            # Attempt YYYY-MM-DD
            try:
                dt = datetime.strptime(dt_val[:10], "%Y-%m-%d")
                return dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None
    return None


class FeatureExtractor:
    """
    Extracts features for retention prediction and decay calibration.
    """

    @staticmethod
    def extract_elapsed_days(
        last_revised: Any,
        reference_time: Optional[datetime] = None,
    ) -> float:
        """
        Calculates non-negative elapsed days between last_revised and reference_time.
        If last_revised is None or invalid, returns 0.0.
        """
        if reference_time is None:
            ref_dt = datetime.now(timezone.utc)
        else:
            ref_dt = parse_datetime(reference_time) or datetime.now(timezone.utc)

        rev_dt = parse_datetime(last_revised)
        if rev_dt is None:
            return 0.0

        delta = ref_dt - rev_dt
        days = delta.total_seconds() / 86400.0
        return max(0.0, float(days))

    @staticmethod
    def extract_topic_features(
        topic: Any,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Extracts features from a Topic entity (SQLAlchemy model or dict).
        """
        if hasattr(topic, "__dict__"):
            topic_id = getattr(topic, "id", "")
            name = getattr(topic, "name", "")
            difficulty = getattr(topic, "difficulty", "Medium")
            mastery = getattr(topic, "mastery_score", 50.0)
            retention = getattr(topic, "retention_score", 70.0)
            decay_lambda = getattr(topic, "decay_rate_lambda", 0.08)
            last_revised = getattr(topic, "last_revised", None)
            completed = getattr(topic, "completed", False)
        elif isinstance(topic, dict):
            topic_id = topic.get("id", "")
            name = topic.get("name", "")
            difficulty = topic.get("difficulty", "Medium")
            mastery = topic.get("mastery_score", topic.get("mastery", 50.0))
            retention = topic.get("retention_score", topic.get("retention", 70.0))
            decay_lambda = topic.get("decay_rate_lambda", topic.get("decay_lambda", 0.08))
            last_revised = topic.get("last_revised")
            completed = topic.get("completed", False)
        else:
            return {
                "topic_id": "",
                "name": "",
                "difficulty": "Medium",
                "mastery_score": 50.0,
                "retention_score": 70.0,
                "decay_lambda": 0.08,
                "elapsed_days": 0.0,
                "completed": False,
            }

        elapsed_days = FeatureExtractor.extract_elapsed_days(last_revised, reference_time)

        # Sanitize numeric fields
        try:
            mastery_f = max(0.0, min(100.0, float(mastery)))
        except (ValueError, TypeError):
            mastery_f = 50.0

        try:
            retention_f = max(0.0, min(100.0, float(retention)))
        except (ValueError, TypeError):
            retention_f = 70.0

        try:
            lambda_f = max(0.01, min(0.30, float(decay_lambda)))
        except (ValueError, TypeError):
            lambda_f = 0.08

        return {
            "topic_id": str(topic_id),
            "name": str(name),
            "difficulty": str(difficulty),
            "mastery_score": mastery_f,
            "retention_score": retention_f,
            "decay_lambda": lambda_f,
            "elapsed_days": elapsed_days,
            "completed": bool(completed),
        }

    @staticmethod
    def extract_calibration_observations(
        revision_history: Optional[List[Any]] = None,
        quiz_attempts: Optional[List[Any]] = None,
        reference_time: Optional[datetime] = None,
    ) -> List[Tuple[float, float, float]]:
        """
        Extracts normalized observation tuples (elapsed_days, score, weight)
        from revision histories and quiz attempts.
        Preserves distinct legitimate events without heuristic matching loss.
        If an explicit linked event ID (e.g. quiz_attempt_id in revision record) is present,
        prevents double counting the same underlying learning event.
        """
        observations: List[Tuple[float, float, float]] = []
        linked_quiz_ids = set()

        if revision_history:
            for item in revision_history:
                if hasattr(item, "__dict__"):
                    interval = getattr(item, "interval_days", 0)
                    score = getattr(item, "score", None)
                    q_id = getattr(item, "quiz_attempt_id", None)
                elif isinstance(item, dict):
                    interval = item.get("interval_days", item.get("elapsed_days", 0))
                    score = item.get("score")
                    q_id = item.get("quiz_attempt_id")
                else:
                    continue

                if q_id:
                    linked_quiz_ids.add(str(q_id))

                if score is not None:
                    try:
                        t = float(interval)
                        s = float(score)
                        if t > 0:
                            observations.append((t, s, 1.0))
                    except (ValueError, TypeError):
                        continue

        if quiz_attempts:
            for item in quiz_attempts:
                if hasattr(item, "__dict__"):
                    q_id = getattr(item, "id", None)
                    score = getattr(item, "score", getattr(item, "accuracy", None))
                    attempted_at = getattr(item, "attempted_at", None)
                elif isinstance(item, dict):
                    q_id = item.get("id")
                    score = item.get("score", item.get("accuracy"))
                    attempted_at = item.get("attempted_at")
                else:
                    continue

                # If this quiz attempt was already counted via an explicitly linked revision event, skip it
                if q_id and str(q_id) in linked_quiz_ids:
                    continue

                if score is not None and attempted_at is not None:
                    try:
                        elapsed = FeatureExtractor.extract_elapsed_days(attempted_at, reference_time)
                        s = float(score)
                        if elapsed > 0:
                            observations.append((elapsed, s, 1.2))
                    except (ValueError, TypeError):
                        continue

        return observations


feature_extractor = FeatureExtractor()
