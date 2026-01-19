"""Dashboard HTML routes."""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.api.deps import get_current_user_optional

router = dashboard_router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent.parent / "frontend" / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def root(request: Request) -> Response:
    """Redirect to dashboard or login."""
    return RedirectResponse(url="/dashboard")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: str | None = Depends(get_current_user_optional),
) -> Response:
    """Main dashboard page."""
    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": current_user},
    )


@router.get("/orders", response_class=HTMLResponse)
async def orders_page(
    request: Request,
    current_user: str | None = Depends(get_current_user_optional),
) -> Response:
    """Orders list page."""
    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "user": current_user},
    )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail_page(
    request: Request,
    order_id: int,
    current_user: str | None = Depends(get_current_user_optional),
) -> Response:
    """Order detail page."""
    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "order_detail.html",
        {"request": request, "user": current_user, "order_id": order_id},
    )


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    current_user: str | None = Depends(get_current_user_optional),
) -> Response:
    """Tasks list page."""
    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "user": current_user},
    )


@router.get("/metrics", response_class=HTMLResponse)
async def metrics_page(
    request: Request,
    current_user: str | None = Depends(get_current_user_optional),
) -> Response:
    """Metrics/analytics page."""
    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "metrics.html",
        {"request": request, "user": current_user},
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: str | None = Depends(get_current_user_optional),
) -> Response:
    """Settings page (Etsy connection, spell types)."""
    if not current_user:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "user": current_user},
    )
