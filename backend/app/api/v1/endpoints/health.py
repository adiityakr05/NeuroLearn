import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter()
logger = logging.getLogger("neurolearn.health")


@router.get("/health", response_model=HealthResponse, summary="System Health Check")
def health_check(db: Session = Depends(get_db)):
    """
    Performs a live connectivity check against the configured database
    and returns overall platform health status without leaking internal details.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        # Log technical error internally without leaking credentials/details to callers
        logger.error("Health check database probe failed: %s", exc.__class__.__name__, exc_info=True)
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        project=settings.PROJECT_NAME,
        database=db_status,
    )
