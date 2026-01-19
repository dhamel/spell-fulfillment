"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import Token, TokenData
from app.core.security import create_access_token, verify_password
from app.api.deps import get_db
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
settings = get_settings()


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate operator and return JWT token."""
    from app.models.operator import Operator
    from sqlalchemy import select

    # Query operator by username
    result = await db.execute(
        select(Operator).where(Operator.username == form_data.username)
    )
    operator = result.scalar_one_or_none()

    if not operator or not verify_password(form_data.password, operator.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not operator.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token = create_access_token(data={"sub": operator.username})

    # Set cookie for browser-based access
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Log out operator by clearing the auth cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=TokenData)
async def get_current_user(
    current_user: TokenData = Depends(),
) -> TokenData:
    """Get current authenticated operator info."""
    # This will be implemented with the get_current_user dependency
    return current_user
