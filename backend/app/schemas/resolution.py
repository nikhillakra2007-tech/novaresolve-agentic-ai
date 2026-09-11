import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Refunds ---
class RefundCreateRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="ID of the order to refund")
    amount: Decimal = Field(..., gt=0, description="Refund amount in USD")
    reason: str = Field(..., min_length=3, description="Justification for the refund")
    case_id: Optional[uuid.UUID] = Field(None, description="Optional ID of the associated case")


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    reason: str
    status: str
    requires_approval: bool
    case_id: Optional[uuid.UUID] = None
    approved_by: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None


# --- Replacements ---
class ReplacementCreateRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="ID of the order")
    product_id: uuid.UUID = Field(..., description="ID of the product to replace")
    warehouse_id: uuid.UUID = Field(..., description="Target warehouse to dispatch replacement from")
    quantity: int = Field(1, gt=0, description="Quantity of items to replace")
    reason: str = Field(..., min_length=3, description="Reason for replacement")
    case_id: Optional[uuid.UUID] = Field(None, description="Optional ID of the associated case")


class ReplacementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reason: str
    status: str
    requires_approval: bool
    case_id: Optional[uuid.UUID] = None
    created_at: datetime


# --- Cancellations ---
class CancellationCreateRequest(BaseModel):
    order_id: uuid.UUID = Field(..., description="ID of the order to cancel")
    reason: str = Field(..., min_length=3, description="Reason for cancellation")
    case_id: Optional[uuid.UUID] = Field(None, description="Optional ID of the associated case")


class CancellationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    reason: str
    status: str
    requires_approval: bool
    case_id: Optional[uuid.UUID] = None
    created_at: datetime
