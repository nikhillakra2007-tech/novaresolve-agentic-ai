from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.resolution import (
    RefundCreateRequest,
    RefundResponse,
    ReplacementCreateRequest,
    ReplacementResponse,
    CancellationCreateRequest,
    CancellationResponse,
)
from backend.app.services.refund_service import RefundService
from backend.app.services.replacement_service import ReplacementService
from backend.app.services.cancellation_service import CancellationService

router = APIRouter(tags=["Resolutions"])


@router.post(
    "/refunds",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and Process Refund",
    description=(
        "Executes a state-changing refund transaction. Enforces customer status checks, "
        "order existence, cumulative refund caps, and approval requirement thresholds."
    ),
)
def create_refund(
    request: RefundCreateRequest,
    db: Session = Depends(get_db),
):
    refund = RefundService.create_refund(db, request=request)
    return refund


@router.post(
    "/replacements",
    response_model=ReplacementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Replacement Order",
    description=(
        "Executes a state-changing replacement order. Enforces warehouse stock reservation "
        "with row-level pessimistic locking. Raises 409 if requested warehouse is out of stock."
    ),
)
def create_replacement(
    request: ReplacementCreateRequest,
    db: Session = Depends(get_db),
):
    replacement = ReplacementService.create_replacement(db, request=request)
    return replacement


@router.post(
    "/cancellations",
    response_model=CancellationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Unfulfilled Order",
    description=(
        "Executes an order cancellation. Disallows cancellation if order has already shipped or "
        "is in-transit (raises 409 conflict)."
    ),
)
def cancel_order(
    request: CancellationCreateRequest,
    db: Session = Depends(get_db),
):
    cancellation = CancellationService.cancel_order(db, request=request)
    return cancellation
