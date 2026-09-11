from typing import List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import String, Numeric, Boolean, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.order import OrderItem
    from backend.app.db.models.inventory import Inventory
    from backend.app.db.models.replacement import Replacement


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="chk_product_price_non_negative"),
        Index("idx_products_category", "category"),
    )

    sku: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
    )
    inventory: Mapped[List["Inventory"]] = relationship(
        "Inventory",
        back_populates="product",
    )
    replacements: Mapped[List["Replacement"]] = relationship(
        "Replacement",
        back_populates="product",
    )
