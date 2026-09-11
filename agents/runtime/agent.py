import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session

from agents.state.models import AgentRunResult
from agents.state.manager import StateManager
from agents.runtime.loop import AgentLoop
from backend.app.services.case_service import CaseService
from backend.app.db.models.refund import Refund
from backend.app.db.models.replacement import Replacement
from backend.app.db.models.case import Case

logger = logging.getLogger("nova.agents.runtime")


class NovaResolveAgent:
    """Primary entrypoint for autonomous customer case resolution."""

    @classmethod
    def run(cls, db: Session, case_id: uuid.UUID) -> AgentRunResult:
        """Executes the autonomous agent loop on the designated case."""
        logger.info(f"NovaResolveAgent received execution request for case '{case_id}'")
        state = StateManager.initialize_state(db=db, case_id=case_id)
        return AgentLoop.run(db=db, state=state)

    @classmethod
    def resume(
        cls,
        db: Session,
        case_id: uuid.UUID,
        approved: bool = True,
        reviewer_notes: Optional[str] = None,
    ) -> AgentRunResult:
        """Resumes an awaiting_approval case following human supervisor decision."""
        logger.info(f"NovaResolveAgent received resume request for case '{case_id}' (approved={approved})")
        case = CaseService.get_case_by_id(db, case_id)

        if not approved:
            # Supervisor rejected the resolution
            case.status = "escalated"
            case.resolution_status = "rejected"
            db.commit()

            CaseService.log_agent_event(
                db=db,
                case_id=case_id,
                event_type="APPROVAL_REJECTED",
                status="rejected",
                message=f"Supervisor rejected pending action: {reviewer_notes or 'Approval denied.'}",
            )

            return AgentRunResult(
                success=False,
                case_id=case_id,
                status="escalated",
                resolution_status="rejected",
                requires_approval=False,
                current_step="human_approval",
                final_outcome=f"Resolution was rejected by supervisor: {reviewer_notes or 'Approval denied.'}",
                reason=reviewer_notes or "Approval rejected.",
            )

        # Supervisor approved the resolution!
        CaseService.log_agent_event(
            db=db,
            case_id=case_id,
            event_type="APPROVAL_GRANTED",
            status="approved",
            message=f"Supervisor granted approval: {reviewer_notes or 'Resolution approved.'}",
        )

        # If a pending refund exists for this case, promote it to completed
        pending_refund = db.query(Refund).filter(Refund.case_id == case_id, Refund.status == "pending").first()
        if pending_refund:
            pending_refund.status = "completed"
            pending_refund.requires_approval = False
            db.commit()

        # Update case to executing and clear requires_approval gate
        case.status = "executing"
        case.resolution_status = "completed"
        case.requires_approval = False
        db.commit()

        # Resume agent loop to verify the approved resolution state
        state = StateManager.initialize_state(db=db, case_id=case_id)
        state.approval_status = "approved"
        state.requires_approval = False
        state.resolution_status = "completed"
        return AgentLoop.run(db=db, state=state)
