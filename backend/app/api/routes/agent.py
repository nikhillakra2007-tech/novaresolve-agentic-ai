import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models.agent_event import AgentEvent
from agents.runtime.agent import NovaResolveAgent
from agents.state.models import AgentRunResult

logger = logging.getLogger("nova.api.agent")

router = APIRouter(prefix="/agent", tags=["agent-runtime"])


class AgentRunRequest(BaseModel):
    case_id: uuid.UUID = Field(..., description="Target case ID for the autonomous agent to resolve")


class AgentResumeRequest(BaseModel):
    case_id: uuid.UUID = Field(..., description="Target case ID currently in awaiting_approval status")
    approved: bool = Field(True, description="True if human supervisor approved the action, False to reject")
    reviewer_notes: Optional[str] = Field(None, description="Optional supervisor notes")


class AgentRunResponse(BaseModel):
    success: bool
    case_id: uuid.UUID
    status: str
    resolution_status: Optional[str] = None
    requires_approval: bool
    current_step: Optional[str] = None
    final_outcome: str
    reason: Optional[str] = None
    steps_executed: int
    replans: int
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/run", response_model=AgentRunResponse, summary="Execute Autonomous Agent")
def run_agent(req: AgentRunRequest, db: Session = Depends(get_db)):
    """Triggers the autonomous agent runtime on a customer case."""
    try:
        result: AgentRunResult = NovaResolveAgent.run(db=db, case_id=req.case_id)
        return AgentRunResponse(**result.model_dump())
    except Exception as exc:
        logger.exception(f"Error running agent on case '{req.case_id}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution encountered an internal error: {str(exc)}",
        )


@router.post("/resume", response_model=AgentRunResponse, summary="Resume Approved Case")
def resume_agent(req: AgentResumeRequest, db: Session = Depends(get_db)):
    """Resumes an awaiting_approval case after human supervisor review."""
    try:
        result: AgentRunResult = NovaResolveAgent.resume(
            db=db,
            case_id=req.case_id,
            approved=req.approved,
            reviewer_notes=req.reviewer_notes,
        )
        return AgentRunResponse(**result.model_dump())
    except Exception as exc:
        logger.exception(f"Error resuming agent on case '{req.case_id}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming case execution: {str(exc)}",
        )


@router.get("/case/{case_id}/trace", summary="Get Case Execution Trace")
def get_case_trace(case_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieves full audit event execution trace for a case."""
    events = (
        db.query(AgentEvent)
        .filter(AgentEvent.case_id == case_id)
        .order_by(AgentEvent.created_at.asc())
        .all()
    )
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "tool_name": e.tool_name,
            "status": e.status,
            "message": e.message,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
