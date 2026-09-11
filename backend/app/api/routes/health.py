from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.db.session import check_db_connection
from backend.app.schemas.health import HealthResponse, DatabaseHealth

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System and Database Health Check",
    description="Checks the health of NovaCart API and verifies live PostgreSQL connectivity with latency and pool statistics.",
)
def get_health():
    db_check = check_db_connection()
    is_connected = db_check.get("status") == "connected"

    overall_status = "healthy" if is_connected else "unhealthy"
    status_code = status.HTTP_200_OK if is_connected else status.HTTP_503_SERVICE_UNAVAILABLE

    response_payload = {
        "service": settings.PROJECT_NAME + " API",
        "status": overall_status,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "database": db_check,
    }

    return JSONResponse(status_code=status_code, content=response_payload)
