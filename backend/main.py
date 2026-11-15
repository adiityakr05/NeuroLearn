"""
NeuroLearn FastAPI Backend
Phase 2.5 — Retention Prediction and Study Event API
"""

import logging
from backend.study_planner import StudyPlannerService
from backend.study_session_service import StudySessionService
from backend.study_completion_service import StudyCompletionService
from backend.study_analytics_service import StudyAnalyticsService
from backend.study_analytics_service import StudyAnalyticsService
from backend.study_insights_service import StudyInsightsService
from backend.study_insights_service import StudyInsightsService
from backend.learning_behavior_service import LearningBehaviorService
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.database import initialize_database
from backend.review_service import ReviewEventService
from backend.schedule_repository import ScheduleRepository
from backend.scheduling_service import PersonalizedSchedulingService

from ml.data.schemas import ReviewEventRecord
from ml.service.contracts import PredictionRequestItem, BatchPredictionRequest
from ml.service.inference import RetentionInferenceService


logger = logging.getLogger(__name__)

app = FastAPI(
    title="NeuroLearn API",
    description="Backend API for NeuroLearn adaptive learning",
    version="0.3.0",
)

# Load the registered ML model or activate its fallback.
inference_service = RetentionInferenceService()


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

@app.on_event("startup")
def startup_event():
    """Initialize SQLite database when the API starts."""
    initialize_database()


# --------------------------------------------------
# API SCHEMAS
# --------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    application: str
    timestamp: str


class RetentionPredictionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    topic_id: str = Field(min_length=1)

    elapsed_days: float = Field(ge=0)
    stability_days_prior: float = Field(gt=0)

    repetition_count_prior: int = Field(default=0, ge=0)
    topic_difficulty_prior: float = Field(default=0.5, ge=0.1, le=1.0)

    last_rating_prior: int | None = Field(default=None, ge=1, le=4)

    user_prior_recall_rate: float = Field(default=0.0, ge=0, le=1)
    user_prior_reviews_count: int = Field(default=0, ge=0)

    topic_prior_quiz_avg: float | None = Field(default=None, ge=0, le=1)
    has_prior_quiz: int = Field(default=0, ge=0, le=1)


class BatchRetentionPredictionRequest(BaseModel):
    items: list[RetentionPredictionRequest] = Field(
        min_length=1,
        max_length=100,
    )


class RetentionPredictionResponse(BaseModel):
    user_id: str
    topic_id: str
    predicted_retention_prob: float
    is_cold_start: bool
    model_name: str
    model_version: str
    is_fallback: bool
    fallback_reason: str | None
    is_synthetic_model: bool
    timestamp: str


class ReviewEventRequest(BaseModel):
    event_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    topic_id: str = Field(min_length=1)



    timestamp: str
    elapsed_days: float = Field(ge=0)
    stability_days_prior: float = Field(gt=0)
    repetition_count_prior: int = Field(default=0, ge=0)
    topic_difficulty_prior: float = Field(default=0.5, ge=0.1, le=1.0)
    last_rating_prior: int | None = Field(default=None, ge=1, le=4)
    user_prior_recall_rate: float = Field(default=0.0, ge=0, le=1)
    user_prior_reviews_count: int = Field(default=0, ge=0)
    topic_prior_quiz_avg: float | None = Field(default=None, ge=0, le=1)
    has_prior_quiz: int = Field(default=0, ge=0, le=1)
    recall_success: int = Field(ge=0, le=1)
    is_synthetic: bool = False


class ReviewEventResponse(BaseModel):
    event_id: str
    user_id: str
    topic_id: str
    stored: bool



# --------------------------------------------------
# RETENTION PREDICTION
# --------------------------------------------------

@app.post(
    "/api/v1/retention/predict",
    response_model=RetentionPredictionResponse,
)
def predict_retention(request: RetentionPredictionRequest):
    try:
        history = ReviewEventService.get_user_history(
        user_id=request.user_id
        )
        
        request.user_prior_reviews_count = history["total_review_count"]
        
        request.user_prior_recall_rate = (
        history["overall_recall_rate"]
        if history["overall_recall_rate"] is not None
        else 0.5
    )

        prediction_request = PredictionRequestItem(
            user_id=request.user_id,
            topic_id=request.topic_id,
            elapsed_days=request.elapsed_days,
            stability_days_prior=request.stability_days_prior,
            repetition_count_prior=request.repetition_count_prior,
            topic_difficulty_prior=request.topic_difficulty_prior,
            last_rating_prior=request.last_rating_prior,
            user_prior_recall_rate=request.user_prior_recall_rate,
            user_prior_reviews_count=request.user_prior_reviews_count,
            topic_prior_quiz_avg=request.topic_prior_quiz_avg,
            has_prior_quiz=request.has_prior_quiz,
        )

        prediction = inference_service.predict_one(
            prediction_request
        )

        return prediction.to_dict()

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Retention prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Retention prediction failed.",
        )


