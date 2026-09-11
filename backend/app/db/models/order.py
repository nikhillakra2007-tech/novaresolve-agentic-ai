import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Numeric, Integer, Text, DateTime, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.db.models.customer import Customer
    from backend.app.db.models.product import Product
    from backend.app.db.models.shipment import Shipment
    from backend.app.db.models.case import Case
    from backend.app.db.models.refund import Refund
    from backend.app.db.models.replacement import Replacement
    from backend.app.db.models.cancellation import Cancellation


class Order(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('placed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded', 'replacement_pending', 'replacement_sent')",
            name="chk_order_status",
        ),
        CheckConstraint("total_amount >= 0", name="chk_order_total_amount_non_negative"),
        Index("idx_orders_customer_id", "customer_id"),
        Index("idx_orders_status", "status"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), default="placed", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
    expected_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    shipments: Mapped[List["Shipment"]] = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="order",
    )
    refunds: Mapped[List["Refund"]] = relationship(
        "Refund",
        back_populates="order",
    )
    replacements: Mapped[List["Replacement"]] = relationship(
        "Replacement",
        back_populates="order",
    )
    cancellations: Mapped[List["Cancellation"]] = relationship(
        "Cancellation",
        back_populates="order",
    )


class OrderItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="chk_order_item_unit_price_non_negative"),
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

    @property
    def total_item_price(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price

    @property
    def product_name(self) -> Optional[str]:
        return self.product.name if self.product else None

    @property
    def product_sku(self) -> Optional[str]:
        return self.product.sku if self.product else None

