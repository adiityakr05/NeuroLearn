"""
NeuroLearn Analytics Service
============================
Historical Analytics Engine transforming raw student learning events
(quiz attempts, revision records, study sessions, recommendations)
into verifiable, tenant-isolated longitudinal analytics.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.models.entities import (
    User,
    Subject,
    Topic,
    QuizAttempt,
    RevisionHistory,
    StudySession,
    Recommendation,
)
from app.schemas.entities import (
    HistoricalAnalyticsResponse,
    HistoricalAnalyticsSummary,
    MasteryTrajectoriesResponse,
    TopicMasteryTrajectory,
    MasteryTrajectoryPoint,
    RetentionAnalyticsResponse,
    DecayDistributionStats,
    HistoricalRevisionItem,
    RetentionCurveDataPoint,
    OverdueTopicItem,
    StudyBehaviorResponse,
    DailyStudyConsistencyPoint,
    RecommendationEffectivenessResponse,
    RecommendationStatusCounts,
    RecommendationRates,
    RecommendationFeedbackStats,
    RecommendationSubsequentPerformance,
)
from app.ml.retention_model import RetentionModel, DEFAULT_LAMBDA, DEFAULT_TARGET_RETENTION


def _ensure_utc(dt: Any) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(dt, str):
        try:
            clean = dt.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(clean)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            try:
                parsed = datetime.strptime(dt[:10], "%Y-%m-%d")
                return parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return None
    return None


class AnalyticsService:
    @staticmethod
    def resolve_time_window(time_range: str) -> Tuple[int, datetime, datetime]:
        """
        Maps a frontend timeRange string to window_days, start_datetime, and end_datetime.
        Supported:
          '14d' -> 14 days
          '30d' -> 30 days (default)
          'semester' -> 120 days
          '7d' -> 7 days (backend test/drill support)
        """
        now = datetime.now(timezone.utc)
        if time_range == "7d":
            days = 7
        elif time_range == "14d":
            days = 14
        elif time_range == "semester":
            days = 120
        else:
            days = 30  # default 30d

        start_dt = now - timedelta(days=days)
        return days, start_dt, now

    @staticmethod
    def reconstruct_mastery_trajectories(
        db: Session,
        user_id: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> MasteryTrajectoriesResponse:
        """
        Reconstructs topic mastery trajectories using chronological QuizAttempt records.
        Loads pre-window attempts to determine true starting mastery instead of resetting to 50.
        Uses EMA formula: M_k = round((M_{k-1} * 0.7) + (S_k * 0.3), 1)
        """
        # Get all topics belonging to user's subjects
        topics = list(
            db.scalars(
                select(Topic)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Subject.user_id == user_id)
                .order_by(Topic.name.asc())
            ).all()
        )

        if not topics:
            return MasteryTrajectoriesResponse(is_reconstructed=True, topics=[])

        # Fetch all quiz attempts for this user, ordered deterministically by attempted_at and id
        all_attempts = list(
            db.scalars(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .order_by(QuizAttempt.attempted_at.asc(), QuizAttempt.id.asc())
            ).all()
        )

        # Group attempts by topic
        attempts_by_topic: Dict[str, List[QuizAttempt]] = {}
        for a in all_attempts:
            attempts_by_topic.setdefault(a.topic_id, []).append(a)

        topic_trajectories: List[TopicMasteryTrajectory] = []

        for t in topics:
            parent_subj = db.scalar(select(Subject).where(Subject.id == t.subject_id))
            subj_name = parent_subj.name if parent_subj else "General"

            t_attempts = attempts_by_topic.get(t.id, [])
            
            # 1. Partition attempts: pre-window vs. in-window
            pre_window_attempts = []
            in_window_attempts = []

            for att in t_attempts:
                att_time = _ensure_utc(att.attempted_at)
                if att_time and att_time < start_dt:
                    pre_window_attempts.append(att)
                elif att_time and start_dt <= att_time <= end_dt:
                    in_window_attempts.append(att)

            # 2. Reconstruct starting mastery from pre-window history
            current_m = 50.0  # baseline topic mastery
            has_pre_history = len(pre_window_attempts) > 0

            for pre_att in pre_window_attempts:
                score_val = pre_att.score if pre_att.score is not None else pre_att.accuracy
                current_m = round((current_m * 0.7) + (score_val * 0.3), 1)

            starting_mastery = current_m
            starting_status = "prior_reconstructed_stable" if has_pre_history else "initial_default_baseline"

            # 3. Build trajectory points
            points: List[MasteryTrajectoryPoint] = [
                MasteryTrajectoryPoint(
                    date=start_dt.isoformat(),
                    mastery=starting_mastery,
                    label="window_start",
                )
            ]

            if not in_window_attempts:
                # Stable throughout the window
                points.append(
                    MasteryTrajectoryPoint(
                        date=end_dt.isoformat(),
                        mastery=starting_mastery,
                        label=starting_status,
                    )
                )
            else:
                for in_att in in_window_attempts:
                    score_val = in_att.score if in_att.score is not None else in_att.accuracy
                    current_m = round((current_m * 0.7) + (score_val * 0.3), 1)
                    att_time = _ensure_utc(in_att.attempted_at) or start_dt
                    points.append(
                        MasteryTrajectoryPoint(
                            date=att_time.isoformat(),
                            mastery=current_m,
                            quiz_id=in_att.id,
                            score=score_val,
                            label="reconstructed_event",
                        )
                    )

            topic_trajectories.append(
                TopicMasteryTrajectory(
                    topic_id=t.id,
                    topic_name=t.name,
                    subject_id=t.subject_id,
                    subject_name=subj_name,
                    starting_mastery=starting_mastery,
                    starting_status=starting_status,
                    current_mastery=current_m,
                    data_points=points,
                )
            )

        return MasteryTrajectoriesResponse(
            is_reconstructed=True,
            reconstruction_method="exponential_moving_average_discrete_replay",
            formula="M_k = round((M_{k-1} * 0.7) + (S_k * 0.3), 1)",
            topics=topic_trajectories,
        )

    @staticmethod
    def compute_retention_analytics(
        db: Session,
        user_id: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> RetentionAnalyticsResponse:
        """
        Computes retention analytics:
        - Current decay rate lambda distribution
        - Historical revision events within window
        - Ebbinghaus curve points with discrete observed recall checks
        - Overdue topics
        """
        topics = list(
            db.scalars(
                select(Topic)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Subject.user_id == user_id)
            ).all()
        )

        # 1. Current Decay Rate Lambda Distribution
        high_stab = 0
        mod_decay = 0
        fast_decay = 0

        for t in topics:
            lam = t.decay_rate_lambda or DEFAULT_LAMBDA
            if lam <= 0.05:
                high_stab += 1
            elif lam <= 0.12:
                mod_decay += 1
            else:
                fast_decay += 1

        decay_dist = DecayDistributionStats(
            high_stability_count=high_stab,
            moderate_decay_count=mod_decay,
            fast_decay_count=fast_decay,
        )

        # 2. Historical Revisions within window
        start_date_str = start_dt.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")

        revs = list(
            db.scalars(
                select(RevisionHistory)
                .join(Topic, RevisionHistory.topic_id == Topic.id)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(
                    Subject.user_id == user_id,
                    RevisionHistory.revision_date >= start_date_str,
                    RevisionHistory.revision_date <= end_date_str,
                )
                .order_by(RevisionHistory.revision_date.asc())
            ).all()
        )

        rev_items: List[HistoricalRevisionItem] = []
        for r in revs:
            parent_t = db.scalar(select(Topic).where(Topic.id == r.topic_id))
            parent_s = db.scalar(select(Subject).where(Subject.id == parent_t.subject_id)) if parent_t else None
            rev_items.append(
                HistoricalRevisionItem(
                    id=r.id,
                    topic_id=r.topic_id,
                    topic_name=parent_t.name if parent_t else "Topic",
                    subject_name=parent_s.name if parent_s else "Subject",
                    date=r.revision_date,
                    score=r.score,
                    interval_days=r.interval_days,
                    repetition_number=r.repetition_number,
                )
            )

        # 3. Predicted Retention vs Actual Recall Points over 30 days
        # Ebbinghaus modeled curve: R(t) = 100 * exp(-lambda * t)
        retention_model = RetentionModel()
        avg_lambda = (
            sum(t.decay_rate_lambda for t in topics) / len(topics)
            if topics
            else DEFAULT_LAMBDA
        )

        # Collect actual quiz accuracy within window
        in_window_quizzes = list(
            db.scalars(
                select(QuizAttempt)
                .where(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.attempted_at >= start_dt,
                    QuizAttempt.attempted_at <= end_dt,
                )
                .order_by(QuizAttempt.attempted_at.asc())
            ).all()
        )

        # Map actual quiz accuracy by elapsed day offset
        # Find closest target day in target_days = [1, 2, 4, 7, 10, 14, 18, 22, 26, 30]
        target_days = [1, 2, 4, 7, 10, 14, 18, 22, 26, 30]
        actual_by_day: Dict[int, List[float]] = {}
        for q in in_window_quizzes:
            q_time = _ensure_utc(q.attempted_at)
            if q_time:
                raw_offset = max(1, min(30, int((q_time - start_dt).total_seconds() / 86400)))
                # Map raw_offset to nearest target day
                closest_target = min(target_days, key=lambda td: abs(td - raw_offset))
                actual_by_day.setdefault(closest_target, []).append(q.accuracy)

        curve_points: List[RetentionCurveDataPoint] = []

        for d in target_days:
            pred_val = round(100.0 * math.exp(-avg_lambda * d), 1)
            # Modeled counterfactual baseline without spaced repetition
            baseline_val = round(100.0 * math.exp(-0.15 * d), 1)
            
            # Actual discrete recall checks if present on this day
            actual_val = None
            if d in actual_by_day:
                actual_val = round(sum(actual_by_day[d]) / len(actual_by_day[d]), 1)

            rev_evt = None
            if d == 1:
                rev_evt = "Initial Study"
            elif d == 7:
                rev_evt = "1st Consolidation"
            elif d == 14:
                rev_evt = "2nd Review"
            elif d == 22:
                rev_evt = "3rd Consolidation"

            curve_points.append(
                RetentionCurveDataPoint(
                    day=d,
                    predicted=pred_val,
                    actual=actual_val,
                    baseline_without_repetition=baseline_val,
                    revision_event=rev_evt,
                    note="Counterfactual baseline without repetition modeled with accelerated forgetting" if d == 30 else None,
                )
            )

        # 4. Overdue Topics
        now_utc = datetime.now(timezone.utc)
        overdue_list: List[OverdueTopicItem] = []
        for t in topics:
            if t.next_revision:
                next_rev_dt = _ensure_utc(t.next_revision)
                if next_rev_dt and next_rev_dt < now_utc:
                    days_over = max(1, int((now_utc - next_rev_dt).total_seconds() / 86400))
                    parent_s = db.scalar(select(Subject).where(Subject.id == t.subject_id))
                    decay_pct = round(100.0 - (t.retention_score or 70.0), 1)
                    overdue_list.append(
                        OverdueTopicItem(
                            topic_id=t.id,
                            topic_name=t.name,
                            subject_name=parent_s.name if parent_s else "Subject",
                            days_overdue=days_over,
                            predicted_decay=f"-{decay_pct}% since scheduled interval",
                            current_retention=t.retention_score or 70.0,
                        )
                    )

        return RetentionAnalyticsResponse(
            current_decay_distribution=decay_dist,
            historical_revisions=rev_items,
            predicted_vs_actual=curve_points,
            overdue_topics=overdue_list,
        )

    @staticmethod
    def compute_study_behavior_analytics(
        db: Session,
        user_id: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> StudyBehaviorResponse:
        """
        Computes study session behavior metrics:
        - Planned vs measured actual duration vs legacy estimated duration
        - Completed, abandoned, and pending counts
        - Daily consistency
        """
        start_date_str = start_dt.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")

        sessions = list(
            db.scalars(
                select(StudySession)
                .where(
                    StudySession.user_id == user_id,
                    StudySession.date >= start_date_str,
                    StudySession.date <= end_date_str,
                )
                .order_by(StudySession.date.asc())
            ).all()
        )

        total_sessions = len(sessions)
        completed_sessions = [s for s in sessions if s.status == "completed"]
        abandoned_sessions = [s for s in sessions if s.status == "abandoned"]
        pending_sessions = [s for s in sessions if s.status == "pending"]
        in_progress_sessions = [s for s in sessions if s.status == "in_progress"]

        planned_minutes = sum(s.duration_minutes for s in sessions)

        # Separate completed actual duration from abandoned and legacy unmeasured
        completed_actual_minutes = 0
        legacy_estimated_minutes = 0
        abandoned_minutes = 0
        sessions_with_measured = 0

        for s in completed_sessions:
            if s.actual_duration_minutes is not None:
                completed_actual_minutes += s.actual_duration_minutes
                sessions_with_measured += 1
            else:
                legacy_estimated_minutes += s.duration_minutes

        for s in abandoned_sessions:
            if s.actual_duration_minutes is not None:
                abandoned_minutes += s.actual_duration_minutes

        total_elapsed_minutes = completed_actual_minutes + abandoned_minutes
        total_completed_minutes = completed_actual_minutes + legacy_estimated_minutes

        completion_pct = (
            round((len(completed_sessions) / total_sessions) * 100.0, 1)
            if total_sessions > 0
            else 0.0
        )
        abandonment_pct = (
            round((len(abandoned_sessions) / total_sessions) * 100.0, 1)
            if total_sessions > 0
            else 0.0
        )

        avg_actual_dur = (
            round(completed_actual_minutes / sessions_with_measured, 1)
            if sessions_with_measured > 0
            else 0.0
        )

        # Group daily consistency
        daily_map: Dict[str, Dict[str, int]] = {}
        for s in sessions:
            d_str = s.date
            if d_str not in daily_map:
                daily_map[d_str] = {
                    "planned_minutes": 0,
                    "actual_minutes": 0,
                    "completed_sessions": 0,
                    "abandoned_sessions": 0,
                }
            daily_map[d_str]["planned_minutes"] += s.duration_minutes
            if s.actual_duration_minutes is not None:
                daily_map[d_str]["actual_minutes"] += s.actual_duration_minutes
            elif s.status == "completed":
                daily_map[d_str]["actual_minutes"] += s.duration_minutes

            if s.status == "completed":
                daily_map[d_str]["completed_sessions"] += 1
            elif s.status == "abandoned":
                daily_map[d_str]["abandoned_sessions"] += 1

        daily_points: List[DailyStudyConsistencyPoint] = [
            DailyStudyConsistencyPoint(
                date=k,
                planned_minutes=v["planned_minutes"],
                actual_minutes=v["actual_minutes"],
                completed_sessions=v["completed_sessions"],
                abandoned_sessions=v["abandoned_sessions"],
            )
            for k, v in sorted(daily_map.items())
        ]

        return StudyBehaviorResponse(
            planned_minutes=planned_minutes,
            completed_actual_minutes=completed_actual_minutes,
            measured_actual_minutes=completed_actual_minutes,  # Backward-compatible alias
            abandoned_minutes=abandoned_minutes,
            legacy_estimated_minutes=legacy_estimated_minutes,
            total_elapsed_minutes=total_elapsed_minutes,
            total_completed_minutes=total_completed_minutes,
            total_sessions=total_sessions,
            completed_sessions=len(completed_sessions),
            abandoned_sessions=len(abandoned_sessions),
            pending_sessions=len(pending_sessions),
            in_progress_sessions=len(in_progress_sessions),
            completion_percentage=completion_pct,
            abandonment_percentage=abandonment_pct,
            average_actual_duration_minutes=avg_actual_dur,
            sessions_with_measured_duration=sessions_with_measured,
            daily_consistency=daily_points,
        )

    @staticmethod
    def compute_recommendation_effectiveness(
        db: Session,
        user_id: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> RecommendationEffectivenessResponse:
        """
        Computes recommendation effectiveness with mathematically rigorous,
        mutually exclusive status partitions and non-causal performance correlation.
        """
        recs = list(
            db.scalars(
                select(Recommendation)
                .where(
                    Recommendation.user_id == user_id,
                    Recommendation.created_at >= start_dt,
                    Recommendation.created_at <= end_dt,
                )
            ).all()
        )

        total_recs = len(recs)
        pending_c = sum(1 for r in recs if r.status == "pending")
        accepted_c = sum(1 for r in recs if r.status == "accepted")
        completed_c = sum(1 for r in recs if r.status == "completed")
        dismissed_c = sum(1 for r in recs if r.status == "dismissed")

        # Mutually exclusive status counts
        status_counts = RecommendationStatusCounts(
            pending=pending_c,
            accepted=accepted_c,
            completed=completed_c,
            dismissed=dismissed_c,
        )

        # Rates (denominator is total_recs)
        currently_accepted_rate = (
            round((accepted_c / total_recs) * 100.0, 1)
            if total_recs > 0
            else 0.0
        )
        completion_rate = (
            round((completed_c / total_recs) * 100.0, 1)
            if total_recs > 0
            else 0.0
        )
        dismissal_rate = (
            round((dismissed_c / total_recs) * 100.0, 1)
            if total_recs > 0
            else 0.0
        )
        pending_rate = (
            round((pending_c / total_recs) * 100.0, 1)
            if total_recs > 0
            else 0.0
        )
        adoption_rate = (
            round(((accepted_c + completed_c) / total_recs) * 100.0, 1)
            if total_recs > 0
            else 0.0
        )

        rates = RecommendationRates(
            currently_accepted_rate=currently_accepted_rate,
            completion_rate=completion_rate,
            dismissal_rate=dismissal_rate,
            pending_rate=pending_rate,
            adoption_rate=adoption_rate,
            acceptance_rate=adoption_rate,  # Backward-compatible alias
        )

        # Feedback stats (denominator is only recommendations where feedback was provided)
        with_feedback = [r for r in recs if r.feedback_helpful is not None]
        helpful_count = sum(1 for r in with_feedback if r.feedback_helpful is True)
        unhelpful_count = sum(1 for r in with_feedback if r.feedback_helpful is False)
        helpful_ratio = (
            round((helpful_count / len(with_feedback)) * 100.0, 1)
            if with_feedback
            else 0.0
        )

        feedback_stats = RecommendationFeedbackStats(
            total_with_feedback=len(with_feedback),
            helpful_count=helpful_count,
            unhelpful_count=unhelpful_count,
            helpful_ratio=helpful_ratio,
        )

        # Subsequent Quiz Performance Correlation (Non-Causal)
        completed_recs_with_topics = [
            r for r in recs if r.status == "completed" and r.topic_id is not None
        ]

        subsequent_scores: List[float] = []
        for r in completed_recs_with_topics:
            rec_finish_time = _ensure_utc(r.updated_at) or start_dt
            window_end = rec_finish_time + timedelta(days=7)
            
            subsequent_attempts = list(
                db.scalars(
                    select(QuizAttempt)
                    .where(
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.topic_id == r.topic_id,
                        QuizAttempt.attempted_at > rec_finish_time,
                        QuizAttempt.attempted_at <= window_end,
                    )
                ).all()
            )
            for sa in subsequent_attempts:
                subsequent_scores.append(sa.score if sa.score is not None else sa.accuracy)

        subsequent_perf = RecommendationSubsequentPerformance(
            has_data=len(subsequent_scores) > 0,
            correlated_subsequent_quiz_average=(
                round(sum(subsequent_scores) / len(subsequent_scores), 1)
                if subsequent_scores
                else None
            ),
            sample_size=len(subsequent_scores),
            causality_disclaimer="correlation_only_non_causal",
        )

        return RecommendationEffectivenessResponse(
            total_recommendations=total_recs,
            status_counts=status_counts,
            rates=rates,
            feedback=feedback_stats,
            subsequent_performance=subsequent_perf,
        )

    @staticmethod
    def get_historical_analytics(
        db: Session,
        user_id: str,
        time_range: str = "30d",
    ) -> HistoricalAnalyticsResponse:
        """
        Coordinates full historical analytics aggregation across all sub-engines.
        Produces typed domain schemas as well as an adapted frontend_bundle
        matching the exact expectations of Analytics.jsx.
        """
        window_days, start_dt, end_dt = AnalyticsService.resolve_time_window(time_range)

        # Execute component engines
        trajectories = AnalyticsService.reconstruct_mastery_trajectories(db, user_id, start_dt, end_dt)
        retention_data = AnalyticsService.compute_retention_analytics(db, user_id, start_dt, end_dt)
        study_behavior = AnalyticsService.compute_study_behavior_analytics(db, user_id, start_dt, end_dt)
        recommendation_eff = AnalyticsService.compute_recommendation_effectiveness(db, user_id, start_dt, end_dt)

        # Quizzes in window for summary metrics
        in_window_quizzes = list(
            db.scalars(
                select(QuizAttempt)
                .where(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.attempted_at >= start_dt,
                    QuizAttempt.attempted_at <= end_dt,
                )
            ).all()
        )
        avg_quiz_acc = (
            round(sum(q.accuracy for q in in_window_quizzes) / len(in_window_quizzes), 1)
            if in_window_quizzes
            else 0.0
        )
        avg_recall = (
            round(sum(q.score for q in in_window_quizzes) / len(in_window_quizzes), 1)
            if in_window_quizzes
            else 0.0
        )

        # Topics for overall retention
        topics = list(
            db.scalars(
                select(Topic)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Subject.user_id == user_id)
            ).all()
        )
        avg_retention = (
            round(sum(t.retention_score for t in topics) / len(topics), 1)
            if topics
            else 70.0
        )

        # Summary KPIs
        rev_history = retention_data.historical_revisions
        avg_interval = (
            round(sum(r.interval_days for r in rev_history) / len(rev_history), 1)
            if rev_history
            else 4.5
        )

        summary = HistoricalAnalyticsSummary(
            predicted_overall_retention=avg_retention,
            average_quiz_accuracy=avg_quiz_acc,
            actual_recall_average=avg_recall,
            revision_compliance_rate=study_behavior.completion_percentage,
            average_interval_days=avg_interval,
            total_completed_quizzes=len(in_window_quizzes),
            total_completed_revisions=len(rev_history),
            planned_study_minutes=study_behavior.planned_minutes,
            actual_study_minutes=study_behavior.completed_actual_minutes + study_behavior.legacy_estimated_minutes,
            measured_actual_minutes=study_behavior.completed_actual_minutes,
            legacy_estimated_minutes=study_behavior.legacy_estimated_minutes,
            actual_study_minutes_note="Sum of completed measured actual minutes and legacy completed estimated minutes",
        )

        # ======================================================================
        # ADAPTED FRONTEND BUNDLE (for Analytics.jsx & Recharts)
        # ======================================================================
        # 1. retentionDecayCurve
        retentionDecayCurve = [
            {
                "day": p.day,
                "predicted": p.predicted,
                "actual": p.actual,
                "baselineWithoutRepetition": p.baseline_without_repetition,
                "revisionEvent": p.revision_event,
                "note": p.note,
            }
            for p in retention_data.predicted_vs_actual
        ]

        # 2. quizTrends
        quizTrends = [
            {
                "id": q.id,
                "date": q.attempted_at.strftime("%Y-%m-%d") if q.attempted_at else "2026-11-01",
                "title": q.title,
                "subject": db.scalar(
                    select(Subject.name)
                    .join(Topic, Topic.subject_id == Subject.id)
                    .where(Topic.id == q.topic_id)
                ) or "Subject",
                "score": q.score,
                "accuracy": q.accuracy,
                "classAvg": 70,
            }
            for q in in_window_quizzes
        ]

        # 3. topicQuizPerformance
        topicQuizPerformance = [
            {
                "topic": t.topic_name,
                "accuracy": round(t.current_mastery, 1),
                "difficulty": "Medium",
                "subject": t.subject_name,
            }
            for t in trajectories.topics
        ]

        # 4. subjectMasteryComparison
        subjects = list(db.scalars(select(Subject).where(Subject.user_id == user_id)).all())
        subjectMasteryComparison = []
        for s in subjects:
            subj_topics = [t for t in trajectories.topics if t.subject_id == s.id]
            subj_mastery = (
                round(sum(t.current_mastery for t in subj_topics) / len(subj_topics), 1)
                if subj_topics
                else 50.0
            )
            status_val = "strong" if subj_mastery >= 80 else "on_track" if subj_mastery >= 65 else "needs_focus"
            strongest = max(subj_topics, key=lambda x: x.current_mastery).topic_name if subj_topics else "None"
            weakest = min(subj_topics, key=lambda x: x.current_mastery).topic_name if subj_topics else "None"

            subjectMasteryComparison.append(
                {
                    "subject": s.name,
                    "code": s.code,
                    "mastery": subj_mastery,
                    "targetMastery": s.target_mastery or 80,
                    "retentionScore": round(subj_mastery * 0.95, 1),
                    "status": status_val,
                    "strongestTopic": strongest,
                    "weakestTopic": weakest,
                }
            )

        # 5. revisionFrequency (computed from actual study_sessions in window)
        num_weeks = min(5, max(1, window_days // 7))
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        window_sessions = list(
            db.scalars(
                select(StudySession).where(
                    StudySession.user_id == user_id,
                    StudySession.date >= start_str,
                    StudySession.date <= end_str,
                )
            ).all()
        )
        revisionFrequency = []
        for i in range(num_weeks):
            w_start = (start_dt + timedelta(days=i * 7)).strftime("%Y-%m-%d")
            w_end = (start_dt + timedelta(days=(i + 1) * 7 - 1)).strftime("%Y-%m-%d")
            w_sess = [s for s in window_sessions if w_start <= s.date <= w_end]
            w_comp = sum(1 for s in w_sess if s.status == "completed")
            w_missed = sum(1 for s in w_sess if s.status in ("abandoned", "pending") and s.date < end_str)
            w_total = w_comp + w_missed
            w_compliance = round((w_comp / w_total) * 100.0, 1) if w_total > 0 else 0.0
            revisionFrequency.append({
                "week": f"Week {i+1}",
                "completed": w_comp,
                "missed": w_missed,
                "compliance": w_compliance,
            })

        # 6. overdueList
        overdueList = [
            {
                "id": od.topic_id,
                "topic": od.topic_name,
                "subject": od.subject_name,
                "daysOverdue": od.days_overdue,
                "predictedDecay": od.predicted_decay,
                "currentRetention": od.current_retention,
            }
            for od in retention_data.overdue_topics
        ]

        frontend_bundle = {
            "summary": {
                "predictedOverallRetention": summary.predicted_overall_retention,
                "averageQuizAccuracy": summary.average_quiz_accuracy,
                "actualRecallAverage": summary.actual_recall_average,
                "revisionComplianceRate": summary.revision_compliance_rate,
                "averageIntervalDays": summary.average_interval_days,
            },
            "retentionDecayCurve": retentionDecayCurve,
            "quizTrends": quizTrends,
            "topicQuizPerformance": topicQuizPerformance,
            "subjectMasteryComparison": subjectMasteryComparison,
            "revisionFrequency": revisionFrequency,
            "overdueList": overdueList,
        }

        return HistoricalAnalyticsResponse(
            time_range=time_range,
            window_days=window_days,
            start_date=start_dt.isoformat(),
            end_date=end_dt.isoformat(),
            summary=summary,
            mastery_trajectories=trajectories,
            retention_analytics=retention_data,
            study_behavior=study_behavior,
            recommendation_effectiveness=recommendation_eff,
            frontend_bundle=frontend_bundle,
        )


analytics_service = AnalyticsService()
