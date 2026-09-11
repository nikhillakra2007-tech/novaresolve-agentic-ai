import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session

from backend.app.db.models.policy import Policy
from backend.app.schemas.policy import (
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
)
from backend.app.core.exceptions import BusinessRuleViolationError


class PolicyService:
    @staticmethod
    def evaluate_policy(
        db: Session,
        request: Optional[Union[PolicyEvaluationRequest, Dict[str, Any]]] = None,
        issue_type: Optional[str] = None,
        action: Optional[str] = None,
        amount: Optional[Decimal] = None,
        order_status: Optional[str] = None,
        days_since_order: Optional[int] = None,
        has_shipment: Optional[bool] = None,
        shipment_status: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> PolicyEvaluationResponse:
        """Evaluates active policies in order of priority against decision context without mutating state."""
        # Unpack from request if provided
        if request is not None:
            if isinstance(request, dict):
                eff_issue_type = request.get("issue_type") or request.get("action_type") or issue_type
                eff_action = request.get("action") or action
                eff_amount = request.get("amount") if request.get("amount") is not None else amount
                eff_order_status = request.get("order_status") or order_status
                eff_days = request.get("days_since_order") if request.get("days_since_order") is not None else days_since_order
                eff_has_shipment = request.get("has_shipment") if request.get("has_shipment") is not None else has_shipment
                eff_shipment_status = request.get("shipment_status") or shipment_status
                eff_context = request.get("context") or context or {}
            else:
                eff_issue_type = request.issue_type or request.action_type or issue_type
                eff_action = request.action or action
                eff_amount = request.amount if request.amount is not None else amount
                eff_order_status = request.order_status or order_status
                eff_days = request.days_since_order if request.days_since_order is not None else days_since_order
                eff_has_shipment = request.has_shipment if request.has_shipment is not None else has_shipment
                eff_shipment_status = request.shipment_status or shipment_status
                eff_context = request.context or context or {}
        else:
            eff_issue_type = issue_type or kwargs.get("action_type")
            eff_action = action
            eff_amount = amount
            eff_order_status = order_status
            eff_days = days_since_order
            eff_has_shipment = has_shipment
            eff_shipment_status = shipment_status
            eff_context = context or {}

        if not eff_issue_type:
            raise BusinessRuleViolationError("Policy evaluation requires an issue_type or action_type.")

        query = (
            db.query(Policy)
            .filter(
                Policy.active == True,
                Policy.issue_type == eff_issue_type,
            )
            .order_by(Policy.priority.asc())
        )

        policies: List[Policy] = query.all()
        if not policies:
            return PolicyEvaluationResponse(
                allowed=False,
                action=eff_action or "unknown",
                risk_level="high",
                requires_approval=True,
                reason=f"No active policies found for issue type '{eff_issue_type}'.",
                applicable_conditions={},
                matched_policy_id=None,
            )

        # Evaluate policies in priority sequence
        for pol in policies:
            conds = pol.conditions or {}
            match = True
            rejection_reasons = []

            # 1. Action match check if caller requested a specific action
            if eff_action and pol.action != eff_action:
                continue

            # 2. Maximum amount condition
            if eff_amount is not None and "max_amount" in conds:
                max_amt = Decimal(str(conds["max_amount"]))
                if eff_amount > max_amt:
                    match = False
                    rejection_reasons.append(f"Amount ${eff_amount} exceeds policy limit of ${max_amt}")

            # 3. Minimum amount condition
            if eff_amount is not None and "min_amount" in conds:
                min_amt = Decimal(str(conds["min_amount"]))
                if eff_amount < min_amt:
                    match = False
                    rejection_reasons.append(f"Amount ${eff_amount} is below minimum threshold ${min_amt}")

            # 4. Days since order condition
            if eff_days is not None and "within_days" in conds:
                within = int(conds["within_days"])
                if eff_days > within:
                    match = False
                    rejection_reasons.append(f"Order age {eff_days} days exceeds limit of {within} days")

            # 5. Delivery requirement
            if conds.get("requires_delivery") is True:
                if eff_shipment_status != "delivered" and eff_order_status != "delivered":
                    match = False
                    rejection_reasons.append("Policy requires order/shipment to be in delivered state")

            # 6. Allowed order statuses
            if eff_order_status and "allowed_order_statuses" in conds:
                allowed_statuses = conds["allowed_order_statuses"]
                if eff_order_status not in allowed_statuses:
                    match = False
                    rejection_reasons.append(f"Order status '{eff_order_status}' not in allowed statuses {allowed_statuses}")

            # 7. Disallowed order statuses
            if eff_order_status and "disallowed_order_statuses" in conds:
                disallowed = conds["disallowed_order_statuses"]
                if eff_order_status in disallowed:
                    match = False
                    rejection_reasons.append(f"Order status '{eff_order_status}' is explicitly disallowed by policy")

            if match:
                requires_appr = (
                    pol.risk_level == "high"
                    or conds.get("requires_approval") is True
                    or conds.get("requires_human_review") is True
                )
                return PolicyEvaluationResponse(
                    allowed=True,
                    action=pol.action,
                    risk_level=pol.risk_level,
                    requires_approval=requires_appr,
                    reason=f"Authorized under policy '{pol.action}' (priority {pol.priority}).",
                    applicable_conditions=conds,
                    matched_policy_id=pol.id,
                )

        # If no policy was matched positively
        return PolicyEvaluationResponse(
            allowed=False,
            action=eff_action or "unknown",
            risk_level="medium",
            requires_approval=True,
            reason="Requested action did not satisfy criteria of any active policy.",
            applicable_conditions={},
            matched_policy_id=None,
        )
