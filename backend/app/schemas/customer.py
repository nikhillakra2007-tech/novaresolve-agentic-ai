import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Unique customer email")
    phone: Optional[str] = Field(None, description="Contact phone number")
    status: str = Field(..., description="Customer account status: active, blocked, inactive")
    is_blocked: bool = Field(False, description="True if customer is restricted from initiating resolutions")
    is_active: bool = Field(True, description="True if customer status is active")
    created_at: datetime
