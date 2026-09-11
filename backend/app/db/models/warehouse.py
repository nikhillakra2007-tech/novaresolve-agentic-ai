from typing import List, TYPE_CHECKING
from sqlalchemy import String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.inventory import Inventory
    from backend.app.db.models.replacement import Replacement


class Warehouse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "warehouses"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'maintenance')", name="chk_warehouse_status"),
    )

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    # Relationships
    inventory: Mapped[List["Inventory"]] = relationship(
        "Inventory",
        back_populates="warehouse",
    )
    replacements: Mapped[List["Replacement"]] = relationship(
        "Replacement",
        back_populates="warehouse",
    )
