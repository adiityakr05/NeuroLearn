
"""
NeuroLearn Schedule Repository
Phase 2.5.8 — Persistent Review Scheduling
"""

import uuid
from datetime import datetime, timezone

from backend.database import get_connection


class ScheduleRepository:
    """Persist and retrieve personalized review schedules."""

    @staticmethod
    def save_schedule(schedule: dict) -> dict:
        """Insert or update a learner's schedule for a topic."""

        now = datetime.now(timezone.utc).isoformat()

        schedule_id = uuid.uuid4().hex

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO review_schedules (
                    schedule_id,
                    user_id,
                    topic_id,
                    predicted_retention_prob,
                    recommended_interval_days,
                    next_review_at,
                    is_review_due,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(user_id, topic_id)
                DO UPDATE SET
                    schedule_id = excluded.schedule_id,
                    predicted_retention_prob =
                        excluded.predicted_retention_prob,
                    recommended_interval_days =
                        excluded.recommended_interval_days,
                    next_review_at = excluded.next_review_at,
                    is_review_due = excluded.is_review_due,
                    updated_at = excluded.updated_at
                """,
                (
                    schedule_id,
                    schedule["user_id"],
                    schedule["topic_id"],
                    schedule["predicted_retention_prob"],
                    schedule["recommended_interval_days"],
                    schedule["next_review_at"],
                    int(schedule["is_review_due"]),
                    now,
                    now,
                ),
            )

            row = connection.execute(
                """
                SELECT *
                FROM review_schedules
                WHERE user_id = ? AND topic_id = ?
                """,
                (
                    schedule["user_id"],
                    schedule["topic_id"],
                ),
            ).fetchone()

            return dict(row)

    @staticmethod
    def get_user_schedules(user_id: str) -> list[dict]:
        """Return all schedules belonging to a learner."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM review_schedules
                WHERE user_id = ?
                ORDER BY next_review_at ASC
                """,
                (user_id,),
            ).fetchall()

            return [dict(row) for row in rows]

    @staticmethod
    def get_due_schedules(user_id: str) -> list[dict]:
        """Return schedules whose review time has arrived."""

        now = datetime.now(timezone.utc).isoformat()

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM review_schedules
                WHERE user_id = ?
                  AND next_review_at <= ?
                ORDER BY next_review_at ASC
                """,
                (user_id, now),
            ).fetchall()

            return [dict(row) for row in rows]
