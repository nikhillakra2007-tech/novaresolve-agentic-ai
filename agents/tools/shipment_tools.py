import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.services.shipment_service import ShipmentService


class GetShipmentInput(BaseModel):
    order_id: uuid.UUID = Field(..., description="Order UUID to lookup shipment for")


class ShipmentData(BaseModel):
    shipment_id: uuid.UUID
    order_id: uuid.UUID
    tracking_number: str
    carrier: str
    status: str
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    is_delayed: bool = False


class GetShipmentTool(BaseTool):
    name = "get_shipment"
    description = (
        "Retrieve shipment tracking information, carrier, and fulfillment delivery status for a specific order ID."
    )
    category = "observation"
    input_schema = GetShipmentInput
    output_schema = ShipmentData

    def _run(self, context: ToolContext, params: GetShipmentInput) -> ToolResult:
        shipment = ShipmentService.get_shipment_by_order_id(context.db, params.order_id)
        is_delayed = shipment.status in ["delayed"] or (
            shipment.estimated_delivery is not None
            and shipment.actual_delivery is None
            and datetime.now(shipment.estimated_delivery.tzinfo) > shipment.estimated_delivery
        )
        data = ShipmentData(
            shipment_id=shipment.id,
            order_id=shipment.order_id,
            tracking_number=shipment.tracking_number,
            carrier=shipment.carrier,
            status=shipment.status,
            shipped_at=shipment.shipped_at,
            estimated_delivery=shipment.estimated_delivery,
            actual_delivery=shipment.actual_delivery,
            is_delayed=is_delayed,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Retrieved shipment '{shipment.tracking_number}' ({shipment.carrier}) in status '{shipment.status}'.",
        )


get_shipment = GetShipmentTool()
