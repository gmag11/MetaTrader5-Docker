"""FastAPI application for copytrader monitoring and control."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..utils.logging import get_logger
from .state import set_engine, get_engine  # noqa: F401

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("api_starting")
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Import routers here to avoid circular imports
    from .routes.accounts import router as accounts_router
    from .routes.deploy import router as deploy_router
    from .routes.health import router as health_router
    from .routes.positions import router as positions_router

    app = FastAPI(
        title="CopyTrader API",
        description="MetaTrader 5 Trade Copier Service API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
    app.include_router(positions_router, prefix="/positions", tags=["Positions"])
    app.include_router(deploy_router, prefix="/deploy", tags=["Deployment"])

    return app
