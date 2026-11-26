from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Header, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User, Topic, Subject
from app.schemas.entities import QuizAttemptCreate, QuizAttemptResponse
from app.services.activity_service import activity_service
from app.services.gemini_quiz_service import gemini_quiz_service
from app.agents.problem_generator import problem_generator
from app.agents.schemas import TopicContext

router = APIRouter()


class QuizGenerateRequest(BaseModel):
    topic_id: str
    difficulty: str = Field("Medium", pattern="^(Easy|Medium|Hard)$")
    num_questions: int = Field(5, ge=1, le=20)


@router.post(
    "/generate",
    summary="Generate practice/diagnostic MCQ questions for a topic",
)
async def generate_quiz_questions(
    req: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates MCQ practice questions for a topic using Google Gemini (if configured),
    falling back to ProblemGenerator / Fallback Question Bank when Gemini is unavailable.
    """
    topic = db.scalar(
        select(Topic)
        .join(Subject, Topic.subject_id == Subject.id)
        .where(Topic.id == req.topic_id, Subject.user_id == current_user.id)
    )
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found",
        )

    subject = db.scalar(select(Subject).where(Subject.id == topic.subject_id))
    subject_name = subject.name if subject else "Subject"

    # 1. Attempt live Google Gemini generation
    gemini_questions = await gemini_quiz_service.generate_questions(
        subject=subject_name,
        topic=topic.name,
        difficulty=req.difficulty,
        num_questions=req.num_questions,
    )
    if gemini_questions:
        return {
            "topic_id": topic.id,
            "topic_name": topic.name,
            "difficulty": req.difficulty,
            "source": gemini_questions[0]["source"],
            "questions": gemini_questions,
        }

    # 2. Fallback to ProblemGenerator + Fallback Question Bank
    topic_ctx = TopicContext(
        topic_id=topic.id,
        subject_id=topic.subject_id,
        subject_name=subject.name if subject else "Subject",
        name=topic.name,
        difficulty=req.difficulty,
        mastery_score=topic.mastery_score,
        retention_score=topic.retention_score,
        decay_rate_lambda=topic.decay_rate_lambda,
        completed=topic.completed,
    )

    probes = []
    source = "ProblemGenerator"
    try:
        probes = problem_generator.generate_for_topic(topic_ctx, count=req.num_questions)
    except Exception:
        probes = []

    questions = []
    for idx, p in enumerate(probes[: req.num_questions]):
        opts = getattr(p, "options", None) or [
            f"Core principle of {topic.name}",
            f"Unrelated concept outside {topic.name}",
            f"Partial approximation of {topic.name}",
            f"Opposite assumption to {topic.name}",
        ]
        questions.append({
            "id": f"pg_{idx+1}",
            "question": getattr(p, "prompt", None) or getattr(p, "question", f"Question {idx+1} on {topic.name}"),
            "options": opts,
            "correctIndex": getattr(p, "correct_index", 0),
            "explanation": getattr(p, "explanation", f"Reviews key {req.difficulty.lower()}-tier concepts in {topic.name}."),
            "source": source,
        })

    # Fallback bank if ProblemGenerator returned fewer questions than requested
    if len(questions) < req.num_questions:
        fallback_templates = [
            (
                f"Which statement best describes the fundamental concept of {topic.name}?",
                [
                    f"It governs the core mechanism and behavior within {topic.name}.",
                    f"It only applies when {topic.name} is completely omitted.",
                    "It is an unrelated historical footnote.",
                    "It contradicts standard principles in this subject.",
                ],
                0,
                f"Understanding the core mechanism of {topic.name} is essential for {req.difficulty} mastery.",
            ),
            (
                f"When applying {topic.name} ({req.difficulty} level) to a problem, what is the primary factor to evaluate first?",
                [
                    "The boundary conditions and governing constraints of the topic.",
                    "Ignoring all input parameters.",
                    "Assuming constant output regardless of state.",
                    "Skipping verification steps.",
                ],
                0,
                "Evaluating governing constraints first prevents common conceptual errors.",
            ),
            (
                f"What is a common misconception when studying {topic.name}?",
                [
                    "Confusing surface-level memorization with underlying causal relationships.",
                    "Practicing active recall at spaced intervals.",
                    "Testing understanding with diagnostic problems.",
                    "Connecting the topic to prerequisite concepts.",
                ],
                0,
                "Active recall and causal understanding outperform rote memorization.",
            ),
            (
                f"How does {topic.name} relate to overall mastery in {subject.name if subject else 'this subject'}?",
                [
                    "It builds foundational intuition needed for advanced problem solving.",
                    "It has no connection to any other topic.",
                    "It only matters if never reviewed.",
                    "It replaces the need for practice.",
                ],
                0,
                f"{topic.name} is a key building block in {subject.name if subject else 'the curriculum'}.",
            ),
            (
                f"Which study strategy is most effective for retaining {topic.name} long-term?",
                [
                    "Spaced repetition combined with self-testing before retention decays.",
                    "Single-session cramming without review.",
                    "Passive re-reading without attempting problems.",
                    "Avoiding difficult practice questions.",
                ],
                0,
                "Spaced active recall slows the Ebbinghaus forgetting rate.",
            ),
        ]
        while len(questions) < req.num_questions:
            t_idx = len(questions) % len(fallback_templates)
            q_text, q_opts, q_ans, q_exp = fallback_templates[t_idx]
            questions.append({
                "id": f"fb_{len(questions)+1}",
                "question": q_text,
                "options": q_opts,
                "correctIndex": q_ans,
                "explanation": q_exp,
                "source": "Fallback Question Bank",
            })

    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "difficulty": req.difficulty,
        "source": source if probes else "Fallback Question Bank",
        "questions": questions,
    }


@router.post(
    "",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a quiz attempt",
)
def record_quiz_attempt(
    attempt_in: QuizAttemptCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Optional client UUID for idempotent submission"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records a quiz attempt for the current student.
    Validates total_questions, correct_answers, and score percentage bounds.
    Supports optional Idempotency-Key HTTP header for duplicate prevention.
    """
    effective_key = idempotency_key or attempt_in.idempotency_key
    if effective_key:
        attempt_in.idempotency_key = effective_key
    return activity_service.create_quiz_attempt(db, current_user.id, attempt_in)


@router.get(
    "",
    response_model=List[QuizAttemptResponse],
    summary="List quiz attempts with filters",
)
def list_quiz_attempts(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    topic_id: Optional[str] = Query(None, description="Filter by topic ID"),
    start_date: Optional[str] = Query(None, description="Filter from ISO date"),
    end_date: Optional[str] = Query(None, description="Filter to ISO date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists quiz attempts for the student, with optional subject, topic, and date range filters.
    """
    return activity_service.get_quiz_attempts(
        db,
        user_id=current_user.id,
        subject_id=subject_id,
        topic_id=topic_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{attempt_id}",
    response_model=QuizAttemptResponse,
    summary="Retrieve a quiz attempt by ID",
)
def get_quiz_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single quiz attempt by ID.
    Returns 404 if not found or unauthorized.
    """
    return activity_service.get_quiz_attempt_by_id(db, attempt_id, current_user.id)
