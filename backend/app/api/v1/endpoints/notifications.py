from typing import Dict, Set
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User, Subject, Topic, StudySession, Recommendation

router = APIRouter()

# Per-user read/dismissed notification tracking (keyed by user_id)
_READ_IDS: Dict[str, Set[str]] = {}
_DISMISSED_IDS: Dict[str, Set[str]] = {}


def _build_real_notifications(db: Session, user_id: str):
    now_utc = datetime.now(timezone.utc)
    today_date = now_utc.date()
    today_str = today_date.strftime("%Y-%m-%d")
    read_set = _READ_IDS.get(user_id, set())
    dismissed_set = _DISMISSED_IDS.get(user_id, set())

    items = []

    # 1. Pending AI Recommendations
    pending_recs = list(
        db.scalars(
            select(Recommendation)
            .where(Recommendation.user_id == user_id, Recommendation.status == "pending")
            .order_by(Recommendation.created_at.desc())
            .limit(5)
        ).all()
    )
    for r in pending_recs:
        nid = f"rec_{r.id}"
        if nid in dismissed_set:
            continue
        items.append({
            "id": nid,
            "title": f"AI Recommendation: {r.title}",
            "description": r.reason_detail or "New adaptive study recommendation generated.",
            "category": "recommendation",
            "timestamp": (r.created_at or now_utc).isoformat(),
            "read": nid in read_set,
        })

    # 2. Overdue / Due Spaced Repetition Topics
    topics = list(
        db.scalars(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.user_id == user_id)
        ).all()
    )
    for t in topics:
        if t.next_revision and t.next_revision.date() <= today_date:
            nid = f"rev_{t.id}_{today_str}"
            if nid in dismissed_set:
                continue
            overdue_days = (today_date - t.next_revision.date()).days
            items.append({
                "id": nid,
                "title": f"Revision {'Overdue' if overdue_days > 0 else 'Due'}: {t.name}",
                "description": f"Predicted retention is {round(t.retention_score, 1)}%. Review recommended to prevent decay.",
                "category": "revision",
                "timestamp": t.next_revision.isoformat(),
                "read": nid in read_set,
            })

    # 3. Upcoming Examinations (within 14 days)
    subjects = list(db.scalars(select(Subject).where(Subject.user_id == user_id)).all())
    for s in subjects:
        if s.exam_date:
            days_left = (s.exam_date.date() - today_date).days
            if 0 <= days_left <= 14:
                nid = f"exam_{s.id}_{today_str}"
                if nid in dismissed_set:
                    continue
                items.append({
                    "id": nid,
                    "title": f"Upcoming Exam: {s.name} ({days_left}d left)",
                    "description": f"Target mastery: {s.target_mastery}%. Prioritize weak topics.",
                    "category": "exam",
                    "timestamp": now_utc.isoformat(),
                    "read": nid in read_set,
                })

    # 4. Completed Study Sessions Today
    completed_today = list(
        db.scalars(
            select(StudySession).where(
                StudySession.user_id == user_id,
                StudySession.date == today_str,
                StudySession.status == "completed",
            )
        ).all()
    )
    for sess in completed_today[:3]:
        nid = f"sess_{sess.id}"
        if nid in dismissed_set:
            continue
        mins = sess.actual_duration_minutes if sess.actual_duration_minutes is not None else sess.duration_minutes
        items.append({
            "id": nid,
            "title": "Study Session Completed",
            "description": f"Recorded {mins} focused minutes.",
            "category": "session",
            "timestamp": (sess.completed_at or now_utc).isoformat(),
            "read": nid in read_set,
        })

    return items


@router.get("", summary="List authenticated student notifications")
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = _build_real_notifications(db, current_user.id)
    unread_count = sum(1 for n in items if not n["read"])
    return {"notifications": items, "unreadCount": unread_count}


@router.get("/unread-count", summary="Get unread notification count")
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = _build_real_notifications(db, current_user.id)
    return {"unreadCount": sum(1 for n in items if not n["read"])}


@router.patch("/{notification_id}/read", summary="Mark a notification as read")
def mark_as_read(notification_id: str, current_user: User = Depends(get_current_user)):
    _READ_IDS.setdefault(current_user.id, set()).add(notification_id)
    return {"id": notification_id, "read": True}


@router.patch("/read-all", summary="Mark all notifications as read")
def mark_all_as_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = _build_real_notifications(db, current_user.id)
    read_set = _READ_IDS.setdefault(current_user.id, set())
    for n in items:
        read_set.add(n["id"])
    return {"unreadCount": 0}


@router.delete("/{notification_id}", summary="Dismiss/delete a notification")
def dismiss_notification(notification_id: str, current_user: User = Depends(get_current_user)):
    _DISMISSED_IDS.setdefault(current_user.id, set()).add(notification_id)
    return {"id": notification_id, "dismissed": True}
