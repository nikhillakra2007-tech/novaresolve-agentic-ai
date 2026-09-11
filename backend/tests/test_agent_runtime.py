import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.db.models.customer import Customer
from backend.app.db.models.order import Order, OrderItem
from backend.app.db.models.shipment import Shipment
from backend.app.db.models.product import Product
from backend.app.db.models.warehouse import Warehouse
from backend.app.db.models.inventory import Inventory
from backend.app.db.models.case import Case
from backend.app.db.models.agent_event import AgentEvent
from backend.app.db.models.refund import Refund
from backend.app.db.models.replacement import Replacement
from backend.app.db.models.cancellation import Cancellation
from backend.app.db.models.policy import Policy

from agents.runtime.agent import NovaResolveAgent
from agents.runtime.loop import AgentLoop
from agents.state.models import AgentState, AgentRunResult, AgentAction
from agents.state.manager import StateManager
from agents.planning.planner import AgentPlanner
from agents.replanning.replanner import AgentReplanner
from agents.tools.registry import TOOL_REGISTRY
from agents.tools.base import ToolContext, ToolResultStatus


def make_test_customer(db: Session, status: str = "active") -> Customer:
    uid = uuid.uuid4().hex[:8]
    cust = Customer(
        email=f"agent_runtime_{uid}@example.com",
        name=f"Agent Runtime Cust {uid}",
        status=status,
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


# ============================================================
# 1. BASIC RUNTIME & INVESTIGATION TEST
# ============================================================

def test_agent_basic_investigation(db_session: Session):
    """Test that agent initializes from a Case, plans investigation, and gathers customer/order/shipment facts."""
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("45.00"),
        shipping_address="123 Investigation Way",
        order_date=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="My item was broken. I want a refund.",
        status="open",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()

    state = StateManager.initialize_state(db_session, case.id)
    assert state.customer_goal == case.customer_goal
    assert state.evidence["customer"] is None

    # Planner should select get_customer first
    action1 = AgentPlanner.select_action(state)
    assert action1 is not None
    assert action1.tool_name == "get_customer"
    assert action1.parameters["customer_id"] == customer.id


# ============================================================
# 2. TOOL REGISTRY ENFORCEMENT & SECURITY
# ============================================================

def test_tool_registry_enforcement_in_runtime(db_session: Session):
    """Ensures arbitrary or malicious actions are rejected by the Tool Registry."""
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="investigate",
        customer_goal="Run raw SQL injection",
        status="open",
    )
    db_session.add(case)
    db_session.commit()

    ctx = ToolContext(db=db_session, case_id=case.id)

    # Unauthorized arbitrary SQL call
    res = TOOL_REGISTRY.execute("raw_sql", ctx, {"query": "DROP TABLE users;"})
    assert res.success is False
    assert res.status == ToolResultStatus.INVALID
    assert "strictly prohibited" in res.message

    # Unregistered tool
    res2 = TOOL_REGISTRY.execute("non_existent_tool", ctx, {})
    assert res2.success is False
    assert res2.status == ToolResultStatus.NOT_FOUND


# ============================================================
# 3. END-TO-END AUTONOMOUS REFUND SCENARIO (SUCCESS)
# ============================================================

