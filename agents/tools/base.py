import uuid
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Any, Dict, Type, Union
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import (
    ResourceNotFoundError,
    CustomerBlockedError,
    CustomerInactiveError,
    BusinessRuleViolationError,
    InsufficientInventoryError,
    PolicyDenialError,
    OrderStateConflictError,
    DomainError,
)

logger = logging.getLogger("nova.agents.tools")


class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    POLICY_DENIED = "policy_denied"
    INSUFFICIENT_INVENTORY = "insufficient_inventory"
    DUPLICATE = "duplicate"
    APPROVAL_REQUIRED = "approval_required"
    CONFLICT = "conflict"
    CUSTOMER_BLOCKED = "customer_blocked"
    CUSTOMER_INACTIVE = "customer_inactive"


class ToolError(BaseModel):
    error_type: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    tool_name: str
    data: Optional[Any] = None
    error: Optional[ToolError] = None
    status: ToolResultStatus
    message: str


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: Session
    case_id: Optional[uuid.UUID] = None


class BaseTool(ABC):
    name: str
    description: str
    category: str = "general"
    input_schema: Type[BaseModel]
    output_schema: Optional[Type[BaseModel]] = None

    def execute(
        self,
        context: ToolContext,
        params: Union[BaseModel, Dict[str, Any], None] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes the tool with typed schema validation and domain exception handling."""
        # 1. Parse and validate inputs
        try:
            if params is None:
                validated_params = self.input_schema(**kwargs)
            elif isinstance(params, dict):
                merged = {**params, **kwargs}
                validated_params = self.input_schema(**merged)
            elif isinstance(params, self.input_schema):
                validated_params = params
            else:
                validated_params = self.input_schema(**params.model_dump())
        except ValidationError as ve:
            error_details = [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in ve.errors()]
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.INVALID,
                message=f"Validation failed for tool '{self.name}': {ve.errors()[0]['msg'] if ve.errors() else 'Invalid parameters'}",
                error=ToolError(
                    error_type="ValidationError",
                    message=str(ve),
                    details={"validation_errors": error_details},
                ),
            )
        except Exception as ex:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.INVALID,
                message=f"Parameter parsing error for tool '{self.name}': {str(ex)}",
                error=ToolError(error_type=type(ex).__name__, message=str(ex)),
            )

        # 2. Run the tool execution
        try:
            return self._run(context, validated_params)
        except ResourceNotFoundError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.NOT_FOUND,
                message=e.message,
                error=ToolError(error_type="ResourceNotFoundError", message=e.message, details=e.details),
            )
        except PolicyDenialError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.POLICY_DENIED,
                message=e.message,
                error=ToolError(error_type="PolicyDenialError", message=e.message, details=e.details),
            )
        except InsufficientInventoryError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.INSUFFICIENT_INVENTORY,
                message=e.message,
                error=ToolError(error_type="InsufficientInventoryError", message=e.message, details=e.details),
            )
        except OrderStateConflictError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.CONFLICT,
                message=e.message,
                error=ToolError(error_type="OrderStateConflictError", message=e.message, details=e.details),
            )
        except CustomerBlockedError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.CUSTOMER_BLOCKED,
                message=e.message,
                error=ToolError(error_type="CustomerBlockedError", message=e.message, details=e.details),
            )
        except CustomerInactiveError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.CUSTOMER_INACTIVE,
                message=e.message,
                error=ToolError(error_type="CustomerInactiveError", message=e.message, details=e.details),
            )
        except BusinessRuleViolationError as e:
            # Distinguish duplicate resolution violations
            is_dup = "already" in e.message.lower() or "duplicate" in e.message.lower()
            status = ToolResultStatus.DUPLICATE if is_dup else ToolResultStatus.INVALID
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=status,
                message=e.message,
                error=ToolError(error_type="BusinessRuleViolationError", message=e.message, details=e.details),
            )
        except DomainError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.FAILED,
                message=e.message,
                error=ToolError(error_type=type(e).__name__, message=e.message, details=e.details),
            )
        except Exception as ex:
            logger.exception(f"Unexpected error executing tool '{self.name}'")
            return ToolResult(
                success=False,
                tool_name=self.name,
                status=ToolResultStatus.FAILED,
                message=f"An unexpected internal error occurred while executing tool '{self.name}'.",
                error=ToolError(
                    error_type="InternalError",
                    message="Internal error occurred. Diagnostic details logged securely.",
                ),
            )

    @abstractmethod
    def _run(self, context: ToolContext, params: Any) -> ToolResult:
        """Internal execution method implemented by subclasses."""
        pass

    def get_json_schema(self) -> Dict[str, Any]:
        """Returns JSON schema representation of the tool contract for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.input_schema.model_json_schema(),
        }
