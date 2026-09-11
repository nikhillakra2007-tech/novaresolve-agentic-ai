import uuid
import logging
from typing import Optional, Any, Dict, List
from sqlalchemy.orm import Session

from agents.state.models import AgentState, AgentObservation
from agents.tools.base import ToolResultStatus
from backend.app.services.case_service import CaseService
from backend.app.db.models.agent_event import AgentEvent

logger = logging.getLogger("nova.agents.state_manager")


class StateManager:
    """Manages the lifecycle, transitions, evidence ingestion, and persistence of AgentState."""

    @staticmethod
    def initialize_state(db: Session, case_id: uuid.UUID) -> AgentState:
        """Loads a case from the database and initializes a fresh AgentState context."""
        case = CaseService.get_case_by_id(db, case_id)

        has_approval = db.query(AgentEvent).filter(
            AgentEvent.case_id == case.id,
            AgentEvent.event_type == "APPROVAL_GRANTED",
        ).first()

        approval_status = "approved" if has_approval else (
            "pending" if case.requires_approval and case.status == "awaiting_approval" else "not_required"
        )

        # Initialize base state from persisted case
        state = AgentState(
            case_id=case.id,
            customer_id=case.customer_id,
            order_id=case.order_id,
            customer_goal=case.customer_goal,
            issue_type=case.issue_type,
            current_status=case.status,
            current_plan=case.current_plan if isinstance(case.current_plan, list) else [],
            current_step=case.current_step,
            risk_level=case.risk_level,
            requires_approval=case.requires_approval,
            approval_status=approval_status,
            resolution_type=case.resolution_type,
            resolution_status=case.resolution_status,
        )
        return state

    @staticmethod
    def ingest_observation(state: AgentState, observation: AgentObservation) -> None:
        """Ingests a tool execution observation into runtime state, memory, and structured evidence."""
        state.observations.append(observation)
        state.last_tool = observation.tool_name
        state.last_result = {
            "status": observation.status.value,
            "message": observation.message,
            "data": observation.data,
        }

        # Track tool usage frequency
        count = state.same_tool_counts.get(observation.tool_name, 0)
        state.same_tool_counts[observation.tool_name] = count + 1

        state.tool_history.append(
            {
                "tool_name": observation.tool_name,
                "status": observation.status.value,
                "timestamp": observation.timestamp.isoformat(),
            }
        )

        # Update evidence based on tool observations
        if observation.data:
            if observation.tool_name == "search_alternative_inventory":
                alternatives = observation.data.get("alternatives", [])
                state.evidence["alternative_inventory"] = alternatives
            elif observation.status == ToolResultStatus.SUCCESS:
                if observation.tool_name == "get_customer":
                    state.evidence["customer"] = observation.data
                elif observation.tool_name == "get_order":
                    state.evidence["order"] = observation.data
                elif observation.tool_name == "get_shipment":
                    state.evidence["shipment"] = observation.data
                elif observation.tool_name == "check_inventory":
                    inv_data = observation.data
                    prod_id = inv_data.get("product_id")
                    wh_id = inv_data.get("warehouse_id")
                    if prod_id and wh_id:
                        key = f"{prod_id}_{wh_id}"
                        state.evidence["inventory"][key] = inv_data
                    elif prod_id:
                        state.evidence["inventory"][str(prod_id)] = inv_data

        # Policy evaluations
        if observation.tool_name == "evaluate_policy" and observation.data:
            state.evidence["policy"] = observation.data
            p_data = observation.data
            if "risk_level" in p_data and p_data["risk_level"]:
                state.risk_level = p_data["risk_level"]
            if "requires_approval" in p_data:
                if state.approval_status != "approved":
                    state.requires_approval = bool(p_data["requires_approval"])
                    if state.requires_approval:
                        state.approval_status = "pending"

        # Action execution outcomes
        if observation.tool_name == "create_refund":
            state.resolution_type = "refund"
            if observation.status == ToolResultStatus.SUCCESS and observation.data:
                state.resolution_status = observation.data.get("status", "completed")
                if observation.data.get("requires_approval"):
                    state.requires_approval = True
                    state.approval_status = "pending"
            elif observation.status == ToolResultStatus.APPROVAL_REQUIRED:
                state.resolution_status = "pending"
                state.requires_approval = True
                state.approval_status = "pending"
            else:
                state.resolution_status = "failed"
                state.failure_reason = observation.message

        elif observation.tool_name == "create_replacement":
            state.resolution_type = "replacement"
            if observation.status == ToolResultStatus.SUCCESS and observation.data:
                state.resolution_status = observation.data.get("status", "processing")
            elif observation.status == ToolResultStatus.APPROVAL_REQUIRED:
                state.resolution_status = "pending"
                state.requires_approval = True
                state.approval_status = "pending"
            else:
                state.resolution_status = "failed"
                state.failure_reason = observation.message

        elif observation.tool_name == "cancel_order":
            state.resolution_type = "cancellation"
            if observation.status == ToolResultStatus.SUCCESS and observation.data:
                state.resolution_status = "completed"
            else:
                state.resolution_status = "failed"
                state.failure_reason = observation.message

        # Verification outcome
        if observation.tool_name == "verify_resolution":
            if observation.status == ToolResultStatus.SUCCESS:
                state.verification_status = "verified"
            elif observation.status == ToolResultStatus.APPROVAL_REQUIRED:
                state.verification_status = "awaiting_approval"
                state.requires_approval = True
                state.approval_status = "pending"
            else:
                state.verification_status = "unverified"
                state.failure_reason = observation.message

    @staticmethod
    def persist_state(db: Session, state: AgentState) -> None:
        """Persists allowed state fields into the database Case entity."""
        updates: Dict[str, Any] = {
            "status": state.current_status,
            "current_plan": state.current_plan,
            "current_step": state.current_step,
            "resolution_type": state.resolution_type,
            "resolution_status": state.resolution_status,
            "risk_level": state.risk_level,
            "requires_approval": state.requires_approval,
        }
        CaseService.persist_case_state(db, state.case_id, updates)

    @staticmethod
    def record_event(
        db: Session,
        state: AgentState,
        event_type: str,
        tool_name: Optional[str] = None,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        status: str = "success",
        message: Optional[str] = None,
    ) -> None:
        """Logs an observable audit event into the database for case execution tracing."""
        CaseService.log_agent_event(
            db=db,
            case_id=state.case_id,
            event_type=event_type,
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            status=status,
            message=message,
        )
