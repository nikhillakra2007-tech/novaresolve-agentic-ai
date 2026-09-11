import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.db.models.case import Case
from backend.app.db.models.order import Order
from backend.app.db.models.refund import Refund
from backend.app.db.models.replacement import Replacement
from backend.app.db.models.cancellation import Cancellation
from backend.app.db.models.inventory import Inventory
from backend.app.schemas.case import VerificationResponse
from backend.app.services.case_service import CaseService


class VerificationService:
    @staticmethod
    def verify_resolution(db: Session, case_id: uuid.UUID) -> VerificationResponse:
        """Independently verifies whether the case's intended resolution was successfully reflected in the database."""
        case = CaseService.get_case_by_id(db, case_id)

        if not case.resolution_type:
            return VerificationResponse(
                verified=False,
                case_id=case.id,
                resolution_type=None,
                expected_state={"resolution_type": "refund | replacement | cancellation"},
                observed_state={"resolution_type": None, "case_status": case.status},
                message="Case does not have an active or attempted resolution to verify.",
            )

        res_type = case.resolution_type.lower()

        if res_type == "refund":
            refunds = db.query(Refund).filter(Refund.case_id == case.id).all()
            if not refunds:
                return VerificationResponse(
                    verified=False,
                    case_id=case.id,
                    resolution_type="refund",
                    expected_state={"refund_record_exists": True},
                    observed_state={"refund_record_exists": False},
                    message="No refund record found associated with this case.",
                )

            refund = refunds[-1]
            order = db.query(Order).filter(Order.id == refund.order_id).first()

            if refund.status == "completed":
                is_verified = True
                msg = f"Refund of ${refund.amount} verified in completed status."
            elif refund.status == "pending" and refund.requires_approval:
                is_verified = True
                msg = f"Refund of ${refund.amount} verified in pending approval status."
            else:
                is_verified = False
                msg = f"Refund status '{refund.status}' does not represent a valid verified state."

            return VerificationResponse(
                verified=is_verified,
                case_id=case.id,
                resolution_type="refund",
                expected_state={"status": "completed or pending approval", "amount": str(refund.amount)},
                observed_state={
                    "refund_status": refund.status,
                    "requires_approval": refund.requires_approval,
                    "order_status": order.status if order else None,
                },
                message=msg,
            )

        if res_type == "replacement":
            replacements = db.query(Replacement).filter(Replacement.case_id == case.id).all()
            if not replacements:
                return VerificationResponse(
                    verified=False,
                    case_id=case.id,
                    resolution_type="replacement",
                    expected_state={"replacement_record_exists": True},
                    observed_state={"replacement_record_exists": False},
                    message="No replacement record found associated with this case.",
                )

            replacement = replacements[-1]
            order = db.query(Order).filter(Order.id == replacement.order_id).first()
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == replacement.product_id,
                    Inventory.warehouse_id == replacement.warehouse_id,
                )
                .first()
            )

            reserved = inventory.reserved_quantity if inventory else 0
            is_verified = (
                replacement.status in ["processing", "completed"]
                and reserved >= replacement.quantity
                and order is not None
                and order.status == "replacement_pending"
            )

            return VerificationResponse(
                verified=is_verified,
                case_id=case.id,
                resolution_type="replacement",
                expected_state={
                    "replacement_status": "processing",
                    "quantity": replacement.quantity,
                    "order_status": "replacement_pending",
                },
                observed_state={
                    "replacement_status": replacement.status,
                    "quantity": replacement.quantity,
                    "warehouse_reserved_quantity": reserved,
                    "order_status": order.status if order else None,
                },
                message="Replacement resolution verified successfully."
                if is_verified
                else "Replacement state mismatch observed in order or inventory.",
            )

        if res_type == "cancellation":
            cancellations = db.query(Cancellation).filter(Cancellation.case_id == case.id).all()
            if not cancellations:
                return VerificationResponse(
                    verified=False,
                    case_id=case.id,
                    resolution_type="cancellation",
                    expected_state={"cancellation_record_exists": True},
                    observed_state={"cancellation_record_exists": False},
                    message="No cancellation record found associated with this case.",
                )

            cancellation = cancellations[-1]
            order = db.query(Order).filter(Order.id == cancellation.order_id).first()
            is_verified = (
                cancellation.status == "approved"
                and order is not None
                and order.status == "cancelled"
            )

            return VerificationResponse(
                verified=is_verified,
                case_id=case.id,
                resolution_type="cancellation",
                expected_state={"cancellation_status": "approved", "order_status": "cancelled"},
                observed_state={
                    "cancellation_status": cancellation.status,
                    "order_status": order.status if order else None,
                },
                message="Cancellation resolution verified successfully."
                if is_verified
                else "Cancellation state mismatch observed.",
            )

        return VerificationResponse(
            verified=False,
            case_id=case.id,
            resolution_type=case.resolution_type,
            expected_state={},
            observed_state={},
            message=f"Unsupported resolution type '{case.resolution_type}'.",
        )
