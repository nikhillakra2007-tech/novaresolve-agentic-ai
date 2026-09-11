import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from agents.tools.base import BaseTool, ToolContext, ToolResult, ToolResultStatus
from backend.app.services.refund_service import RefundService
from backend.app.services.replacement_service import ReplacementService
from backend.app.services.cancellation_service import CancellationService
from backend.app.services.case_service import CaseService


# --- Refund Tool ---
class CreateRefundInput(BaseModel):
    order_id: uuid.UUID = Field(..., description="ID of the order to refund")
    amount: Decimal = Field(..., gt=0, description="Monetary amount in USD to refund")
    reason: str = Field(..., min_length=3, description="Customer issue explanation / reason")
    case_id: Optional[uuid.UUID] = Field(None, description="Optional associated case ID")


class RefundData(BaseModel):
    refund_id: uuid.UUID
    case_id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    reason: str
    status: str
    requires_approval: bool
    created_at: datetime
    processed_at: Optional[datetime] = None


class CreateRefundTool(BaseTool):
    name = "create_refund"
    description = (
        "Execute or stage a monetary refund for an order. Delegates to RefundService for policy evaluation, "
        "order locking, and balance validation. High-risk or large refunds enter pending approval state."
    )
    category = "action"
    input_schema = CreateRefundInput
    output_schema = RefundData

    def _run(self, context: ToolContext, params: CreateRefundInput) -> ToolResult:
        eff_case_id = params.case_id or context.case_id
        refund = RefundService.create_refund(
            db=context.db,
            order_id=params.order_id,
            amount=params.amount,
            reason=params.reason,
            case_id=eff_case_id,
        )

        data = RefundData(
            refund_id=refund.id,
            case_id=refund.case_id,
            order_id=refund.order_id,
            amount=refund.amount,
            reason=refund.reason,
            status=refund.status,
            requires_approval=refund.requires_approval,
            created_at=refund.created_at,
            processed_at=refund.processed_at,
        )

        if refund.requires_approval or refund.status == "pending":
            result_status = ToolResultStatus.APPROVAL_REQUIRED
            msg = f"Refund of ${refund.amount} staged for human approval (case: {refund.case_id})."
        else:
            result_status = ToolResultStatus.SUCCESS
            msg = f"Refund of ${refund.amount} completed successfully (case: {refund.case_id})."

        # Log audit event if case exists
        try:
            CaseService.log_agent_event(
                db=context.db,
                case_id=refund.case_id,
                event_type="refund_created",
                tool_name=self.name,
                input_data={"order_id": str(params.order_id), "amount": str(params.amount), "reason": params.reason},
                output_data={"refund_id": str(refund.id), "status": refund.status, "requires_approval": refund.requires_approval},
                status=result_status.value,
                message=msg,
            )
        except Exception:
            pass

        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=result_status,
            message=msg,
        )


# --- Replacement Tool ---
class CreateReplacementInput(BaseModel):
    order_id: uuid.UUID = Field(..., description="Original order UUID")
    product_id: uuid.UUID = Field(..., description="Product UUID to be replaced")
    warehouse_id: uuid.UUID = Field(..., description="Warehouse UUID to dispatch replacement from")
    quantity: int = Field(1, gt=0, description="Quantity of replacement units")
    reason: str = Field(..., min_length=3, description="Justification for replacement")
    case_id: Optional[uuid.UUID] = Field(None, description="Optional associated case ID")


class ReplacementData(BaseModel):
    replacement_id: uuid.UUID
    case_id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reason: str
    status: str
    requires_approval: bool
    created_at: datetime


