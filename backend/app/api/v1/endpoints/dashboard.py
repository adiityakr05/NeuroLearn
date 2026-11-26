from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User, Subject, Topic, StudySession, QuizAttempt, Recommendation
from app.services.activity_service import activity_service

router = APIRouter()


@router.get(
    "",
    summary="Get unified student dashboard data",
)
def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified dashboard endpoint feeding frontend Dashboard view using real database records:
    - stats: today study hours (actual completed), yesterday delta, completed sessions, retention, real streak
    - upcomingExams: subjects with exam_date
    - subjectMastery: per-subject mastery breakdown
    - weeklyActivity: actual completed study hours per day for the current week (Mon-Sun)
    - aiRecommendations: active 4-element recommendations
    - todaySchedule: sessions scheduled for today
    """
    now_utc = datetime.now(timezone.utc)
    today_date = now_utc.date()
    today_str = today_date.strftime("%Y-%m-%d")
    yesterday_str = (today_date - timedelta(days=1)).strftime("%Y-%m-%d")

    def _session_minutes(s_dict) -> int:
        actual = s_dict.get("actual_duration_minutes")
        return actual if actual is not None else (s_dict.get("duration_minutes") or 0)

    # 1. Today's & Yesterday's sessions
    today_sessions = activity_service.get_study_sessions(
        db, user_id=current_user.id, start_date=today_str, end_date=today_str
    )
    completed_today = [s for s in today_sessions if s["status"] == "completed"]
    today_minutes = sum(_session_minutes(s) for s in completed_today)
    today_hours = round(today_minutes / 60.0, 1)

    yesterday_sessions = activity_service.get_study_sessions(
        db, user_id=current_user.id, start_date=yesterday_str, end_date=yesterday_str
    )
    completed_yesterday = [s for s in yesterday_sessions if s["status"] == "completed"]
    yesterday_minutes = sum(_session_minutes(s) for s in completed_yesterday)
    yesterday_delta_minutes = (today_minutes - yesterday_minutes) if (today_minutes > 0 or yesterday_minutes > 0) else None

    # 2. Overall progress & real retention metrics
    progress_stats = activity_service.get_overall_progress(db, current_user.id)
    user_topics = list(
        db.scalars(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.user_id == current_user.id)
        ).all()
    )
    avg_retention = (
        round(sum(t.retention_score for t in user_topics) / len(user_topics), 1)
        if user_topics
        else None
    )

    # 3. Real Study Streak (consecutive days with at least 1 completed session or quiz attempt)
    completed_session_dates = set(
        db.scalars(
            select(StudySession.date).where(
                StudySession.user_id == current_user.id,
                StudySession.status == "completed",
            )
        ).all()
    )
    quiz_dates = {
        dt.strftime("%Y-%m-%d")
        for dt in db.scalars(
            select(QuizAttempt.attempted_at).where(QuizAttempt.user_id == current_user.id)
        ).all()
        if dt is not None
    }
    active_dates = completed_session_dates | quiz_dates
    streak = 0
    check_date = today_date if today_str in active_dates else (today_date - timedelta(days=1))
    while check_date.strftime("%Y-%m-%d") in active_dates:
        streak += 1
        check_date -= timedelta(days=1)

    # 4. Real Weekly Activity (Mon-Sun of current week)
    monday_date = today_date - timedelta(days=today_date.weekday())
    sunday_date = monday_date + timedelta(days=6)
    week_sessions = activity_service.get_study_sessions(
        db,
        user_id=current_user.id,
        start_date=monday_date.strftime("%Y-%m-%d"),
        end_date=sunday_date.strftime("%Y-%m-%d"),
    )
    weekly_activity = []
    for i in range(7):
        d = monday_date + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        day_completed = [s for s in week_sessions if s["date"] == d_str and s["status"] == "completed"]
        day_hours = round(sum(_session_minutes(s) for s in day_completed) / 60.0, 2)
        weekly_activity.append(
            {
                "day": d.strftime("%a"),
                "date": d_str,
                "hours": day_hours,
                "target": 4.0,
                "retentionScore": avg_retention,
            }
        )

    # 5. Upcoming exams (subjects with exam_date)
    subjects = list(
        db.scalars(
            select(Subject)
            .where(Subject.user_id == current_user.id)
            .order_by(Subject.created_at.asc())
        ).all()
    )
    upcoming_exams = []
    for s in subjects:
        if s.exam_date:
            days_left = max(0, (s.exam_date.date() - today_date).days)
            upcoming_exams.append(
                {
                    "id": f"exam_{s.id}",
                    "subject": s.name,
                    "code": s.code,
                    "date": s.exam_date.strftime("%Y-%m-%d"),
                    "daysLeft": days_left,
                    "targetMastery": s.target_mastery,
                    "currentMastery": next(
                        (sp.mastery for sp in progress_stats.subjects_progress if sp.subject_id == s.id),
                        0.0,
                    ),
                    "status": "critical" if days_left <= 14 else "on_track",
                }
            )

    # 6. Subject mastery list for chart
    subject_mastery = [
        {
            "subject": sp.subject_name,
            "mastery": sp.mastery,
            "color": sp.color,
        }
        for sp in progress_stats.subjects_progress
    ]

    # 7. Active recommendations
    active_recs = list(
        db.scalars(
            select(Recommendation)
            .where(Recommendation.user_id == current_user.id, Recommendation.status == "pending")
            .limit(5)
        ).all()
    )

    stats = {
        "todayStudyHours": today_hours,
        "todayTargetHours": 4.0,
        "yesterdayDeltaMinutes": yesterday_delta_minutes,
        "completedSessions": len(completed_today),
        "pendingTasks": len([s for s in today_sessions if s["status"] in ("pending", "in_progress")]),
        "overallProgress": int(avg_retention) if avg_retention is not None else None,
        "activeStreak": streak,
    }

    return {
        "stats": stats,
        "upcomingExams": upcoming_exams,
        "subjectMastery": subject_mastery,
        "weeklyActivity": weekly_activity,
        "aiRecommendations": active_recs,
        "todaySchedule": today_sessions,
    }


@router.get(
    "/activity",
    summary="Get yearly LeetCode-style study activity calendar and streak stats",
)
def get_yearly_activity(
    year: Optional[int] = None,
    daily_goal_minutes: int = 120,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full-year daily study activity from actual completed StudySession records
    for the authenticated student, along with current and longest streak statistics.
    """
    now_utc = datetime.now(timezone.utc)
    target_year = min(year or now_utc.year, now_utc.year)
    start_str = f"{target_year}-01-01"
    end_str = f"{target_year}-12-31"

    completed_sessions = list(
        db.scalars(
            select(StudySession).where(
                StudySession.user_id == current_user.id,
                StudySession.status == "completed",
                StudySession.date >= start_str,
                StudySession.date <= end_str,
            )
        ).all()
    )

    daily_map = {}
    for s in completed_sessions:
        mins = s.actual_duration_minutes if s.actual_duration_minutes is not None else (s.duration_minutes or 0)
        if s.date not in daily_map:
            daily_map[s.date] = {"minutes": 0, "sessionsCount": 0}
        daily_map[s.date]["minutes"] += max(0, mins)
        daily_map[s.date]["sessionsCount"] += 1

    def _intensity(mins: int) -> int:
        if mins <= 0:
            return 0
        if mins < 25:
            return 1
        if mins < 50:
            return 2
        if mins < 90:
            return 3
        return 4

    days = []
    cur = datetime(target_year, 1, 1).date()
    end_d = datetime(target_year, 12, 31).date()
    while cur <= end_d:
        d_str = cur.strftime("%Y-%m-%d")
        info = daily_map.get(d_str, {"minutes": 0, "sessionsCount": 0})
        mins = info["minutes"]
        days.append({
            "date": d_str,
            "minutes": mins,
            "sessionsCount": info["sessionsCount"],
            "goalMet": mins >= daily_goal_minutes,
            "intensity": _intensity(mins),
        })
        cur += timedelta(days=1)

    # Calculate current & longest streak from qualifying days (or any completed study day)
    qualifying_dates = sorted([d["date"] for d in days if d["minutes"] > 0])
    longest_streak = 0
    run = 0
    prev_d = None
    for d_str in qualifying_dates:
        d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        if prev_d and (d_obj - prev_d).days == 1:
            run += 1
        else:
            run = 1
        longest_streak = max(longest_streak, run)
        prev_d = d_obj

    today_date = now_utc.date()
    today_str = today_date.strftime("%Y-%m-%d")
    qual_set = set(qualifying_dates)
    current_streak = 0
    chk = today_date if today_str in qual_set else (today_date - timedelta(days=1))
    while chk.strftime("%Y-%m-%d") in qual_set:
        current_streak += 1
        chk -= timedelta(days=1)

    total_minutes = sum(d["minutes"] for d in days)
    return {
        "year": target_year,
        "currentYear": now_utc.year,
        "dailyGoalMinutes": daily_goal_minutes,
        "currentStreak": current_streak,
        "longestStreak": longest_streak,
        "totalActiveDays": len(qualifying_dates),
        "totalFocusedHours": round(total_minutes / 60.0, 1),
        "days": days,
    }
