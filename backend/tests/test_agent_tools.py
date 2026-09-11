import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.db.models.customer import Customer
from backend.app.db.models.order import Order, OrderItem
from backend.app.db.models.product import Product
from backend.app.db.models.warehouse import Warehouse
from backend.app.db.models.inventory import Inventory
from backend.app.db.models.shipment import Shipment
from backend.app.db.models.case import Case
from backend.app.db.models.agent_event import AgentEvent
from backend.app.db.models.refund import Refund
from backend.app.db.models.replacement import Replacement
from backend.app.db.models.cancellation import Cancellation

from agents.tools import (
    TOOL_REGISTRY,
    ToolContext,
    ToolResultStatus,
    get_tool,
    list_tools,
    execute_tool,
    get_customer,
    get_order,
    get_shipment,
    check_inventory,
    search_alternative_inventory,
    get_case_state,
    evaluate_policy,
    create_refund,
    create_replacement,
    cancel_order,
    persist_case_state,
    log_agent_event,
    verify_resolution,
)


def make_test_customer(db: Session, status: str = "active") -> Customer:
    """Creates an isolated test customer that does not collide with seeded scenario customers."""
    cust = Customer(
        name=f"Tool Test Customer {uuid.uuid4().hex[:6]}",
        email=f"tool_{uuid.uuid4().hex[:8]}@example.com",
        status=status,
    )
    db.add(cust)
    db.flush()
    return cust


# ============================================================
# 1. TOOL DISCOVERY & REGISTRY TESTS
# ============================================================

def test_tool_discovery_all_exist():
    expected_tools = {
        "get_customer",
        "get_order",
        "get_shipment",
        "check_inventory",
        "search_alternative_inventory",
        "get_case_state",
        "evaluate_policy",
        "create_refund",
        "create_replacement",
        "cancel_order",
        "persist_case_state",
        "log_agent_event",
        "verify_resolution",
    }
    registered_names = set(TOOL_REGISTRY.list_tool_names())
    assert expected_tools.issubset(registered_names)
    assert len(registered_names) == 13


def test_tool_names_unique():
    tools = list_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names)), "Tool names in registry must be unique"


def test_tool_descriptions_present():
    for tool in list_tools():
        assert tool.description is not None
        assert len(tool.description.strip()) > 20, f"Description for {tool.name} is too short"


def test_tool_input_contracts_typed():
    for tool in list_tools():
        assert hasattr(tool, "input_schema")
        assert issubclass(tool.input_schema, BaseModel)


def test_registry_disallows_arbitrary_functions(db_session: Session):
    ctx = ToolContext(db=db_session)
    res1 = execute_tool("execute_sql", ctx, query="SELECT * FROM users")
    assert res1.success is False
    assert res1.status == ToolResultStatus.INVALID

    res2 = execute_tool("raw_sql", ctx)
    assert res2.success is False
    assert res2.status == ToolResultStatus.INVALID

    res3 = execute_tool("eval", ctx)
    assert res3.success is False

    res4 = execute_tool("unknown_tool_xyz", ctx)
    assert res4.success is False
    assert res4.status == ToolResultStatus.NOT_FOUND


# ============================================================
# 2. CUSTOMER TOOLS
# ============================================================

def test_get_customer_success(db_session: Session):
    customer = make_test_customer(db_session, status="active")
    db_session.commit()
    ctx = ToolContext(db=db_session)

    res = get_customer.execute(ctx, customer_id=customer.id)
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["customer_id"] == str(customer.id)
    assert res.data["name"] == customer.name
    assert res.data["is_active"] is True
    assert res.data["is_blocked"] is False