class CreateReplacementTool(BaseTool):
    name = "create_replacement"
    description = (
        "Create a product replacement order from a specific warehouse. Delegates to ReplacementService "
        "to verify order items, evaluate replacement policy, and atomically reserve inventory. "
        "Does NOT auto-reroute warehouses."
    )
    category = "action"
    input_schema = CreateReplacementInput
    output_schema = ReplacementData

    def _run(self, context: ToolContext, params: CreateReplacementInput) -> ToolResult:
        eff_case_id = params.case_id or context.case_id
        replacement = ReplacementService.create_replacement(
            db=context.db,
            order_id=params.order_id,
            product_id=params.product_id,
            warehouse_id=params.warehouse_id,
            quantity=params.quantity,
            reason=params.reason,
            case_id=eff_case_id,
        )

        data = ReplacementData(
            replacement_id=replacement.id,
            case_id=replacement.case_id,
            order_id=replacement.order_id,
            product_id=replacement.product_id,
            warehouse_id=replacement.warehouse_id,
            quantity=replacement.quantity,
            reason=replacement.reason,
            status=replacement.status,
            requires_approval=replacement.requires_approval,
            created_at=replacement.created_at,
        )

        msg = (
            f"Replacement order created for {replacement.quantity} unit(s) "
            f"dispatched from warehouse '{replacement.warehouse_id}'."
        )

        try:
            CaseService.log_agent_event(
                db=context.db,
                case_id=replacement.case_id,
                event_type="replacement_created",
                tool_name=self.name,
                input_data={
                    "order_id": str(params.order_id),
                    "product_id": str(params.product_id),
                    "warehouse_id": str(params.warehouse_id),
                    "quantity": params.quantity,
                },
                output_data={"replacement_id": str(replacement.id), "status": replacement.status},
                status=ToolResultStatus.SUCCESS.value,
                message=msg,
            )
        except Exception:
            pass

        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=msg,
        )


# --- Cancellation Tool ---
class CancelOrderInput(BaseModel):
    order_id: uuid.UUID = Field(..., description="ID of the order to cancel")
    reason: str = Field(..., min_length=3, description="Cancellation reason")
    case_id: Optional[uuid.UUID] = Field(None, description="Optional associated case ID")


class CancellationData(BaseModel):
    cancellation_id: uuid.UUID
    case_id: uuid.UUID
    order_id: uuid.UUID
    reason: str
    status: str
    requires_approval: bool
    created_at: datetime


class CancelOrderTool(BaseTool):
    name = "cancel_order"
    description = (
        "Cancel an unshipped order. Delegates to CancellationService for cancellation policy evaluation, "
        "order status validation, and shipment conflict checks. Rejects already-shipped or in-transit orders."
    )
    category = "action"
    input_schema = CancelOrderInput
    output_schema = CancellationData

    def _run(self, context: ToolContext, params: CancelOrderInput) -> ToolResult:
        eff_case_id = params.case_id or context.case_id
        cancellation = CancellationService.cancel_order(
            db=context.db,
            order_id=params.order_id,
            reason=params.reason,
            case_id=eff_case_id,
        )

        data = CancellationData(
            cancellation_id=cancellation.id,
            case_id=cancellation.case_id,
            order_id=cancellation.order_id,
            reason=cancellation.reason,
            status=cancellation.status,
            requires_approval=cancellation.requires_approval,
            created_at=cancellation.created_at,
        )

        msg = f"Order '{cancellation.order_id}' successfully cancelled."

        try:
            CaseService.log_agent_event(
                db=context.db,
                case_id=cancellation.case_id,
                event_type="cancellation_created",
                tool_name=self.name,
                input_data={"order_id": str(params.order_id), "reason": params.reason},
                output_data={"cancellation_id": str(cancellation.id), "status": cancellation.status},
                status=ToolResultStatus.SUCCESS.value,
                message=msg,
            )
        except Exception:
            pass

        return ToolResult(
            success=True,
            tool_name=self.name,
            data=data.model_dump(mode="json"),
            status=ToolResultStatus.SUCCESS,
            message=msg,
        )


create_refund = CreateRefundTool()
create_replacement = CreateReplacementTool()
cancel_order = CancelOrderTool()
