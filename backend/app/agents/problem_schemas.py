"""
Problem Generator Schemas
=========================
Pydantic v2 schemas for generated diagnostic questions, practice sets,
and generation metadata.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.agents.schemas import AgentRecommendationCandidate


class GeneratedQuestion(BaseModel):
    id: str
    topic_id: str
    topic_name: str
    question_text: str
    question_type: str  # "mcq", "true_false", "short_answer", "conceptual_application"
    difficulty: str  # "Easy", "Medium", "Hard"
    bloom_level: str  # "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    learning_objective: str

    model_config = ConfigDict(from_attributes=True)


class DiagnosticProbeSet(BaseModel):
    topic_id: str
    topic_name: str
    target_bloom_level: str
    difficulty: str
    questions: List[GeneratedQuestion] = []
    estimated_duration_minutes: int = 15
    diagnostic_rationale: str

    model_config = ConfigDict(from_attributes=True)


class ProblemGeneratorResult(BaseModel):
    user_id: str
    probes: List[DiagnosticProbeSet] = []
    recommendation_candidates: List[AgentRecommendationCandidate] = []
    status: str = "success"  # "success", "insufficient_context", "empty_topics"

    model_config = ConfigDict(from_attributes=True)
