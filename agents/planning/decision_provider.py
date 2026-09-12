from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from agents.state.models import AgentState, AgentAction
from agents.tools.base import BaseTool


class DecisionProvider(ABC):
    """Abstract interface for agent decision making."""

    name: str = "base"
    provider_type: str = "base"

    @abstractmethod
    def decide(
        self,
        state: AgentState,
        tools: List[BaseTool],
        db: Optional[Session] = None,
    ) -> Optional[AgentAction]:
        """Examines the current agent state and returns the next AgentAction to execute,
        or None if no action is warranted / goal is terminal.
        """
        pass


class DecisionProviderFactory:
    """Factory to instantiate the configured DecisionProvider."""

    @classmethod
    def get_default_provider(cls) -> DecisionProvider:
        """Instantiates default decision provider based on system configuration."""
        from backend.app.core.config import settings
        from agents.planning.deterministic_provider import DeterministicDecisionProvider
        from agents.planning.llm.provider import LLMDecisionProvider
        from agents.planning.llm.client import GeminiClient

        # If LLM provider is requested and configured
        if settings.LLM_PROVIDER.lower() == "gemini":
            fallback = (
                DeterministicDecisionProvider()
                if settings.LLM_FALLBACK_TO_DETERMINISTIC
                else None
            )
            client = GeminiClient(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.LLM_MODEL,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            )
            return LLMDecisionProvider(
                client=client,
                fallback_provider=fallback,
                fallback_on_error=settings.LLM_FALLBACK_TO_DETERMINISTIC,
            )

        return DeterministicDecisionProvider()
