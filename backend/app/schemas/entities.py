from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==============================================================================
# USER SCHEMAS
# ==============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    program: Optional[str] = "B.Tech Computer Science & AI"
    semester: Optional[str] = "Semester 6"
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    program: Optional[str] = None
    semester: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# SUBJECT SCHEMAS
# ==============================================================================

class SubjectBase(BaseModel):
    name: str
    code: str
    color: str = "#6366F1"
    description: Optional[str] = None
    target_mastery: float = 80.0
    exam_date: Optional[datetime] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    target_mastery: Optional[float] = None
    exam_date: Optional[datetime] = None


class SubjectResponse(SubjectBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubjectWithTopicsResponse(SubjectResponse):
    topics: List["TopicResponse"] = []


# ==============================================================================
# TOPIC SCHEMAS
# ==============================================================================

class TopicBase(BaseModel):
    name: str
    difficulty: str = "Medium"
    mastery_score: float = 50.0
    retention_score: float = 70.0
    completed: bool = False
    last_revised: Optional[datetime] = None
    next_revision: Optional[datetime] = None


class TopicCreate(TopicBase):
    subject_id: Optional[str] = None


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    difficulty: Optional[str] = None
    mastery_score: Optional[float] = None
    retention_score: Optional[float] = None
    completed: Optional[bool] = None
    last_revised: Optional[datetime] = None
    next_revision: Optional[datetime] = None


class TopicResponse(TopicBase):
    id: str
    subject_id: str
    decay_rate_lambda: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Rebuild model to resolve forward reference in SubjectWithTopicsResponse
SubjectWithTopicsResponse.model_rebuild()


# ==============================================================================
# STUDY SESSION SCHEMAS
# ==============================================================================

class StudySessionBase(BaseModel):
    subject_id: str
    topic_id: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    session_date: Optional[str] = None  # Supported alias for date
    time_slot: Optional[str] = None
    duration_minutes: int = 45
    status: str = "pending"  # pending, in_progress, completed
    priority: str = "medium"  # low, medium, high, urgent
    retention_score: float = 70.0
    repetition_cycle: Optional[str] = None
    is_overdue: bool = False
    ai_reason: Optional[str] = None
    notes: Optional[str] = None


class StudySessionCreate(StudySessionBase):
    pass


class StudySessionUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    date: Optional[str] = None
    session_date: Optional[str] = None
    time_slot: Optional[str] = None
    duration_minutes: Optional[int] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class StudySessionResponse(BaseModel):
    id: str
    user_id: str
    subject_id: str
    topic_id: Optional[str] = None
    title: Optional[str] = None
    date: str
    session_date: str
    time_slot: Optional[str] = None
    duration_minutes: int
    status: str
    priority: str
    retention_score: float
    repetition_cycle: Optional[str] = None
    is_overdue: bool
    ai_reason: Optional[str] = None
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# QUIZ ATTEMPT SCHEMAS
# ==============================================================================

class QuizAttemptBase(BaseModel):
    topic_id: str
    title: Optional[str] = "Topic Quiz"
    subject_id: Optional[str] = None
    score: Optional[float] = None
    accuracy: Optional[float] = None
    score_percentage: Optional[float] = None  # Alias for score/accuracy
    total_questions: int = Field(default=10, ge=1)
    correct_answers: int = Field(default=0, ge=0)
    time_taken_seconds: Optional[int] = None
    attempted_at: Optional[datetime] = None
    critic_notes: Optional[str] = None


class QuizAttemptCreate(QuizAttemptBase):
    pass


class QuizAttemptResponse(BaseModel):
    id: str
    user_id: str
    topic_id: str
    subject_id: Optional[str] = None
    title: str
    score: float
    accuracy: float
    score_percentage: float
    total_questions: int
    correct_answers: int
    time_taken_seconds: Optional[int] = None
    attempted_at: datetime
    critic_evaluated: bool
    critic_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# REVISION HISTORY SCHEMAS
# ==============================================================================

class RevisionHistoryBase(BaseModel):
    topic_id: str
    revision_date: str
    score: float = Field(ge=0.0, le=100.0)
    mastery_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    retention_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    interval_days: int = 0
    repetition_number: int = 1
    notes: Optional[str] = None


class RevisionHistoryCreate(RevisionHistoryBase):
    pass


class RevisionHistoryResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    topic_id: str
    revision_date: str
    score: float
    mastery_score: float
    retention_score: float
    interval_days: int
    repetition_number: int
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# PROGRESS & ANALYTICS SCHEMAS
# ==============================================================================

class SubjectProgress(BaseModel):
    subject_id: str
    subject_name: str
    subject_code: str
    color: str
    mastery: float
    target_mastery: float
    total_topics: int
    completed_topics: int
    total_sessions: int
    completed_sessions: int
    total_study_minutes: int
    average_quiz_score: Optional[float] = None


class TopicProgress(BaseModel):
    topic_id: str
    topic_name: str
    subject_id: str
    subject_name: str
    difficulty: str
    mastery_score: float
    retention_score: float
    completed: bool
    revision_count: int
    quiz_attempts_count: int
    last_revised: Optional[datetime] = None
    next_revision: Optional[datetime] = None


class OverallProgressStats(BaseModel):
    total_study_minutes: int
    total_study_hours: float
    total_sessions: int
    completed_sessions: int
    pending_sessions: int
    total_subjects: int
    total_topics: int
    completed_topics: int
    total_quiz_attempts: int
    average_quiz_accuracy: float
    total_revisions: int
    overall_progress_percentage: float
    subjects_progress: List[SubjectProgress] = []
    topics_progress: List[TopicProgress] = []


# ==============================================================================
# RECOMMENDATION SCHEMAS
# ==============================================================================

class RecommendationBase(BaseModel):
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    agent_element: str = "Performance Element"
    type: str
    priority: str = "medium"
    title: str
    reason_type: str
    reason_detail: str
    suggested_slot: Optional[str] = None
    estimated_duration_minutes: int = 45
    status: str = "pending"  # pending, accepted, dismissed, completed


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationFeedbackRequest(BaseModel):
    helpful: bool
    note: Optional[str] = None


class RecommendationStatusUpdate(BaseModel):
    status: str  # pending, accepted, dismissed, completed
    student_adherence: Optional[str] = None  # Followed, Partially Followed, Ignored


class RecommendationResponse(RecommendationBase):
    id: str
    user_id: str
    student_adherence: Optional[str] = None
    feedback_helpful: Optional[bool] = None
    feedback_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationsHubResponse(BaseModel):
    activeRecommendations: List[RecommendationResponse]
    history: List[RecommendationResponse]
    countsByElement: dict
    totalPending: int


# ==============================================================================
# STUDY PLANNER SCHEMAS
# ==============================================================================

class DailyStudyPlanResponse(BaseModel):
    date: str
    sessions: List[StudySessionResponse]
    totalSessions: int
    completedSessions: int
    totalMinutes: int


class StudyPlanRescheduleRequest(BaseModel):
    taskId: Optional[str] = None
    task_id: Optional[str] = None
    newDate: Optional[str] = None
    new_date: Optional[str] = None
    newSlot: Optional[str] = None
    new_slot: Optional[str] = None
    reason: Optional[str] = None


class StudyTaskStatusToggleRequest(BaseModel):
    taskId: Optional[str] = None
    task_id: Optional[str] = None
    status: str = "completed"
