"""Shared API dependencies."""

from typing import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import async_session_maker

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def _decode_token(token: str) -> str:
    """Decode and validate JWT token, return username."""
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    username: str | None = payload.get("sub")
    if username is None:
        raise JWTError("No subject in token")
    return username


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Get current authenticated user from JWT token (API routes)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        return _decode_token(token)
    except JWTError:
        raise credentials_exception


async def get_current_user_optional(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    access_token: str | None = Cookie(default=None),
) -> str | None:
    """Get current user from JWT token or cookie (for HTML pages)."""
    # Try Bearer token first (for API requests)
    if token:
        try:
            return _decode_token(token)
        except JWTError:
            pass

    # Fall back to cookie (for browser page requests)
    if access_token:
        try:
            return _decode_token(access_token)
        except JWTError:
            pass

    return None
