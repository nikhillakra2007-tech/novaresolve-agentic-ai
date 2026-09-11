import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.schemas.case import CaseStateUpdateRequest
from backend.app.services.case_service import CaseService
from backend.app.services.verification_service import VerificationService


# --- Get Case State ---
class GetCaseStateInput(BaseModel):
    case_id: uuid.UUID = Field(..., description="Unique case UUID")


class CaseStateData(BaseModel):
    case_id: uuid.UUID
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


class GetCaseStateTool(BaseTool):
    name = "get_case_state"
    description = (
        "Retrieve current state, plan, progress step, and resolution status for a specific case ID."
    )
    category = "observation"
    input_schema = GetCaseStateInput
    output_schema = CaseStateData

    def _run(self, context: ToolContext, params: GetCaseStateInput) -> ToolResult:
        case = CaseService.get_case_by_id(context.db, params.case_id)
        data = CaseStateData(
            case_id=case.id,
            customer_id=case.customer_id,
            order_id=case.order_id,
            issue_type=case.issue_type,
            customer_goal=case.customer_goal,
            status=case.status,
            risk_level=case.risk_level,
            current_plan=case.current_plan,
            current_step=case.current_step,
            resolution_type=case.resolution_type,
            resolution_status=case.resolution_status,
            requires_approval=case.requires_approval,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Retrieved state for case '{case.id}' in status '{case.status}'.",
        )


# --- Persist Case State ---
class PersistCaseStateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: uuid.UUID = Field(..., description="Case UUID to update")
    status: Optional[str] = Field(None, description="Updated case status")
    current_plan: Optional[Any] = Field(None, description="Serialized plan representation")
    current_step: Optional[str] = Field(None, description="Current execution step")
    resolution_type: Optional[str] = Field(None, description="Resolution type: refund, replacement, cancellation")
    resolution_status: Optional[str] = Field(None, description="Resolution status")
    risk_level: Optional[str] = Field(None, description="Assessed risk level: low, medium, high")
    requires_approval: Optional[bool] = Field(None, description="Approval flag")


class PersistCaseStateTool(BaseTool):
    name = "persist_case_state"
    description = (
        "Safely update allowed state fields for a case (status, current_plan, current_step, "
        "resolution_type, resolution_status, risk_level, requires_approval). "
        "Cannot modify customer_id, order_id, or internal database metadata."
    )
    category = "case_support"
    input_schema = PersistCaseStateInput
    output_schema = CaseStateData

    def _run(self, context: ToolContext, params: PersistCaseStateInput) -> ToolResult:
        update_req = CaseStateUpdateRequest(
            status=params.status,
            current_plan=params.current_plan,
            current_step=params.current_step,
            resolution_type=params.resolution_type,
            resolution_status=params.resolution_status,
            risk_level=params.risk_level,
            requires_approval=params.requires_approval,
        )
        case = CaseService.persist_case_state(
            db=context.db,
            case_id=params.case_id,
            updates=update_req,
        )
        data = CaseStateData(
            case_id=case.id,
            customer_id=case.customer_id,
            order_id=case.order_id,
            issue_type=case.issue_type,
            customer_goal=case.customer_goal,
            status=case.status,
            risk_level=case.risk_level,
            current_plan=case.current_plan,
            current_step=case.current_step,
            resolution_type=case.resolution_type,
            resolution_status=case.resolution_status,
            requires_approval=case.requires_approval,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Persisted updated state for case '{case.id}'.",
        )


# --- Log Agent Event ---
class LogAgentEventInput(BaseModel):
    case_id: uuid.UUID = Field(..., description="Target case UUID")
    event_type: str = Field(..., min_length=2, description="Event category: tool_call, state_transition, etc.")
    tool_name: Optional[str] = Field(None, description="Optional tool name")
    input_data: Optional[Any] = Field(None, description="Input payload")
    output_data: Optional[Any] = Field(None, description="Output payload")
    status: str = Field("success", description="Status outcome: success, failed, blocked")
    message: Optional[str] = Field(None, description="Summary event message")


class AgentEventData(BaseModel):
    event_id: uuid.UUID
    case_id: uuid.UUID
    event_type: str
    tool_name: Optional[str] = None
    status: str
    message: Optional[str] = None
    created_at: datetime


class LogAgentEventTool(BaseTool):
    name = "log_agent_event"
    description = (
        "Record an observable audit event in the database for case progression, tool execution, or state transition."
    )
    category = "case_support"
    input_schema = LogAgentEventInput
    output_schema = AgentEventData

    def _run(self, context: ToolContext, params: LogAgentEventInput) -> ToolResult:
        event = CaseService.log_agent_event(
            db=context.db,
            case_id=params.case_id,
            event_type=params.event_type,
            tool_name=params.tool_name,
            input_data=params.input_data,
            output_data=params.output_data,
            status=params.status,
            message=params.message,
        )
        data = AgentEventData(
            event_id=event.id,
            case_id=event.case_id,
            event_type=event.event_type,
            tool_name=event.tool_name,
            status=event.status,
            message=event.message,
            created_at=event.created_at,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Logged agent event '{event.event_type}' for case '{event.case_id}'.",
        )


# --- Verify Resolution ---
class VerifyResolutionInput(BaseModel):
    case_id: uuid.UUID = Field(..., description="Target case UUID to verify")


class VerificationData(BaseModel):
    verified: bool
    case_id: uuid.UUID
    resolution_type: Optional[str] = None
    expected_state: Optional[Dict[str, Any]] = None
    observed_state: Optional[Dict[str, Any]] = None
    message: str


class VerifyResolutionTool(BaseTool):
    name = "verify_resolution"
    description = (
        "Verify that the executed resolution for a case is consistent across case records, "
        "resolution entities (refund/replacement/cancellation), orders, and inventory."
    )
    category = "case_support"
    input_schema = VerifyResolutionInput
    output_schema = VerificationData

    def _run(self, context: ToolContext, params: VerifyResolutionInput) -> ToolResult:
        ver_resp = VerificationService.verify_resolution(context.db, params.case_id)
        data = VerificationData(
            verified=ver_resp.verified,
            case_id=ver_resp.case_id,
            resolution_type=ver_resp.resolution_type,
            expected_state=ver_resp.expected_state,
            observed_state=ver_resp.observed_state,
            message=ver_resp.message,
        )
        if ver_resp.verified:
            status = ToolResultStatus.SUCCESS
        elif ver_resp.observed_state and ver_resp.observed_state.get("is_pending_approval"):
            status = ToolResultStatus.APPROVAL_REQUIRED
        else:
            status = ToolResultStatus.BLOCKED

        return ToolResult(
            success=ver_resp.verified,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=status,
            message=ver_resp.message,
        )


get_case_state = GetCaseStateTool()
persist_case_state = PersistCaseStateTool()
log_agent_event = LogAgentEventTool()
verify_resolution = VerifyResolutionTool()
