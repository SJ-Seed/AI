"""FastAPI application and Redis queue lifecycle."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.core.config import load_settings
from app.core.logging import get_logger
from app.infrastructure.queue.arq_analysis_queue import ManagedArqAnalysisQueue
from app.infrastructure.queue.redis_connection import (
    RedisConnectionManager,
    RedisUnavailableError,
)


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    redis_connections = RedisConnectionManager(settings.redis_url)
    app.state.redis_connections = redis_connections
    app.state.analysis_queue = ManagedArqAnalysisQueue(
        redis_connections,
        settings.analysis_queue_name,
    )

    try:
        await redis_connections.ping()
    except RedisUnavailableError:
        logger.warning("Redis is unavailable during application startup")

    try:
        yield
    finally:
        await redis_connections.close()


def create_app() -> FastAPI:
    application = FastAPI(lifespan=lifespan)
    application.include_router(analysis_router)
    application.include_router(health_router)
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
