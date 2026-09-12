import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("nova.agents.planning.llm.client")


class LLMClientError(Exception):
    """Exception raised for LLM client communication or configuration errors."""
    pass


class GeminiClient:
    """Client for Google Gemini API handling authentication, request creation,
    structured JSON retrieval, timeout, and error isolation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        timeout_seconds: int = 15,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Google GenAI client: %s", str(e))
                self._client = None

    def is_available(self) -> bool:
        """Returns True if the client is properly configured with an API key and client instance."""
        return bool(self.api_key and self._client)

    def generate_decision(
        self,
        system_instruction: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Sends the structured decision request to the Gemini model and returns parsed JSON.
        Catches API errors and timeouts without leaking credentials.
        """
        if not self.is_available():
            raise LLMClientError("Gemini API key is not configured or client failed to initialize.")

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1,  # Low temperature for deterministic/controlled decision making
            )

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config,
            )

            if not response or not response.text:
                raise LLMClientError("Received empty response from Gemini model.")

            raw_text = response.text.strip()
            # Handle potential markdown code fences in model output
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            data = json.loads(raw_text)
            if not isinstance(data, dict):
                raise LLMClientError(f"Expected JSON object from model, got {type(data).__name__}")

            return data

        except json.JSONDecodeError as jde:
            logger.error("Failed to parse JSON from LLM response: %s", str(jde))
            raise LLMClientError(f"Malformed JSON response from model: {str(jde)}") from jde
        except Exception as ex:
            # Mask any potential API key in error string
            err_msg = str(ex)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
            logger.error("Error communicating with Gemini API: %s", err_msg)
            raise LLMClientError(f"Gemini API error: {err_msg}") from ex
