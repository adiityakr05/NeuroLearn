
"""
NeuroLearn Adaptive Learning Planner
Phase 2.7.1 — Learning Behavior Analysis
"""

import json
from datetime import datetime, timedelta, timezone

from backend.database import get_connection


class LearningBehaviorService:
    """Analyze learner study behavior and activity patterns."""

    @staticmethod
    def get_activity_summary(user_id: str) -> dict:
        """Summarize learner study activity."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT session_date, actual_minutes
                FROM study_session_completions
                WHERE user_id = ?
                ORDER BY session_date DESC
                """,
                (user_id,),
            ).fetchall()

        if not rows:
            return {
                "user_id": user_id,
                "total_sessions": 0,
                "active_study_days": 0,
                "average_session_minutes": 0,
                "last_study_date": None,
            }

        study_dates = {
            datetime.fromisoformat(row["session_date"]).date()
            for row in rows
        }

        total_minutes = sum(
            row["actual_minutes"] for row in rows
        )

        latest_date = max(study_dates)

        return {
            "user_id": user_id,
            "total_sessions": len(rows),
            "active_study_days": len(study_dates),
            "average_session_minutes": round(
                total_minutes / len(rows), 2
            ),
            "last_study_date": latest_date.isoformat(),
        }

    @staticmethod
    def get_study_timing_patterns(user_id: str) -> dict:
        """Identify the learner's most common study period."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT created_at, actual_minutes
                FROM study_session_completions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()

        periods = {
            "morning": 0,
            "afternoon": 0,
            "evening": 0,
            "night": 0,
        }

        for row in rows:
            timestamp = datetime.fromisoformat(
                row["created_at"]
            )

            hour = timestamp.hour

            if 5 <= hour < 12:
                periods["morning"] += 1
            elif 12 <= hour < 17:
                periods["afternoon"] += 1
            elif 17 <= hour < 21:
                periods["evening"] += 1
            else:
                periods["night"] += 1

        most_common = (
            max(periods, key=periods.get)
            if rows
            else None
        )

        return {
            "user_id": user_id,
            "session_count_by_period": periods,
            "most_common_study_period": most_common,
            "total_sessions": len(rows),
        }

    @staticmethod
    def get_learning_behavior(user_id: str) -> dict:
        """Generate a learner behavior summary."""

        activity = LearningBehaviorService.get_activity_summary(
            user_id
        )

        timing = (
            LearningBehaviorService.get_study_timing_patterns(
                user_id
            )
        )

        insights = []

        if activity["total_sessions"] == 0:
            insights.append(
                "No study activity has been recorded yet."
            )
        else:
            insights.append(
                f"You have completed {activity['total_sessions']} "
                "study sessions."
            )

            insights.append(
                f"Your average study session lasts "
                f"{activity['average_session_minutes']} minutes."
            )

        period = timing["most_common_study_period"]

        if period:
            insights.append(
                f"Your most common study period is {period}."
            )

        return {
            "user_id": user_id,
            "activity": activity,
            "timing": timing,
            "insights": insights,
            "insight_count": len(insights),
        }
