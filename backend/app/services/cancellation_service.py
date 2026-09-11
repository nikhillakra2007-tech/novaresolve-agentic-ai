import uuid
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.db.models.order import Order
from backend.app.db.models.case import Case
from backend.app.db.models.customer import Customer
from backend.app.db.models.shipment import Shipment
from backend.app.db.models.cancellation import Cancellation
from backend.app.schemas.resolution import CancellationCreateRequest
from backend.app.services.customer_service import CustomerService
from backend.app.core.exceptions import (
    ResourceNotFoundError,
    BusinessRuleViolationError,
    OrderStateConflictError,
)


class CancellationService:
    @staticmethod
    def cancel_order(
        db: Session,
        request: Optional[CancellationCreateRequest] = None,
        case_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Cancellation:
        """Cancels an order if permitted by its current fulfillment and shipment state."""
        if request is not None:
            eff_order_id = request.order_id
            eff_reason = request.reason
            eff_case_id = request.case_id or case_id
        else:
            eff_order_id = order_id or kwargs.get("order_id")
            eff_reason = reason or kwargs.get("reason")
            eff_case_id = case_id or kwargs.get("case_id")

        if not eff_order_id or not eff_reason:
            raise BusinessRuleViolationError("order_id and reason are required for cancellation.")

        order = db.query(Order).filter(Order.id == eff_order_id).first()
        if not order:
            raise ResourceNotFoundError(f"Order with ID '{eff_order_id}' was not found.")

        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if customer:
            CustomerService.validate_active_requester(customer)

        if eff_case_id:
            case = db.query(Case).filter(Case.id == eff_case_id).first()
            if not case:
                raise ResourceNotFoundError(f"Case with ID '{eff_case_id}' was not found.")
            if case.order_id and case.order_id != eff_order_id:
                raise BusinessRuleViolationError(
                    f"Case '{eff_case_id}' is associated with order '{case.order_id}', not '{eff_order_id}'."
                )
        else:
            case = db.query(Case).filter(Case.order_id == eff_order_id).first()
            if not case:
                case = Case(
                    customer_id=order.customer_id,
                    order_id=order.id,
                    issue_type="cancellation",
                    customer_goal=f"Cancellation request for order {order.id}",
                    status="investigating",
                    risk_level="low",
                )
                db.add(case)
                db.flush()

        # Invariant 1: Cannot cancel already cancelled orders
        if order.status == "cancelled":
            raise OrderStateConflictError(
                f"Order '{eff_order_id}' is already cancelled.",
                details={"order_id": str(eff_order_id), "order_status": order.status},
            )

        # Invariant 2: Cannot cancel delivered or refunded orders
        if order.status in ["delivered", "refunded"]:
            raise OrderStateConflictError(
                f"Order '{eff_order_id}' is in status '{order.status}' and cannot be cancelled directly.",
                details={"order_id": str(eff_order_id), "order_status": order.status},
            )

        # Invariant 3: Cannot cancel orders that have shipped / are in transit
        shipments = db.query(Shipment).filter(Shipment.order_id == eff_order_id).all()
        for sh in shipments:
            if sh.status in ["in_transit", "out_for_delivery", "delivered", "delayed"]:
                raise OrderStateConflictError(
                    f"Order '{eff_order_id}' has already shipped (tracking: {sh.tracking_number}, carrier: {sh.carrier}) and cannot be cancelled.",
                    details={
                        "order_id": str(eff_order_id),
                        "shipment_id": str(sh.id),
                        "tracking_number": sh.tracking_number,
                        "carrier": sh.carrier,
                        "shipment_status": sh.status,
                    },
                )

        if order.status == "shipped":
            raise OrderStateConflictError(
                f"Order '{eff_order_id}' is already shipped and cannot be cancelled.",
                details={"order_id": str(eff_order_id), "order_status": order.status},
            )

        # If cancellable:
        cancellation = Cancellation(
            case_id=case.id,
            order_id=order.id,
            reason=eff_reason,
            status="approved",
            requires_approval=False,
        )
        db.add(cancellation)

        order.status = "cancelled"
        case.resolution_type = "cancellation"
        case.resolution_status = "completed"

        db.commit()
        db.refresh(cancellation)
        return cancellation
