import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import (
    BusinessRuleViolationError,
    InsufficientInventoryError,
    OrderStateConflictError,
    CustomerBlockedError,
    PolicyDenialError,
)
from backend.app.db.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    Warehouse,
    Inventory,
    Policy,
    Case,
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
    # Test refund policy under 100 with eligible reason
    req_small = PolicyEvaluationRequest(
        action_type="refund",
        amount=Decimal("45.00"),
        order_status="delivered",
        reason="defective item",
    )
    res_small = PolicyService.evaluate_policy(db_session, request=req_small)
    assert res_small.allowed is True
    assert res_small.requires_approval is False

    # Test refund policy over 100
    req_large = PolicyEvaluationRequest(
        action_type="refund",
        amount=Decimal("150.00"),
        order_status="delivered",
        reason="damaged in transit",
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


def test_policy_allowed_reasons_condition(db_session: Session):
    """Task 4: Tests allowed_reasons policy condition matching and denial."""
    # Eligible reasons from seeded policy: damaged, wrong_item, defective, not_as_described
    for allowed_reason in ["damaged", "wrong_item", "defective component", "item not_as_described"]:
        req = PolicyEvaluationRequest(
            action_type="refund",
            amount=Decimal("50.00"),
            order_status="delivered",
            reason=allowed_reason,
        )
        res = PolicyService.evaluate_policy(db_session, request=req)
        assert res.allowed is True, f"Expected {allowed_reason} to be allowed"

    # Disallowed reasons: buyer remorse, changed mind, unwanted
    for disallowed_reason in ["changed mind", "unwanted gift", "found cheaper elsewhere"]:
        req = PolicyEvaluationRequest(
            action_type="refund",
            amount=Decimal("50.00"),
            order_status="delivered",
            reason=disallowed_reason,
        )
        res = PolicyService.evaluate_policy(db_session, request=req)
        assert res.allowed is False, f"Expected {disallowed_reason} to be denied"


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

    # 1. Refund below threshold ($50) with allowed reason
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
        reason="Second claim - defective",
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
        reason="Defective part",
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


def test_replacement_quantity_persistence_and_reservation(db_session: Session):
    """Task 1: Tests quantity persistence and reservation synchronization for quantity=1 and quantity=3."""
    customer = Customer(
        name="Quantity Test User",
        email=f"qty_test_{uuid.uuid4().hex[:6]}@example.com",
        status="active",
    )
    db_session.add(customer)
    db_session.flush()

    product = db_session.query(Product).filter(Product.sku == "AUD-NC-HEADPHONES-01").first()
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("599.97"),
        status="delivered",
        shipping_address="Multi Quantity Address",
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=5,
        unit_price=Decimal("199.99"),
    )
    db_session.add(item)
    db_session.commit()

    inv = db_session.query(Inventory).filter(
        Inventory.warehouse_id == dallas.id,
        Inventory.product_id == product.id,
    ).first()
    inv_reserved_before = inv.reserved_quantity

    # 1. Test quantity=3
    req_qty3 = ReplacementCreateRequest(
        order_id=order.id,
        product_id=product.id,
        warehouse_id=dallas.id,
        quantity=3,
        reason="Bulk defective batch",
    )
    replacement3 = ReplacementService.create_replacement(db_session, req_qty3)

    # Verify persisted quantity in model and returned object
    assert replacement3.quantity == 3
    db_session.refresh(replacement3)
    assert replacement3.quantity == 3

    # Verify inventory reserved_quantity increases by exactly 3
    db_session.refresh(inv)
    assert inv.reserved_quantity == inv_reserved_before + 3

    # 2. Test invalid quantities rejected by schema validation
    with pytest.raises(ValidationError):
        ReplacementCreateRequest(
            order_id=order.id,
            product_id=product.id,
            warehouse_id=dallas.id,
            quantity=0,
            reason="Zero quantity",
        )

    with pytest.raises(ValidationError):
        ReplacementCreateRequest(
            order_id=order.id,
            product_id=product.id,
            warehouse_id=dallas.id,
            quantity=-1,
            reason="Negative quantity",
        )


