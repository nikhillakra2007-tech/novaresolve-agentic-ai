import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.services.order_service import OrderService


class GetOrderInput(BaseModel):
    order_id: uuid.UUID = Field(..., description="Unique order UUID")
    customer_id: Optional[uuid.UUID] = Field(
        None, description="Optional customer UUID to verify order ownership"
    )


class OrderItemData(BaseModel):
    item_id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_item_price: Decimal


class OrderData(BaseModel):
    order_id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    total_amount: Decimal
    order_date: datetime
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    shipping_address: str
    items: List[OrderItemData] = Field(default_factory=list)


class GetOrderTool(BaseTool):
    name = "get_order"
    description = (
        "Retrieve order details including line items, shipping address, status, and delivery dates. "
        "Optionally verifies customer ownership when customer_id is provided."
    )
    category = "observation"
    input_schema = GetOrderInput
    output_schema = OrderData

    def _run(self, context: ToolContext, params: GetOrderInput) -> ToolResult:
        order = OrderService.get_order_by_id(
            db=context.db,
            order_id=params.order_id,
            customer_id=params.customer_id,
        )
        items_data = []
        for item in order.items:
            items_data.append(
                OrderItemData(
                    item_id=item.id,
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else None,
                    product_sku=item.product.sku if item.product else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_item_price=item.total_item_price,
                )
            )

        data = OrderData(
            order_id=order.id,
            customer_id=order.customer_id,
            status=order.status,
            total_amount=order.total_amount,
            order_date=order.order_date,
            expected_delivery=order.expected_delivery,
            actual_delivery=order.actual_delivery,
            shipping_address=order.shipping_address,
            items=items_data,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Retrieved order '{order.id}' in status '{order.status}'.",
        )


get_order = GetOrderTool()
