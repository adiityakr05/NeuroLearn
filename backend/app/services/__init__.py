from app.services.user_service import user_service, UserService
from app.services.curriculum_service import (
    subject_service,
    topic_service,
    SubjectService,
    TopicService,
)

from app.services.activity_service import activity_service, ActivityService
from app.services.planner_service import (
    planner_service,
    recommendation_service,
    PlannerService,
    RecommendationService,
)
from app.services.agent_adapters import (
    ai_agent_adapter,
    ml_retention_adapter,
    AIAgentAdapter,
    MLRetentionAdapter,
)

__all__ = [
    "user_service",
    "UserService",
    "subject_service",
    "topic_service",
    "SubjectService",
    "TopicService",
    "activity_service",
    "ActivityService",
    "planner_service",
    "recommendation_service",
    "PlannerService",
    "RecommendationService",
    "ai_agent_adapter",
    "ml_retention_adapter",
    "AIAgentAdapter",
    "MLRetentionAdapter",
]
