"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Start background scheduler for Etsy polling
    from app.services.etsy import start_scheduler
    start_scheduler()

    yield

    # Shutdown
    # Stop background scheduler
    from app.services.etsy import stop_scheduler
    stop_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Automated Etsy spell fulfillment system",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_path = Path(__file__).parent.parent / "frontend" / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Register API routers
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix="/api/v1")

    # Register dashboard routes
    from app.api.dashboard import dashboard_router

    app.include_router(dashboard_router)

    return app


# Create the application instance
app = create_app()

# Templates for dashboard
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "frontend" / "templates")
)