def test_agent_e2e_successful_refund(db_session: Session):
    """Scenario: Low-risk damaged order requested for refund.
    Agent autonomously:
    1. Identifies goal
    2. Investigates customer, order, shipment
    3. Evaluates policy (allowed, low risk)
    4. Executes create_refund
    5. Verifies resolution
    6. Reaches RESOLVED state
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("49.99"),
        shipping_address="456 Refund Blvd",
        order_date=datetime.now(timezone.utc) - timedelta(days=4),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="The mug arrived damaged in shipment. Please issue a refund.",
        status="open",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()

    # Execute Autonomous Agent Runtime
    result: AgentRunResult = NovaResolveAgent.run(db=db_session, case_id=case.id)

    # Assertions on AgentRunResult
    assert result.success is True
    assert result.status == "resolved"
    assert result.resolution_status == "completed"
    assert result.requires_approval is False
    assert "successfully resolved" in result.final_outcome
    assert result.steps_executed > 0

    # Verify DB Case entity
    db_session.refresh(case)
    assert case.status == "resolved"
    assert case.resolution_type == "refund"
    assert case.resolution_status == "completed"

    # Verify Refund record
    refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund is not None
    assert refund.amount == Decimal("49.99")
    assert refund.status == "completed"

    # Verify audit event history
    events = (
        db_session.query(AgentEvent)
        .filter(AgentEvent.case_id == case.id)
        .order_by(AgentEvent.created_at.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert "GOAL_IDENTIFIED" in event_types
    assert "CUSTOMER_LOOKUP" in event_types
    assert "ORDER_LOOKUP" in event_types
    assert "SHIPMENT_LOOKUP" in event_types
    assert "POLICY_CHECK" in event_types
    assert "ACTION_EXECUTED" in event_types
    assert "VERIFICATION_SUCCESS" in event_types
    assert "RESOLVED" in event_types


# ============================================================
# 4. ADAPTIVE INVENTORY REPLANNING SCENARIO (DEMO SCENARIO 1 & 2)
# ============================================================

def test_agent_adaptive_replacement_replanning(db_session: Session):
    """Scenario: Customer requests replacement for damaged product.
    - Primary warehouse has 0 stock.
    - create_replacement fails with INSUFFICIENT_INVENTORY.
    - Agent detects constraint, triggers REPLAN_STARTED.
    - Agent executes search_alternative_inventory, finds secondary warehouse with stock.
    - Agent triggers REPLAN_COMPLETED, executes create_replacement with secondary warehouse.
    - Verifies resolution and marks case RESOLVED.
    """
    warehouses = db_session.query(Warehouse).filter(Warehouse.status == "active").order_by(Warehouse.created_at.asc()).all()
    primary_wh = warehouses[0]
    alt_wh = warehouses[1]
    customer = make_test_customer(db_session)

    test_prod = Product(
        name="Adaptive Headset",
        sku=f"ADAPT-SKU-{uuid.uuid4().hex[:6]}",
        price=Decimal("79.99"),
        category="Electronics",
    )
    db_session.add(test_prod)
    db_session.flush()

    # Primary warehouse: 0 units available
    inv_primary = Inventory(
        product_id=test_prod.id,
        warehouse_id=primary_wh.id,
        quantity=0,
        reserved_quantity=0,
    )
    # Secondary warehouse: 25 units available
    inv_alt = Inventory(
        product_id=test_prod.id,
        warehouse_id=alt_wh.id,
        quantity=25,
        reserved_quantity=0,
    )
    db_session.add(inv_primary)
    db_session.add(inv_alt)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("79.99"),
        shipping_address="789 Adaptive Way",
        order_date=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=test_prod.id,
        quantity=1,
        unit_price=Decimal("79.99"),
    )
    db_session.add(item)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="replacement",
        customer_goal="My headset arrived damaged. I need a replacement sent to me.",
        status="open",
        risk_level="low",
        current_plan=[{"step": 1, "primary_warehouse_id": str(primary_wh.id)}],
    )
    db_session.add(case)
    db_session.commit()

    # Execute Autonomous Agent Runtime
    result: AgentRunResult = NovaResolveAgent.run(db=db_session, case_id=case.id)

    # Must be resolved via adaptation
    assert result.success is True
    assert result.status == "resolved"
    assert result.resolution_status == "completed"
    assert result.replans >= 1

    # Check Replacement record in DB was fulfilled by secondary warehouse!
    rep = db_session.query(Replacement).filter(Replacement.case_id == case.id).first()
    assert rep is not None
    assert rep.status == "processing"
    assert rep.warehouse_id == alt_wh.id  # Successfully adapted from primary_wh to alt_wh!
    assert rep.quantity == 1

    # Verify audit event trace
    events = (
        db_session.query(AgentEvent)
        .filter(AgentEvent.case_id == case.id)
        .order_by(AgentEvent.created_at.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert "CONSTRAINT_DETECTED" in event_types
    assert "REPLAN_STARTED" in event_types
    assert "REPLAN_COMPLETED" in event_types
    assert "VERIFICATION_SUCCESS" in event_types
    assert "RESOLVED" in event_types


# ============================================================
# 5. HIGH-RISK REFUND & APPROVAL GATE SCENARIO
# ============================================================

def test_agent_high_risk_approval_gate_and_resume(db_session: Session):
    """Scenario: Refund > $100 requires supervisor approval.
    - Agent evaluates policy -> requires_approval=True.
    - Agent creates refund -> refund is staged as pending.
    - Verification returns APPROVAL_REQUIRED (not verified!).
    - Case transitions to awaiting_approval.
    - Agent pauses execution.
    - Then supervisor approves via NovaResolveAgent.resume().
    - Pending refund is marked completed.
    - Verification succeeds -> Case marks RESOLVED.
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("180.00"),
        shipping_address="100 Approval Way",
        order_date=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="High value item damaged in transit. Requesting full refund.",
        status="open",
        risk_level="high",
        requires_approval=True,
    )
    db_session.add(case)
    db_session.commit()

    # Step 1: Initial Run -> Must pause at approval gate
    run_res: AgentRunResult = NovaResolveAgent.run(db=db_session, case_id=case.id)

    assert run_res.success is False
    assert run_res.status == "awaiting_approval"
    assert run_res.requires_approval is True
    assert "awaiting supervisor approval" in run_res.final_outcome.lower()

    # Confirm case in DB is awaiting_approval (NOT resolved!)
    db_session.refresh(case)
    assert case.status == "awaiting_approval"
    assert case.requires_approval is True

    # Confirm consequential action (refund) was NOT executed prior to approval
    staged_refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert staged_refund is None

    # Step 2: Supervisor Grants Approval via NovaResolveAgent.resume()
    resume_res: AgentRunResult = NovaResolveAgent.resume(
        db=db_session,
        case_id=case.id,
        approved=True,
        reviewer_notes="Supervisor reviewed damage evidence and approved refund.",
    )

    assert resume_res.success is True
    assert resume_res.status == "resolved"
    assert resume_res.resolution_status == "completed"

    # Confirm DB records
    db_session.refresh(case)
    assert case.status == "resolved"
    assert case.requires_approval is False

    completed_refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert completed_refund is not None
    assert completed_refund.status == "completed"
    assert completed_refund.requires_approval is False