# --------------------------------------------------
# BATCH RETENTION PREDICTION
# --------------------------------------------------

@app.post("/api/v1/retention/predict/batch")
def predict_retention_batch(
    request: BatchRetentionPredictionRequest,
):
    try:
        items = [
            PredictionRequestItem(
                user_id=item.user_id,
                topic_id=item.topic_id,
                elapsed_days=item.elapsed_days,
                stability_days_prior=item.stability_days_prior,
                repetition_count_prior=item.repetition_count_prior,
                topic_difficulty_prior=item.topic_difficulty_prior,
                last_rating_prior=item.last_rating_prior,
                user_prior_recall_rate=item.user_prior_recall_rate,
                user_prior_reviews_count=item.user_prior_reviews_count,
                topic_prior_quiz_avg=item.topic_prior_quiz_avg,
                has_prior_quiz=item.has_prior_quiz,
            )
            for item in request.items
        ]

        batch_request = BatchPredictionRequest(items=items)
        predictions = inference_service.predict_batch(batch_request)

        return {
            "predictions": [
                prediction.to_dict()
                for prediction in predictions
            ]
        }

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Batch retention prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Batch retention prediction failed.",
        )


# --------------------------------------------------
# REVIEW EVENT API
# --------------------------------------------------


@app.post(
    "/api/v1/reviews",
    response_model=ReviewEventResponse,
    status_code=201,
)
def create_review_event(request: ReviewEventRequest):
    try:
        event = ReviewEventRecord.from_dict(
            request.model_dump()
        )
        result = ReviewEventService.save_event(event)

        try:
            prediction_request = RetentionPredictionRequest(
                user_id=request.user_id,
                topic_id=request.topic_id,
                elapsed_days=request.elapsed_days,
                stability_days_prior=request.stability_days_prior,
                repetition_count_prior=request.repetition_count_prior,
                topic_difficulty_prior=request.topic_difficulty_prior,
                last_rating_prior=request.last_rating_prior,
                user_prior_recall_rate=request.user_prior_recall_rate,
                user_prior_reviews_count=request.user_prior_reviews_count,
                topic_prior_quiz_avg=request.topic_prior_quiz_avg,
                has_prior_quiz=request.has_prior_quiz,
            )

            prediction = predict_retention(prediction_request)

            schedule = PersonalizedSchedulingService.build_review_schedule(
                predicted_retention_prob=prediction["predicted_retention_prob"],
                user_id=request.user_id,
                topic_id=request.topic_id,
            )

            ScheduleRepository.save_schedule(schedule)

        except Exception:
            logger.exception("Automatic schedule refresh failed")

        return result

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(
                status_code=409,
                detail="Review event already exists.",
            )

        logger.exception("Review event storage failed")
        raise HTTPException(
            status_code=500,
            detail="Review event storage failed.",
        )

# --------------------------------------------------
# STUDY PRIORITY API
# --------------------------------------------------

@app.get("/api/v1/study-plan/{user_id}/priorities")
def get_study_priorities(user_id: str):
    priorities = StudyPlannerService.prioritize_due_reviews(
        user_id
    )

    return {
        "user_id": user_id,
        "priorities": priorities,
        "count": len(priorities),
    }

# --------------------------------------------------
# STUDY SESSION API
# --------------------------------------------------

