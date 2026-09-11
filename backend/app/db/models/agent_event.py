import uuid
from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.case import Case


class AgentEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_events"
    __table_args__ = (
        Index("idx_agent_events_case_id", "case_id"),
        Index("idx_agent_events_event_type", "event_type"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    input_data: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="agent_events")
