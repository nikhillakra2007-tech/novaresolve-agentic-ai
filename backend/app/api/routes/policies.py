from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.policy import (
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
)
from backend.app.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.post(
    "/evaluate",
    response_model=PolicyEvaluationResponse,
    summary="Evaluate Business Policy Constraints",
    description=(
        "Evaluates whether a proposed resolution action is permitted against database-configured policies. "
        "Pure decision service: returns structured authorization facts without mutating state."
    ),
)
def evaluate_policy(
    request: PolicyEvaluationRequest,
    db: Session = Depends(get_db),
):
    result = PolicyService.evaluate_policy(db, request=request)
    return result
