import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.customer import Customer
    from backend.app.db.models.order import Order
    from backend.app.db.models.agent_event import AgentEvent
    from backend.app.db.models.refund import Refund
    from backend.app.db.models.replacement import Replacement
    from backend.app.db.models.cancellation import Cancellation


class Case(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'investigating', 'planning', 'awaiting_approval', 'executing', 'verifying', 'replanning', 'resolved', 'escalated', 'failed')",
            name="chk_case_status",
        ),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="chk_case_risk_level"),
        Index("idx_cases_customer_id", "customer_id"),
        Index("idx_cases_order_id", "order_id"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_risk_level", "risk_level"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    current_plan: Mapped[Optional[Any]] = mapped_column(JSONB, default=list, nullable=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolution_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    resolution_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="cases")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="cases")
    agent_events: Mapped[List["AgentEvent"]] = relationship(
        "AgentEvent",
        back_populates="case",
        cascade="all, delete-orphan",
    )
    refunds: Mapped[List["Refund"]] = relationship(
        "Refund",
        back_populates="case",
        cascade="all, delete-orphan",
    )
    replacements: Mapped[List["Replacement"]] = relationship(
        "Replacement",
        back_populates="case",
        cascade="all, delete-orphan",
    )
    cancellations: Mapped[List["Cancellation"]] = relationship(
        "Cancellation",
        back_populates="case",
        cascade="all, delete-orphan",
    )
