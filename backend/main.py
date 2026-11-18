import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from security import RateLimiter, RateLimitMiddleware, SecurityHeadersMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_for_production()
    for warning in settings.warn_for_production():
        logger.warning(warning)
    scheduler = None
    if settings.scheduler_enabled and settings.app_env != "test":
        from ingestion.scheduler import start_scheduler

        scheduler = start_scheduler(settings)
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    docs = settings.docs_enabled
    app = FastAPI(
        title="Prediction Market Analytics API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )

    app.state.rate_limiter = RateLimiter(settings.rate_limit)
    app.add_middleware(RateLimitMiddleware, limiter=app.state.rate_limiter, settings=settings)
    # Added last so it runs first: 429 responses get the security headers too.
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
            max_age=600,
        )

    from routers import health, markets, watchlists

    app.include_router(health.router)
    app.include_router(markets.router)
    app.include_router(watchlists.router)
    return app


app = create_app()
