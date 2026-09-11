import uuid
from typing import Optional, List
from pydantic import BaseModel, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.services.inventory_service import InventoryService


# --- Check Inventory ---
class CheckInventoryInput(BaseModel):
    product_id: uuid.UUID = Field(..., description="Unique product UUID")
    warehouse_id: uuid.UUID = Field(..., description="Unique warehouse UUID")


class InventoryData(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    warehouse_name: str
    warehouse_status: str
    quantity: int
    reserved_quantity: int
    available_quantity: int


class CheckInventoryTool(BaseTool):
    name = "check_inventory"
    description = (
        "Check available inventory for a specific product at a specific warehouse. "
        "Returns quantity, reserved quantity, and available quantity. "
        "This tool does not select alternative warehouses or modify inventory."
    )
    category = "observation"
    input_schema = CheckInventoryInput
    output_schema = InventoryData

    def _run(self, context: ToolContext, params: CheckInventoryInput) -> ToolResult:
        inv_resp = InventoryService.check_inventory(
            db=context.db,
            product_id=params.product_id,
            warehouse_id=params.warehouse_id,
        )
        data = InventoryData(
            product_id=inv_resp.product_id,
            warehouse_id=inv_resp.warehouse_id,
            warehouse_name=inv_resp.warehouse_name,
            warehouse_status=inv_resp.warehouse_status,
            quantity=inv_resp.quantity,
            reserved_quantity=inv_resp.reserved_quantity,
            available_quantity=inv_resp.available_quantity,
        )
        msg = (
            f"Available: {inv_resp.available_quantity} units of SKU '{inv_resp.product_sku}' "
            f"at warehouse '{inv_resp.warehouse_name}'."
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=msg,
        )


# --- Search Alternative Inventory ---
class SearchAlternativeInventoryInput(BaseModel):
    product_id: uuid.UUID = Field(..., description="Product UUID to find stock for")
    required_quantity: int = Field(
        1, gt=0, description="Minimum available units required (default: 1)"
    )
    exclude_warehouse_id: Optional[uuid.UUID] = Field(
        None, description="Optional warehouse UUID to exclude (e.g. depleted warehouse)"
    )


class WarehouseAlternativeData(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    location: str
    warehouse_status: str
    available_quantity: int


class AlternativeInventoryData(BaseModel):
    product_id: uuid.UUID
    product_sku: Optional[str] = None
    required_quantity: int
    alternatives: List[WarehouseAlternativeData] = Field(default_factory=list)


class SearchAlternativeInventoryTool(BaseTool):
    name = "search_alternative_inventory"
    description = (
        "Discover active alternative warehouses containing sufficient available stock for a product, "
        "optionally excluding a depleted warehouse. Does not make automatic routing decisions."
    )
    category = "observation"
    input_schema = SearchAlternativeInventoryInput
    output_schema = AlternativeInventoryData

    def _run(self, context: ToolContext, params: SearchAlternativeInventoryInput) -> ToolResult:
        alt_resp = InventoryService.search_alternative_inventory(
            db=context.db,
            product_id=params.product_id,
            required_quantity=params.required_quantity,
            exclude_warehouse_id=params.exclude_warehouse_id,
        )
        alternatives = [
            WarehouseAlternativeData(
                warehouse_id=alt.warehouse_id,
                warehouse_name=alt.warehouse_name,
                location=alt.location,
                warehouse_status=alt.warehouse_status,
                available_quantity=alt.available_quantity,
            )
            for alt in alt_resp.alternatives
        ]
        data = AlternativeInventoryData(
            product_id=alt_resp.product_id,
            product_sku=alt_resp.product_sku,
            required_quantity=alt_resp.required_quantity,
            alternatives=alternatives,
        )
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=f"Found {len(alternatives)} alternative warehouse(s) with >= {params.required_quantity} units available.",
        )


check_inventory = CheckInventoryTool()
search_alternative_inventory = SearchAlternativeInventoryTool()
