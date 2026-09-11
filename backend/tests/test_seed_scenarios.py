import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from backend.app.db.models import (
    Customer,
    Order,
    Shipment,
    Case,
    Refund,
    Replacement,
    Cancellation,
    AgentEvent,
    Inventory,
    Product,
    Warehouse,
)


def test_scenario_1_replacement_success(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario1_alice@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None
    assert case.resolution_type == "replacement"
    assert case.risk_level == "low"
    assert case.requires_approval is False

    # Check that primary warehouse has stock
    warehouse = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()
    product = db_session.query(Product).filter(Product.sku == "AUD-NC-HEADPHONES-01").first()
    inv = db_session.query(Inventory).filter(
        Inventory.warehouse_id == warehouse.id,
        Inventory.product_id == product.id,
    ).first()
    assert inv.quantity >= 10


def test_scenario_2_replacement_fails_primary_succeeds_alternate(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario2_bob@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None
    assert case.status == "replanning"

    # Dallas must be 0, Reno must have positive stock
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()
    reno = db_session.query(Warehouse).filter(Warehouse.name == "Reno West Warehouse").first()
    product = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()

    inv_dallas = db_session.query(Inventory).filter(
        Inventory.warehouse_id == dallas.id,
        Inventory.product_id == product.id,
    ).first()
    inv_reno = db_session.query(Inventory).filter(
        Inventory.warehouse_id == reno.id,
        Inventory.product_id == product.id,
    ).first()

    assert inv_dallas.quantity == 0
    assert inv_reno.quantity > 0


def test_scenario_3_refund_below_approval_threshold(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario3_charlie@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None
    assert case.requires_approval is False

    refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund is not None
    assert refund.amount < Decimal("100.00")
    assert refund.status == "completed"
    assert refund.requires_approval is False


def test_scenario_4_refund_exceeds_approval_threshold(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario4_diana@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None
    assert case.requires_approval is True
    assert case.risk_level == "high"
    assert case.status == "awaiting_approval"

    refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund is not None
    assert refund.amount > Decimal("100.00")
    assert refund.status == "pending"
    assert refund.requires_approval is True


def test_scenario_5_order_delayed_in_transit(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario5_evan@example.com").first()
    assert customer is not None

    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order is not None

    shipment = db_session.query(Shipment).filter(Shipment.order_id == order.id).first()
    assert shipment is not None
    assert shipment.status == "delayed"


def test_scenario_6_delivered_order_damaged(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario6_fiona@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None
    assert case.issue_type == "damaged_in_transit"

    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order.status == "delivered"


def test_scenario_7_cancellation_allowed(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario7_george@example.com").first()
    assert customer is not None

    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order is not None
    assert order.status == "placed"

    # No shipment should exist for an unshipped order
    shipment = db_session.query(Shipment).filter(Shipment.order_id == order.id).first()
    assert shipment is None

    cancellation = db_session.query(Cancellation).filter(Cancellation.order_id == order.id).first()
    assert cancellation is not None
    assert cancellation.status == "approved"


def test_scenario_8_cancellation_blocked_by_shipment(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario8_hannah@example.com").first()
    assert customer is not None

    order = db_session.query(Order).filter(Order.customer_id == customer.id).first()
    assert order.status == "shipped"

    shipment = db_session.query(Shipment).filter(Shipment.order_id == order.id).first()
    assert shipment is not None
    assert shipment.status == "in_transit"

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case.resolution_status == "cancellation_blocked"


def test_scenario_9_verification_detects_state_mismatch(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario9_ian@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None

    # Find the verification failed event
    event = db_session.query(AgentEvent).filter(
        AgentEvent.case_id == case.id,
        AgentEvent.event_type == "VERIFICATION_FAILED",
    ).first()
    assert event is not None
    assert event.status == "failure"
    assert "state mismatch" in event.message.lower()


def test_scenario_10_action_failure_and_replanning(db_session: Session):
    customer = db_session.query(Customer).filter(Customer.email == "scenario10_julia@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case.status == "replanning"

    # Check for failure event and replanning event
    failure_evt = db_session.query(AgentEvent).filter(
        AgentEvent.case_id == case.id,
        AgentEvent.event_type == "TOOL_CALL",
        AgentEvent.status == "failure",
    ).first()
    assert failure_evt is not None
    assert "503" in str(failure_evt.output_data)

    replan_evt = db_session.query(AgentEvent).filter(
        AgentEvent.case_id == case.id,
        AgentEvent.event_type == "REPLAN_STARTED",
    ).first()
    assert replan_evt is not None
