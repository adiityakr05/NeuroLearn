from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    subjects,
    topics,
    study_sessions,
    quizzes,
    revisions,
    analytics,
    planner,
    recommendations,
    dashboard,
    spaced_repetition,
    notifications,
)

api_router = APIRouter()

# Register endpoints under /api
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(topics.router, prefix="/topics", tags=["Topics"])
api_router.include_router(study_sessions.router, prefix="/study-sessions", tags=["Study Sessions"])
api_router.include_router(quizzes.router, prefix="/quiz-attempts", tags=["Quiz Attempts"])
api_router.include_router(revisions.router, prefix="/revision-history", tags=["Revision History"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Progress & Analytics"])
api_router.include_router(planner.router, prefix="/study-plan", tags=["Study Planner"])
api_router.include_router(spaced_repetition.router, prefix="/spaced-repetition", tags=["Spaced Repetition"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["AI Recommendations"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# Future domain routers will be registered here incrementally:
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
# api_router.include_router(subjects.router, prefix="/subjects", tags=["Subjects"])
# api_router.include_router(planner.router, prefix="/study-plan", tags=["Planner"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
# api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
