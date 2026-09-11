import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.db.models.order import Order
from backend.app.db.models.shipment import Shipment
from backend.app.core.exceptions import ResourceNotFoundError


class ShipmentService:
    @staticmethod
    def get_shipment_by_order_id(db: Session, order_id: uuid.UUID) -> Shipment:
        """Retrieves shipment facts for an order or raises ResourceNotFoundError."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ResourceNotFoundError(f"Order with ID '{order_id}' was not found.")

        shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if not shipment:
            raise ResourceNotFoundError(f"No shipment found for order ID '{order_id}'.")

        return shipment

    @staticmethod
    def get_shipment_by_id(db: Session, shipment_id: uuid.UUID) -> Shipment:
        """Retrieves a shipment directly by its ID."""
        shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if not shipment:
            raise ResourceNotFoundError(f"Shipment with ID '{shipment_id}' was not found.")
        return shipment
