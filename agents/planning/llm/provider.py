import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from pydantic import ValidationError

from agents.state.models import AgentState, AgentAction
from agents.tools.base import BaseTool
from agents.tools.registry import ToolRegistry
from agents.tools import TOOL_REGISTRY
from agents.planning.decision_provider import DecisionProvider
from agents.planning.llm.client import GeminiClient, LLMClientError
from agents.planning.llm.prompts import (
    SYSTEM_INSTRUCTIONS,
    build_llm_state_context,
    format_tools_for_prompt,
)

logger = logging.getLogger("nova.agents.planning.llm.provider")


class LLMDecisionProvider(DecisionProvider):
    """LLM-driven decision provider that uses Google Gemini to reason over
    case evidence and select controlled tool actions.
    """

    name: str = "llm"
    provider_type: str = "gemini"

    # Strict list of prohibited keywords to block unauthorized execution attempts
    PROHIBITED_ACTIONS = {
        "raw_sql",
        "execute_sql",
        "query_database",
        "exec",
        "eval",
        "shell",
        "bash",
        "python",
        "exec_python",
    }

    def __init__(
        self,
        client: Optional[GeminiClient] = None,
        fallback_provider: Optional[DecisionProvider] = None,
        fallback_on_error: bool = True,
    ) -> None:
        self.client = client or GeminiClient()
        self.fallback_provider = fallback_provider
        self.fallback_on_error = fallback_on_error

    def decide(
        self,
        state: AgentState,
        tools: List[BaseTool],
        db: Optional[Session] = None,
    ) -> Optional[AgentAction]:
        """Decides the next AgentAction by providing state context and tool definitions to the LLM."""
        # 1. Immediate exit for terminal or paused states
        if state.verification_status == "verified" or state.current_status in {"resolved", "escalated", "failed"}:
            return None
        if state.requires_approval and state.current_status == "awaiting_approval":
            return None

        # 2. Build controlled, sanitized state context and tool schemas
        state_context = build_llm_state_context(state)
        tool_schemas = [tool.get_json_schema() for tool in tools] if tools else TOOL_REGISTRY.get_schemas()

        # Build Gemini function declarations from schemas
        tool_declarations = []
        try:
            from google.genai import types
            for s in tool_schemas:
                tool_declarations.append(
                    types.FunctionDeclaration(
                        name=s["name"],
                        description=s["description"],
                        parameters=s["parameters"],
                    )
                )
        except Exception:
            tool_declarations = None

        user_prompt = (
            "CURRENT AUTHORITATIVE CASE STATE:\n"
            f"{json.dumps(state_context, indent=2)}\n\n"
            "AVAILABLE CONTROLLED TOOLS (Registry Schema):\n"
            f"{format_tools_for_prompt(tool_schemas)}\n\n"
            "Based strictly on the authoritative evidence and rules, select the next single tool action to execute, "
            "or set action to null if the case is finished or cannot be resolved safely."
        )

        decision_data: Optional[Dict[str, Any]] = None

        # 3. Call LLM Client with error isolation
        try:
            if not self.client or not self.client.is_available():
                raise LLMClientError("Gemini client is not available or API key is missing.")

            logger.debug(f"Invoking Gemini LLM decision provider for case '{state.case_id}'")
            decision_data = self.client.generate_decision(
                system_instruction=SYSTEM_INSTRUCTIONS,
                user_prompt=user_prompt,
                tool_declarations=tool_declarations,
            )
        except Exception as ex:
            logger.warning(f"LLM decision provider error for case '{state.case_id}': {str(ex)}")
            if self.fallback_on_error and self.fallback_provider:
                logger.info(f"Falling back to {self.fallback_provider.name} decision provider for case '{state.case_id}'")
                fallback_action = self.fallback_provider.decide(state, tools, db)
                if fallback_action:
                    fallback_action.source = "deterministic_fallback"
                return fallback_action
            else:
                # No fallback configured: record failure on state
                state.failure_reason = f"LLM decision failure: {str(ex)}"
                return None

        # 4. Parse structured response
        action_name = decision_data.get("action")
        arguments = decision_data.get("arguments", {})
        rationale = decision_data.get("reason", "LLM-selected action.")
        expected_outcome = decision_data.get("expected_outcome", "Tool execution observation.")

        # 5. Handle null / empty action
        if not action_name or str(action_name).lower() in {"null", "none"}:
            logger.info(f"LLM indicated no further tool action required for case '{state.case_id}'.")
            return None

        action_name = str(action_name).strip()

        # 6. Prohibited tool check
        if (
            action_name.lower() in self.PROHIBITED_ACTIONS
            or action_name.lower().startswith(("exec_", "eval_"))
            or any(p in action_name.lower() for p in ["raw_sql", "query_database", "shell"])
        ):
            logger.error(f"Security Alert: LLM attempted to invoke prohibited capability '{action_name}'. Blocking action.")
            state.failure_reason = f"Security violation: LLM selected prohibited tool '{action_name}'."
            return None

        # 7. Tool Registry validation (only authorized tools can be called)
        if action_name not in TOOL_REGISTRY.list_tool_names():
            logger.error(f"LLM requested unregistered tool '{action_name}'. Blocking execution.")
            state.failure_reason = f"LLM requested unknown/unregistered tool '{action_name}'."
            return None

        # 8. Schema validation using the registered tool's input_schema
        tool = TOOL_REGISTRY.get(action_name)
        try:
            if not isinstance(arguments, dict):
                arguments = {}
            # Validate through Pydantic input schema
            tool.input_schema(**arguments)
        except ValidationError as ve:
            logger.error(f"LLM arguments failed schema validation for tool '{action_name}': {str(ve)}")
            state.failure_reason = f"LLM arguments failed schema validation for '{action_name}': {ve.errors()[0]['msg'] if ve.errors() else str(ve)}"
            return None
        except Exception as ex:
            logger.error(f"Parameter validation error for tool '{action_name}': {str(ex)}")
            state.failure_reason = f"Parameter validation error for '{action_name}': {str(ex)}"
            return None

        # 9. Build and return validated AgentAction
        return AgentAction(
            tool_name=action_name,
            parameters=arguments,
            rationale=rationale,
            expected_outcome=expected_outcome,
            source="llm",
        )
