import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.order import Order
    from backend.app.db.models.case import Case
    from backend.app.db.models.product import Product
    from backend.app.db.models.warehouse import Warehouse


class Replacement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "replacements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'processing', 'shipped', 'completed', 'failed', 'rejected')",
            name="chk_replacement_status",
        ),
        CheckConstraint("quantity > 0", name="chk_replacement_quantity_positive"),
        Index("idx_replacements_order_id", "order_id"),
        Index("idx_replacements_case_id", "case_id"),
        Index("idx_replacements_product_id", "product_id"),
        Index("idx_replacements_warehouse_id", "warehouse_id"),
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
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="replacements")
    case: Mapped["Case"] = relationship("Case", back_populates="replacements")
    product: Mapped["Product"] = relationship("Product", back_populates="replacements")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="replacements")
