"""
환경변수 관리
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    database_url: str
    redis_url: str | None
    model_path: Path
    model_version: str
    openai_timeout_seconds: float
    max_retry_count: int
    max_image_size_mb: int


def load_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    return Settings(
        openai_api_key=api_key,
        database_url=database_url,
        redis_url=os.getenv("REDIS_URL"),
        model_path=Path(os.getenv("MODEL_PATH", "./compiled_leaf_disease")),
        model_version=os.getenv("MODEL_VERSION", ""),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "5")),
        max_image_size_mb=int(os.getenv("MAX_IMAGE_SIZE_MB", "10")),
    )
