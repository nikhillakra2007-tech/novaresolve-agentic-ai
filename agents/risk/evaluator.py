import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from agents.state.models import AgentState

logger = logging.getLogger("nova.agents.risk")


class RiskEvaluator:
    """Evaluates case risk profile and enforces human-in-the-loop approval gates."""

    # Default approval thresholds
    HIGH_RISK_REFUND_THRESHOLD = Decimal("100.00")

    @classmethod
    def should_require_approval(cls, state: AgentState) -> bool:
        """Determines if the current case state and planned resolution requires supervisor approval."""
        # 1. Direct policy requirement
        if state.requires_approval:
            return True

        # 2. Check policy evidence
        policy_data = state.evidence.get("policy")
        if policy_data and policy_data.get("requires_approval") is True:
            return True

        # 3. Check customer risk level
        cust_data = state.evidence.get("customer")
        if cust_data and cust_data.get("risk_level") == "high":
            return True

        # 4. Check resolution amount
        order_data = state.evidence.get("order")
        if order_data and "total_amount" in order_data:
            amt = Decimal(str(order_data["total_amount"]))
            if amt > cls.HIGH_RISK_REFUND_THRESHOLD:
                return True

        return False
