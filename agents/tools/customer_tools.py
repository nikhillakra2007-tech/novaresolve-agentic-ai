import uuid
from typing import Optional
from pydantic import BaseModel, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.services.customer_service import CustomerService


class GetCustomerInput(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Unique customer UUID")


class CustomerData(BaseModel):
    customer_id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    status: str
    is_active: bool
    is_blocked: bool


class GetCustomerTool(BaseTool):
    name = "get_customer"
    description = (
        "Retrieve customer profile and account status by customer ID. "
        "Returns name, email, phone, status, and active/blocked flags. "
        "Does not expose internal database fields."
    )
    category = "observation"
    input_schema = GetCustomerInput
    output_schema = CustomerData

    def _run(self, context: ToolContext, params: GetCustomerInput) -> ToolResult:
        customer = CustomerService.get_customer_by_id(context.db, params.customer_id)
        data = CustomerData(
            customer_id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            status=customer.status,
            is_active=(customer.status == "active"),
            is_blocked=(customer.status == "blocked"),
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Retrieved profile for customer '{customer.name}'.",
        )


get_customer = GetCustomerTool()
