import uuid
from typing import Optional, Any, Dict, Union
from sqlalchemy.orm import Session

from backend.app.db.models.case import Case
from backend.app.db.models.agent_event import AgentEvent
from backend.app.schemas.case import CaseStateUpdateRequest
from backend.app.core.exceptions import ResourceNotFoundError, BusinessRuleViolationError

ALLOWED_CASE_STATUSES = {
    "open",
    "investigating",
    "planning",
    "awaiting_approval",
    "executing",
    "verifying",
    "replanning",
    "resolved",
    "escalated",
    "failed",
}

ALLOWED_RISK_LEVELS = {"low", "medium", "high"}

ALLOWED_UPDATE_FIELDS = {
    "status",
    "current_plan",
    "current_step",
    "resolution_type",
    "resolution_status",
    "risk_level",
    "requires_approval",
}


class CaseService:
    @staticmethod
    def get_case_by_id(db: Session, case_id: uuid.UUID) -> Case:
        """Retrieves a case by ID or raises ResourceNotFoundError."""
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ResourceNotFoundError(f"Case with ID '{case_id}' was not found.")
        return case

    @staticmethod
    def persist_case_state(
        db: Session,
        case_id: uuid.UUID,
        updates: Union[CaseStateUpdateRequest, Dict[str, Any]],
    ) -> Case:
        """Safely updates allowed lifecycle and plan fields for a case."""
        case = CaseService.get_case_by_id(db, case_id)

        if isinstance(updates, CaseStateUpdateRequest):
            data = updates.model_dump(exclude_unset=True)
        elif isinstance(updates, dict):
            # Guard against attempting to update forbidden or arbitrary fields
            invalid_keys = set(updates.keys()) - ALLOWED_UPDATE_FIELDS
            if invalid_keys:
                raise BusinessRuleViolationError(
                    f"Cannot update arbitrary case fields: {sorted(list(invalid_keys))}. "
                    f"Allowed fields are: {sorted(list(ALLOWED_UPDATE_FIELDS))}."
                )
            data = {k: v for k, v in updates.items() if k in ALLOWED_UPDATE_FIELDS and v is not None}
        else:
            raise BusinessRuleViolationError("Updates must be a CaseStateUpdateRequest or dict.")

        if "status" in data and data["status"] is not None:
            status_val = str(data["status"]).lower()
            if status_val not in ALLOWED_CASE_STATUSES:
                raise BusinessRuleViolationError(
                    f"Invalid case status '{data['status']}'. Must be one of: {sorted(list(ALLOWED_CASE_STATUSES))}."
                )
            case.status = status_val

        if "risk_level" in data and data["risk_level"] is not None:
            risk_val = str(data["risk_level"]).lower()
            if risk_val not in ALLOWED_RISK_LEVELS:
                raise BusinessRuleViolationError(
                    f"Invalid risk level '{data['risk_level']}'. Must be one of: {sorted(list(ALLOWED_RISK_LEVELS))}."
                )
            case.risk_level = risk_val

        if "current_plan" in data:
            case.current_plan = data["current_plan"]

        if "current_step" in data:
            case.current_step = data["current_step"]

        if "resolution_type" in data:
            case.resolution_type = data["resolution_type"]

        if "resolution_status" in data:
            case.resolution_status = data["resolution_status"]

        if "requires_approval" in data and data["requires_approval"] is not None:
            case.requires_approval = bool(data["requires_approval"])

        db.commit()
        db.refresh(case)
        return case

    @staticmethod
    def log_agent_event(
        db: Session,
        case_id: uuid.UUID,
        event_type: str,
        tool_name: Optional[str] = None,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        status: str = "success",
        message: Optional[str] = None,
    ) -> AgentEvent:
        """Persists an observable audit event in the database for case tracing."""
        # Verify case exists
        case = CaseService.get_case_by_id(db, case_id)

        # Sanitize sensitive fields if present
        sanitized_input = CaseService._sanitize_payload(input_data)
        sanitized_output = CaseService._sanitize_payload(output_data)

        event = AgentEvent(
            case_id=case.id,
            event_type=event_type,
            tool_name=tool_name,
            input_data=sanitized_input,
            output_data=sanitized_output,
            status=status,
            message=message,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def _sanitize_payload(payload: Any) -> Any:
        """Redacts sensitive credentials or tokens from audit logs."""
        if not isinstance(payload, dict):
            return payload

        redacted = {}
        sensitive_keys = {"password", "secret", "token", "api_key", "auth", "credential"}
        for k, v in payload.items():
            if any(sens in str(k).lower() for sens in sensitive_keys):
                redacted[k] = "[REDACTED]"
            elif isinstance(v, dict):
                redacted[k] = CaseService._sanitize_payload(v)
            else:
                redacted[k] = v
        return redacted
