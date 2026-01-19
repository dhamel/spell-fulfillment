"""Order model for Etsy orders."""

import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.spell_type import SpellType
    from app.models.spell import Spell


class OrderStatus(str, enum.Enum):
    """Order status enumeration."""

    PENDING = "pending"
    GENERATING = "generating"
    REVIEW = "review"
    APPROVED = "approved"
    DELIVERED = "delivered"
    FAILED = "failed"


class Order(Base, TimestampMixin):
    """Etsy order with spell request details."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Etsy identifiers
    etsy_receipt_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    etsy_listing_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    etsy_transaction_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Customer info
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Spell details
    spell_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("spell_types.id"), nullable=True
    )
    raw_spell_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    intention: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personalization_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.PENDING,
        nullable=False,
    )

    # Order details
    etsy_order_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    order_total_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    # Relationships
    spell_type: Mapped[Optional["SpellType"]] = relationship(
        "SpellType", back_populates="orders"
    )
    spells: Mapped[list["Spell"]] = relationship(
        "Spell", back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def current_spell(self) -> Optional["Spell"]:
        """Get the current (latest) spell version."""
        if not self.spells:
            return None
        return max(self.spells, key=lambda s: s.version)
