import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.services.policy_service import PolicyService


class EvaluatePolicyInput(BaseModel):
    issue_type: str = Field(..., description="Issue type: refund, replacement, cancellation, etc.")
    action: Optional[str] = Field(None, description="Specific action to evaluate (e.g. create_replacement_order)")
    amount: Optional[Decimal] = Field(None, ge=0, description="Amount in USD for monetary requests")
    order_status: Optional[str] = Field(None, description="Current status of the associated order")
    days_since_order: Optional[int] = Field(None, ge=0, description="Elapsed calendar days since order placement")
    has_shipment: Optional[bool] = Field(None, description="Whether shipment record exists")
    shipment_status: Optional[str] = Field(None, description="Current shipment carrier status")
    reason: Optional[str] = Field(None, description="Customer-provided justification or reason code")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional contextual attributes")


class PolicyEvaluationData(BaseModel):
    allowed: bool
    action: str
    risk_level: str
    requires_approval: bool
    reason: str
    applicable_conditions: Dict[str, Any] = Field(default_factory=dict)
    matched_policy_id: Optional[uuid.UUID] = None


class EvaluatePolicyTool(BaseTool):
    name = "evaluate_policy"
    description = (
        "Evaluate business policies against issue type, action, order status, shipment status, "
        "refund amount, and return reasons without modifying any business state."
    )
    category = "decision"
    input_schema = EvaluatePolicyInput
    output_schema = PolicyEvaluationData

    def _run(self, context: ToolContext, params: EvaluatePolicyInput) -> ToolResult:
        eval_resp = PolicyService.evaluate_policy(
            db=context.db,
            issue_type=params.issue_type,
            action=params.action,
            amount=params.amount,
            order_status=params.order_status,
            days_since_order=params.days_since_order,
            has_shipment=params.has_shipment,
            shipment_status=params.shipment_status,
            reason=params.reason,
            context=params.context,
        )
        data = PolicyEvaluationData(
            allowed=eval_resp.allowed,
            action=eval_resp.action,
            risk_level=eval_resp.risk_level,
            requires_approval=eval_resp.requires_approval,
            reason=eval_resp.reason,
            applicable_conditions=eval_resp.applicable_conditions,
            matched_policy_id=eval_resp.matched_policy_id,
        )
        status = ToolResultStatus.SUCCESS if eval_resp.allowed else ToolResultStatus.POLICY_DENIED
        return ToolResult(
            success=eval_resp.allowed,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=status,
            message=eval_resp.reason,
        )


evaluate_policy = EvaluatePolicyTool()
