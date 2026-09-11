import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.db.models.order import Order


class Shipment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('label_created', 'in_transit', 'out_for_delivery', 'delivered', 'delayed', 'lost', 'returned')",
            name="chk_shipment_status",
        ),
        Index("idx_shipments_order_id", "order_id"),
        Index("idx_shipments_status", "status"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tracking_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    carrier: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="label_created", nullable=False)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="shipments")

    @property
    def is_delayed(self) -> bool:
        """Dynamically computes whether the shipment is delayed."""
        return self.status == "delayed"
