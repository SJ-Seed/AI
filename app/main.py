"""FastAPI application and Redis queue lifecycle."""

from contextlib import asynccontextmanager

from arq.connections import create_pool
from fastapi import FastAPI

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.core.config import load_settings, require_redis_url
from app.infrastructure.queue.arq_analysis_queue import ArqAnalysisQueue
from app.infrastructure.queue.redis_settings import build_redis_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    redis_url = require_redis_url(settings)
    redis = await create_pool(build_redis_settings(redis_url))

    try:
        app.state.analysis_queue = ArqAnalysisQueue(
            redis,
            settings.analysis_queue_name,
        )
        yield
    finally:
        await redis.aclose()


def create_app() -> FastAPI:
    application = FastAPI(lifespan=lifespan)
    application.include_router(analysis_router)
    application.include_router(health_router)
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
