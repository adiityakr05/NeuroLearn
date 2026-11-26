"""
NeuroLearn Milestone 7 - Synthetic Student Profiles
===================================================
10 Deterministic Student Profiles for AI Quality and Personalization Evaluation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from app.agents.schemas import (
    StudentProfileContext,
    SubjectContext,
    TopicContext,
    QuizAttemptContext,
    StudySessionContext,
    StudentContext,
)


def get_base_time() -> datetime:
    return datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)


def create_profile_1_high_performer() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_1_high",
        email="high_performer@neurolearn.ai",
        full_name="High Performer",
        program="Computer Science",
        semester="Semester 6",
        daily_capacity_minutes=120,
    )
    subj = SubjectContext(
        id="subj_high_1",
        name="Deep Learning",
        code="DL601",
        target_mastery=85.0,
        exam_date=now + timedelta(days=20),
    )
    topics = [
        TopicContext(
            id="t_high_1",
            subject_id="subj_high_1",
            subject_name="Deep Learning",
            name="Convolutional Networks",
            difficulty="Hard",
            mastery_score=92.0,
            retention_score=94.0,
            decay_rate_lambda=0.03,
            elapsed_days=1.5,
            last_revised=now - timedelta(days=1, hours=12),
            next_revision=now + timedelta(days=8),
        ),
        TopicContext(
            id="t_high_2",
            subject_id="subj_high_1",
            subject_name="Deep Learning",
            name="Recurrent Neural Networks",
            difficulty="Medium",
            mastery_score=88.0,
            retention_score=90.0,
            decay_rate_lambda=0.04,
            elapsed_days=2.0,
            last_revised=now - timedelta(days=2),
            next_revision=now + timedelta(days=6),
        ),
    ]
    quizzes = [
        QuizAttemptContext(
            id="q_high_1",
            topic_id="t_high_1",
            topic_name="Convolutional Networks",
            score=95.0,
            accuracy=95.0,
            total_questions=10,
            correct_answers=9,
            critic_evaluated=False,
            created_at=now - timedelta(days=1, hours=12),
        ),
        QuizAttemptContext(
            id="q_high_2",
            topic_id="t_high_2",
            topic_name="Recurrent Neural Networks",
            score=90.0,
            accuracy=90.0,
            total_questions=10,
            correct_answers=9,
            critic_evaluated=False,
            created_at=now - timedelta(days=2),
        ),
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=quizzes,
    )


def create_profile_2_low_performer() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_2_low",
        email="low_performer@neurolearn.ai",
        full_name="Struggling Student",
        program="Computer Science",
        semester="Semester 6",
        daily_capacity_minutes=90,
    )
    subj = SubjectContext(
        id="subj_low_1",
        name="Operating Systems",
        code="OS602",
        target_mastery=75.0,
        exam_date=now + timedelta(days=15),
    )
    topics = [
        TopicContext(
            id="t_low_1",
            subject_id="subj_low_1",
            subject_name="Operating Systems",
            name="Memory Paging & Segmentation",
            difficulty="Hard",
            mastery_score=35.0,
            retention_score=40.0,
            decay_rate_lambda=0.18,
            elapsed_days=3.0,
            last_revised=now - timedelta(days=3),
            next_revision=now - timedelta(days=1),
        ),
        TopicContext(
            id="t_low_2",
            subject_id="subj_low_1",
            subject_name="Operating Systems",
            name="Semaphore Synchronization",
            difficulty="Medium",
            mastery_score=42.0,
            retention_score=45.0,
            decay_rate_lambda=0.15,
            elapsed_days=2.5,
            last_revised=now - timedelta(days=2, hours=12),
            next_revision=now,
        ),
    ]
    quizzes = [
        QuizAttemptContext(
            id="q_low_1",
            topic_id="t_low_1",
            topic_name="Memory Paging & Segmentation",
            score=30.0,
            accuracy=30.0,
            total_questions=10,
            correct_answers=3,
            critic_evaluated=False,
            created_at=now - timedelta(days=3),
        ),
        QuizAttemptContext(
            id="q_low_2",
            topic_id="t_low_1",
            topic_name="Memory Paging & Segmentation",
            score=40.0,
            accuracy=40.0,
            total_questions=10,
            correct_answers=4,
            critic_evaluated=False,
            created_at=now - timedelta(days=1),
        ),
        QuizAttemptContext(
            id="q_low_3",
            topic_id="t_low_2",
            topic_name="Semaphore Synchronization",
            score=45.0,
            accuracy=45.0,
            total_questions=10,
            correct_answers=4,
            critic_evaluated=False,
            created_at=now - timedelta(days=2),
        ),
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=quizzes,
    )


def create_profile_3_rapid_decay() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_3_decay",
        email="rapid_decay@neurolearn.ai",
        full_name="Rapid Forgetter",
        program="Data Science",
        semester="Semester 4",
        daily_capacity_minutes=90,
    )
    subj = SubjectContext(
        id="subj_decay_1",
        name="Linear Algebra",
        code="MATH201",
        target_mastery=80.0,
        exam_date=now + timedelta(days=14),
    )
    topics = [
        TopicContext(
            id="t_decay_1",
            subject_id="subj_decay_1",
            subject_name="Linear Algebra",
            name="Eigenvalues & Eigenvectors",
            difficulty="Hard",
            mastery_score=60.0,
            retention_score=35.0,
            decay_rate_lambda=0.28,
            elapsed_days=6.0,
            last_revised=now - timedelta(days=6),
            next_revision=now - timedelta(days=2),
        )
    ]
    quizzes = [
        QuizAttemptContext(
            id="q_decay_1",
            topic_id="t_decay_1",
            topic_name="Eigenvalues & Eigenvectors",
            score=50.0,
            accuracy=50.0,
            total_questions=10,
            correct_answers=5,
            critic_evaluated=False,
            created_at=now - timedelta(days=6),
        )
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=quizzes,
    )


def create_profile_4_exam_imminent() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_4_exam_3d",
        email="exam_imminent@neurolearn.ai",
        full_name="Exam Crammer",
        program="Computer Science",
        semester="Semester 6",
        daily_capacity_minutes=120,
    )
    subj = SubjectContext(
        id="subj_exam_1",
        name="Computer Networks",
        code="CN603",
        target_mastery=85.0,
        exam_date=now + timedelta(days=3),
    )
    topics = [
        TopicContext(
            id="t_exam_1",
            subject_id="subj_exam_1",
            subject_name="Computer Networks",
            name="TCP Congestion Control",
            difficulty="Hard",
            mastery_score=50.0,
            retention_score=60.0,
            decay_rate_lambda=0.10,
            elapsed_days=3.0,
            last_revised=now - timedelta(days=3),
            next_revision=now,
        ),
        TopicContext(
            id="t_exam_2",
            subject_id="subj_exam_1",
            subject_name="Computer Networks",
            name="Routing Protocols (OSPF & BGP)",
            difficulty="Medium",
            mastery_score=55.0,
            retention_score=65.0,
            decay_rate_lambda=0.08,
            elapsed_days=2.0,
            last_revised=now - timedelta(days=2),
            next_revision=now + timedelta(days=1),
        ),
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=[],
    )


def create_profile_5_exam_distant() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_5_exam_30d",
        email="exam_distant@neurolearn.ai",
        full_name="Long Term Planner",
        program="Computer Science",
        semester="Semester 6",
        daily_capacity_minutes=90,
    )
    subj = SubjectContext(
        id="subj_distant_1",
        name="Compiler Design",
        code="CD604",
        target_mastery=80.0,
        exam_date=now + timedelta(days=30),
    )
    topics = [
        TopicContext(
            id="t_distant_1",
            subject_id="subj_distant_1",
            subject_name="Compiler Design",
            name="Lexical Analysis",
            difficulty="Medium",
            mastery_score=60.0,
            retention_score=75.0,
            decay_rate_lambda=0.07,
            elapsed_days=4.0,
            last_revised=now - timedelta(days=4),
            next_revision=now + timedelta(days=5),
        )
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=[],
    )


def create_profile_6_capacity_constrained() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_6_capacity_30m",
        email="busy_student@neurolearn.ai",
        full_name="Busy Part-Time Student",
        program="Software Engineering",
        semester="Semester 5",
        daily_capacity_minutes=30,
    )
    subj = SubjectContext(
        id="subj_busy_1",
        name="Software Architecture",
        code="SE501",
        target_mastery=75.0,
    )
    topics = [
        TopicContext(
            id="t_busy_1",
            subject_id="subj_busy_1",
            subject_name="Software Architecture",
            name="Microservices Communication",
            difficulty="Hard",
            mastery_score=45.0,
            retention_score=50.0,
            decay_rate_lambda=0.10,
            elapsed_days=5.0,
        ),
        TopicContext(
            id="t_busy_2",
            subject_id="subj_busy_1",
            subject_name="Software Architecture",
            name="Event-Driven Patterns",
            difficulty="Medium",
            mastery_score=50.0,
            retention_score=55.0,
            decay_rate_lambda=0.09,
            elapsed_days=4.0,
        ),
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=[],
    )


def create_profile_7_high_mastery_low_retention() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_7_high_m_low_r",
        email="lapsed_master@neurolearn.ai",
        full_name="Lapsed Master",
        daily_capacity_minutes=90,
    )
    subj = SubjectContext(
        id="subj_lapsed_1",
        name="Database Management",
        code="DB401",
        target_mastery=85.0,
    )
    topics = [
        TopicContext(
            id="t_lapsed_1",
            subject_id="subj_lapsed_1",
            subject_name="Database Management",
            name="Query Optimization & B-Trees",
            difficulty="Hard",
            mastery_score=95.0,
            retention_score=35.0,
            decay_rate_lambda=0.08,
            elapsed_days=25.0,
            last_revised=now - timedelta(days=25),
        )
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=[],
    )


def create_profile_8_low_mastery_high_retention() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_8_low_m_high_r",
        email="fresh_learner@neurolearn.ai",
        full_name="Fresh Learner",
        daily_capacity_minutes=90,
    )
    subj = SubjectContext(
        id="subj_fresh_1",
        name="Algorithms",
        code="CS301",
        target_mastery=80.0,
    )
    topics = [
        TopicContext(
            id="t_fresh_1",
            subject_id="subj_fresh_1",
            subject_name="Algorithms",
            name="Dynamic Programming (Knapsack)",
            difficulty="Hard",
            mastery_score=30.0,
            retention_score=98.0,
            decay_rate_lambda=0.08,
            elapsed_days=0.08,
            last_revised=now - timedelta(hours=2),
        )
    ]
    quizzes = [
        QuizAttemptContext(
            id="q_fresh_1",
            topic_id="t_fresh_1",
            topic_name="Dynamic Programming (Knapsack)",
            score=35.0,
            accuracy=35.0,
            total_questions=10,
            correct_answers=3,
            critic_evaluated=False,
            created_at=now - timedelta(hours=2),
        )
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=quizzes,
    )


def create_profile_9_overdue_heavy() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_9_overdue",
        email="overdue_student@neurolearn.ai",
        full_name="Overdue Student",
        daily_capacity_minutes=120,
    )
    subj = SubjectContext(
        id="subj_overdue_1",
        name="Information Security",
        code="IS502",
        target_mastery=80.0,
    )
    topics = [
        TopicContext(
            id="t_overdue_1",
            subject_id="subj_overdue_1",
            subject_name="Information Security",
            name="RSA Public Key Cryptography",
            difficulty="Hard",
            mastery_score=55.0,
            retention_score=40.0,
            decay_rate_lambda=0.12,
            elapsed_days=10.0,
            last_revised=now - timedelta(days=10),
            next_revision=now - timedelta(days=4),
        ),
        TopicContext(
            id="t_overdue_2",
            subject_id="subj_overdue_1",
            subject_name="Information Security",
            name="AES Symmetric Encryption",
            difficulty="Medium",
            mastery_score=60.0,
            retention_score=48.0,
            decay_rate_lambda=0.09,
            elapsed_days=8.0,
            last_revised=now - timedelta(days=8),
            next_revision=now - timedelta(days=2),
        ),
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=[],
    )


def create_profile_10_insufficient_history() -> StudentContext:
    now = get_base_time()
    student = StudentProfileContext(
        user_id="syn_user_10_newbie",
        email="newbie@neurolearn.ai",
        full_name="Brand New Student",
        daily_capacity_minutes=60,
    )
    subj = SubjectContext(
        id="subj_new_1",
        name="Introduction to Computing",
        code="CS100",
        target_mastery=70.0,
    )
    topics = [
        TopicContext(
            id="t_new_1",
            subject_id="subj_new_1",
            subject_name="Introduction to Computing",
            name="Binary & Hexadecimal Numbers",
            difficulty="Easy",
            mastery_score=50.0,
            retention_score=70.0,
            decay_rate_lambda=0.08,
            elapsed_days=0.0,
            last_revised=None,
            next_revision=None,
        )
    ]
    return StudentContext(
        reference_time=now,
        student=student,
        subjects=[subj],
        topics=topics,
        recent_quizzes=[],
    )


def get_all_synthetic_profiles() -> Dict[str, StudentContext]:
    return {
        "1_high_performer": create_profile_1_high_performer(),
        "2_low_performer": create_profile_2_low_performer(),
        "3_rapid_decay": create_profile_3_rapid_decay(),
        "4_exam_imminent": create_profile_4_exam_imminent(),
        "5_exam_distant": create_profile_5_exam_distant(),
        "6_capacity_constrained": create_profile_6_capacity_constrained(),
        "7_high_mastery_low_retention": create_profile_7_high_mastery_low_retention(),
        "8_low_mastery_high_retention": create_profile_8_low_mastery_high_retention(),
        "9_overdue_heavy": create_profile_9_overdue_heavy(),
        "10_insufficient_history": create_profile_10_insufficient_history(),
    }