# ============================================================
# 6. CANCELLATION CONFLICT SCENARIO
# ============================================================

def test_agent_cancellation_conflict_escalates(db_session: Session):
    """Scenario: Customer wants cancellation for order that is already in_transit.
    cancel_order returns CONFLICT.
    Agent detects constraint, recognizes in-transit shipment cannot be cancelled,
    and cleanly escalates case without repeating action.
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="shipped",
        total_amount=Decimal("60.00"),
        shipping_address="200 InTransit Way",
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="in_transit",
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="cancellation",
        customer_goal="Please cancel my order immediately.",
        status="open",
    )
    db_session.add(case)
    db_session.commit()

    run_res: AgentRunResult = NovaResolveAgent.run(db=db_session, case_id=case.id)

    assert run_res.success is False
    assert run_res.status == "escalated"
    assert "escalated" in run_res.final_outcome.lower()

    db_session.refresh(case)
    assert case.status == "escalated"


# ============================================================
# 7. POLICY DENIAL SCENARIO
# ============================================================

def test_agent_policy_denial_blocks_and_escalates(db_session: Session):
    """Scenario: Customer requests refund for buyer remorse after 40 days (policy allows <= 30 days).
    Policy evaluation returns allowed=False.
    Agent does NOT execute refund, and cleanly escalates.
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("45.00"),
        shipping_address="300 Remorse Ave",
        order_date=datetime.now(timezone.utc) - timedelta(days=40),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=35),
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="I changed mind, remorse return.",
        status="open",
    )
    db_session.add(case)
    db_session.commit()

    run_res: AgentRunResult = NovaResolveAgent.run(db=db_session, case_id=case.id)

    assert run_res.success is False
    assert run_res.status == "escalated"

    # Confirm NO refund was created
    refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund is None


# ============================================================
# 8. MULTI-CASE ISOLATION ON SAME ORDER
# ============================================================

