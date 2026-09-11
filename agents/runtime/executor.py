import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict

from agents.state.models import AgentAction, AgentObservation
from agents.tools.base import ToolContext, ToolResult, ToolResultStatus
from agents.tools.registry import TOOL_REGISTRY

logger = logging.getLogger("nova.agents.executor")


class ToolExecutor:
    """Executes planned AgentActions securely through the Phase 3 Tool Registry."""

    @staticmethod
    def execute(action: AgentAction, context: ToolContext) -> AgentObservation:
        """Invokes the target tool via TOOL_REGISTRY and transforms the result into a typed observation."""
        logger.info(f"Executing tool '{action.tool_name}' with parameters: {action.parameters}")

        try:
            tool_result: ToolResult = TOOL_REGISTRY.execute(
                name=action.tool_name,
                context=context,
                params=action.parameters,
            )

            observation = AgentObservation(
                tool_name=action.tool_name,
                status=tool_result.status,
                data=tool_result.data,
                message=tool_result.message,
                timestamp=datetime.now(timezone.utc),
            )
            return observation

        except Exception as exc:
            logger.exception(f"Unexpected error executing action '{action.tool_name}'")
            return AgentObservation(
                tool_name=action.tool_name,
                status=ToolResultStatus.FAILED,
                data=None,
                message=f"Execution error invoking tool '{action.tool_name}': {str(exc)}",
                timestamp=datetime.now(timezone.utc),
            )
