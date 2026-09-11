import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.db.models.order import Order, OrderItem
from backend.app.db.models.case import Case
from backend.app.db.models.customer import Customer
from backend.app.db.models.product import Product
from backend.app.db.models.warehouse import Warehouse
from backend.app.db.models.inventory import Inventory
from backend.app.db.models.replacement import Replacement
from backend.app.schemas.resolution import ReplacementCreateRequest
from backend.app.services.customer_service import CustomerService
from backend.app.services.policy_service import PolicyService
from backend.app.core.exceptions import (
    ResourceNotFoundError,
    BusinessRuleViolationError,
    InsufficientInventoryError,
    PolicyDenialError,
)


class ReplacementService:
    @staticmethod
    def create_replacement(
        db: Session,
        request: Optional[ReplacementCreateRequest] = None,
        case_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        quantity: Optional[int] = None,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Replacement:
        """Executes a replacement transaction with policy enforcement, atomic inventory reservation, and quantity persistence."""
        if request is not None:
            eff_order_id = request.order_id
            eff_product_id = request.product_id
            eff_warehouse_id = request.warehouse_id
            eff_quantity = request.quantity
            eff_reason = request.reason
            eff_case_id = request.case_id or case_id
        else:
            eff_order_id = order_id or kwargs.get("order_id")
            eff_product_id = product_id or kwargs.get("product_id")
            eff_warehouse_id = warehouse_id or kwargs.get("warehouse_id")
            eff_quantity = quantity if quantity is not None else kwargs.get("quantity", 1)
            eff_reason = reason or kwargs.get("reason")
            eff_case_id = case_id or kwargs.get("case_id")

        if not eff_order_id or not eff_product_id or not eff_warehouse_id or not eff_reason:
            raise BusinessRuleViolationError("order_id, product_id, warehouse_id, and reason are required.")

        if eff_quantity <= 0:
            raise BusinessRuleViolationError("Replacement quantity must be greater than zero.")

        # 1. Validate order existence
        order = db.query(Order).filter(Order.id == eff_order_id).first()
        if not order:
            raise ResourceNotFoundError(f"Order with ID '{eff_order_id}' was not found.")

        # 2. Validate customer active status
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if customer:
            CustomerService.validate_active_requester(customer)

        # 3. Validate explicit case_id if provided
        if eff_case_id:
            existing_case = db.query(Case).filter(Case.id == eff_case_id).first()
            if not existing_case:
                raise ResourceNotFoundError(f"Case with ID '{eff_case_id}' was not found.")
            if existing_case.order_id and existing_case.order_id != eff_order_id:
                raise BusinessRuleViolationError(
                    f"Case '{eff_case_id}' is associated with order '{existing_case.order_id}', not '{eff_order_id}'."
                )

        # 4. Product must belong to original order items
        product = db.query(Product).filter(Product.id == eff_product_id).first()
        if not product:
            raise ResourceNotFoundError(f"Product with ID '{eff_product_id}' was not found.")

        order_item = (
            db.query(OrderItem)
            .filter(
                OrderItem.order_id == eff_order_id,
                OrderItem.product_id == eff_product_id,
            )
            .first()
        )
        if not order_item:
            raise BusinessRuleViolationError(
                f"Product '{product.sku}' does not belong to order '{eff_order_id}'.",
                details={"order_id": str(eff_order_id), "product_id": str(eff_product_id)},
            )

        # 5. Warehouse must exist and be active
        warehouse = db.query(Warehouse).filter(Warehouse.id == eff_warehouse_id).first()
        if not warehouse:
            raise ResourceNotFoundError(f"Warehouse with ID '{eff_warehouse_id}' was not found.")

        if warehouse.status != "active":
            raise BusinessRuleViolationError(
                f"Warehouse '{warehouse.name}' is {warehouse.status} and cannot fulfill replacements.",
                details={"warehouse_id": str(eff_warehouse_id), "status": warehouse.status},
            )

        # 6. ENFORCE POLICY: evaluate replacement policy before mutating inventory
        days_since_order = None
        if order.order_date:
            days_since_order = (datetime.now(timezone.utc) - order.order_date).days

        policy_decision = PolicyService.evaluate_policy(
            db=db,
            issue_type="replacement",
            action="create_replacement_order",
            order_status=order.status,
            days_since_order=days_since_order,
            reason=eff_reason,
        )
        if not policy_decision.allowed:
            raise PolicyDenialError(
                f"Replacement disallowed by policy: {policy_decision.reason}",
                details={
                    "action": policy_decision.action,
                    "reason": policy_decision.reason,
                    "applicable_conditions": policy_decision.applicable_conditions,
                },
            )

        # 7. Inventory check with FOR UPDATE lock for concurrency safety
        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == eff_product_id,
                Inventory.warehouse_id == eff_warehouse_id,
            )
            .with_for_update()
            .first()
        )

        available_qty = (inventory.quantity - inventory.reserved_quantity) if inventory else 0

        # CRITICAL: If 0 or insufficient stock, return observable constraint. DO NOT auto-reroute!
        if available_qty < eff_quantity:
            raise InsufficientInventoryError(
                f"Insufficient inventory at {warehouse.name} for SKU {product.sku}. Available: {available_qty}, Requested: {eff_quantity}.",
                details={
                    "warehouse_id": str(warehouse.id),
                    "warehouse_name": warehouse.name,
                    "product_id": str(product.id),
                    "product_sku": product.sku,
                    "available_quantity": available_qty,
                    "requested_quantity": eff_quantity,
                },
            )

        # 8. All validations, policy checks, and inventory checks passed.
        # Execute state-changing transaction (Case creation deferred to here).
        try:
            if eff_case_id:
                case = db.query(Case).filter(Case.id == eff_case_id).first()
            else:
                case = db.query(Case).filter(Case.order_id == eff_order_id).first()
                if not case:
                    case = Case(
                        customer_id=order.customer_id,
                        order_id=order.id,
                        issue_type="replacement",
                        customer_goal=f"Replacement request for order {order.id}",
                        status="investigating",
                        risk_level="low",
                    )
                    db.add(case)
                    db.flush()

            # Reserve inventory atomically
            inventory.reserved_quantity += eff_quantity

            replacement = Replacement(
                case_id=case.id,
                order_id=order.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=eff_quantity,
                reason=eff_reason,
                status="processing",
                requires_approval=False,
            )
            db.add(replacement)

            order.status = "replacement_pending"
            case.resolution_type = "replacement"
            case.resolution_status = "processing"

            db.commit()
            db.refresh(replacement)
            return replacement

        except Exception:
            db.rollback()
            raise
