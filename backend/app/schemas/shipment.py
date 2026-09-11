import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    tracking_number: str
    carrier: str
    status: str
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    is_delayed: bool = Field(False, description="True if status is delayed or overdue")
