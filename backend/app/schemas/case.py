import uuid
from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    issue_type: str
    customer_goal: str
    status: str
    risk_level: str
    current_plan: Optional[Any] = None
    current_step: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_status: Optional[str] = None
    requires_approval: bool = False
    created_at: datetime
    updated_at: datetime


class CaseStateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Forbids arbitrary fields

    status: Optional[str] = Field(
        None,
        description="Case lifecycle status: open, investigating, planning, awaiting_approval, executing, verifying, replanning, resolved, escalated, failed",
    )
    current_plan: Optional[Any] = Field(None, description="Serialized execution plan steps")
    current_step: Optional[str] = Field(None, description="Current step in plan execution")
    resolution_type: Optional[str] = Field(None, description="Type of resolution: refund, replacement, cancellation")
    resolution_status: Optional[str] = Field(None, description="Resolution status: completed, pending, processing, failed")
    risk_level: Optional[str] = Field(None, description="Risk level: low, medium, high")
    requires_approval: Optional[bool] = Field(None, description="Whether resolution requires human approval")


class AgentEventCreateRequest(BaseModel):
    case_id: uuid.UUID
    event_type: str = Field(..., min_length=2, description="Type of event: tool_call, state_transition, error, etc.")
    tool_name: Optional[str] = Field(None, description="Name of executed tool if applicable")
    input_data: Optional[Any] = Field(None, description="Sanitized input payload")
    output_data: Optional[Any] = Field(None, description="Sanitized output payload")
    status: str = Field("success", description="Status of the event: success, failed, blocked")
    message: Optional[str] = Field(None, description="Descriptive event message")


class AgentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    event_type: str
    tool_name: Optional[str] = None
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    status: str
    message: Optional[str] = None
    created_at: datetime


class VerificationResponse(BaseModel):
    verified: bool = Field(..., description="Whether the resolution state is valid and consistent")
    case_id: uuid.UUID
    resolution_type: Optional[str] = None
    expected_state: Optional[Dict[str, Any]] = None
    observed_state: Optional[Dict[str, Any]] = None
    message: str
