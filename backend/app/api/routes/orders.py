from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.order import OrderResponse
from backend.app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get Order Details",
    description="Fetches an order with its constituent order items. Optionally verifies customer ownership.",
)
def get_order(
    order_id: UUID = Path(..., description="Unique order UUID"),
    customer_id: Optional[UUID] = Query(None, description="Optional customer UUID to verify ownership"),
    db: Session = Depends(get_db),
):
    order = OrderService.get_order(db, order_id=order_id, customer_id=customer_id)
    return order
