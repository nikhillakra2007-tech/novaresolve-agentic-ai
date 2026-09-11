import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class PolicyEvaluationRequest(BaseModel):
    issue_type: Optional[str] = Field(None, description="Issue type: refund, replacement, cancellation, delay, damage")
    action_type: Optional[str] = Field(None, description="Action or issue type alias (e.g. refund, cancellation, replacement)")
    action: Optional[str] = Field(None, description="Target action: auto_refund, create_replacement_order, cancel_unshipped_order, etc.")
    amount: Optional[Decimal] = Field(None, ge=0, description="Amount in currency for refund evaluation")
    order_status: Optional[str] = Field(None, description="Current status of the order")
    days_since_order: Optional[int] = Field(None, ge=0, description="Order age in days")
    has_shipment: Optional[bool] = Field(None, description="Whether order has a shipment record")
    shipment_status: Optional[str] = Field(None, description="Current shipment status")
    reason: Optional[str] = Field(None, description="Customer stated reason for refund, replacement, or cancellation")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional arbitrary rule parameters")


class PolicyEvaluationResponse(BaseModel):
    allowed: bool = Field(..., description="Whether the requested resolution action is permitted")
    action: str = Field(..., description="Target action evaluated")
    risk_level: str = Field(..., description="Evaluated risk: low, medium, high")
    requires_approval: bool = Field(..., description="Whether human approval is required before execution")
    reason: str = Field(..., description="Policy decision explanation")
    applicable_conditions: Dict[str, Any] = Field(default_factory=dict)
    matched_policy_id: Optional[uuid.UUID] = None