def test_multi_case_isolation_on_same_order(db_session: Session):
    """Ensures two cases on the same order do not interfere with each other."""
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("80.00"),
        shipping_address="400 Isolation St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.flush()

    case_a = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Item A damaged in transit, refund please.",
        status="open",
    )
    case_b = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="inquiry",
        customer_goal="Question regarding warranty on item B.",
        status="open",
    )
    db_session.add(case_a)
    db_session.add(case_b)
    db_session.commit()

    # Run agent ONLY on case_a
    res_a = NovaResolveAgent.run(db=db_session, case_id=case_a.id)
    assert res_a.success is True
    assert res_a.status == "resolved"

    # Verify case_b is untouched
    db_session.refresh(case_b)
    assert case_b.status == "open"
    assert case_b.resolution_status is None


# ============================================================
# 9. API ENDPOINTS INTEGRATION TEST
# ============================================================

def test_api_agent_run_and_trace(client: TestClient, db_session: Session):
    """Tests POST /api/agent/run, GET /api/agent/case/{case_id}/trace, and POST /api/agent/resume endpoints."""
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("35.00"),
        shipping_address="500 API Way",
        order_date=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Item broken, refund requested.",
        status="open",
    )
    db_session.add(case)
    db_session.commit()

    # 1. Trigger agent via API
    resp = client.post("/api/agent/run", json={"case_id": str(case.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == str(case.id)
    assert data["success"] is True
    assert data["status"] == "resolved"

    # 2. Query execution trace via API
    trace_resp = client.get(f"/api/agent/case/{case.id}/trace")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert len(trace_data) > 0
    event_types = [t["event_type"] for t in trace_data]
    assert "GOAL_IDENTIFIED" in event_types
    assert "RESOLVED" in event_types


# ============================================================
# 10. VERIFICATION MISMATCH SCENARIO (DEMO SCENARIO 3)
# ============================================================

def test_agent_verification_mismatch_prevents_resolution(db_session: Session):
    """Scenario: Action was created, but deterministic verification discovers state mismatch
    (e.g. underlying refund was marked failed/rejected or deleted).
    Agent runtime:
    1. Detects verification failure
    2. Does NOT falsely declare case resolved
    3. Records VERIFICATION_FAILED audit event
    4. Triggers controlled escalation/adaptation
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("45.00"),
        shipping_address="700 Mismatch St",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Refund missing order",
        status="executing",
        resolution_type="refund",
        resolution_status="completed",
    )
    db_session.add(case)
    db_session.flush()

    # Intentionally insert a REJECTED refund in DB to create state mismatch
    mismatched_refund = Refund(
        case_id=case.id,
        order_id=order.id,
        amount=Decimal("45.00"),
        reason="defective item",
        status="rejected",
        requires_approval=False,
    )
    db_session.add(mismatched_refund)
    db_session.commit()

    # Run agent on this case
    res = NovaResolveAgent.run(db=db_session, case_id=case.id)

    # Must NOT be resolved!
    assert res.success is False
    assert res.status != "resolved"
    assert res.status == "escalated"

    db_session.refresh(case)
    assert case.status != "resolved"

    # Confirm audit trail recorded verification failure
    events = db_session.query(AgentEvent).filter(AgentEvent.case_id == case.id).all()
    event_types = [e.event_type for e in events]
    assert "VERIFICATION_FAILED" in event_types


# ============================================================
# 11. LOOP PROTECTION SAFEGUARD TEST
# ============================================================

def test_agent_loop_protection_safeguard(db_session: Session):
    """Ensures agent does not loop infinitely when tools continuously return unresolvable failures."""
    customer = make_test_customer(db_session)
    case = Case(
        customer_id=customer.id,
        issue_type="unknown_unresolvable_issue",
        customer_goal="Do impossible task",
        status="open",
    )
    db_session.add(case)
    db_session.commit()

    # Agent must terminate safely without hanging or exceeding limits
    res = NovaResolveAgent.run(db=db_session, case_id=case.id)

    assert res.success is False
    assert res.status == "escalated"
    assert res.steps_executed <= AgentLoop.MAX_AGENT_STEPS
    assert "escalated" in res.final_outcome.lower()


# ============================================================
# 12. FOCUSED CORRECTION PASS TESTS (A, B, C, D)
# ============================================================

def test_risk_evaluator_approval_gate_prevents_pre_approval_action(db_session: Session):
    """Test A: Verifies that RiskEvaluator is actively integrated into the loop
    decision boundary, transitions the case to awaiting_approval, records APPROVAL_REQUIRED,
    and prevents consequential state-changing actions from executing before approval.
    Proves behavior comes from integrated RiskEvaluator rather than pre-existing requires_approval.
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("150.00"),  # > $100 threshold evaluated by RiskEvaluator
        shipping_address="123 Risk Gate Way",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="FedEx",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.flush()

    # Case explicitly starts with requires_approval=False
    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Item broken on arrival. Please issue refund.",
        status="open",
        risk_level="high",
        requires_approval=False,  # Explicitly False
    )
    db_session.add(case)
    db_session.commit()

    # Run agent loop
    result = NovaResolveAgent.run(db=db_session, case_id=case.id)

    # Agent should halt at awaiting_approval via RiskEvaluator gate
    assert result.success is False
    assert result.status == "awaiting_approval"
    assert result.requires_approval is True

    # Case in DB must reflect awaiting_approval
    db_session.refresh(case)
    assert case.status == "awaiting_approval"
    assert case.requires_approval is True

    # Crucial assertion: Consequential action must NOT have executed before approval
    refund_record = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund_record is None

    # Audit events must record APPROVAL_REQUIRED
    events = (
        db_session.query(AgentEvent)
        .filter(AgentEvent.case_id == case.id)
        .order_by(AgentEvent.created_at.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert "APPROVAL_REQUIRED" in event_types


def test_unknown_intent_escalates_without_refund(db_session: Session):
    """Test B: Ambiguous / unknown customer intent must not default to refund.
    Planner returns no actionable resolution, and AgentLoop safely escalates
    without creating financial or state mutations.
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("65.00"),
        shipping_address="789 Ambiguous Lane",
        order_date=datetime.now(timezone.utc) - timedelta(days=4),
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="unknown",
        customer_goal="I have a problem with my order and need help.",
        status="open",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()

    result = NovaResolveAgent.run(db=db_session, case_id=case.id)

    # Must safely escalate
    assert result.success is False
    assert result.status == "escalated"

    # MANDATORY: No Refund record was created
    refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund is None

    # No replacement or cancellation created either
    replacement = db_session.query(Replacement).filter(Replacement.case_id == case.id).first()
    assert replacement is None
    cancellation = db_session.query(Cancellation).filter(Cancellation.case_id == case.id).first()
    assert cancellation is None


def test_refund_pivot_reevaluates_policy(db_session: Session):
    """Test C: Replacement inventory exhausted across all warehouses.
    Agent pivots from replacement to refund, but re-evaluates policy first.
    When policy denies refund, agent escalates without creating refund.
    When policy requires approval, agent halts at awaiting_approval.
    """
    customer = make_test_customer(db_session)
    test_prod = Product(
        sku=f"SKU_STOCKOUT_{uuid.uuid4().hex[:6]}",
        name="Zero Stock Gadget",
        price=Decimal("60.00"),
        category="Electronics",
    )
    u_wh = uuid.uuid4().hex[:6]
    wh_primary = Warehouse(name=f"Depleted WH 1 {u_wh}", location="Region A", status="active")
    wh_secondary = Warehouse(name=f"Depleted WH 2 {u_wh}", location="Region B", status="active")
    db_session.add(test_prod)
    db_session.add(wh_primary)
    db_session.add(wh_secondary)
    db_session.flush()

    # Both warehouses have 0 stock
    inv1 = Inventory(product_id=test_prod.id, warehouse_id=wh_primary.id, quantity=0, reserved_quantity=0)
    inv2 = Inventory(product_id=test_prod.id, warehouse_id=wh_secondary.id, quantity=0, reserved_quantity=0)
    db_session.add(inv1)
    db_session.add(inv2)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("60.00"),
        shipping_address="555 Stockout Blvd",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=test_prod.id,
        quantity=1,
        unit_price=Decimal("60.00"),
    )
    db_session.add(item)
    db_session.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment)
    db_session.flush()

    # Scenario C1: Restrictive policy denies refund
    active_policies = db_session.query(Policy).filter(Policy.issue_type == "refund", Policy.active == True).all()
    for p in active_policies:
        p.active = False
    db_session.flush()

    restrictive_policy = Policy(
        issue_type="refund",
        action="refund",
        conditions={"max_amount": 10.00},  # Order is $60, so this policy will deny
        risk_level="low",
        priority=1,
        active=True,
    )
    db_session.add(restrictive_policy)
    db_session.flush()

    case_c1 = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="replacement",
        customer_goal="Item arrived damaged. Please send replacement.",
        status="open",
        risk_level="low",
        current_plan=[{"step": 1, "primary_warehouse_id": str(wh_primary.id)}],
    )
    db_session.add(case_c1)
    db_session.commit()

    res_c1 = NovaResolveAgent.run(db=db_session, case_id=case_c1.id)

    # Because replacement stock was 0 everywhere and candidate refund was denied by policy,
    # agent must escalate and NOT blindly issue a refund!
    assert res_c1.success is False
    assert res_c1.status == "escalated"
    refund_c1 = db_session.query(Refund).filter(Refund.case_id == case_c1.id).first()
    assert refund_c1 is None

    # Restore policies
    db_session.delete(restrictive_policy)
    for p in active_policies:
        p.active = True
    db_session.commit()

    # Scenario C2: Policy requires approval for refund alternative (high amount >= $100)
    order_c2 = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("150.00"),  # High value refund alternative
        shipping_address="555 Stockout Blvd",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order_c2)
    db_session.flush()

    item_c2 = OrderItem(
        order_id=order_c2.id,
        product_id=test_prod.id,
        quantity=1,
        unit_price=Decimal("150.00"),
    )
    db_session.add(item_c2)
    db_session.flush()

    shipment_c2 = Shipment(
        order_id=order_c2.id,
        tracking_number=f"TRK_{uuid.uuid4().hex[:8]}",
        carrier="UPS",
        status="delivered",
        actual_delivery=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(shipment_c2)
    db_session.flush()

    case_c2 = Case(
        customer_id=customer.id,
        order_id=order_c2.id,
        issue_type="replacement",
        customer_goal="Item arrived damaged. Please send replacement.",
        status="open",
        risk_level="low",
        requires_approval=False,
        current_plan=[{"step": 1, "primary_warehouse_id": str(wh_primary.id)}],
    )
    db_session.add(case_c2)
    db_session.commit()

    res_c2 = NovaResolveAgent.run(db=db_session, case_id=case_c2.id)

    # Agent detects 0 stock -> pivots to evaluate refund policy -> policy requires approval
    # -> halts at awaiting_approval -> no final resolution without supervisor approval!
    assert res_c2.success is False
    assert res_c2.status == "awaiting_approval"
    assert res_c2.requires_approval is True
    refund_c2 = db_session.query(Refund).filter(Refund.case_id == case_c2.id).first()
    assert refund_c2 is None


def test_verification_failure_enters_replanning(db_session: Session):
    """Test D: Verification failure triggers explicit replanning / recovery path,
    recording VERIFICATION_FAILED and CONSTRAINT_DETECTED, and never falsely resolving.
    """
    customer = make_test_customer(db_session)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("50.00"),
        shipping_address="999 Verify Path",
        order_date=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=customer.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Item broken, refund please.",
        status="executing",
        resolution_type="refund",
        resolution_status="completed",
    )
    db_session.add(case)
    db_session.flush()

    # Deterministic mismatch: A rejected refund record
    mismatched_refund = Refund(
        case_id=case.id,
        order_id=order.id,
        amount=Decimal("50.00"),
        reason="defective item",
        status="rejected",
        requires_approval=False,
    )
    db_session.add(mismatched_refund)
    db_session.commit()

    result = NovaResolveAgent.run(db=db_session, case_id=case.id)

    # Must NOT be resolved!
    assert result.success is False
    assert result.status != "resolved"
    assert result.status == "escalated"

    events = (
        db_session.query(AgentEvent)
        .filter(AgentEvent.case_id == case.id)
        .order_by(AgentEvent.created_at.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert "VERIFICATION_FAILED" in event_types
    assert "CONSTRAINT_DETECTED" in event_types
    assert "REPLAN_STARTED" in event_types
    assert "RESOLVED" not in event_types
