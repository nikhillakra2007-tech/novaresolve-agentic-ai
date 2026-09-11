import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.order import Order
    from backend.app.db.models.case import Case


class Cancellation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cancellations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'completed', 'failed', 'rejected')",
            name="chk_cancellation_status",
        ),
        Index("idx_cancellations_order_id", "order_id"),
        Index("idx_cancellations_case_id", "case_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="cancellations")
    case: Mapped["Case"] = relationship("Case", back_populates="cancellations")
