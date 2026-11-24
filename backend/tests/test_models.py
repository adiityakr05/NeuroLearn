import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.models import (
    User,
    Subject,
    Topic,
    StudySession,
    QuizAttempt,
    RevisionHistory,
    Recommendation,
)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Creates an isolated in-memory SQLite database session for testing models.
    """
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_create_user(db_session: Session):
    user = User(
        email="test.student@college.edu",
        hashed_password="fake_hashed_secret_123",
        full_name="Test Student",
        program="B.Tech Computer Science & AI",
        semester="Semester 6",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test.student@college.edu"
    assert user.is_active is True
    assert user.created_at is not None


def test_user_email_unique_constraint(db_session: Session):
    user1 = User(
        email="duplicate@college.edu",
        hashed_password="hash1",
        full_name="Student One",
    )
    user2 = User(
        email="duplicate@college.edu",
        hashed_password="hash2",
        full_name="Student Two",
    )
    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_user_subject_topic_relationships_and_cascades(db_session: Session):
    user = User(
        email="aditya@college.edu",
        hashed_password="fake_hashed_secret_123",
        full_name="Aditya Kumar",
    )
    db_session.add(user)
    db_session.commit()

    # Create Subject
    subject = Subject(
        user_id=user.id,
        name="Machine Learning",
        code="CS601",
        color="#6366F1",
        description="Core ML Foundations",
        target_mastery=85.0,
    )
    db_session.add(subject)
    db_session.commit()

    # Create Topics under Subject
    topic1 = Topic(
        subject_id=subject.id,
        name="Support Vector Machines & Kernels",
        difficulty="Hard",
        mastery_score=52.0,
        retention_score=55.0,
        decay_rate_lambda=0.08,
    )
    topic2 = Topic(
        subject_id=subject.id,
        name="Neural Networks: Backpropagation",
        difficulty="Hard",
        mastery_score=84.0,
        retention_score=88.0,
        decay_rate_lambda=0.04,
    )
    db_session.add_all([topic1, topic2])
    db_session.commit()

    # Verify relationships
    db_session.refresh(user)
    assert len(user.subjects) == 1
    assert user.subjects[0].code == "CS601"

    db_session.refresh(subject)
    assert len(subject.topics) == 2
    assert {t.name for t in subject.topics} == {
        "Support Vector Machines & Kernels",
        "Neural Networks: Backpropagation",
    }

    # Test Cascade Delete: deleting user should cascade delete subjects and topics
    user_id = user.id
    subject_id = subject.id
    db_session.delete(user)
    db_session.commit()

    assert db_session.scalar(select(User).where(User.id == user_id)) is None
    assert db_session.scalar(select(Subject).where(Subject.id == subject_id)) is None
    assert len(db_session.scalars(select(Topic).where(Topic.subject_id == subject_id)).all()) == 0


def test_study_session_creation(db_session: Session):
    user = User(email="learner@college.edu", hashed_password="pw", full_name="Learner")
    db_session.add(user)
    db_session.commit()

    subject = Subject(user_id=user.id, name="Operating Systems", code="CS603")
    db_session.add(subject)
    db_session.commit()

    topic = Topic(subject_id=subject.id, name="Virtual Memory")
    db_session.add(topic)
    db_session.commit()

    session = StudySession(
        user_id=user.id,
        subject_id=subject.id,
        topic_id=topic.id,
        date="2026-11-24",
        time_slot="09:00 AM - 10:30 AM",
        duration_minutes=90,
        status="pending",
        priority="high",
        retention_score=68.5,
        repetition_cycle="Cycle 2",
        ai_reason="Decay threshold crossed; revision needed before exam.",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user.id == user.id
    assert session.subject.code == "CS603"
    assert session.topic.name == "Virtual Memory"
    assert session.is_overdue is False


def test_quiz_attempt_and_revision_history(db_session: Session):
    user = User(email="tester@college.edu", hashed_password="pw", full_name="Tester")
    db_session.add(user)
    db_session.commit()

    subject = Subject(user_id=user.id, name="Algorithms", code="CS604")
    db_session.add(subject)
    db_session.commit()

    topic = Topic(subject_id=subject.id, name="Dynamic Programming: 0/1 Knapsack")
    db_session.add(topic)
    db_session.commit()

    # Quiz attempt
    quiz = QuizAttempt(
        user_id=user.id,
        topic_id=topic.id,
        title="DP Diagnostic Test",
        score=75.0,
        accuracy=80.0,
        total_questions=10,
        correct_answers=8,
        critic_evaluated=True,
        critic_notes="Solid base, need work on 2D table space optimization.",
    )
    db_session.add(quiz)

    # Revision history
    rev = RevisionHistory(
        topic_id=topic.id,
        revision_date="2026-11-23",
        score=80.0,
        interval_days=4,
        repetition_number=2,
        note="Optimal recall achieved.",
    )
    db_session.add(rev)
    db_session.commit()

    db_session.refresh(topic)
    assert len(topic.quiz_attempts) == 1
    assert topic.quiz_attempts[0].score == 75.0
    assert len(topic.revision_history) == 1
    assert topic.revision_history[0].interval_days == 4


def test_recommendation_creation(db_session: Session):
    user = User(email="agent_test@college.edu", hashed_password="pw", full_name="Agent Student")
    db_session.add(user)
    db_session.commit()

    subject = Subject(user_id=user.id, name="Database Systems", code="CS602")
    db_session.add(subject)
    db_session.commit()

    rec = Recommendation(
        user_id=user.id,
        subject_id=subject.id,
        agent_element="Performance Element",
        type="spaced_repetition",
        priority="medium",
        title="Spaced Review: B+ Trees",
        reason_type="Optimal Interval Milestone",
        reason_detail="Interval 3 milestone reached. 30m review locks long-term retention.",
        suggested_slot="Tomorrow, 11:00 AM",
        estimated_duration_minutes=30,
        status="pending",
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    assert rec.id is not None
    assert rec.agent_element == "Performance Element"
    assert rec.status == "pending"
    assert rec.user.email == "agent_test@college.edu"
