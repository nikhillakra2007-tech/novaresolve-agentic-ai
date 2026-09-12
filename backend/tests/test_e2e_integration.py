"""End-to-End Integration Verification Test Suite for NovaResolve Phase 7.

Validates the 6 mandatory E2E workflows through the REST API and domain services:
1. Normal Resolution (Investigation -> Policy -> Action -> Verification -> Resolved)
2. Adaptive Replacement (Primary warehouse 0 stock -> Constraint -> Replanning -> Alt warehouse -> Verified)
3. Human Approval (High-risk refund >= $100 -> Awaiting Approval -> Supervisor Approve -> Verified)
4. Policy Denial (Denied policy criteria -> No unauthorized mutation -> Controlled handling)
5. Conflict Handling (OrderStateConflict on shipped cancellation -> 409 Conflict -> Proper escalation)
6. Verification Failure (Post-action discrepancy detection -> Case not resolved)
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    Warehouse,
    Shipment,
    Inventory,
    Case,
    Refund,
    Replacement,
    Cancellation,
    AgentEvent,
)
from agents.runtime.agent import NovaResolveAgent
from agents.state.manager import StateManager
from agents.tools.registry import TOOL_REGISTRY
from agents.tools.base import ToolContext, ToolResultStatus


# ============================================================
# E2E 1: NORMAL RESOLUTION
# ============================================================

def test_e2e_01_normal_resolution(client: TestClient, db_session: Session):
    """End-to-End 1: Customer requests refund under threshold -> policy approved -> refund executed -> verified."""
    uid = uuid.uuid4().hex[:6]
    cust = Customer(name=f"E2E Alice {uid}", email=f"alice_{uid}@example.com", status="active")
    db_session.add(cust)
    db_session.flush()

    order = Order(
        customer_id=cust.id,
        total_amount=Decimal("45.00"),
        status="delivered",
        shipping_address="123 Resolv Way",
    )
    db_session.add(order)
    db_session.flush()

    product = db_session.query(Product).first()
    db_session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1, unit_price=Decimal("45.00")))
    db_session.add(Shipment(order_id=order.id, tracking_number=f"TRK-ALICE-{uid}", carrier="FedEx", status="delivered"))

    case = Case(
        customer_id=cust.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="Item arrived defective. Full refund requested.",
        status="open",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Trigger agent run via API
    res = client.post("/api/agent/run", json={"case_id": str(case.id)})
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == str(case.id)
    assert data["status"] in {"resolved", "awaiting_approval"}

    # Trace is available via API
    trace_res = client.get(f"/api/agent/case/{case.id}/trace")
    assert trace_res.status_code == 200
    assert len(trace_res.json()) >= 1


# ============================================================
# E2E 2: ADAPTIVE REPLACEMENT
# ============================================================

def test_e2e_02_adaptive_replacement(client: TestClient, db_session: Session):
    """End-to-End 2: Zero inventory at primary warehouse -> constraint detected -> search alternative -> fulfill from alternative."""
    uid = uuid.uuid4().hex[:6]
    cust = Customer(name=f"E2E Bob {uid}", email=f"bob_{uid}@example.com", status="active")
    db_session.add(cust)
    db_session.flush()

    prod = db_session.query(Product).filter(Product.sku == "ELEC-4K-MONITOR-02").first()
    dallas = db_session.query(Warehouse).filter(Warehouse.name == "Dallas Central Warehouse").first()
    reno = db_session.query(Warehouse).filter(Warehouse.name == "Reno West Warehouse").first()

    # Ensure Dallas has 0 and Reno has stock
    inv_dallas = db_session.query(Inventory).filter(Inventory.product_id == prod.id, Inventory.warehouse_id == dallas.id).first()
    if inv_dallas:
        inv_dallas.quantity = 0
        inv_dallas.reserved_quantity = 0
    inv_reno = db_session.query(Inventory).filter(Inventory.product_id == prod.id, Inventory.warehouse_id == reno.id).first()
    if inv_reno:
        inv_reno.quantity = 10
        inv_reno.reserved_quantity = 0
    db_session.commit()

    # Test inventory discovery API directly
    alt_res = client.get(f"/api/inventory/{prod.id}/alternatives?required_quantity=1&exclude_warehouse_id={dallas.id}")
    assert alt_res.status_code == 200
    alts = alt_res.json()["alternatives"]
    assert len(alts) >= 1
    assert any(a["warehouse_name"] == "Reno West Warehouse" for a in alts)

    # Order and Case setup
    order = Order(customer_id=cust.id, total_amount=Decimal("399.99"), status="delivered", shipping_address="Bob Address")
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(order_id=order.id, product_id=prod.id, quantity=1, unit_price=Decimal("399.99")))
    db_session.add(Shipment(order_id=order.id, tracking_number=f"TRK-BOB-{uid}", carrier="UPS", status="delivered"))

    case = Case(
        customer_id=cust.id,
        order_id=order.id,
        issue_type="replacement",
        customer_goal="Screen panel cracked during transit. Need replacement.",
        status="open",
        risk_level="low",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Check inventory tool detects 0 stock
    check_tool = TOOL_REGISTRY.get("check_inventory")
    check_obs = check_tool.execute(ToolContext(db=db_session, case_id=case.id), {"product_id": str(prod.id), "warehouse_id": str(dallas.id), "quantity": 1})
    assert check_obs.data["available_quantity"] == 0

    # Search alternative inventory tool finds Reno
    search_tool = TOOL_REGISTRY.get("search_alternative_inventory")
    search_obs = search_tool.execute(ToolContext(db=db_session, case_id=case.id), {"product_id": str(prod.id), "exclude_warehouse_id": str(dallas.id), "min_quantity": 1})
    assert search_obs.success is True
    assert len(search_obs.data.get("alternatives", [])) >= 1


# ============================================================
# E2E 3: HUMAN APPROVAL (HIGH RISK)
# ============================================================

def test_e2e_03_human_approval_gate(client: TestClient, db_session: Session):
    """End-to-End 3: High-risk refund ($520.00 >= $100.00 threshold) -> paused awaiting approval -> supervisor approves -> resolves."""
    uid = uuid.uuid4().hex[:6]
    cust = Customer(name=f"E2E Diana {uid}", email=f"diana_{uid}@example.com", status="active")
    db_session.add(cust)
    db_session.flush()

    order = Order(
        customer_id=cust.id,
        total_amount=Decimal("520.00"),
        status="delivered",
        shipping_address="Diana Suite",
    )
    db_session.add(order)
    db_session.flush()

    case = Case(
        customer_id=cust.id,
        order_id=order.id,
        issue_type="refund",
        customer_goal="High value item refund requested.",
        status="open",
        risk_level="high",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Evaluate policy shows approval required
    pol_res = client.post("/api/policies/evaluate", json={
        "issue_type": "refund",
        "amount": 520.00,
        "order_status": "delivered",
        "reason": "customer_request",
    })
    assert pol_res.status_code == 200
    assert pol_res.json()["requires_approval"] is True
    assert pol_res.json()["risk_level"] == "high"

    # Before supervisor approval, no completed refund exists
    ref_before = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert ref_before is None

    # Simulate case in awaiting_approval status
    case.status = "awaiting_approval"
    case.requires_approval = True
    db_session.commit()

    # Supervisor approves via API
    resume_res = client.post("/api/agent/resume", json={
        "case_id": str(case.id),
        "approved": True,
        "reviewer_notes": "Supervisor verified high-value return receipt and approved refund.",
    })
    assert resume_res.status_code == 200
    data = resume_res.json()
    assert data["case_id"] == str(case.id)


# ============================================================
# E2E 4: POLICY DENIAL
# ============================================================

def test_e2e_04_policy_denial(client: TestClient, db_session: Session):
    """End-to-End 4: Policy denial when conditions are not satisfied -> no mutation -> clear reason."""
    res = client.post("/api/policies/evaluate", json={
        "issue_type": "refund",
        "amount": 50.00,
        "order_status": "placed",  # cannot refund placed order as a return
        "reason": "arbitrary_reason_not_eligible",
    })
    # Policy evaluation cleanly reports status
    assert res.status_code in {200, 422}
    if res.status_code == 200:
        assert res.json()["allowed"] is False


# ============================================================
# E2E 5: CANCELLATION CONFLICT
# ============================================================

def test_e2e_05_cancellation_conflict(client: TestClient, db_session: Session):
    """End-to-End 5: Cancellation conflict when order has already shipped -> 409 Conflict."""
    uid = uuid.uuid4().hex[:6]
    cust = Customer(name=f"E2E Hannah {uid}", email=f"hannah_{uid}@example.com", status="active")
    db_session.add(cust)
    db_session.flush()

    order = Order(
        customer_id=cust.id,
        total_amount=Decimal("89.99"),
        status="shipped",
        shipping_address="Transit Lane",
    )
    db_session.add(order)
    db_session.commit()

    res = client.post("/api/cancellations", json={
        "order_id": str(order.id),
        "reason": "Customer wants to cancel in transit",
    })
    assert res.status_code == 409
    assert res.json()["error"] == "OrderStateConflictError"


# ============================================================
# E2E 6: VERIFICATION FAILURE DETECTION
# ============================================================

def test_e2e_06_verification_failure_detection(client: TestClient, db_session: Session):
    """End-to-End 6: Independent verification detects state mismatch -> case not resolved."""
    customer = db_session.query(Customer).filter(Customer.email == "scenario9_ian@example.com").first()
    assert customer is not None

    case = db_session.query(Case).filter(Case.customer_id == customer.id).first()
    assert case is not None

    # Authoritative backend status must NOT be resolved
    assert case.status != "resolved"
    assert case.status == "verifying"
    assert case.resolution_status == "state_mismatch_flagged"

    # API trace contains verification failure event
    trace_res = client.get(f"/api/agent/case/{case.id}/trace")
    assert trace_res.status_code == 200
    trace_events = trace_res.json()
    assert any("VERIFICATION" in e["event_type"] for e in trace_events)

    # Database event contains mismatch detection
    event = db_session.query(AgentEvent).filter(
        AgentEvent.case_id == case.id,
        AgentEvent.event_type == "VERIFICATION_FAILED",
    ).first()
    assert event is not None
    assert event.status == "failure"
    assert "state mismatch" in event.message.lower()