def test_policy_enforcement_and_denial_blocks_mutation(db_session: Session):
    """Task 2: Verifies that policy denial raises PolicyDenialError and prevents DB record creation."""
    customer = Customer(
        name="Policy Denial Test User",
        email=f"policy_denial_{uuid.uuid4().hex[:6]}@example.com",
        status="active",
    )
    db_session.add(customer)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("80.00"),
        status="delivered",
        shipping_address="Denial Address",
    )
    db_session.add(order)
    db_session.commit()

    refund_count_before = db_session.query(Refund).count()

    # Disallowed reason for refund
    req_denied_refund = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("40.00"),
        reason="Found it cheaper at competitor",
    )
    with pytest.raises(PolicyDenialError) as exc_info:
        RefundService.create_refund(db_session, req_denied_refund)
    assert "policy" in str(exc_info.value).lower()

    # Verify no refund was committed to the DB
    assert db_session.query(Refund).count() == refund_count_before

    # High-risk allowed refund ($150 on $200 order) enters approval pending state
    order_high = Order(
        customer_id=customer.id,
        total_amount=Decimal("200.00"),
        status="delivered",
        shipping_address="High Risk Address",
    )
    db_session.add(order_high)
    db_session.commit()

    req_high_risk = RefundCreateRequest(
        order_id=order_high.id,
        amount=Decimal("150.00"),
        reason="Damaged item during delivery",
    )
    refund_high = RefundService.create_refund(db_session, req_high_risk)
    assert refund_high.status == "pending"
    assert refund_high.requires_approval is True


def test_prevent_partial_case_creation_on_failed_operations(db_session: Session):
    """Task 3: Ensures that failing operations do not leave orphaned/partially created Cases in the DB."""
    customer = Customer(
        name="Orphan Test User",
        email=f"orphan_test_{uuid.uuid4().hex[:6]}@example.com",
        status="active",
    )
    db_session.add(customer)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("100.00"),
        status="delivered",
        shipping_address="Orphan Test Address",
    )
    db_session.add(order)
    db_session.commit()

    initial_case_count = db_session.query(Case).count()

    # 1. Failed refund due to policy denial -> No new case
    req_bad_refund = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("30.00"),
        reason="Changed my mind completely",
    )
    with pytest.raises(PolicyDenialError):
        RefundService.create_refund(db_session, req_bad_refund)
    assert db_session.query(Case).count() == initial_case_count

    # 2. Failed refund due to excess balance -> No new case
    req_excess_refund = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("250.00"),
        reason="Defective item",
    )
    with pytest.raises(BusinessRuleViolationError):
        RefundService.create_refund(db_session, req_excess_refund)
    assert db_session.query(Case).count() == initial_case_count

    # 3. Failed replacement due to insufficient inventory -> No new case
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()
    monitor = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()
    order_item = OrderItem(
        order_id=order.id,
        product_id=monitor.id,
        quantity=1,
        unit_price=Decimal("100.00"),
    )
    db_session.add(order_item)
    db_session.commit()

    req_bad_rep = ReplacementCreateRequest(
        order_id=order.id,
        product_id=monitor.id,
        warehouse_id=dallas.id,  # 0 stock
        quantity=1,
        reason="Defective screen",
    )
    with pytest.raises(InsufficientInventoryError):
        ReplacementService.create_replacement(db_session, req_bad_rep)
    assert db_session.query(Case).count() == initial_case_count


def test_concurrent_refunds_balance_protection(db_session: Session):
    """Task 5: Pessimistic locking protects order balance so two refunds cannot exceed total_amount."""
    customer = Customer(
        name="Concurrent Test User",
        email=f"concur_test_{uuid.uuid4().hex[:6]}@example.com",
        status="active",
    )
    db_session.add(customer)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("100.00"),
        status="delivered",
        shipping_address="Lock Test Address",
    )
    db_session.add(order)
    db_session.commit()

    # Refund 1 requests $70 of $100 -> succeeds
    req1 = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("70.00"),
        reason="Damaged item",
    )
    ref1 = RefundService.create_refund(db_session, req1)
    assert ref1.amount == Decimal("70.00")

    # Refund 2 requests $50 of remaining $30 -> rejected by balance check
    req2 = RefundCreateRequest(
        order_id=order.id,
        amount=Decimal("50.00"),
        reason="Defective accessories",
    )
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        RefundService.create_refund(db_session, req2)
    assert "exceeds" in str(exc_info.value).lower()


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
