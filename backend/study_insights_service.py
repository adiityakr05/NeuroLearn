
"""
NeuroLearn Adaptive Study Planner
Phase 2.6.6 — Adaptive Learning Insights
"""

import json
from datetime import datetime, timedelta, timezone

from backend.database import get_connection


class StudyInsightsService:
    """Generate adaptive learning insights from learner study data."""

    @staticmethod
    def get_performance_trend(user_id: str) -> dict:
        """Compare recent study performance with the previous period."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_date,
                    completion_rate,
                    actual_minutes
                FROM study_session_completions
                WHERE user_id = ?
                ORDER BY session_date DESC
                """,
                (user_id,),
            ).fetchall()

        now = datetime.now(timezone.utc)
        recent_cutoff = (now - timedelta(days=7)).isoformat()
        previous_cutoff = (now - timedelta(days=14)).isoformat()

        recent = [
            row for row in rows
            if row["session_date"] >= recent_cutoff
        ]

        previous = [
            row for row in rows
            if previous_cutoff <= row["session_date"] < recent_cutoff
        ]

        def average_completion(records):
            if not records:
                return 0

            return round(
                sum(row["completion_rate"] for row in records)
                / len(records),
                4,
            )

        recent_average = average_completion(recent)
        previous_average = average_completion(previous)

        return {
            "user_id": user_id,
            "recent_sessions": len(recent),
            "previous_sessions": len(previous),
            "recent_completion_rate": recent_average,
            "previous_completion_rate": previous_average,
            "performance_change": round(
                recent_average - previous_average,
                4,
            ),
            "trend": (
                "improving"
                if recent_average > previous_average
                else "declining"
                if recent_average < previous_average
                else "stable"
            ),
        }


    @staticmethod
    def get_study_consistency(user_id: str) -> dict:
        """Calculate study activity and streak statistics."""

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT session_date
                FROM study_session_completions
                WHERE user_id = ?
                ORDER BY session_date DESC
                """,
                (user_id,),
            ).fetchall()

        study_dates = sorted({
            datetime.fromisoformat(row["session_date"])
            .date()
            for row in rows
        })

        if not study_dates:
            return {
                "user_id": user_id,
                "active_study_days": 0,
                "current_streak": 0,
                "longest_streak": 0,
            }

        active_days = len(study_dates)
        longest_streak = 1
        streak = 1

        for index in range(1, len(study_dates)):
            difference = (
                study_dates[index] - study_dates[index - 1]
            ).days

            if difference == 1:
                streak += 1
                longest_streak = max(
                    longest_streak,
                    streak,
                )
            else:
                streak = 1

        today = datetime.now(timezone.utc).date()
        latest_date = study_dates[-1]

        current_streak = (
            streak
            if (today - latest_date).days <= 1
            else 0
        )

        return {
            "user_id": user_id,
            "active_study_days": active_days,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
        }


    @staticmethod
    def get_weak_topics(user_id: str) -> dict:
        """Identify topics with the lowest completion rates."""

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

        weak_topics = []

        for stats in topic_stats.values():
            stats["completion_rate"] = round(
                stats["times_completed"]
                / stats["times_planned"],
                4,
            )

            if stats["completion_rate"] < 0.6:
                weak_topics.append(stats)

        weak_topics.sort(
            key=lambda item: item["completion_rate"]
        )

        return {
            "user_id": user_id,
            "weak_topics": weak_topics,
            "count": len(weak_topics),
        }


    @staticmethod
    def get_personalized_insights(user_id: str) -> dict:
        """Generate personalized learning insights."""

        performance = StudyInsightsService.get_performance_trend(
            user_id
        )

        consistency = StudyInsightsService.get_study_consistency(
            user_id
        )

        weak_topics = StudyInsightsService.get_weak_topics(
            user_id
        )

        insights = []

        if performance["trend"] == "improving":
            insights.append(
                "Your study completion performance is improving."
            )
        elif performance["trend"] == "declining":
            insights.append(
                "Your recent study completion performance has declined."
            )
        else:
            insights.append(
                "Your study completion performance is stable."
            )

        if consistency["current_streak"] >= 7:
            insights.append(
                "Excellent consistency! You have studied "
                "for at least 7 consecutive days."
            )
        elif consistency["current_streak"] >= 3:
            insights.append(
                "You are building a consistent study habit."
            )
        else:
            insights.append(
                "Try maintaining a regular daily study routine."
            )

        if weak_topics["count"] > 0:
            insights.append(
                f"You have {weak_topics['count']} topics "
                "with completion rates below 60%."
            )
        else:
            insights.append(
                "No weak topics were identified from "
                "your recorded study sessions."
            )

        return {
            "user_id": user_id,
            "performance": performance,
            "consistency": consistency,
            "weak_topics": weak_topics,
            "insights": insights,
            "insight_count": len(insights),
        }
