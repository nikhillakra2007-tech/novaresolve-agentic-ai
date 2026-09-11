import uuid
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from backend.app.db.models.order import Order, OrderItem
from backend.app.db.models.product import Product
from backend.app.core.exceptions import ResourceNotFoundError


class OrderService:
    @staticmethod
    def get_order_by_id(
        db: Session,
        order_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
    ) -> Order:
        """Retrieves an order by ID with items and optionally validates customer ownership."""
        query = (
            db.query(Order)
            .options(joinedload(Order.items).joinedload(OrderItem.product))
            .filter(Order.id == order_id)
        )
        order = query.first()
        if not order:
            raise ResourceNotFoundError(f"Order with ID '{order_id}' was not found.")

        if customer_id and order.customer_id != customer_id:
            raise ResourceNotFoundError(
                f"Order '{order_id}' was not found for customer '{customer_id}'."
            )

        return order

    # Convenience alias for uniform service interface
    get_order = get_order_by_id
