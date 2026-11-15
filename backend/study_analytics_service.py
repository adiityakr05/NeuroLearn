
"""
NeuroLearn Adaptive Study Planner
Phase 2.6.5 — Study Analytics and Learner Adherence
"""

import json
from datetime import datetime, timedelta, timezone
from backend.database import get_connection


class StudyAnalyticsService:
    """Calculate learner study analytics from completion records."""

    @staticmethod
    def get_study_analytics(user_id: str) -> dict:
        """Return overall study completion and time statistics."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    planned_minutes,
                    actual_minutes,
                    topics_planned,
                    topics_completed,
                    completion_rate
                FROM study_session_completions
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        if not rows:
            return {
                "user_id": user_id,
                "total_sessions": 0,
                "total_planned_minutes": 0,
                "total_actual_minutes": 0,
                "average_planned_minutes": 0,
                "average_actual_minutes": 0,
                "overall_completion_rate": 0,
                "time_adherence_rate": 0,
            }

        total_sessions = len(rows)
        total_planned = sum(row["planned_minutes"] for row in rows)
        total_actual = sum(row["actual_minutes"] for row in rows)

        total_topics_planned = sum(
            len(json.loads(row["topics_planned"]))
            for row in rows
        )

        total_topics_completed = sum(
            len(json.loads(row["topics_completed"]))
            for row in rows
        )

        completion_rate = (
            total_topics_completed / total_topics_planned
            if total_topics_planned > 0
            else 0
        )

        time_adherence_rate = (
            total_actual / total_planned
            if total_planned > 0
            else 0
        )

        return {
            "user_id": user_id,
            "total_sessions": total_sessions,
            "total_planned_minutes": total_planned,
            "total_actual_minutes": total_actual,
            "average_planned_minutes": round(
                total_planned / total_sessions, 2
            ),
            "average_actual_minutes": round(
                total_actual / total_sessions, 2
            ),
            "overall_completion_rate": round(completion_rate, 4),
            "time_adherence_rate": round(time_adherence_rate, 4),
        }

    @staticmethod
    def get_topic_analytics(user_id: str) -> dict:
        """Return completion statistics grouped by topic."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT topics_planned, topics_completed
                FROM study_session_completions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()

        topic_stats = {}

        for row in rows:
            planned = json.loads(row["topics_planned"])
            completed = json.loads(row["topics_completed"])

            for topic in planned:
                if topic not in topic_stats:
                    topic_stats[topic] = {
                        "topic_id": topic,
                        "times_planned": 0,
                        "times_completed": 0,
                    }

                topic_stats[topic]["times_planned"] += 1

                if topic in completed:
                    topic_stats[topic]["times_completed"] += 1

        topics = []

        for stats in topic_stats.values():
            planned_count = stats["times_planned"]
            completed_count = stats["times_completed"]

            stats["completion_rate"] = round(
                completed_count / planned_count,
                4,
            )

            topics.append(stats)

        topics.sort(key=lambda item: item["completion_rate"])

        return {
            "user_id": user_id,
            "topics": topics,
            "count": len(topics),
        }
        
    @staticmethod
    def get_weekly_analytics(user_id: str) -> dict:
        """Return study analytics for the last seven days."""

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=7)
        ).isoformat()

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    planned_minutes,
                    actual_minutes,
                    topics_planned,
                    topics_completed
                FROM study_session_completions
                WHERE user_id = ?
                AND created_at >= ?
                """,
                (user_id, cutoff),
            ).fetchall()

        total_sessions = len(rows)
        planned_minutes = sum(
            row["planned_minutes"] for row in rows
        )
        actual_minutes = sum(
            row["actual_minutes"] for row in rows
        )

        planned_topics = sum(
            len(json.loads(row["topics_planned"]))
            for row in rows
        )
        completed_topics = sum(
            len(json.loads(row["topics_completed"]))
            for row in rows
        )

        return {
            "user_id": user_id,
            "period_days": 7,
            "total_sessions": total_sessions,
            "planned_minutes": planned_minutes,
            "actual_minutes": actual_minutes,
            "planned_topics": planned_topics,
            "completed_topics": completed_topics,
            "completion_rate": round(
                completed_topics / planned_topics, 4
            ) if planned_topics else 0,
        }
