from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import String, Integer, Boolean, DateTime, CheckConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, UUIDPrimaryKeyMixin


class Policy(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="chk_policy_risk_level"),
    )

    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
