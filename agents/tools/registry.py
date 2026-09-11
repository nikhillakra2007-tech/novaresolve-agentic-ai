import logging
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus, ToolError
from agents.tools.customer_tools import get_customer
from agents.tools.order_tools import get_order
from agents.tools.shipment_tools import get_shipment
from agents.tools.inventory_tools import check_inventory, search_alternative_inventory
from agents.tools.policy_tools import evaluate_policy
from agents.tools.resolution_tools import create_refund, create_replacement, cancel_order
from agents.tools.case_tools import (
    get_case_state,
    persist_case_state,
    log_agent_event,
    verify_resolution,
)

logger = logging.getLogger("nova.agents.registry")


class ToolRegistry:
    """Central registry of approved, typed agent tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Registers the 13 authorized Phase 3 tools."""
        default_tools = [
            # Observation
            get_customer,
            get_order,
            get_shipment,
            check_inventory,
            search_alternative_inventory,
            get_case_state,
            # Decision
            evaluate_policy,
            # State-Changing Actions
            create_refund,
            create_replacement,
            cancel_order,
            # Case / Event / Verification Support
            persist_case_state,
            log_agent_event,
            verify_resolution,
        ]
        for tool in default_tools:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Registers a tool ensuring unique, deterministic names and approved base class."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Registered tool must inherit from BaseTool, got '{type(tool)}'.")
        if not tool.name or not isinstance(tool.name, str):
            raise ValueError("Tool must have a non-empty string name.")
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieves an authorized tool by name or raises KeyError."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in the tool registry.")
        return self._tools[name]

    def list_tools(self) -> List[BaseTool]:
        """Returns list of all authorized tools."""
        return list(self._tools.values())

    def list_tool_names(self) -> List[str]:
        """Returns sorted list of tool names."""
        return sorted(list(self._tools.keys()))

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schemas for all registered tools formatted for LLM tool calling."""
        return [tool.get_json_schema() for tool in self._tools.values()]

    def execute(
        self,
        name: str,
        context: ToolContext,
        params: Union[BaseModel, Dict[str, Any], None] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes a registered tool securely. Rejects unregistered or arbitrary execution."""
        # 1. Reject arbitrary SQL / Python / bash execution patterns
        prohibited = {"raw_sql", "execute_sql", "eval", "exec", "query_database", "shell"}
        if name in prohibited or any(p in name.lower() for p in prohibited):
            return ToolResult(
                success=False,
                tool_name=name,
                status=ToolResultStatus.INVALID,
                message=f"Execution of arbitrary or dangerous capability '{name}' is strictly prohibited.",
                error=ToolError(error_type="SecurityViolation", message="Prohibited capability requested."),
            )

        if name not in self._tools:
            return ToolResult(
                success=False,
                tool_name=name,
                status=ToolResultStatus.NOT_FOUND,
                message=f"Tool '{name}' is not recognized or authorized.",
                error=ToolError(
                    error_type="ToolNotFoundError",
                    message=f"No tool registered under name '{name}'. Available: {self.list_tool_names()}",
                ),
            )

        tool = self._tools[name]
        return tool.execute(context=context, params=params, **kwargs)


# Global singleton instance
TOOL_REGISTRY = ToolRegistry()


def get_tool(name: str) -> BaseTool:
    return TOOL_REGISTRY.get(name)


def list_tools() -> List[BaseTool]:
    return TOOL_REGISTRY.list_tools()


def execute_tool(
    name: str,
    context: ToolContext,
    params: Union[BaseModel, Dict[str, Any], None] = None,
    **kwargs: Any,
) -> ToolResult:
    return TOOL_REGISTRY.execute(name, context=context, params=params, **kwargs)