@app.get("/api/v1/study-plan/{user_id}/session")
def generate_study_session(
    user_id: str,
    total_minutes: int = 30,
):
    try:
        return StudySessionService.generate_session(
            user_id=user_id,
            total_minutes=total_minutes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# --------------------------------------------------
# STUDY COMPLETION API
# --------------------------------------------------

from pydantic import BaseModel, Field


class StudyCompletionRequest(BaseModel):
    user_id: str
    planned_minutes: int = Field(gt=0)
    actual_minutes: int = Field(ge=0)
    topics_planned: list[str]
    topics_completed: list[str]


@app.post("/api/v1/study-plan/completions", status_code=201)
def record_study_completion(request: StudyCompletionRequest):
    try:
        return StudyCompletionService.record_completion(
            **request.model_dump()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/study-plan/{user_id}/completions")
def get_study_completions(user_id: str):
    history = StudyCompletionService.get_completion_history(
        user_id
    )

    return {
        "user_id": user_id,
        "history": history,
        "count": len(history),
    }


# --------------------------------------------------
# REVIEW HISTORY
# --------------------------------------------------

@app.get("/api/v1/reviews/{user_id}")
def get_review_history(user_id: str):
    try:
        history = ReviewEventService.get_user_history(
            user_id=user_id
        )
        return history

    except Exception:
        logger.exception("Review history retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Review history retrieval failed.",
        )


@app.get("/api/v1/reviews/{user_id}/history")
def get_review_events(user_id: str):
    try:
        events = ReviewEventService.get_user_events(
            user_id=user_id
        )
        return {
            "user_id": user_id,
            "events": events,
            "count": len(events),
        }

    except Exception:
        logger.exception("Review event retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Review event retrieval failed.",
        )


# --------------------------------------------------
# PERSONALIZED REVIEW SCHEDULING
# --------------------------------------------------

@app.post("/api/v1/retention/schedule")
def create_review_schedule(
    request: RetentionPredictionRequest,
):
    try:
        prediction = predict_retention(request)

        schedule = PersonalizedSchedulingService.build_review_schedule(
            predicted_retention_prob=prediction.predicted_retention_prob,
            user_id=request.user_id,
            topic_id=request.topic_id,
        )

        return ScheduleRepository.save_schedule(schedule)

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception:
        logger.exception("Review schedule creation failed")
        raise HTTPException(
            status_code=500,
            detail="Review schedule creation failed.",
        )



# --------------------------------------------------
# REVIEW SCHEDULE RETRIEVAL
# --------------------------------------------------

@app.get("/api/v1/retention/schedules/{user_id}")
def get_review_schedules(user_id: str):
    try:
        schedules = ScheduleRepository.get_user_schedules(user_id)

        return {
            "user_id": user_id,
            "schedules": schedules,
            "count": len(schedules),
        }

    except Exception:
        logger.exception("Schedule retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Schedule retrieval failed.",
        )


# --------------------------------------------------
# REVIEW SCHEDULE DUE STATUS REFRESH
# --------------------------------------------------

@app.post("/api/v1/retention/schedules/{user_id}/refresh-due")
def refresh_due_status(user_id: str):
    try:
        updated_count = ScheduleRepository.refresh_due_status(user_id)

        return {
            "user_id": user_id,
            "updated_count": updated_count,
            "schedules": ScheduleRepository.get_user_schedules(user_id),
        }

    except Exception:
        logger.exception("Schedule due-status refresh failed")
        raise HTTPException(
            status_code=500,
            detail="Schedule due-status refresh failed.",
        )



@app.get("/api/v1/retention/schedules/{user_id}/due")
def get_due_review_schedules(user_id: str):
    try:
        schedules = ScheduleRepository.get_due_schedules(user_id)

        return {
            "user_id": user_id,
            "due_schedules": schedules,
            "count": len(schedules),
        }

    except Exception:
        logger.exception("Due schedule retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Due schedule retrieval failed.",
        )


# --------------------------------------------------
# ROOT AND HEALTH
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "application": "NeuroLearn",
        "status": "running",
        "version": "0.3.0",
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        application="NeuroLearn API",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# --------------------------------------------------
# STUDY ANALYTICS API
# --------------------------------------------------


@app.get("/api/v1/study-plan/{user_id}/analytics")
def get_study_analytics(user_id: str):
    return StudyAnalyticsService.get_study_analytics(
        user_id
    )


@app.get("/api/v1/study-plan/{user_id}/topic-analytics")
def get_topic_analytics(user_id: str):
    return StudyAnalyticsService.get_topic_analytics(
        user_id
    )

@app.get("/api/v1/study-plan/{user_id}/weekly-analytics")
def get_weekly_analytics(user_id: str):
    return StudyAnalyticsService.get_weekly_analytics(
        user_id
    )

# --------------------------------------------------
# ADAPTIVE LEARNING INSIGHTS API
# --------------------------------------------------


@app.get("/api/v1/study-plan/{user_id}/performance-trend")
def get_performance_trend(user_id: str):
    return StudyInsightsService.get_performance_trend(
        user_id
    )

@app.get("/api/v1/study-plan/{user_id}/weekly-analytics")
def get_weekly_analytics(user_id: str):
    return StudyInsightsService.get_weekly_analytics(
        user_id
    )


@app.get("/api/v1/study-plan/{user_id}/consistency")
def get_study_consistency(user_id: str):
    return StudyInsightsService.get_study_consistency(
        user_id
    )


@app.get("/api/v1/study-plan/{user_id}/weak-topics")
def get_weak_topics(user_id: str):
    return StudyInsightsService.get_weak_topics(
        user_id
    )


@app.get("/api/v1/study-plan/{user_id}/insights")
def get_personalized_insights(user_id: str):
    return StudyInsightsService.get_personalized_insights(
        user_id
    )


# --------------------------------------------------
# LEARNING BEHAVIOR API
# --------------------------------------------------


@app.get("/api/v1/study-plan/{user_id}/activity-summary")
def get_activity_summary(user_id: str):
    return LearningBehaviorService.get_activity_summary(
        user_id
    )


@app.get("/api/v1/study-plan/{user_id}/study-timing")
def get_study_timing_patterns(user_id: str):
    return LearningBehaviorService.get_study_timing_patterns(
        user_id
    )


@app.get("/api/v1/study-plan/{user_id}/learning-behavior")
def get_learning_behavior(user_id: str):
    return LearningBehaviorService.get_learning_behavior(
        user_id
    )
