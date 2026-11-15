
"""
NeuroLearn Adaptive Study Planner
Phase 2.6.4 — Study Session Completion Tracking
"""

import json
import uuid
from datetime import datetime, timezone

from backend.database import get_connection


class StudyCompletionService:
    """Persist and retrieve completed study sessions."""

    @staticmethod
    def record_completion(
        user_id: str,
        planned_minutes: int,
        actual_minutes: int,
        topics_planned: list[str],
        topics_completed: list[str],
    ) -> dict:
        """Record a completed study session."""

        if planned_minutes <= 0:
            raise ValueError("planned_minutes must be positive")

        if actual_minutes < 0:
            raise ValueError("actual_minutes cannot be negative")

        if not topics_planned:
            raise ValueError("topics_planned cannot be empty")

        planned_set = set(topics_planned)
        completed_set = set(topics_completed)

        if not completed_set.issubset(planned_set):
            raise ValueError(
                "topics_completed must be a subset of topics_planned"
            )

        completion_rate = (
            len(completed_set) / len(planned_set)
        )

        completion_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO study_session_completions (
                    completion_id,
                    user_id,
                    session_date,
                    planned_minutes,
                    actual_minutes,
                    topics_planned,
                    topics_completed,
                    completion_rate,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    completion_id,
                    user_id,
                    now,
                    planned_minutes,
                    actual_minutes,
                    json.dumps(topics_planned),
                    json.dumps(topics_completed),
                    completion_rate,
                    now,
                ),
            )

        return {
            "completion_id": completion_id,
            "user_id": user_id,
            "planned_minutes": planned_minutes,
            "actual_minutes": actual_minutes,
            "topics_planned": topics_planned,
            "topics_completed": topics_completed,
            "completion_rate": completion_rate,
            "created_at": now,
        }

    @staticmethod
    def get_completion_history(user_id: str) -> list[dict]:
        """Return study completion history for a user."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM study_session_completions
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        history = []

        for row in rows:
            item = dict(row)
            item["topics_planned"] = json.loads(
                item["topics_planned"]
            )
            item["topics_completed"] = json.loads(
                item["topics_completed"]
            )
            history.append(item)

        return history
