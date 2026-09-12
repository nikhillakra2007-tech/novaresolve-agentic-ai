import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from agents.state.models import AgentState, AgentAction
from agents.tools.base import BaseTool
from agents.planning.decision_provider import DecisionProvider
from agents.planning.planner import AgentPlanner

logger = logging.getLogger("nova.agents.planning.deterministic")


class DeterministicDecisionProvider(DecisionProvider):
    """Deterministic, rule-based decision provider delegating to AgentPlanner."""

    name: str = "deterministic"
    provider_type: str = "deterministic"

    def decide(
        self,
        state: AgentState,
        tools: List[BaseTool],
        db: Optional[Session] = None,
    ) -> Optional[AgentAction]:
        """Generates the next action using deterministic state rules."""
        logger.debug(f"DeterministicDecisionProvider evaluating state for case '{state.case_id}'")
        action = AgentPlanner.select_action(state)
        return action
