from uuid import UUID
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.shipment import ShipmentResponse
from backend.app.services.shipment_service import ShipmentService

router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.get(
    "/{order_id}",
    response_model=ShipmentResponse,
    summary="Get Shipment by Order ID",
    description="Fetches shipment details, tracking events, and computes dynamic delivery delay flags for an order.",
)
def get_shipment_by_order_id(
    order_id: UUID = Path(..., description="Order UUID associated with the shipment"),
    db: Session = Depends(get_db),
):
    shipment = ShipmentService.get_shipment_by_order_id(db, order_id=order_id)
    return shipment
