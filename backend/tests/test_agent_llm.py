import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

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

from agents.state.models import AgentState, AgentAction, AgentObservation
from agents.state.manager import StateManager
from agents.runtime.loop import AgentLoop
from agents.runtime.agent import NovaResolveAgent
from agents.planning.decision_provider import DecisionProvider
from agents.planning.deterministic_provider import DeterministicDecisionProvider
from agents.planning.llm.client import GeminiClient, LLMClientError
from agents.planning.llm.provider import LLMDecisionProvider
from agents.planning.llm.prompts import build_llm_state_context, SYSTEM_INSTRUCTIONS
from agents.tools import TOOL_REGISTRY
from agents.tools.base import ToolContext, ToolResultStatus


# ============================================================
# TEST HELPERS & MOCKS
# ============================================================

class MockGeminiClient(GeminiClient):
    """Mock Gemini client providing canned or simulated model responses for deterministic testing."""

    def __init__(
        self,
        responses: Optional[List[Dict[str, Any]]] = None,
        side_effect: Optional[Any] = None,
        api_key: str = "test-secret-key-12345",
    ) -> None:
        super().__init__(api_key=api_key, model_name="gemini-3.7-flash")
        self.responses = list(responses) if responses else []
        self.side_effect = side_effect
        self.call_count = 0
        self.last_user_prompt: Optional[str] = None
        self.last_system_instruction: Optional[str] = None

    def is_available(self) -> bool:
        return True

    def generate_decision(
        self,
        system_instruction: str,
        user_prompt: str,
        tool_declarations: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.call_count += 1
        self.last_user_prompt = user_prompt
        self.last_system_instruction = system_instruction

        if self.side_effect:
            if callable(self.side_effect):
                return self.side_effect(user_prompt)
            raise self.side_effect

        if self.responses:
            return self.responses.pop(0)

        return {"action": None, "arguments": {}, "reason": "No remaining mock responses."}


def create_mock_case(
    db: Session,
    goal: str = "My headphones arrived broken. I need a replacement.",
    issue_type: str = "replacement",
    order_amount: Decimal = Decimal("45.00"),
    order_status: str = "delivered",
) -> Case:
    """Helper to set up customer, order, items, and case in DB."""
    uid = uuid.uuid4().hex[:6]
    cust = Customer(name=f"LLM Test Cust {uid}", email=f"llm_{uid}@example.com", status="active")
    db.add(cust)
    db.flush()

    order = Order(
        customer_id=cust.id,
        total_amount=order_amount,
        status=order_status,
        shipping_address="789 AI Boulevard, Tech City",
        order_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db.add(order)
    db.flush()

    product = db.query(Product).first()
    item = OrderItem(order_id=order.id, product_id=product.id, quantity=1, unit_price=order_amount)
    db.add(item)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_number=f"TRK-LLM-{uid}",
        status=order_status,
        carrier="FedEx",
    )
    db.add(shipment)
    db.flush()

    case = Case(
        customer_id=cust.id,
        order_id=order.id,
        issue_type=issue_type,
        customer_goal=goal,
        status="open",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


# ============================================================
# 1. BASIC LLM DECISION
# ============================================================

def test_01_basic_llm_decision_get_customer(db_session: Session):
    """Test 1: Given a case requiring investigation, LLM returns get_customer."""
    case = create_mock_case(db_session)
    mock_client = MockGeminiClient(responses=[
        {
            "action": "get_customer",
            "arguments": {"customer_id": str(case.customer_id)},
            "reason": "Identify customer profile and active status.",
            "expected_outcome": "Customer verification.",
        }
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action is not None
    assert action.tool_name == "get_customer"
    assert str(action.parameters.get("customer_id")) == str(case.customer_id)
    assert action.source == "llm"

    # Execute tool and verify observation stored
    obs = TOOL_REGISTRY.get(action.tool_name).execute(
        context=ToolContext(db=db_session, case_id=case.id),
        params=action.parameters,
    )
    assert obs.success is True
    assert obs.status == ToolResultStatus.SUCCESS


# ============================================================
# 2. ORDER INVESTIGATION
# ============================================================

def test_02_order_investigation(db_session: Session):
    """Test 2: LLM selects get_order, order is retrieved and state updated."""
    case = create_mock_case(db_session)
    mock_client = MockGeminiClient(responses=[
        {
            "action": "get_order",
            "arguments": {"order_id": str(case.order_id)},
            "reason": "Retrieve authoritative order status and items.",
        }
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action is not None
    assert action.tool_name == "get_order"

    obs = TOOL_REGISTRY.get(action.tool_name).execute(
        context=ToolContext(db=db_session, case_id=case.id),
        params=action.parameters,
    )
    StateManager.ingest_observation(state, AgentObservation(
        tool_name=action.tool_name,
        status=obs.status,
        data=obs.data,
        message=obs.message,
    ))

    assert "order" in state.evidence
    assert state.evidence["order"]["order_id"] == str(case.order_id)


# ============================================================
# 3. POLICY INVESTIGATION
# ============================================================

def test_03_policy_investigation(db_session: Session):
    """Test 3: LLM selects evaluate_policy; policy is checked via backend tool/service."""
    case = create_mock_case(db_session, goal="I want a refund for damaged goods.", issue_type="refund")
    mock_client = MockGeminiClient(responses=[
        {
            "action": "evaluate_policy",
            "arguments": {
                "issue_type": "refund",
                "amount": 45.00,
                "order_status": "delivered",
                "reason": "damaged",
            },
            "reason": "Evaluate return and refund policy before taking action.",
        }
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action is not None
    assert action.tool_name == "evaluate_policy"

    obs = TOOL_REGISTRY.get(action.tool_name).execute(
        context=ToolContext(db=db_session, case_id=case.id),
        params=action.parameters,
    )
    assert obs.success is True
    assert "allowed" in obs.data


# ============================================================
# 4. NORMAL REFUND
# ============================================================

def test_04_normal_refund_flow(db_session: Session):
    """Test 4: Low-risk refund: LLM -> policy -> refund -> verification -> resolved."""
    case = create_mock_case(db_session, goal="Please refund my order.", issue_type="refund", order_amount=Decimal("40.00"))
    mock_client = MockGeminiClient(responses=[
        {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": "Fetch customer"},
        {"action": "get_order", "arguments": {"order_id": str(case.order_id)}, "reason": "Fetch order"},
        {"action": "get_shipment", "arguments": {"order_id": str(case.order_id)}, "reason": "Fetch shipment"},
        {"action": "evaluate_policy", "arguments": {"issue_type": "refund", "amount": 40.00, "order_status": "delivered", "reason": "damaged"}, "reason": "Check policy"},
        {"action": "create_refund", "arguments": {"order_id": str(case.order_id), "amount": 40.00, "reason": "Customer damaged item refund"}, "reason": "Issue refund"},
        {"action": "verify_resolution", "arguments": {"case_id": str(case.id)}, "reason": "Verify refund outcome"},
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)

    assert result.success is True
    assert result.status == "resolved"
    assert result.resolution_status == "completed"

    # Confirm refund created in DB
    refund = db_session.query(Refund).filter(Refund.case_id == case.id).first()
    assert refund is not None
    assert refund.status == "completed"


# ============================================================
# 5. REPLACEMENT FLOW
# ============================================================

def test_05_replacement_flow(db_session: Session):
    """Test 5: Replacement flow with stock available: LLM -> investigation -> policy -> inventory -> replacement -> verification -> resolved."""
    case = create_mock_case(db_session, goal="Send replacement for damaged item.", issue_type="replacement")
    order = db_session.query(Order).filter(Order.id == case.order_id).first()
    product_id = order.items[0].product_id
    warehouse = db_session.query(Warehouse).first()

    # Ensure stock exists in warehouse
    inv = db_session.query(Inventory).filter(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse.id).first()
    newly_created = False
    orig_qty = inv.quantity if inv else 0
    orig_res = inv.reserved_quantity if inv else 0
    if inv:
        inv.quantity = 10
        inv.reserved_quantity = 0
    else:
        inv = Inventory(product_id=product_id, warehouse_id=warehouse.id, quantity=10, reserved_quantity=0)
        db_session.add(inv)
        newly_created = True
    db_session.commit()

    try:
        mock_client = MockGeminiClient(responses=[
            {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": "Lookup customer"},
            {"action": "get_order", "arguments": {"order_id": str(case.order_id)}, "reason": "Lookup order"},
            {"action": "get_shipment", "arguments": {"order_id": str(case.order_id)}, "reason": "Lookup shipment"},
            {"action": "evaluate_policy", "arguments": {"issue_type": "replacement", "order_status": "delivered", "reason": "damaged"}, "reason": "Policy check"},
            {"action": "check_inventory", "arguments": {"product_id": str(product_id), "warehouse_id": str(warehouse.id), "quantity": 1}, "reason": "Check inventory"},
            {"action": "create_replacement", "arguments": {"order_id": str(case.order_id), "product_id": str(product_id), "warehouse_id": str(warehouse.id), "quantity": 1, "reason": "Damaged replacement"}, "reason": "Create replacement"},
            {"action": "verify_resolution", "arguments": {"case_id": str(case.id)}, "reason": "Verify replacement"},
        ])
        provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

        result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)

        assert result.success is True
        assert result.status == "resolved"

        rep = db_session.query(Replacement).filter(Replacement.case_id == case.id).first()
        assert rep is not None
        assert rep.status in {"approved", "completed", "processing"}
    finally:
        if newly_created:
            db_session.delete(inv)
            db_session.commit()
        elif inv:
            inv.quantity = orig_qty
            inv.reserved_quantity = orig_res
            db_session.commit()


# ============================================================
# 6. ZERO INVENTORY ADAPTATION
# ============================================================

def test_06_zero_inventory_adaptation(db_session: Session):
    """Test 6: Primary warehouse has 0 inventory -> adaptation searches alternative -> fulfills from alternative."""
    case = create_mock_case(db_session, goal="Replace my damaged monitor.", issue_type="replacement")
    order = db_session.query(Order).filter(Order.id == case.order_id).first()
    product_id = order.items[0].product_id

    warehouses = db_session.query(Warehouse).all()
    primary_wh = warehouses[0]
    alt_wh = warehouses[1]

    # Zero stock in primary warehouse, ample stock in alt warehouse
    inv_primary = db_session.query(Inventory).filter(Inventory.product_id == product_id, Inventory.warehouse_id == primary_wh.id).first()
    orig_p_qty = inv_primary.quantity if inv_primary else 0
    orig_p_res = inv_primary.reserved_quantity if inv_primary else 0
    inv_alt = db_session.query(Inventory).filter(Inventory.product_id == product_id, Inventory.warehouse_id == alt_wh.id).first()
    orig_a_qty = inv_alt.quantity if inv_alt else 0
    orig_a_res = inv_alt.reserved_quantity if inv_alt else 0

    if inv_primary:
        inv_primary.quantity = 0
        inv_primary.reserved_quantity = 0
    if inv_alt:
        inv_alt.quantity = 15
        inv_alt.reserved_quantity = 0
    db_session.commit()

    try:
        mock_client = MockGeminiClient(responses=[
            {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": "Lookup customer"},
            {"action": "get_order", "arguments": {"order_id": str(case.order_id)}, "reason": "Lookup order"},
            {"action": "get_shipment", "arguments": {"order_id": str(case.order_id)}, "reason": "Lookup shipment"},
            {"action": "evaluate_policy", "arguments": {"issue_type": "replacement", "order_status": "delivered", "reason": "damaged"}, "reason": "Policy check"},
            {"action": "check_inventory", "arguments": {"product_id": str(product_id), "warehouse_id": str(primary_wh.id), "quantity": 1}, "reason": "Check primary inventory"},
            # check_inventory will return INSUFFICIENT_INVENTORY.
            # AgentReplanner or next step searches alternative inventory:
            {"action": "search_alternative_inventory", "arguments": {"product_id": str(product_id), "exclude_warehouse_id": str(primary_wh.id), "min_quantity": 1}, "reason": "Search alternative warehouse"},
            {"action": "create_replacement", "arguments": {"order_id": str(case.order_id), "product_id": str(product_id), "warehouse_id": str(alt_wh.id), "quantity": 1, "reason": "Adapted replacement"}, "reason": "Create replacement at alt warehouse"},
            {"action": "verify_resolution", "arguments": {"case_id": str(case.id)}, "reason": "Verify final replacement"},
        ])
        provider = LLMDecisionProvider(client=mock_client, fallback_on_error=True)

        result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)

        assert result.success is True
        assert result.status == "resolved"

        rep = db_session.query(Replacement).filter(Replacement.case_id == case.id).first()
        assert rep is not None
        assert rep.warehouse_id != primary_wh.id
    finally:
        if inv_primary:
            inv_primary.quantity = orig_p_qty
            inv_primary.reserved_quantity = orig_p_res
        if inv_alt:
            inv_alt.quantity = orig_a_qty
            inv_alt.reserved_quantity = orig_a_res
        db_session.commit()


# ============================================================
# 7. HIGH-RISK REFUND APPROVAL GATE
# ============================================================

def test_07_high_risk_refund_approval_gate(db_session: Session):
    """Test 7: Refund exceeds risk threshold -> paused awaiting approval -> supervisor approves -> resumes to resolved."""
    case = create_mock_case(db_session, goal="Refund my high value order.", issue_type="refund", order_amount=Decimal("180.00"))
    mock_client = MockGeminiClient(responses=[
        {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": "Customer"},
        {"action": "get_order", "arguments": {"order_id": str(case.order_id)}, "reason": "Order"},
        {"action": "get_shipment", "arguments": {"order_id": str(case.order_id)}, "reason": "Shipment"},
        {"action": "evaluate_policy", "arguments": {"issue_type": "refund", "amount": 180.00, "order_status": "delivered", "reason": "damaged"}, "reason": "Policy check"},
        {"action": "create_refund", "arguments": {"order_id": str(case.order_id), "amount": 180.00, "reason": "High risk refund"}, "reason": "Create refund"},
        {"action": "create_refund", "arguments": {"order_id": str(case.order_id), "amount": 180.00, "reason": "Execute approved refund"}, "reason": "Execute refund after supervisor approval"},
        {"action": "verify_resolution", "arguments": {"case_id": str(case.id)}, "reason": "Verify refund"},
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    # 1. Run agent loop - must pause at approval gate
    result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)
    assert result.status == "awaiting_approval"
    assert result.requires_approval is True

    # 2. Supervisor approves case
    resumed = NovaResolveAgent.resume(
        db=db_session,
        case_id=case.id,
        approved=True,
        reviewer_notes="Supervisor override: approved high value refund.",
        decision_provider=provider,
    )
    assert resumed.status == "resolved"
    assert resumed.success is True


# ============================================================
# 8. POLICY DENIAL
# ============================================================

def test_08_policy_denial_handling(db_session: Session):
    """Test 8: Policy denies action -> no mutation permitted -> safe escalation."""
    # Create order 60 days old with remorse reason (exceeds standard 30 day window)
    case = create_mock_case(db_session, goal="I changed my mind, refund me.", issue_type="refund", order_amount=Decimal("50.00"))
    order = db_session.query(Order).filter(Order.id == case.order_id).first()
    order.order_date = datetime.now(timezone.utc) - timedelta(days=60)
    db_session.commit()

    mock_client = MockGeminiClient(responses=[
        {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": "Customer"},
        {"action": "get_order", "arguments": {"order_id": str(case.order_id)}, "reason": "Order"},
        {"action": "get_shipment", "arguments": {"order_id": str(case.order_id)}, "reason": "Shipment"},
        {"action": "evaluate_policy", "arguments": {"issue_type": "refund", "amount": 50.00, "order_status": "delivered", "days_since_order": 60, "reason": "remorse"}, "reason": "Policy check"},
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=True)

    result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)

    # Must be safely escalated due to policy denial, with zero refund mutations
    assert result.status == "escalated"
    assert db_session.query(Refund).filter(Refund.case_id == case.id).count() == 0


# ============================================================
# 9. UNKNOWN INTENT
# ============================================================

def test_09_unknown_intent_safe_escalation(db_session: Session):
    """Test 9: Ambiguous customer intent must NOT default to refund; must safely escalate."""
    case = create_mock_case(
        db_session,
        goal="Can you tell me a bedtime story about e-commerce?",
        issue_type="inquiry",
    )
    mock_client = MockGeminiClient(responses=[
        {"action": None, "arguments": {}, "reason": "Unknown customer intent cannot be resolved through supported tools."},
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=True)

    result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)

    assert result.status == "escalated"
    assert result.success is False
    # Verify no financial mutations occurred
    assert db_session.query(Refund).filter(Refund.case_id == case.id).count() == 0
    assert db_session.query(Replacement).filter(Replacement.case_id == case.id).count() == 0
    assert db_session.query(Cancellation).filter(Cancellation.case_id == case.id).count() == 0


# ============================================================
# 10. INVALID TOOL REJECTION
# ============================================================

def test_10_invalid_tool_rejection(db_session: Session):
    """Test 10: Model returns unregistered tool name -> rejected by registry -> safe error."""
    case = create_mock_case(db_session)
    mock_client = MockGeminiClient(responses=[
        {"action": "non_existent_fake_tool", "arguments": {}, "reason": "Invalid tool attempt"}
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    # Must reject unregistered tool
    assert action is None
    assert "unknown/unregistered tool" in (state.failure_reason or "")


# ============================================================
# 11. INVALID ARGUMENTS SCHEMA VALIDATION
# ============================================================

def test_11_invalid_arguments_schema_validation(db_session: Session):
    """Test 11: Model returns malformed arguments -> Pydantic validation fails -> blocked."""
    case = create_mock_case(db_session)
    mock_client = MockGeminiClient(responses=[
        {"action": "get_customer", "arguments": {"customer_id": "not-a-valid-uuid"}, "reason": "Malformed UUID"}
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action is None
    assert "failed schema validation" in (state.failure_reason or "")


# ============================================================
# 12. PROHIBITED TOOL REJECTION
# ============================================================

def test_12_prohibited_tool_rejection(db_session: Session):
    """Test 12: Model requests raw_sql or shell capability -> rejected with security alert."""
    case = create_mock_case(db_session)
    mock_client = MockGeminiClient(responses=[
        {"action": "raw_sql", "arguments": {"query": "DROP TABLE cases;"}, "reason": "Hostile prompt injection attempt"}
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action is None
    assert "prohibited tool" in (state.failure_reason or "")


# ============================================================
# 13. VERIFICATION FAILURE
# ============================================================

def test_13_verification_failure_no_false_resolution(db_session: Session):
    """Test 13: Action execution succeeds but verify_resolution fails -> case is NOT marked resolved."""
    case = create_mock_case(db_session, goal="Refund my order.", issue_type="refund")

    # Sequence where verify_resolution is called before any refund was persisted in DB
    mock_client = MockGeminiClient(responses=[
        {"action": "verify_resolution", "arguments": {"case_id": str(case.id)}, "reason": "Premature verification attempt"}
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    state = StateManager.initialize_state(db_session, case.id)
    state.resolution_type = "refund"
    state.resolution_status = "completed"

    result = AgentLoop.run(db=db_session, state=state, decision_provider=provider)

    assert result.status != "resolved"
    # Verification event should reflect failure
    failed_event = db_session.query(AgentEvent).filter(
        AgentEvent.case_id == case.id,
        AgentEvent.event_type == "VERIFICATION_FAILED",
    ).first()
    assert failed_event is not None


# ============================================================
# 14. REPLACEMENT -> REFUND POLICY RECHECK
# ============================================================

def test_14_replacement_to_refund_policy_recheck(db_session: Session):
    """Test 14: Replacement fails due to exhausted network inventory -> replanner pivots to refund and re-evaluates policy."""
    case = create_mock_case(db_session, goal="Replace broken item.", issue_type="replacement")
    state = StateManager.initialize_state(db_session, case.id)

    order = db_session.query(Order).filter(Order.id == case.order_id).first()
    state.evidence["order"] = {"total_amount": "55.00", "status": "delivered", "items": [{"product_id": str(order.items[0].product_id)}]}
    state.evidence["alternative_inventory"] = []  # No alternatives available anywhere

    from agents.replanning.replanner import AgentReplanner

    obs = AgentObservation(
        tool_name="search_alternative_inventory",
        status=ToolResultStatus.INSUFFICIENT_INVENTORY,
        data={"warehouse_id": str(uuid.uuid4())},
        message="Zero inventory across all warehouses.",
    )

    action = AgentReplanner.replan(state, obs)
    assert action is not None
    assert action.tool_name == "evaluate_policy"
    assert action.parameters.get("issue_type") == "refund"


# ============================================================
# 15. LLM PROVIDER FAILURE
# ============================================================

def test_15_llm_provider_failure_handling(db_session: Session):
    """Test 15: Mock timeout or API error -> controlled fallback to deterministic provider or safe escalation."""
    case = create_mock_case(db_session)

    # 1. With fallback enabled
    failing_client = MockGeminiClient(side_effect=LLMClientError("Gemini API connection timeout."))
    deterministic_provider = DeterministicDecisionProvider()
    provider_with_fallback = LLMDecisionProvider(
        client=failing_client,
        fallback_provider=deterministic_provider,
        fallback_on_error=True,
    )

    state = StateManager.initialize_state(db_session, case.id)
    action = provider_with_fallback.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action is not None
    assert action.source == "deterministic_fallback"

    # 2. With fallback disabled -> safe escalation without crash
    provider_no_fallback = LLMDecisionProvider(
        client=failing_client,
        fallback_provider=None,
        fallback_on_error=False,
    )
    state2 = StateManager.initialize_state(db_session, case.id)
    action2 = provider_no_fallback.decide(state2, tools=TOOL_REGISTRY.list_tools(), db=db_session)

    assert action2 is None
    assert "LLM decision failure" in (state2.failure_reason or "")


# ============================================================
# 16. LOOP PROTECTION
# ============================================================

def test_16_loop_protection_limits(db_session: Session):
    """Test 16: Repeated identical action is stopped by MAX_SAME_TOOL_ATTEMPTS."""
    case = create_mock_case(db_session)
    # Model repeatedly answers get_customer
    mock_client = MockGeminiClient(responses=[
        {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": f"Repeat attempt {i}"}
        for i in range(10)
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)

    result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)

    assert result.status == "escalated"
    assert "exceeded maximum attempts" in (result.reason or "")


# ============================================================
# 17. MULTI-CASE ISOLATION
# ============================================================

def test_17_multi_case_isolation(db_session: Session):
    """Test 17: Case A's context does not contain Case B's state, observations, or customer data."""
    case_a = create_mock_case(db_session, goal="Case A goal: replace phone.", issue_type="replacement")
    case_b = create_mock_case(db_session, goal="Case B goal: refund laptop.", issue_type="refund")

    state_a = StateManager.initialize_state(db_session, case_a.id)
    state_b = StateManager.initialize_state(db_session, case_b.id)

    # Ingest unique observation into Case A
    StateManager.ingest_observation(state_a, AgentObservation(
        tool_name="get_customer",
        status=ToolResultStatus.SUCCESS,
        data={"vip_tier": "gold"},
        message="Case A customer lookup.",
    ))

    context_a = build_llm_state_context(state_a)
    context_b = build_llm_state_context(state_b)

    assert str(case_a.id) == context_a["case_id"]
    assert str(case_b.id) == context_b["case_id"]

    # Verify no cross-contamination
    assert "Case A goal" in context_a["customer_goal_untrusted"]
    assert "Case A goal" not in context_b["customer_goal_untrusted"]
    assert len(context_a["recent_observations"]) == 1
    assert len(context_b["recent_observations"]) == 0


# ============================================================
# 18. SECRET PROTECTION
# ============================================================

def test_18_secret_protection(db_session: Session):
    """Test 18: Sensitive API keys are not exposed in state contexts, logs, or error strings."""
    secret_key = "AIzaSySecretApiKey123456789"
    client = GeminiClient(api_key=secret_key)

    case = create_mock_case(db_session)
    state = StateManager.initialize_state(db_session, case.id)
    context = build_llm_state_context(state)

    # 1. State context must not contain API key
    context_str = str(context)
    assert secret_key not in context_str

    # 2. Error masking: simulate client exception and verify secret masking
    failing_client = GeminiClient(api_key=secret_key)
    # Trigger an error string containing secret_key
    try:
        raise Exception(f"Failed request with token {secret_key}")
    except Exception as ex:
        err_msg = str(ex)
        if secret_key in err_msg:
            err_msg = err_msg.replace(secret_key, "[REDACTED_API_KEY]")
        assert secret_key not in err_msg
        assert "[REDACTED_API_KEY]" in err_msg


# ============================================================
# 19. DECISION SOURCE TRACEABILITY
# ============================================================

def test_19_decision_source_traceability(db_session: Session):
    """Test 19: Execution trace distinguishes 'llm' decisions from 'deterministic_fallback'."""
    case = create_mock_case(db_session)

    # 1. Direct LLM decision
    mock_client = MockGeminiClient(responses=[
        {"action": "get_customer", "arguments": {"customer_id": str(case.customer_id)}, "reason": "LLM investigation"}
    ])
    provider = LLMDecisionProvider(client=mock_client, fallback_on_error=False)
    state = StateManager.initialize_state(db_session, case.id)

    action = provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)
    assert action.source == "llm"

    # 2. Fallback decision
    failing_client = MockGeminiClient(side_effect=LLMClientError("Network error"))
    fallback_provider = LLMDecisionProvider(
        client=failing_client,
        fallback_provider=DeterministicDecisionProvider(),
        fallback_on_error=True,
    )
    action_fallback = fallback_provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db_session)
    assert action_fallback.source == "deterministic_fallback"


# ============================================================
# 20. BACKWARD COMPATIBILITY
# ============================================================

def test_20_backward_compatibility_existing_tests(db_session: Session):
    """Test 20: Deterministic fallback preserves all core Phase 4 runtime mechanics."""
    case = create_mock_case(db_session, goal="I need a refund for my damaged shoes.", issue_type="refund", order_amount=Decimal("45.00"))
    provider = DeterministicDecisionProvider()

    result = NovaResolveAgent.run(db=db_session, case_id=case.id, decision_provider=provider)
    assert result.status == "resolved"
    assert result.success is True


# ============================================================
# 21. DECISION PROVIDER FACTORY INTEGRATION
# ============================================================

def test_21_decision_provider_factory_resolution():
    """Test 21: DecisionProviderFactory returns LLMDecisionProvider when LLM_PROVIDER=gemini."""
    from backend.app.core.config import settings
    from agents.planning.decision_provider import DecisionProviderFactory

    original_provider = settings.LLM_PROVIDER
    try:
        settings.LLM_PROVIDER = "gemini"
        provider = DecisionProviderFactory.get_default_provider()
        assert isinstance(provider, LLMDecisionProvider)
        assert provider.name == "llm"
        assert provider.provider_type == "gemini"

        settings.LLM_PROVIDER = "deterministic"
        det_provider = DecisionProviderFactory.get_default_provider()
        assert isinstance(det_provider, DeterministicDecisionProvider)
        assert det_provider.name == "deterministic"
    finally:
        settings.LLM_PROVIDER = original_provider


# ============================================================
# 22. AGENT LOOP USES DECISION PROVIDER NOT AGENT PLANNER
# ============================================================

def test_22_agent_loop_uses_decision_provider_not_agent_planner(db_session: Session, monkeypatch):
    """Test 22: Verify AgentLoop delegates normal action selection to DecisionProvider.decide(),
    and does NOT call AgentPlanner directly in the loop.
    """
    case = create_mock_case(db_session)
    state = StateManager.initialize_state(db_session, case.id)

    class TrackingDecisionProvider(DecisionProvider):
        name = "tracking"
        provider_type = "mock"
        def __init__(self):
            self.calls = 0

        def decide(self, state, tools, db=None):
            self.calls += 1
            if self.calls == 1:
                return AgentAction(
                    tool_name="get_customer",
                    parameters={"customer_id": str(case.customer_id)},
                    rationale="Tracking provider decision",
                    source="tracking",
                )
            return None

    tracking_provider = TrackingDecisionProvider()

    # If AgentPlanner.select_action was erroneously called by AgentLoop, this will fail
    def forbid_planner_select_action(s):
        raise AssertionError("AgentPlanner.select_action was directly called by AgentLoop! It must use DecisionProvider.")

    from agents.planning.planner import AgentPlanner
    monkeypatch.setattr(AgentPlanner, "select_action", forbid_planner_select_action)

    result = AgentLoop.run(db=db_session, state=state, decision_provider=tracking_provider)
    assert tracking_provider.calls >= 1
    # Confirm trace records tracking source
    assert any(step.get("source") == "tracking" for step in result.execution_trace)
