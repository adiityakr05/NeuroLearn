import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    # Relationships
    subjects: Mapped[List["Subject"]] = relationship(
        "Subject", back_populates="user", cascade="all, delete-orphan"
    )
    study_sessions: Mapped[List["StudySession"]] = relationship(
        "StudySession", back_populates="user", cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} name={self.full_name}>"


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(50), default="#6366F1", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_mastery: Mapped[float] = mapped_column(Float, default=80.0, nullable=False)
    exam_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    # Unique constraint per user: a user cannot have two subjects with the same code
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_subject_code"),
        Index("ix_subjects_user_name", "user_id", "name"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subjects")
    topics: Mapped[List["Topic"]] = relationship(
        "Topic", back_populates="subject", cascade="all, delete-orphan"
    )
    study_sessions: Mapped[List["StudySession"]] = relationship(
        "StudySession", back_populates="subject", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="subject", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.code} name={self.name}>"


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)  # Easy, Medium, Hard
    mastery_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)       # 0.0 to 100.0
    retention_score: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)     # 0.0 to 100.0
    decay_rate_lambda: Mapped[float] = mapped_column(Float, default=0.08, nullable=False)   # Ebbinghaus lambda
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_revised: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_revision: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_subject_topic_name"),
        Index("ix_topics_next_revision", "next_revision"),
    )

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="topics")
    study_sessions: Mapped[List["StudySession"]] = relationship(
        "StudySession", back_populates="topic", cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="topic", cascade="all, delete-orphan"
    )
    revision_history: Mapped[List["RevisionHistory"]] = relationship(
        "RevisionHistory", back_populates="topic", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} name={self.name} mastery={self.mastery_score}>"


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="SET NULL"), index=True, nullable=True
    )
    date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)              # "YYYY-MM-DD"
    time_slot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)          # e.g. "09:00 AM - 10:30 AM"
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)     # pending, in_progress, completed
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)    # low, medium, high, urgent
    retention_score: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)
    repetition_cycle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # e.g. "Cycle 2 (3-Day Gap)"
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)                 # Performance Element rationale
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_study_sessions_user_date", "user_id", "date"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="study_sessions")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="study_sessions")
    topic: Mapped[Optional["Topic"]] = relationship("Topic", back_populates="study_sessions")

    def __repr__(self) -> str:
        return f"<StudySession id={self.id} date={self.date} status={self.status}>"


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    topic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)                            # 0.0 to 100.0
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)                         # 0.0 to 100.0
    total_questions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    critic_evaluated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    critic_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_user_quiz_idempotency"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="quiz_attempts")
    topic: Mapped["Topic"] = relationship("Topic", back_populates="quiz_attempts")

    def __repr__(self) -> str:
        return f"<QuizAttempt id={self.id} score={self.score} accuracy={self.accuracy}>"


class RevisionHistory(Base):
    __tablename__ = "revision_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    topic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="CASCADE"), index=True, nullable=False
    )
    revision_date: Mapped[str] = mapped_column(String(10), nullable=False)                 # "YYYY-MM-DD"
    score: Mapped[float] = mapped_column(Float, nullable=False)                            # Accuracy achieved (0-100)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)         # Elapsed days since last review
    repetition_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)     # Repetition cycle count
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_revision_history_topic_date", "topic_id", "revision_date"),
    )

    # Relationships
    topic: Mapped["Topic"] = relationship("Topic", back_populates="revision_history")

    def __repr__(self) -> str:
        return f"<RevisionHistory id={self.id} topic_id={self.topic_id} score={self.score}>"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="SET NULL"), index=True, nullable=True
    )
    agent_element: Mapped[str] = mapped_column(
        String(50), default="Performance Element", nullable=False
    )  # Performance Element, Critic, Learning Element, Problem Generator
    type: Mapped[str] = mapped_column(String(50), nullable=False)                          # retention_decay, exam_priority, pacing_optimization, diagnostic_probe
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)    # low, medium, high, urgent
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_type: Mapped[str] = mapped_column(String(100), nullable=False)
    reason_detail: Mapped[str] = mapped_column(Text, nullable=False)                       # Explainable AI rationale
    suggested_slot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)     # pending, accepted, dismissed, completed
    student_adherence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)    # Followed, Partially Followed, Ignored
    feedback_helpful: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)        # True (helpful), False (not helpful)
    feedback_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)               # Student note or feedback comments
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_recommendations_user_status", "user_id", "status"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recommendations")
    subject: Mapped[Optional["Subject"]] = relationship("Subject", back_populates="recommendations")
    topic: Mapped[Optional["Topic"]] = relationship("Topic", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} type={self.type} status={self.status}>"
