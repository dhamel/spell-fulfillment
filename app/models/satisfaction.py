"""Satisfaction rating model for manual feedback tracking."""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.spell import Spell


class Satisfaction(Base, TimestampMixin):
    """Manual customer satisfaction rating."""

    __tablename__ = "satisfactions"
    __table_args__ = (
        CheckConstraint("star_rating >= 1 AND star_rating <= 5", name="valid_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    spell_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("spells.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    star_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    spell: Mapped["Spell"] = relationship("Spell", back_populates="satisfaction")
