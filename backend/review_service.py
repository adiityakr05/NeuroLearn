
"""
Study review-event persistence and learner-history aggregation.
"""

import sqlite3
from typing import Any

from backend.database import get_connection
from ml.data.schemas import ReviewEventRecord


class ReviewEventService:
    """Store review events and aggregate learner history."""

    @staticmethod
    def save_event(event: ReviewEventRecord) -> dict[str, Any]:
        """Validate and persist a review event."""

        event.validate()
        record = event.to_dict()

        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO review_events (
                        event_id,
                        user_id,
                        topic_id,
                        timestamp,
                        elapsed_days,
                        stability_days_prior,
                        repetition_count_prior,
                        topic_difficulty_prior,
                        last_rating_prior,
                        user_prior_recall_rate,
                        user_prior_reviews_count,
                        topic_prior_quiz_avg,
                        has_prior_quiz,
                        recall_success,
                        is_synthetic
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["event_id"],
                        record["user_id"],
                        record["topic_id"],
                        record["timestamp"],
                        record["elapsed_days"],
                        record["stability_days_prior"],
                        record["repetition_count_prior"],
                        record["topic_difficulty_prior"],
                        record["last_rating_prior"],
                        record["user_prior_recall_rate"],
                        record["user_prior_reviews_count"],
                        record["topic_prior_quiz_avg"],
                        int(record["has_prior_quiz"]),
                        record["recall_success"],
                        int(record["is_synthetic"]),
                    ),
                )

        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Review event already exists: {record['event_id']}"
            ) from exc

        return {
            "event_id": record["event_id"],
            "user_id": record["user_id"],
            "topic_id": record["topic_id"],
            "stored": True,
        }

    @staticmethod
    def get_user_events(
        user_id: str,
        topic_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve review events for a user."""

        with get_connection() as connection:
            if topic_id:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM review_events
                    WHERE user_id = ? AND topic_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (user_id, topic_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM review_events
                    WHERE user_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (user_id,),
                ).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def get_user_history(
        user_id: str,
        topic_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate real review history.

        Synthetic events are excluded from all statistics.
        """

        with get_connection() as connection:

            user_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS review_count,
                    AVG(recall_success) AS recall_rate,
                    MAX(timestamp) AS latest_review_timestamp
                FROM review_events
                WHERE user_id = ?
                  AND is_synthetic = 0
                """,
                (user_id,),
            ).fetchone()

            # Retrieve topic statistics for the learner.
            topic_rows = connection.execute(
                """
                SELECT
                    topic_id,
                    COUNT(*) AS review_count,
                    AVG(recall_success) AS recall_rate,
                    MAX(timestamp) AS latest_review_timestamp
                FROM review_events
                WHERE user_id = ?
                  AND is_synthetic = 0
                GROUP BY topic_id
                ORDER BY topic_id
                """,
                (user_id,),
            ).fetchall()

        topics = [
            {
                "topic_id": row["topic_id"],
                "review_count": row["review_count"],
                "recall_rate": (
                    float(row["recall_rate"])
                    if row["recall_rate"] is not None
                    else None
                ),
                "latest_review_timestamp": row[
                    "latest_review_timestamp"
                ],
            }
            for row in topic_rows
        ]

        # Apply optional topic filter to returned topic statistics.
        if topic_id:
            topics = [
                topic for topic in topics
                if topic["topic_id"] == topic_id
            ]

        return {
            "user_id": user_id,
            "total_review_count": user_row["review_count"],
            "overall_recall_rate": (
                float(user_row["recall_rate"])
                if user_row["recall_rate"] is not None
                else None
            ),
            "latest_review_timestamp": user_row[
                "latest_review_timestamp"
            ],
            "topics": topics,
        }
