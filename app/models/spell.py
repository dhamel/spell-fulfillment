"""Spell model for AI-generated spell content."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.satisfaction import Satisfaction


class Spell(Base, TimestampMixin):
    """AI-generated spell content with versioning."""

    __tablename__ = "spells"
    __table_args__ = (UniqueConstraint("order_id", "version", name="uq_spell_order_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status flags
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Delivery tracking
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivery_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    delivery_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="spells")
    satisfaction: Mapped[Optional["Satisfaction"]] = relationship(
        "Satisfaction", back_populates="spell", uselist=False
    )

    @property
    def is_delivered(self) -> bool:
        """Check if spell has been delivered."""
        return self.delivered_at is not None
