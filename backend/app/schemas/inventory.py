import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warehouse_id: uuid.UUID
    warehouse_name: str
    warehouse_status: str
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    quantity: int = Field(..., ge=0)
    reserved_quantity: int = Field(..., ge=0)
    available_quantity: int = Field(..., ge=0, description="Computed as quantity - reserved_quantity")
    updated_at: datetime


class WarehouseInventoryOption(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    location: str
    warehouse_status: str
    available_quantity: int = Field(..., ge=0)


class AlternativeInventoryResponse(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    required_quantity: int
    alternatives: List[WarehouseInventoryOption] = Field(
        default_factory=list,
        description="Available alternative active warehouses with sufficient stock",
    )
