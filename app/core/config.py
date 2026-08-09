"""
환경변수 관리
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    database_url: str
    redis_url: str | None
    analysis_queue_name: str
    model_path: Path
    model_version: str
    openai_timeout_seconds: float
    max_retry_count: int
    max_image_size_mb: int
    retry_base_delay_seconds: float = 2
    retry_max_delay_seconds: float = 60
    image_download_timeout_seconds: float = 10


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    settings = Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        database_url=database_url,
        redis_url=os.getenv("REDIS_URL"),
        analysis_queue_name=os.getenv("ANALYSIS_QUEUE_NAME", "analysis"),
        model_path=Path(os.getenv("MODEL_PATH", "./compiled_leaf_disease")),
        model_version=os.getenv("MODEL_VERSION", ""),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "4")),
        max_image_size_mb=int(os.getenv("MAX_IMAGE_SIZE_MB", "10")),
        retry_base_delay_seconds=float(os.getenv("RETRY_BASE_DELAY_SECONDS", "2")),
        retry_max_delay_seconds=float(os.getenv("RETRY_MAX_DELAY_SECONDS", "60")),
        image_download_timeout_seconds=float(os.getenv("IMAGE_DOWNLOAD_TIMEOUT_SECONDS", "10")),
    )
    if settings.max_retry_count < 0:
        raise RuntimeError("MAX_RETRY_COUNT must be non-negative")
    if settings.max_image_size_mb <= 0:
        raise RuntimeError("MAX_IMAGE_SIZE_MB must be positive")
    if settings.retry_base_delay_seconds < 0:
        raise RuntimeError("RETRY_BASE_DELAY_SECONDS must be non-negative")
    if settings.retry_max_delay_seconds < settings.retry_base_delay_seconds:
        raise RuntimeError("RETRY_MAX_DELAY_SECONDS must be >= RETRY_BASE_DELAY_SECONDS")
    if settings.image_download_timeout_seconds <= 0:
        raise RuntimeError("IMAGE_DOWNLOAD_TIMEOUT_SECONDS must be positive")
    return settings


def require_redis_url(settings: Settings) -> str:
    """
    Redis를 사용하는 프로세스에서 REDIS_URL 설정을 검증한다.
    공통 Settings에서는 Redis 주소를 선택값으로 관리하지만, Queue를 사용하는 FastAPI를 실행할 때는 반드시 필요하다.

    Args:
        settings: 환경변수에서 불러온 애플리케이션 설정

    Returns:
        설정된 Redis 접속 URL

    Raises:
        RuntimeError: REDIS_URL이 설정되지 않은 경우
    """
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL environment variable is required")
    return settings.redis_url


def require_openai_api_key(settings: Settings) -> str:
    """
    AI 기능을 사용하는 프로세스에서 OpenAI API 키를 검증한다.
    FastAPI는 AI 분석을 직접 실행하지 않으므로 API 키 없이 실행할 수 있다.
    향후 Worker나 기존 학습 스크립트처럼 OpenAI를 실제로 사용하는
    프로세스에서만 이 함수를 호출한다.

    Args:
        settings: 환경변수에서 불러온 애플리케이션 설정

    Returns:
        설정된 OpenAI API 키

    Raises:
        RuntimeError: OPENAI_API_KEY가 설정되지 않은 경우
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required")
    return settings.openai_api_key
