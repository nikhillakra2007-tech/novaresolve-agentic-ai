from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.order import Order
    from backend.app.db.models.case import Case


class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'blocked', 'inactive')", name="chk_customer_status"),
        Index("idx_customers_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    # Relationships
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
