"""Etsy OAuth token storage model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EtsyToken(Base, TimestampMixin):
    """Etsy OAuth 2.0 token storage."""

    __tablename__ = "etsy_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_type: Mapped[str] = mapped_column(String(50), default="Bearer", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shop_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        from datetime import timezone

        return datetime.now(timezone.utc) >= self.expires_at
