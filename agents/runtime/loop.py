import uuid
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from agents.state.models import AgentState, AgentAction, AgentObservation, AgentRunResult
from agents.state.manager import StateManager
from agents.planning.planner import AgentPlanner
from agents.replanning.replanner import AgentReplanner
from agents.risk.evaluator import RiskEvaluator
from agents.runtime.executor import ToolExecutor
from agents.tools.base import ToolContext, ToolResultStatus
from agents.tools import TOOL_REGISTRY
from agents.planning.decision_provider import DecisionProvider, DecisionProviderFactory

logger = logging.getLogger("nova.agents.loop")


class AgentLoop:
    """Bounded, safe, autonomous agent execution loop."""

    MAX_AGENT_STEPS = 20
    MAX_REPLANS = 3
    MAX_SAME_TOOL_ATTEMPTS = 3

    @classmethod
    def run(
        cls,
        db: Session,
        state: AgentState,
        decision_provider: Optional[DecisionProvider] = None,
    ) -> AgentRunResult:
        """Executes the autonomous loop until terminal resolution, approval gate, or safe escalation."""
        logger.info(f"Starting agent loop for case '{state.case_id}' (Goal: '{state.customer_goal}')")

        if decision_provider is None:
            decision_provider = DecisionProviderFactory.get_default_provider()

        context = ToolContext(db=db, case_id=state.case_id)

        # 1. Initial Goal Identification event if not already emitted
        if not state.tool_history:
            StateManager.record_event(
                db=db,
                state=state,
                event_type="GOAL_IDENTIFIED",
                message=f"Agent initialized to pursue customer goal: '{state.customer_goal}'",
            )
            state.current_status = "investigating"
            StateManager.persist_state(db, state)

        # Execution trace collector
        trace: List[Dict[str, Any]] = []

        while True:
            state.attempt_count += 1

            # -------------------------------------------------------------
            # 2. Safety Bounds Checks
            # -------------------------------------------------------------
            if state.attempt_count > cls.MAX_AGENT_STEPS:
                logger.warning(f"Exceeded max steps ({cls.MAX_AGENT_STEPS}) for case '{state.case_id}'")
                state.current_status = "escalated"
                state.failure_reason = f"Execution exceeded maximum step limit ({cls.MAX_AGENT_STEPS})."
                StateManager.record_event(
                    db=db,
                    state=state,
                    event_type="ESCALATED",
                    status="escalated",
                    message=state.failure_reason,
                )
                StateManager.persist_state(db, state)
                break

            # Check if already resolved
            if state.verification_status == "verified" or state.current_status == "resolved":
                state.current_status = "resolved"
                state.resolution_status = "completed"
                StateManager.persist_state(db, state)
                break

            # -------------------------------------------------------------
            # 3. Action Selection (Planner or Replanner)
            # -------------------------------------------------------------
            action: Optional[AgentAction] = None

            # Check if previous observation was an unhandled constraint/failure
            last_obs = state.observations[-1] if state.observations else None
            needs_replan = False

            if last_obs and last_obs.status != ToolResultStatus.SUCCESS:
                if last_obs.status == ToolResultStatus.APPROVAL_REQUIRED:
                    # Approval gate triggered
                    state.current_status = "awaiting_approval"
                    state.requires_approval = True
                    state.approval_status = "pending"
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="APPROVAL_REQUIRED",
                        tool_name=last_obs.tool_name,
                        status="approval_required",
                        message=last_obs.message,
                    )
                    StateManager.persist_state(db, state)
                    break

                if AgentReplanner.can_replan(state, last_obs):
                    needs_replan = True
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="CONSTRAINT_DETECTED",
                        tool_name=last_obs.tool_name,
                        status=last_obs.status.value,
                        message=f"Constraint detected: {last_obs.message}",
                    )
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="REPLAN_STARTED",
                        message=f"Initiating replanning adaptation #{state.replan_count + 1}.",
                    )
                    state.current_status = "replanning"
                    StateManager.persist_state(db, state)

                    action = AgentReplanner.replan(state, last_obs)
                    if action:
                        StateManager.record_event(
                            db=db,
                            state=state,
                            event_type="REPLAN_COMPLETED",
                            tool_name=action.tool_name,
                            message=f"Adapted plan: {action.rationale}",
                        )
                    else:
                        logger.warning("Replanner found no valid alternative action. Escalating case.")
                        state.current_status = "escalated"
                        state.failure_reason = f"Cannot adapt plan after constraint on '{last_obs.tool_name}': {last_obs.message}"
                        StateManager.record_event(
                            db=db,
                            state=state,
                            event_type="ESCALATED",
                            status="escalated",
                            message=state.failure_reason,
                        )
                        StateManager.persist_state(db, state)
                        break

            if not action:
                # Regular planned action selection via DecisionProvider
                is_llm = getattr(decision_provider, "name", "") == "llm"
                if is_llm:
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="LLM_DECISION_STARTED",
                        message=f"Invoking LLM decision provider for case '{state.case_id}'",
                    )

                action = decision_provider.decide(state, tools=TOOL_REGISTRY.list_tools(), db=db)

                if action and is_llm:
                    decision_source = getattr(action, "source", "llm")
                    event_type = "LLM_FALLBACK_USED" if decision_source == "deterministic_fallback" else "LLM_DECISION_COMPLETED"
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type=event_type,
                        tool_name=action.tool_name,
                        message=f"Decision provider selected '{action.tool_name}' (source={decision_source}): {action.rationale}",
                    )
                elif not action and is_llm and state.failure_reason:
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="LLM_DECISION_FAILED",
                        status="failed",
                        message=state.failure_reason,
                    )

            if not action:
                # No further action available
                if state.verification_status == "verified":
                    state.current_status = "resolved"
                    state.resolution_status = "completed"
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="RESOLVED",
                        message="Case successfully resolved and verified.",
                    )
                    StateManager.persist_state(db, state)
                elif state.requires_approval and state.current_status == "awaiting_approval":
                    # Paused for approval
                    break
                else:
                    logger.warning("Planner produced no action and resolution not verified. Escalating case.")
                    state.current_status = "escalated"
                    state.failure_reason = state.failure_reason or "No valid autonomous action could be determined."
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="ESCALATED",
                        status="escalated",
                        message=state.failure_reason,
                    )
                    StateManager.persist_state(db, state)
                break

            # -------------------------------------------------------------
            # 4. Repeated Tool Safeguard Check
            # -------------------------------------------------------------
            curr_count = state.same_tool_counts.get(action.tool_name, 0)
            if curr_count >= cls.MAX_SAME_TOOL_ATTEMPTS:
                logger.warning(f"Tool '{action.tool_name}' exceeded max attempts limit ({cls.MAX_SAME_TOOL_ATTEMPTS})")
                state.current_status = "escalated"
                state.failure_reason = f"Loop protection: Tool '{action.tool_name}' exceeded maximum attempts ({cls.MAX_SAME_TOOL_ATTEMPTS})."
                StateManager.record_event(
                    db=db,
                    state=state,
                    event_type="ESCALATED",
                    status="escalated",
                    message=state.failure_reason,
                )
                StateManager.persist_state(db, state)
                break

            # -------------------------------------------------------------
            # 4b. Pre-Execution Consequential Action Risk & Approval Gate
            # -------------------------------------------------------------
            consequential_actions = {"create_refund", "create_replacement", "cancel_order"}
            if action.tool_name in consequential_actions:
                if RiskEvaluator.should_require_approval(state):
                    logger.info(f"Consequential action '{action.tool_name}' requires supervisor approval. Halting execution.")
                    state.current_status = "awaiting_approval"
                    state.requires_approval = True
                    state.approval_status = "pending"
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="APPROVAL_REQUIRED",
                        tool_name=action.tool_name,
                        status="approval_required",
                        message=f"Action '{action.tool_name}' requires supervisor approval before execution.",
                    )
                    StateManager.persist_state(db, state)
                    break

            # -------------------------------------------------------------
            # 5. Execute Action
            # -------------------------------------------------------------
            state.current_step = action.tool_name
            trace_entry = {
                "step": state.attempt_count,
                "tool_name": action.tool_name,
                "rationale": action.rationale,
                "source": getattr(action, "source", "deterministic"),
                "parameters": {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in action.parameters.items()},
            }

            # Map specific lifecycle step events
            step_event_type = cls._map_step_event_type(action.tool_name)
            StateManager.record_event(
                db=db,
                state=state,
                event_type=step_event_type,
                tool_name=action.tool_name,
                input_data=action.parameters,
                message=action.rationale,
            )

            observation = ToolExecutor.execute(action, context)
            StateManager.ingest_observation(state, observation)

            trace_entry["observation_status"] = observation.status.value
            trace_entry["observation_message"] = observation.message
            trace.append(trace_entry)

            # Persist intermediate case state
            StateManager.persist_state(db, state)

            # -------------------------------------------------------------
            # 6. Post-Execution Checks (Approval & Verification)
            # -------------------------------------------------------------
            # Check approval gate
            if observation.status == ToolResultStatus.APPROVAL_REQUIRED:
                state.current_status = "awaiting_approval"
                state.requires_approval = True
                state.approval_status = "pending"
                StateManager.record_event(
                    db=db,
                    state=state,
                    event_type="APPROVAL_REQUIRED",
                    tool_name=action.tool_name,
                    status="approval_required",
                    message=observation.message,
                )
                StateManager.persist_state(db, state)
                break

            # Check verification outcome
            if action.tool_name == "verify_resolution":
                if observation.status == ToolResultStatus.SUCCESS:
                    state.current_status = "resolved"
                    state.resolution_status = "completed"
                    state.verification_status = "verified"
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="VERIFICATION_SUCCESS",
                        tool_name=action.tool_name,
                        message="Deterministic independent state verification passed.",
                    )
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="RESOLVED",
                        message=f"Case resolved successfully: {observation.message}",
                    )
                    StateManager.persist_state(db, state)
                    break
                elif observation.status == ToolResultStatus.APPROVAL_REQUIRED:
                    state.current_status = "awaiting_approval"
                    state.requires_approval = True
                    state.approval_status = "pending"
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="APPROVAL_REQUIRED",
                        tool_name=action.tool_name,
                        status="approval_required",
                        message="Action awaiting human supervisor approval.",
                    )
                    StateManager.persist_state(db, state)
                    break
                else:
                    StateManager.record_event(
                        db=db,
                        state=state,
                        event_type="VERIFICATION_FAILED",
                        tool_name=action.tool_name,
                        status="failed",
                        message=f"Verification failed: {observation.message}",
                    )

        # -------------------------------------------------------------
        # 7. Construct Final AgentRunResult
        # -------------------------------------------------------------
        success = state.current_status == "resolved"
        if success:
            final_outcome = f"Customer issue successfully resolved and verified via {state.resolution_type}."
        elif state.current_status == "awaiting_approval":
            final_outcome = f"Resolution staged ({state.resolution_type}) and paused awaiting supervisor approval."
        elif state.current_status == "escalated":
            final_outcome = f"Case escalated to customer support: {state.failure_reason or 'autonomous resolution blocked.'}"
        else:
            final_outcome = f"Case ended in state '{state.current_status}'."

        return AgentRunResult(
            success=success,
            case_id=state.case_id,
            status=state.current_status,
            resolution_status=state.resolution_status,
            requires_approval=state.requires_approval,
            current_step=state.current_step,
            final_outcome=final_outcome,
            reason=state.failure_reason,
            steps_executed=state.attempt_count,
            replans=state.replan_count,
            execution_trace=trace,
        )

    @staticmethod
    def _map_step_event_type(tool_name: str) -> str:
        """Maps specific tool executions to observable agent audit event types."""
        mapping = {
            "get_customer": "CUSTOMER_LOOKUP",
            "get_order": "ORDER_LOOKUP",
            "get_shipment": "SHIPMENT_LOOKUP",
            "check_inventory": "INVENTORY_CHECK",
            "search_alternative_inventory": "INVENTORY_CHECK",
            "evaluate_policy": "POLICY_CHECK",
            "create_refund": "ACTION_EXECUTED",
            "create_replacement": "ACTION_EXECUTED",
            "cancel_order": "ACTION_EXECUTED",
            "verify_resolution": "VERIFICATION_STARTED",
        }
        return mapping.get(tool_name, "TOOL_CALL")
