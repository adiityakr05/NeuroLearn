"""
Pydantic v2 Schemas for NeuroLearn Multi-Agent System
=====================================================
Defines typed, validated data contracts for student context, agent inputs,
agent outputs, and recommendation candidates.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TopicContext(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    name: str
    difficulty: str = "Medium"  # Easy, Medium, Hard
    mastery_score: float = 50.0
    retention_score: float = 70.0
    decay_rate_lambda: float = 0.08
    completed: bool = False
    last_revised: Optional[datetime] = None
    next_revision: Optional[datetime] = None
    elapsed_days: float = 0.0
    exam_date: Optional[datetime] = None
    days_until_exam: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class SubjectContext(BaseModel):
    id: str
    name: str
    code: str
    target_mastery: float = 80.0
    exam_date: Optional[datetime] = None
    days_until_exam: Optional[float] = None
    topics_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class QuizAttemptContext(BaseModel):
    id: str
    topic_id: str
    topic_name: Optional[str] = None
    score: float
    accuracy: float
    total_questions: int = 10
    correct_answers: int = 0
    attempted_at: Optional[datetime] = None
    critic_evaluated: bool = False
    critic_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StudySessionContext(BaseModel):
    id: str
    subject_id: str
    topic_id: Optional[str] = None
    date: str
    duration_minutes: int = 45
    status: str = "pending"
    priority: str = "medium"

    model_config = ConfigDict(from_attributes=True)


class ExistingRecommendationContext(BaseModel):
    id: str
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    agent_element: str
    type: str
    priority: str
    status: str = "pending"
    title: str

    model_config = ConfigDict(from_attributes=True)


class StudentProfileContext(BaseModel):
    user_id: str
    full_name: str
    email: str
    program: Optional[str] = None
    semester: Optional[str] = None
    daily_capacity_minutes: int = Field(default=120, ge=15, le=720)

    model_config = ConfigDict(from_attributes=True)


class StudentContext(BaseModel):
    """
    Unified context assembled for agent deliberation.
    Automatically propagates exam dates and calculates days_until_exam for topics
    when missing.
    """
    student: StudentProfileContext
    subjects: List[SubjectContext] = []
    topics: List[TopicContext] = []
    recent_quizzes: List[QuizAttemptContext] = []
    study_sessions: List[StudySessionContext] = []
    active_recommendations: List[ExistingRecommendationContext] = []
    reference_time: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def propagate_exam_dates(self) -> "StudentContext":
        """
        When TopicContext.days_until_exam is missing/None, automatically derives it
        from the corresponding SubjectContext.exam_date relative to reference_time.
        Preserves explicitly supplied days_until_exam values and avoids negative days.
        """
        if not self.subjects or not self.topics:
            return self

        ref_dt = self.reference_time
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)

        # Build subject map with exam dates
        subj_exam_map: Dict[str, Any] = {}
        for s in self.subjects:
            exam_dt = s.exam_date
            if exam_dt:
                if isinstance(exam_dt, str):
                    try:
                        exam_dt = datetime.fromisoformat(exam_dt.replace("Z", "+00:00"))
                    except Exception:
                        exam_dt = None
                if exam_dt and exam_dt.tzinfo is None:
                    exam_dt = exam_dt.replace(tzinfo=timezone.utc)
            subj_exam_map[s.id] = (exam_dt, s.days_until_exam)

        updated_topics = []
        for t in self.topics:
            topic_dict = t.model_dump()
            # If days_until_exam is missing or None, derive from subject
            if topic_dict.get("days_until_exam") is None:
                if t.subject_id in subj_exam_map:
                    s_exam_dt, s_days = subj_exam_map[t.subject_id]
                    if s_days is not None:
                        topic_dict["days_until_exam"] = max(0.0, float(s_days))
                    elif s_exam_dt:
                        diff_sec = (s_exam_dt - ref_dt).total_seconds()
                        topic_dict["days_until_exam"] = max(0.0, round(diff_sec / 86400.0, 2))
                    if not topic_dict.get("exam_date") and s_exam_dt:
                        topic_dict["exam_date"] = s_exam_dt
            updated_topics.append(TopicContext(**topic_dict))

        self.topics = updated_topics
        return self


class AgentRecommendationCandidate(BaseModel):
    """
    Standard recommendation output candidate from any agent element.
    Compatible with database Recommendation schema.
    """
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    agent_element: str  # "Performance Element", "Critic", "Learning Element", "Problem Generator"
    type: str  # "retention_decay", "exam_priority", "pacing_optimization", "diagnostic_probe"
    priority: str = "medium"  # "low", "medium", "high", "urgent"
    title: str
    reason_type: str
    reason_detail: str
    suggested_slot: Optional[str] = None
    estimated_duration_minutes: int = 45

    model_config = ConfigDict(from_attributes=True)


class CriticEvaluationResult(BaseModel):
    """
    Structured output from Critic Agent evaluation.
    """
    attempt_id: str
    topic_id: str
    topic_name: str
    score: float
    accuracy: float
    performance_category: str  # "High Concern", "Moderate Concern", "Reinforcement"
    concern_level: str  # "high", "moderate", "low"
    critic_notes: str
    recommended_action: str
    needs_practice: bool
    recommendation_candidate: Optional[AgentRecommendationCandidate] = None

    model_config = ConfigDict(from_attributes=True)
