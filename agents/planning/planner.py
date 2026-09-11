import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from agents.state.models import AgentState, AgentAction
from agents.planning.models import ExecutionPhase

logger = logging.getLogger("nova.agents.planner")


class AgentPlanner:
    """Deterministic, evidence-informed action planner.
    Operates strictly on AgentState without direct database access.
    """

    @staticmethod
    def infer_action_type(goal: str, issue_type: str) -> str:
        """Infers the intended resolution type from the customer goal and case issue type."""
        goal_lower = goal.lower()
        issue_lower = issue_type.lower()

        if "replace" in goal_lower or "replacement" in issue_lower:
            return "replacement"
        elif "cancel" in goal_lower or "cancellation" in issue_lower:
            return "cancellation"
        elif "refund" in goal_lower or "return" in goal_lower or "refund" in issue_lower:
            return "refund"
        return "refund"

    @staticmethod
    def extract_reason(goal: str, issue_type: str) -> str:
        """Extracts standard reason code from goal text."""
        goal_lower = goal.lower()
        if "damaged" in goal_lower or "broken" in goal_lower or "defective" in goal_lower:
            return "damaged"
        elif "delayed" in goal_lower or "late" in goal_lower:
            return "delayed"
        elif "missing" in goal_lower or "lost" in goal_lower:
            return "lost"
        elif "remorse" in goal_lower or "changed mind" in goal_lower:
            return "remorse"
        return "damaged"

    @classmethod
    def _get_primary_warehouse_id(cls, state: AgentState) -> Optional[uuid.UUID]:
        """Resolves preferred/primary fulfillment warehouse from evidence, plan, or shipment."""
        if state.evidence.get("primary_warehouse_id"):
            return uuid.UUID(str(state.evidence["primary_warehouse_id"]))
        if state.current_plan:
            for step in state.current_plan:
                if isinstance(step, dict) and "primary_warehouse_id" in step:
                    return uuid.UUID(str(step["primary_warehouse_id"]))
        shipment_data = state.evidence.get("shipment")
        if shipment_data and isinstance(shipment_data, dict) and shipment_data.get("warehouse_id"):
            return uuid.UUID(str(shipment_data["warehouse_id"]))
        return None

    @classmethod
    def determine_phase(cls, state: AgentState) -> ExecutionPhase:
        """Determines the current execution phase based on accumulated state and observations."""
        # 1. Check terminal states
        if state.verification_status == "verified":
            return ExecutionPhase.RESOLVED
        if state.current_status in {"resolved", "escalated", "failed"}:
            return ExecutionPhase.RESOLVED if state.current_status == "resolved" else ExecutionPhase.ESCALATED
        if state.requires_approval and state.current_status == "awaiting_approval":
            return ExecutionPhase.AWAITING_APPROVAL

        # If resolution was already executed/approved and needs verification:
        if state.resolution_type and (state.approval_status == "approved" or (state.resolution_status in {"completed", "processing"} and not state.requires_approval)):
            if state.verification_status is None:
                return ExecutionPhase.POST_ACTION_VERIFICATION

        # 2. Check Investigation Phase
        if state.evidence.get("customer") is None:
            return ExecutionPhase.INVESTIGATION
        if state.order_id and state.evidence.get("order") is None:
            return ExecutionPhase.INVESTIGATION
        if state.order_id and state.evidence.get("shipment") is None:
            return ExecutionPhase.INVESTIGATION

        # 3. Check Policy Evaluation Phase
        if state.evidence.get("policy") is None:
            return ExecutionPhase.POLICY_CHECK

        # 4. Check Pre-Action Verification Phase (Inventory for replacements)
        action_type = cls.infer_action_type(state.customer_goal, state.issue_type)
        if action_type == "replacement":
            # Check if we have verified stock for either primary or alternative warehouse
            has_stock_check = bool(state.evidence.get("inventory")) or bool(state.evidence.get("alternative_inventory"))
            if not has_stock_check and state.resolution_status is None:
                return ExecutionPhase.PRE_ACTION_VERIFICATION

        # 5. Check Action Execution Phase
        if state.resolution_status is None or state.resolution_status == "failed":
            return ExecutionPhase.ACTION_EXECUTION

        # 6. Check Post-Action Verification Phase
        if state.verification_status is None:
            return ExecutionPhase.POST_ACTION_VERIFICATION

        return ExecutionPhase.RESOLVED

    @classmethod
    def select_action(cls, state: AgentState) -> Optional[AgentAction]:
        """Selects the next discrete AgentAction based on the current goal and accumulated evidence."""
        phase = cls.determine_phase(state)

        # -------------------------------------------------------------
        # Phase 1: INVESTIGATION
        # -------------------------------------------------------------
        if phase == ExecutionPhase.INVESTIGATION:
            if state.evidence.get("customer") is None:
                return AgentAction(
                    tool_name="get_customer",
                    parameters={"customer_id": state.customer_id},
                    rationale="Retrieve customer profile, tier, and account status for case investigation.",
                    expected_outcome="Customer record loaded into evidence.",
                )
            if state.order_id and state.evidence.get("order") is None:
                return AgentAction(
                    tool_name="get_order",
                    parameters={"order_id": state.order_id},
                    rationale="Inspect order items, total amount, and placement date.",
                    expected_outcome="Order details and line items loaded into evidence.",
                )
            if state.order_id and state.evidence.get("shipment") is None:
                return AgentAction(
                    tool_name="get_shipment",
                    parameters={"order_id": state.order_id},
                    rationale="Check shipment carrier status, tracking number, and delivery date.",
                    expected_outcome="Shipment record loaded into evidence.",
                )

        # -------------------------------------------------------------
        # Phase 2: POLICY EVALUATION
        # -------------------------------------------------------------
        if phase == ExecutionPhase.POLICY_CHECK:
            action_type = cls.infer_action_type(state.customer_goal, state.issue_type)
            reason = cls.extract_reason(state.customer_goal, state.issue_type)

            order_data = state.evidence.get("order")
            shipment_data = state.evidence.get("shipment")

            amount = None
            if action_type == "refund":
                if order_data and "total_amount" in order_data:
                    amount = Decimal(str(order_data["total_amount"]))
                else:
                    amount = Decimal("50.00")

            order_status = order_data.get("status") if order_data else None
            days_since = 1
            if order_data and "order_date" in order_data and order_data["order_date"]:
                try:
                    od = datetime.fromisoformat(str(order_data["order_date"]))
                    days_since = max(0, (datetime.now(timezone.utc) - od).days)
                except Exception:
                    days_since = 1

            has_shipment = shipment_data is not None
            shipment_status = shipment_data.get("status") if shipment_data else None

            return AgentAction(
                tool_name="evaluate_policy",
                parameters={
                    "issue_type": action_type,
                    "amount": amount,
                    "order_status": order_status,
                    "days_since_order": days_since,
                    "has_shipment": has_shipment,
                    "shipment_status": shipment_status,
                    "reason": reason,
                },
                rationale=f"Evaluate enterprise policy compliance, risk level, and approval requirement for '{action_type}'.",
                expected_outcome="Policy compliance decision, risk level, and approval rules received.",
            )

        # -------------------------------------------------------------
        # Phase 3: PRE-ACTION VERIFICATION (Stock check for replacement)
        # -------------------------------------------------------------
        if phase == ExecutionPhase.PRE_ACTION_VERIFICATION:
            order_data = state.evidence.get("order", {})
            items = order_data.get("items", [])
            if not items:
                # Cannot proceed without order items
                return None

            target_item = items[0]
            product_id = uuid.UUID(str(target_item["product_id"]))

            primary_wh_id = cls._get_primary_warehouse_id(state)
            if primary_wh_id:
                return AgentAction(
                    tool_name="check_inventory",
                    parameters={
                        "product_id": product_id,
                        "warehouse_id": primary_wh_id,
                    },
                    rationale=f"Check stock availability for product '{product_id}' at primary warehouse '{primary_wh_id}'.",
                    expected_outcome="Inventory quantity verified for target warehouse.",
                )
            else:
                return AgentAction(
                    tool_name="search_alternative_inventory",
                    parameters={
                        "product_id": product_id,
                        "required_quantity": 1,
                    },
                    rationale=f"Discover fulfillment warehouses with available stock for product '{product_id}'.",
                    expected_outcome="List of warehouses with stock available.",
                )

        # -------------------------------------------------------------
        # Phase 4: ACTION EXECUTION
        # -------------------------------------------------------------
        if phase == ExecutionPhase.ACTION_EXECUTION:
            policy_data = state.evidence.get("policy", {})
            if policy_data and policy_data.get("allowed") is False:
                # Policy explicitly denied this action! Do not execute!
                logger.warning(f"Policy denied action: {policy_data.get('reason')}")
                return None

            action_type = cls.infer_action_type(state.customer_goal, state.issue_type)
            reason = cls.extract_reason(state.customer_goal, state.issue_type)

            if action_type == "replacement":
                order_data = state.evidence.get("order", {})
                items = order_data.get("items", [])
                if not items:
                    return None
                target_item = items[0]
                product_id = uuid.UUID(str(target_item["product_id"]))

                # Determine target warehouse: check if alternative warehouse was found
                alternatives = state.evidence.get("alternative_inventory", [])
                if alternatives:
                    # Choose first alternative warehouse with stock
                    chosen_wh = alternatives[0]
                    warehouse_id = uuid.UUID(str(chosen_wh["warehouse_id"]))
                    rationale_txt = f"Create replacement item from alternative warehouse '{chosen_wh.get('warehouse_name')}'."
                else:
                    primary_wh_id = cls._get_primary_warehouse_id(state)
                    if not primary_wh_id:
                        inv_keys = list(state.evidence.get("inventory", {}).keys())
                        if inv_keys and "_" in inv_keys[0]:
                            primary_wh_id = uuid.UUID(inv_keys[0].split("_")[1])
                    warehouse_id = primary_wh_id or uuid.uuid4()
                    rationale_txt = "Create replacement item from primary fulfillment warehouse."

                return AgentAction(
                    tool_name="create_replacement",
                    parameters={
                        "order_id": state.order_id,
                        "product_id": product_id,
                        "warehouse_id": warehouse_id,
                        "quantity": 1,
                        "reason": f"Damaged item replacement ({reason})",
                    },
                    rationale=rationale_txt,
                    expected_outcome="Replacement order created and stock reserved.",
                )

            elif action_type == "refund":
                order_data = state.evidence.get("order", {})
                amount = Decimal(str(order_data.get("total_amount", "50.00")))
                return AgentAction(
                    tool_name="create_refund",
                    parameters={
                        "order_id": state.order_id,
                        "amount": amount,
                        "reason": f"Customer resolution refund ({reason})",
                    },
                    rationale="Execute customer refund under evaluated policy.",
                    expected_outcome="Refund record created and balance updated.",
                )

            elif action_type == "cancellation":
                return AgentAction(
                    tool_name="cancel_order",
                    parameters={
                        "order_id": state.order_id,
                        "reason": f"Customer requested order cancellation ({reason})",
                    },
                    rationale="Execute order cancellation and release reserved items.",
                    expected_outcome="Order cancelled and confirmation issued.",
                )

        # -------------------------------------------------------------
        # Phase 5: POST-ACTION VERIFICATION
        # -------------------------------------------------------------
        if phase == ExecutionPhase.POST_ACTION_VERIFICATION:
            return AgentAction(
                tool_name="verify_resolution",
                parameters={"case_id": state.case_id},
                rationale="Perform independent deterministic verification of final case resolution state.",
                expected_outcome="Resolution state verified against orders, inventory, and domain records.",
            )

        return None
