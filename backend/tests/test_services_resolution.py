import uuid
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.app.core.exceptions import (
    BusinessRuleViolationError,
    InsufficientInventoryError,
    OrderStateConflictError,
    CustomerBlockedError,
)
from backend.app.db.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    Warehouse,
    Inventory,
    Policy,
    Refund,
    Replacement,
    Cancellation,
)
from backend.app.schemas.policy import PolicyEvaluationRequest
from backend.app.schemas.resolution import (
    RefundCreateRequest,
    ReplacementCreateRequest,
    CancellationCreateRequest,
)
from backend.app.services.policy_service import PolicyService
from backend.app.services.refund_service import RefundService
from backend.app.services.replacement_service import ReplacementService
from backend.app.services.cancellation_service import CancellationService


def test_policy_service_evaluation(db_session: Session):
    # Test refund policy under 100
    req_small = PolicyEvaluationRequest(
        action_type="refund",
        amount=Decimal("45.00"),
        order_status="delivered",
    )
    res_small = PolicyService.evaluate_policy(db_session, request=req_small)
    assert res_small.allowed is True
    assert res_small.requires_approval is False

    # Test refund policy over 100
    req_large = PolicyEvaluationRequest(
        action_type="refund",
        amount=Decimal("150.00"),
        order_status="delivered",
    )
    res_large = PolicyService.evaluate_policy(db_session, request=req_large)
    assert res_large.allowed is True
    assert res_large.requires_approval is True

    # Test cancellation policy on shipped order
    req_cancel_shipped = PolicyEvaluationRequest(
        action_type="cancellation",
        order_status="shipped",
    )
    res_cancel_shipped = PolicyService.evaluate_policy(db_session, request=req_cancel_shipped)
    assert res_cancel_shipped.allowed is False


def test_refund_service_execution(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario3_charlie@example.com").first()
    # Create a fresh order for clean transaction testing
    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("120.00"),
        status="delivered",
        shipping_address="742 Evergreen Terrace, Springfield",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    # 1. Refund below threshold ($50)
    req = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("50.00"),
        reason="Defective component",
    )
    refund = RefundService.create_refund(db_session, req)
    assert refund.status == "completed"
    assert refund.requires_approval is False
    assert refund.amount == Decimal("50.00")

    # 2. Refund exceeding balance ($120 - $50 = $70 remaining, asking for $80)
    req_excess = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("80.00"),
        reason="Second claim",
    )
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        RefundService.create_refund(db_session, req_excess)
    assert "exceeds" in str(exc_info.value).lower()


def test_refund_service_blocked_customer(db_session: Session):
    blocked_customer = Customer(
        name="Blocked Test User",
        email=f"blocked_{uuid.uuid4().hex[:6]}@example.com",
        status="blocked",
    )
    db_session.add(blocked_customer)
    db_session.commit()
    db_session.refresh(blocked_customer)

    order = Order(
        customer_id=blocked_customer.id,
        total_amount=Decimal("50.00"),
        status="delivered",
        shipping_address="Blocked Customer Address",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    req = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("20.00"),
        reason="Refund request",
    )
    with pytest.raises(CustomerBlockedError):
        RefundService.create_refund(db_session, req)


def test_replacement_service_insufficient_stock_fails(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario2_bob@example.com").first()
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("399.99"),
        status="delivered",
        shipping_address="Dallas Bob Address",
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("399.99"),
    )
    db_session.add(item)
    db_session.commit()

    # Dallas has 0 available stock -> must raise InsufficientInventoryError
    req = ReplacementCreateRequest(
        order_id=order.id,
        product_id=product.id,
        warehouse_id=dallas.id,
        quantity=1,
        reason="Screen flickering",
    )
    with pytest.raises(InsufficientInventoryError) as exc_info:
        ReplacementService.create_replacement(db_session, req)
    assert "insufficient" in str(exc_info.value).lower()


def test_replacement_service_success_with_reservation(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario2_bob@example.com").first()
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()
    reno = db_session.query(Warehouse).filter(Warehouse.name == "Reno West Warehouse").first()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("399.99"),
        status="delivered",
        shipping_address="Reno Replacement Address",
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price=Decimal("399.99"),
    )
    db_session.add(item)
    db_session.commit()

    # Reno has stock
    inv_before = db_session.query(Inventory).filter(
        Inventory.warehouse_id == reno.id,
        Inventory.product_id == product.id,
    ).first()
    reserved_before = inv_before.reserved_quantity

    req = ReplacementCreateRequest(
        order_id=order.id,
        product_id=product.id,
        warehouse_id=reno.id,
        quantity=1,
        reason="Reno fulfillment test",
    )
    replacement = ReplacementService.create_replacement(db_session, req)
    assert replacement.status == "processing"
    assert replacement.quantity == 1

    # Check reserved_quantity incremented
    db_session.refresh(inv_before)
    assert inv_before.reserved_quantity == reserved_before + 1


def test_cancellation_service_lifecycle(db_session: Session):
    customer = Customer(
        name="Cancellation Test User",
        email=f"cancel_test_{uuid.uuid4().hex[:6]}@example.com",
        status="active",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    # 1. Order placed -> Can be cancelled
    order_cancelable = Order(
        customer_id=customer.id,
        total_amount=Decimal("49.99"),
        status="placed",
        shipping_address="Cancelable Order Address",
    )
    db_session.add(order_cancelable)
    db_session.commit()
    db_session.refresh(order_cancelable)

    req = CancellationCreateRequest(
        order_id=order_cancelable.id,
        reason="Ordered by mistake",
    )
    cancellation = CancellationService.cancel_order(db_session, req)
    assert cancellation.status == "approved"
    db_session.refresh(order_cancelable)
    assert order_cancelable.status == "cancelled"

    # 2. Cancelling already cancelled order raises conflict
    with pytest.raises(OrderStateConflictError):
        CancellationService.cancel_order(db_session, req)

    # 3. Cancelling shipped order (Scenario 8) raises conflict
    scenario8_order = db_session.query(Order).join(Customer).filter(
        Customer.email == "scenario8_hannah@example.com"
    ).first()
    req_shipped = CancellationCreateRequest(
        order_id=scenario8_order.id,
        reason="Too late cancellation attempt",
    )
    with pytest.raises(OrderStateConflictError) as exc_info:
        CancellationService.cancel_order(db_session, req_shipped)
    assert "shipped" in str(exc_info.value).lower()
