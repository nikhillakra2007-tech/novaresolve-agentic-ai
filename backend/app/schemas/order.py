import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    total_item_price: Decimal = Field(..., ge=0)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    total_amount: Decimal = Field(..., ge=0)
    order_date: datetime
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    shipping_address: str
    items: List[OrderItemResponse] = Field(default_factory=list)