def test_get_customer_missing(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = get_customer.execute(ctx, customer_id=uuid.uuid4())
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND
    assert "not found" in res.message.lower()


def test_get_customer_blocked(db_session: Session):
    blocked_cust = make_test_customer(db_session, status="blocked")
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = get_customer.execute(ctx, customer_id=blocked_cust.id)
    assert res.success is True
    assert res.data["status"] == "blocked"
    assert res.data["is_blocked"] is True
    assert res.data["is_active"] is False


# ============================================================
# 3. ORDER TOOLS
# ============================================================

def test_get_order_success(db_session: Session):
    order = db_session.query(Order).first()
    assert order is not None
    ctx = ToolContext(db=db_session)

    res = get_order.execute(ctx, order_id=order.id)
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["order_id"] == str(order.id)
    assert res.data["total_amount"] == str(order.total_amount)
    assert "items" in res.data
    assert len(res.data["items"]) == len(order.items)


def test_get_order_missing(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = get_order.execute(ctx, order_id=uuid.uuid4())
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND


def test_get_order_ownership_mismatch(db_session: Session):
    order = db_session.query(Order).first()
    assert order is not None
    wrong_customer_id = uuid.uuid4()
    ctx = ToolContext(db=db_session)

    res = get_order.execute(ctx, order_id=order.id, customer_id=wrong_customer_id)
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND


# ============================================================
# 4. SHIPMENT TOOLS
# ============================================================

def test_get_shipment_success(db_session: Session):
    shipment = db_session.query(Shipment).first()
    assert shipment is not None
    ctx = ToolContext(db=db_session)

    res = get_shipment.execute(ctx, order_id=shipment.order_id)
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["tracking_number"] == shipment.tracking_number
    assert res.data["carrier"] == shipment.carrier


def test_get_shipment_missing_order(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = get_shipment.execute(ctx, order_id=uuid.uuid4())
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND


def test_get_shipment_missing_shipment(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="processing",
        total_amount=Decimal("45.00"),
        shipping_address="No Shipment St",
    )
    db_session.add(order)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = get_shipment.execute(ctx, order_id=order.id)
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND


# ============================================================
# 5. INVENTORY TOOLS
# ============================================================

def test_check_inventory_success(db_session: Session):
    inv = db_session.query(Inventory).filter(Inventory.quantity > 5).first()
    assert inv is not None
    ctx = ToolContext(db=db_session)

    res = check_inventory.execute(ctx, product_id=inv.product_id, warehouse_id=inv.warehouse_id)
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["quantity"] == inv.quantity
    assert res.data["available_quantity"] == max(0, inv.quantity - inv.reserved_quantity)


def test_check_inventory_zero_stock_fact(db_session: Session):
    test_prod = Product(
        name="Zero Stock Tool Test Item",
        sku=f"ZERO-TOOL-{uuid.uuid4().hex[:6]}",
        price=Decimal("15.00"),
        category="Testing",
    )
    test_wh = Warehouse(
        name=f"Zero Tool WH {uuid.uuid4().hex[:4]}",
        location="Zone Zero",
        status="active",
    )
    db_session.add_all([test_prod, test_wh])
    db_session.flush()

    inv = Inventory(
        product_id=test_prod.id,
        warehouse_id=test_wh.id,
        quantity=5,
        reserved_quantity=5,
    )
    db_session.add(inv)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = check_inventory.execute(ctx, product_id=test_prod.id, warehouse_id=test_wh.id)
    assert res.success is True
    assert res.data["available_quantity"] == 0
    assert res.data["warehouse_id"] == str(test_wh.id)


def test_search_alternative_inventory_success(db_session: Session):
    inv = (
        db_session.query(Inventory)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .filter(Warehouse.status == "active", (Inventory.quantity - Inventory.reserved_quantity) >= 1)
        .first()
    )
    assert inv is not None
    ctx = ToolContext(db=db_session)
    res = search_alternative_inventory.execute(ctx, product_id=inv.product_id, required_quantity=1)
    assert res.success is True
    assert len(res.data["alternatives"]) >= 1


def test_search_alternative_inventory_exclude_warehouse(db_session: Session):
    inv = (
        db_session.query(Inventory)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .filter(Warehouse.status == "active", (Inventory.quantity - Inventory.reserved_quantity) >= 1)
        .first()
    )
    assert inv is not None
    wh = db_session.query(Warehouse).filter(Warehouse.id == inv.warehouse_id).first()
    ctx = ToolContext(db=db_session)

    res = search_alternative_inventory.execute(
        ctx,
        product_id=inv.product_id,
        required_quantity=1,
        exclude_warehouse_id=wh.id,
    )
    assert res.success is True
    excluded_ids = [alt["warehouse_id"] for alt in res.data["alternatives"]]
    assert str(wh.id) not in excluded_ids


# ============================================================
# 6. POLICY TOOL
# ============================================================

def test_evaluate_policy_allowed(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = evaluate_policy.execute(
        ctx,
        issue_type="refund",
        amount=Decimal("45.00"),
        order_status="delivered",
        days_since_order=5,
        has_shipment=True,
        shipment_status="delivered",
        reason="defective item upon arrival",
    )
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["allowed"] is True


def test_evaluate_policy_denied_disallowed_reason(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = evaluate_policy.execute(
        ctx,
        issue_type="refund",
        amount=Decimal("45.00"),
        order_status="delivered",
        days_since_order=5,
        reason="buyer remorse changed my mind",
    )
    assert res.success is False
    assert res.status == ToolResultStatus.POLICY_DENIED
    assert res.data["allowed"] is False


def test_evaluate_policy_approval_required(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = evaluate_policy.execute(
        ctx,
        issue_type="refund",
        amount=Decimal("150.00"),
        order_status="delivered",
        days_since_order=3,
        reason="damaged package in transit",
    )
    assert res.data["requires_approval"] is True


def test_evaluate_policy_does_not_mutate_state(db_session: Session):
    refund_count_before = db_session.query(Refund).count()
    ctx = ToolContext(db=db_session)
    evaluate_policy.execute(
        ctx,
        issue_type="refund",
        amount=Decimal("25.00"),
        order_status="delivered",
        reason="defective item",
    )
    refund_count_after = db_session.query(Refund).count()
    assert refund_count_before == refund_count_after


# ============================================================
# 7. RESOLUTION TOOLS: REFUND
# ============================================================

def test_create_refund_tool_success(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("50.00"),
        shipping_address="123 Tool St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.commit()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = create_refund.execute(
        ctx,
        order_id=order.id,
        amount=Decimal("30.00"),
        reason="defective item upon arrival",
    )
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["amount"] == "30.00"
    assert res.data["status"] == "completed"


def test_create_refund_tool_policy_denial(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("80.00"),
        shipping_address="123 Tool St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = create_refund.execute(
        ctx,
        order_id=order.id,
        amount=Decimal("20.00"),
        reason="buyer remorse changed mind",
    )
    assert res.success is False
    assert res.status == ToolResultStatus.POLICY_DENIED


def test_create_refund_tool_approval_required(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("500.00"),
        shipping_address="123 Tool St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.commit()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = create_refund.execute(
        ctx,
        order_id=order.id,
        amount=Decimal("150.00"),
        reason="damaged package in transit",
    )
    assert res.success is True
    assert res.status == ToolResultStatus.APPROVAL_REQUIRED
    assert res.data["status"] == "pending"
    assert res.data["requires_approval"] is True


def test_create_refund_tool_invalid_amount_exceeded(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("40.00"),
        shipping_address="123 Tool St",
    )
    db_session.add(order)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = create_refund.execute(
        ctx,
        order_id=order.id,
        amount=Decimal("100.00"),
        reason="defective item",
    )
    assert res.success is False
    assert res.status == ToolResultStatus.INVALID


# ============================================================
# 8. RESOLUTION TOOLS: REPLACEMENT
# ============================================================

def test_create_replacement_tool_success(db_session: Session):
    customer = make_test_customer(db_session)
    warehouse = db_session.query(Warehouse).filter(Warehouse.status == "active").first()

    test_prod = Product(
        name="Replacement Test Item",
        sku=f"REP-TOOL-{uuid.uuid4().hex[:6]}",
        price=Decimal("40.00"),
        category="Testing",
    )
    db_session.add(test_prod)
    db_session.flush()

    inv = Inventory(
        product_id=test_prod.id,
        warehouse_id=warehouse.id,
        quantity=50,
        reserved_quantity=0,
    )
    db_session.add(inv)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        status="processing",
        total_amount=Decimal("80.00"),
        shipping_address="Replacement Way",
        order_date=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=test_prod.id,
        quantity=2,
        unit_price=Decimal("40.00"),
    )
    db_session.add(item)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = create_replacement.execute(
        ctx,
        order_id=order.id,
        product_id=test_prod.id,
        warehouse_id=warehouse.id,
        quantity=2,
        reason="defective replacement needed",
    )
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["quantity"] == 2

    # Verify inventory was reserved in DB
    db_session.refresh(inv)
    assert inv.reserved_quantity == 2


def test_create_replacement_tool_insufficient_inventory(db_session: Session):
    customer = make_test_customer(db_session)
    warehouse = db_session.query(Warehouse).filter(Warehouse.status == "active").first()

    test_prod = Product(
        name="Depleted Replacement Item",
        sku=f"DEP-TOOL-{uuid.uuid4().hex[:6]}",
        price=Decimal("50.00"),
        category="Testing",
    )
    db_session.add(test_prod)
    db_session.flush()

    inv = Inventory(
        product_id=test_prod.id,
        warehouse_id=warehouse.id,
        quantity=3,
        reserved_quantity=3,
    )
    db_session.add(inv)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        status="processing",
        total_amount=Decimal("50.00"),
        shipping_address="Depleted Warehouse Rd",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=test_prod.id,
        quantity=1,
        unit_price=Decimal("50.00"),
    )
    db_session.add(item)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = create_replacement.execute(
        ctx,
        order_id=order.id,
        product_id=test_prod.id,
        warehouse_id=warehouse.id,
        quantity=1,
        reason="defective replacement needed",
    )
    assert res.success is False
    assert res.status == ToolResultStatus.INSUFFICIENT_INVENTORY
    assert "insufficient inventory" in res.message.lower()


# ============================================================
# 9. RESOLUTION TOOLS: CANCELLATION
# ============================================================

def test_cancel_order_tool_success(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="placed",
        total_amount=Decimal("60.00"),
        shipping_address="Unshipped St",
    )
    db_session.add(order)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = cancel_order.execute(ctx, order_id=order.id, reason="Customer requested immediate cancellation")
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS
    assert res.data["status"] == "approved"

    db_session.refresh(order)
    assert order.status == "cancelled"


def test_cancel_order_tool_in_transit_conflict(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="shipped",
        total_amount=Decimal("99.00"),
        shipping_address="In Transit Way",
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="in_transit",
    )
    db_session.add(shipment)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = cancel_order.execute(ctx, order_id=order.id, reason="Changed mind")
    assert res.success is False
    assert res.status == ToolResultStatus.CONFLICT
    assert "already shipped" in res.message.lower()


def test_cancel_order_tool_delivered_conflict(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("45.00"),
        shipping_address="Delivered Dr",
    )
    db_session.add(order)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = cancel_order.execute(ctx, order_id=order.id, reason="Cancel please")
    assert res.success is False
    assert res.status == ToolResultStatus.CONFLICT


# ============================================================
# 10. CASE & EVENT TOOLS
# ============================================================

def test_get_case_state_tool_success(db_session: Session):
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="investigation",
        customer_goal="Track down delivery",
        status="investigating",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = get_case_state.execute(ctx, case_id=case.id)
    assert res.success is True
    assert res.data["case_id"] == str(case.id)
    assert res.data["status"] == "investigating"


def test_get_case_state_missing(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = get_case_state.execute(ctx, case_id=uuid.uuid4())
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND


def test_persist_case_state_safe_fields(db_session: Session):
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="refund",
        customer_goal="Process refund",
        status="open",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = persist_case_state.execute(
        ctx,
        case_id=case.id,
        status="planning",
        current_step="evaluating_policy",
        risk_level="medium",
        current_plan=["step1_check_policy", "step2_refund"],
    )
    assert res.success is True
    assert res.data["status"] == "planning"
    assert res.data["current_step"] == "evaluating_policy"
    assert res.data["risk_level"] == "medium"


def test_persist_case_state_arbitrary_field_rejected(db_session: Session):
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="general",
        customer_goal="Testing forbidden fields",
    )
    db_session.add(case)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = persist_case_state.execute(
        ctx,
        case_id=case.id,
        arbitrary_unauthorized_field="malicious_payload",
    )
    assert res.success is False
    assert res.status == ToolResultStatus.INVALID


def test_log_agent_event_persists(db_session: Session):
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="audit_test",
        customer_goal="Audit log verification",
    )
    db_session.add(case)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = log_agent_event.execute(
        ctx,
        case_id=case.id,
        event_type="tool_execution",
        tool_name="check_inventory",
        input_data={"product_id": "test_id"},
        output_data={"available": 10},
        status="success",
        message="Inventory confirmed available",
    )
    assert res.success is True
    assert res.data["event_type"] == "tool_execution"

    event_id = uuid.UUID(res.data["event_id"])
    event_row = db_session.query(AgentEvent).filter(AgentEvent.id == event_id).first()
    assert event_row is not None
    assert event_row.tool_name == "check_inventory"


def test_log_agent_event_missing_case(db_session: Session):
    ctx = ToolContext(db=db_session)
    res = log_agent_event.execute(
        ctx,
        case_id=uuid.uuid4(),
        event_type="audit",
        status="failed",
    )
    assert res.success is False
    assert res.status == ToolResultStatus.NOT_FOUND


# ============================================================
# 11. VERIFICATION TOOL
# ============================================================

def test_verify_resolution_refund_success(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="refunded",
        total_amount=Decimal("35.00"),
        shipping_address="Verify St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Refund order",
        status="resolved",
        resolution_type="refund",
        resolution_status="completed",
    )
    db_session.add(case)
    db_session.flush()

    refund = Refund(
        case_id=case.id,
        order_id=order.id,
        amount=Decimal("35.00"),
        reason="defective item",
        status="completed",
        requires_approval=False,
    )
    db_session.add(refund)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = verify_resolution.execute(ctx, case_id=case.id)
    assert res.success is True
    assert res.data["verified"] is True
    assert res.data["resolution_type"] == "refund"


def test_verify_resolution_replacement_success(db_session: Session):
    customer = make_test_customer(db_session)
    product = Product(
        name="Verify Replacement Prod",
        sku=f"VER-REP-{uuid.uuid4().hex[:6]}",
        price=Decimal("25.00"),
        category="Testing",
    )
    warehouse = db_session.query(Warehouse).filter(Warehouse.status == "active").first()
    db_session.add(product)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        status="replacement_pending",
        total_amount=Decimal("50.00"),
        shipping_address="Replacement Verify St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="replacement",
        customer_goal="Replace defective item",
        status="executing",
        resolution_type="replacement",
        resolution_status="processing",
    )
    db_session.add(case)
    db_session.flush()

    inv = Inventory(
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=10,
        reserved_quantity=2,
    )
    db_session.add(inv)
    db_session.flush()

    replacement = Replacement(
        case_id=case.id,
        order_id=order.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=2,
        reason="defective item",
        status="processing",
    )
    db_session.add(replacement)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = verify_resolution.execute(ctx, case_id=case.id)
    assert res.success is True
    assert res.data["verified"] is True


def test_verify_resolution_cancellation_success(db_session: Session):
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="cancelled",
        total_amount=Decimal("60.00"),
        shipping_address="Cancelled Verify St",
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="cancellation",
        customer_goal="Cancel order",
        status="resolved",
        resolution_type="cancellation",
        resolution_status="completed",
    )
    db_session.add(case)
    db_session.flush()

    canc = Cancellation(
        case_id=case.id,
        order_id=order.id,
        reason="Customer cancellation",
        status="approved",
    )
    db_session.add(canc)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = verify_resolution.execute(ctx, case_id=case.id)
    assert res.success is True
    assert res.data["verified"] is True


def test_verify_resolution_mismatch_fails_cleanly(db_session: Session):
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="refund",
        customer_goal="Refund missing",
        status="failed",
        resolution_type="refund",
    )
    db_session.add(case)
    db_session.commit()

    ctx = ToolContext(db=db_session)
    res = verify_resolution.execute(ctx, case_id=case.id)
    assert res.success is False
    assert res.data["verified"] is False
    assert "no refund record" in res.message.lower()


# ============================================================
# 12. ARCHITECTURAL BOUNDARY & SAFETY TESTS
# ============================================================

def test_tool_boundary_service_delegation(db_session: Session):
    import inspect
    from agents.tools import resolution_tools, inventory_tools, customer_tools

    for mod in [resolution_tools, inventory_tools, customer_tools]:
        src = inspect.getsource(mod)
        assert "db.execute(" not in src, f"Module {mod} contains direct db.execute call!"
        assert "text(" not in src, f"Module {mod} contains raw SQL text constructs!"


def test_domain_errors_distinguishable():
    assert ToolResultStatus.POLICY_DENIED != ToolResultStatus.INSUFFICIENT_INVENTORY
    assert ToolResultStatus.CONFLICT != ToolResultStatus.NOT_FOUND
    assert ToolResultStatus.CUSTOMER_BLOCKED != ToolResultStatus.INVALID
