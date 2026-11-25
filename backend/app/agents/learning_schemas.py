"""
Learning Agent Schemas
======================
Pydantic schemas representing strategy adjustments, trajectory classifications,
and calibration proposals produced by the Learning Agent.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.agents.schemas import AgentRecommendationCandidate


class TopicLearningTrajectory(BaseModel):
    topic_id: str
    topic_name: str
    trend: str  # "improving", "declining", "stable", "consistently_high", "repeated_low", "insufficient_data"
    average_score: float
    score_history: List[float] = []
    current_lambda: float
    proposed_lambda: float
    current_interval_days: int
    proposed_interval_days: int
    proposed_difficulty: Optional[str] = None
    recommended_duration_minutes: int = 45
    rationale: str

    model_config = ConfigDict(from_attributes=True)


class LearningAgentResult(BaseModel):
    user_id: str
    trajectories: List[TopicLearningTrajectory] = []
    recommendation_candidates: List[AgentRecommendationCandidate] = []
    adherence_insights: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)
