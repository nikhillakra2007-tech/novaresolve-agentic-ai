import uuid
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from agents.state.models import AgentState, AgentAction, AgentObservation
from agents.tools.base import ToolResultStatus

logger = logging.getLogger("nova.agents.replanner")


class AgentReplanner:
    """Explicit replanning component that adapts goals and selects alternative actions
    when constraints, environment conflicts, or tool failures are observed.
    """

    MAX_REPLANS = 3

    @classmethod
    def can_replan(cls, state: AgentState, observation: AgentObservation) -> bool:
        """Determines if the observed failure or constraint can trigger an adapted plan."""
        if state.replan_count >= cls.MAX_REPLANS:
            logger.warning(f"Maximum replan limit ({cls.MAX_REPLANS}) reached for case '{state.case_id}'.")
            return False

        # Statuses that warrant adaptation
        adaptable_statuses = {
            ToolResultStatus.INSUFFICIENT_INVENTORY,
            ToolResultStatus.CONFLICT,
            ToolResultStatus.DUPLICATE,
            ToolResultStatus.POLICY_DENIED,
            ToolResultStatus.BLOCKED,
            ToolResultStatus.FAILED,
        }
        return observation.status in adaptable_statuses

    @classmethod
    def replan(cls, state: AgentState, observation: AgentObservation) -> Optional[AgentAction]:
        """Generates an adapted AgentAction to overcome the detected constraint."""
        state.replan_count += 1
        logger.info(f"Replanning #{state.replan_count} triggered for tool '{observation.tool_name}' with status '{observation.status}'")

        # ------------------------------------------------------------------
        # 1. INSUFFICIENT_INVENTORY constraint during replacement
        # ------------------------------------------------------------------
        if observation.status == ToolResultStatus.INSUFFICIENT_INVENTORY:
            order_data = state.evidence.get("order", {})
            items = order_data.get("items", [])
            if not items:
                return None
            product_id = uuid.UUID(str(items[0]["product_id"]))

            # Determine which warehouse had zero inventory
            failed_wh_id = None
            if observation.data and isinstance(observation.data, dict):
                wh_val = observation.data.get("warehouse_id")
                if wh_val:
                    failed_wh_id = uuid.UUID(str(wh_val))

            # If we haven't searched alternatives yet, search them now!
            if not state.evidence.get("alternative_inventory"):
                return AgentAction(
                    tool_name="search_alternative_inventory",
                    parameters={
                        "product_id": product_id,
                        "exclude_warehouse_id": failed_wh_id,
                        "min_quantity": 1,
                    },
                    rationale=(
                        f"Primary fulfillment warehouse has 0 available inventory for product '{product_id}'. "
                        "Replanning: searching alternative warehouses with active stock."
                    ),
                    expected_outcome="List of candidate warehouses with stock available.",
                )

            # If alternatives were searched and found:
            alternatives = state.evidence.get("alternative_inventory", [])
            if alternatives:
                chosen_wh = alternatives[0]
                alt_wh_id = uuid.UUID(str(chosen_wh["warehouse_id"]))
                return AgentAction(
                    tool_name="create_replacement",
                    parameters={
                        "order_id": state.order_id,
                        "product_id": product_id,
                        "warehouse_id": alt_wh_id,
                        "quantity": 1,
                        "reason": f"Adapted replacement from alternative warehouse ({chosen_wh.get('warehouse_name')})",
                    },
                    rationale=(
                        f"Primary warehouse lacked inventory. Adapted plan: fulfilling replacement from "
                        f"alternative warehouse '{chosen_wh.get('warehouse_name')}' with {chosen_wh.get('available_quantity')} units."
                    ),
                    expected_outcome="Replacement created and inventory reserved at alternative warehouse.",
                )

            # If no alternatives exist anywhere in the network:
            # Pivot from replacement to refund!
            logger.info("No alternative warehouses found with stock. Adapting goal from replacement to refund.")
            amount = Decimal(str(order_data.get("total_amount", "50.00")))
            return AgentAction(
                tool_name="create_refund",
                parameters={
                    "order_id": state.order_id,
                    "amount": amount,
                    "reason": "Stock unavailable across all fulfillment centers; automated refund issued.",
                },
                rationale="Inventory unavailable across entire warehouse network. Adapting resolution plan to full refund.",
                expected_outcome="Refund issued in place of unfulfillable replacement.",
            )

        # ------------------------------------------------------------------
        # 2. DUPLICATE resolution already exists
        # ------------------------------------------------------------------
        if observation.status == ToolResultStatus.DUPLICATE:
            logger.info("Resolution already exists. Adapting to verify resolution state directly.")
            return AgentAction(
                tool_name="verify_resolution",
                parameters={"case_id": state.case_id},
                rationale="Resolution entity already exists in database. Verifying existing resolution state directly.",
                expected_outcome="Resolution state verified without duplicate entity creation.",
            )

        # ------------------------------------------------------------------
        # 3. CONFLICT during cancellation (e.g. order in_transit or delivered)
        # ------------------------------------------------------------------
        if observation.status == ToolResultStatus.CONFLICT and observation.tool_name == "cancel_order":
            logger.warning("Order cancellation blocked by shipment status conflict. Checking alternatives.")
            # Since shipment is already in transit or delivered, standard cancellation is impossible.
            # Customer must return the item once delivered or seek escalation.
            # Replanner records constraint and cannot self-cancel in-transit shipment.
            return None

        # ------------------------------------------------------------------
        # 4. POLICY_DENIED
        # ------------------------------------------------------------------
        if observation.status == ToolResultStatus.POLICY_DENIED:
            logger.warning(f"Action '{observation.tool_name}' was denied by enterprise policy.")
            # Do not retry denied actions. Return None to trigger controlled escalation.
            return None

        # ------------------------------------------------------------------
        # 5. VERIFICATION MISMATCH / BLOCKED
        # ------------------------------------------------------------------
        if observation.tool_name == "verify_resolution" and observation.status in {ToolResultStatus.BLOCKED, ToolResultStatus.FAILED}:
            logger.warning("Verification detected state mismatch. Evaluating recovery options.")
            # If resolution failed, cannot verify. Return None to trigger escalation.
            return None

        return None
