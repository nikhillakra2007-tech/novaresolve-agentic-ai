import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.models.order import Order
from backend.app.db.models.case import Case
from backend.app.db.models.customer import Customer
from backend.app.db.models.refund import Refund
from backend.app.schemas.resolution import RefundCreateRequest
from backend.app.services.customer_service import CustomerService
from backend.app.services.policy_service import PolicyService
from backend.app.core.exceptions import (
    ResourceNotFoundError,
    BusinessRuleViolationError,
)


class RefundService:
    @staticmethod
    def create_refund(
        db: Session,
        request: Optional[RefundCreateRequest] = None,
        case_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Refund:
        """Executes or stages a refund against an order and case with transactional safety and policy checks."""
        if request is not None:
            eff_order_id = request.order_id
            eff_amount = request.amount
            eff_reason = request.reason
            eff_case_id = request.case_id or case_id
        else:
            eff_order_id = order_id or kwargs.get("order_id")
            eff_amount = amount if amount is not None else kwargs.get("amount")
            eff_reason = reason or kwargs.get("reason")
            eff_case_id = case_id or kwargs.get("case_id")

        if not eff_order_id or eff_amount is None or not eff_reason:
            raise BusinessRuleViolationError("order_id, amount, and reason are required for refund creation.")

        if eff_amount <= Decimal("0.00"):
            raise BusinessRuleViolationError("Refund amount must be greater than zero.")

        order = db.query(Order).filter(Order.id == eff_order_id).first()
        if not order:
            raise ResourceNotFoundError(f"Order with ID '{eff_order_id}' was not found.")

        # Validate customer
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if customer:
            CustomerService.validate_active_requester(customer)

        # Resolve or link case
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
                    issue_type="refund",
                    customer_goal=f"Refund request for order {order.id}",
                    status="investigating",
                    risk_level="low",
                )
                db.add(case)
                db.flush()

        # Check total existing completed refunds for this order
        completed_refunds_sum = (
            db.query(func.coalesce(func.sum(Refund.amount), Decimal("0.00")))
            .filter(
                Refund.order_id == eff_order_id,
                Refund.status == "completed",
            )
            .scalar()
        )

        remaining_refundable = order.total_amount - completed_refunds_sum
        if eff_amount > remaining_refundable:
            raise BusinessRuleViolationError(
                f"Requested refund of ${eff_amount} exceeds remaining refundable order balance of ${remaining_refundable}.",
                details={
                    "order_total": str(order.total_amount),
                    "already_refunded": str(completed_refunds_sum),
                    "requested": str(eff_amount),
                },
            )

        # Check duplicate resolution in case
        existing_duplicate = (
            db.query(Refund)
            .filter(
                Refund.case_id == case.id,
                Refund.order_id == eff_order_id,
                Refund.amount == eff_amount,
                Refund.status.in_(["completed", "pending"]),
            )
            .first()
        )
        if existing_duplicate:
            raise BusinessRuleViolationError(
                f"A refund of ${eff_amount} is already {existing_duplicate.status} for case '{case.id}'.",
                details={"existing_refund_id": str(existing_duplicate.id)},
            )

        # Evaluate refund policy
        policy_decision = PolicyService.evaluate_policy(
            db=db,
            issue_type="refund",
            amount=eff_amount,
            order_status=order.status,
        )

        requires_approval = (
            policy_decision.requires_approval
            or eff_amount >= Decimal("100.00")
        )

        status_str = "pending" if requires_approval else "completed"
        approved_by = None if requires_approval else "agent_auto_policy"
        processed_at = None if requires_approval else datetime.now(timezone.utc)

        refund = Refund(
            case_id=case.id,
            order_id=order.id,
            amount=eff_amount,
            reason=eff_reason,
            status=status_str,
            requires_approval=requires_approval,
            approved_by=approved_by,
            processed_at=processed_at,
        )

        db.add(refund)

        # If fully refunded and auto-approved, update order status
        if status_str == "completed" and (completed_refunds_sum + eff_amount) >= order.total_amount:
            order.status = "refunded"

        # Update case resolution state
        case.resolution_type = "refund"
        case.resolution_status = "completed" if status_str == "completed" else "awaiting_approval"
        case.requires_approval = requires_approval

        db.commit()
        db.refresh(refund)
        return refund
