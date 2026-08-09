"""애플리케이션의 Redis 설정을 arq 설정으로 변환하는 유틸리티"""

from arq.connections import RedisSettings


def build_redis_settings(redis_url: str | None) -> RedisSettings:
    """
    Redis URL을 arq의 RedisSettings 객체로 변환한다.
    이 함수는 설정만 생성하며 실제 Redis 연결을 생성하거나 연결의 생명주기를 관리하지 않는다.

    Args:
        redis_url: Redis 접속 주소
            예: redis://redis:6379/0

    Returns:
        arq에서 Redis 연결을 생성할 때 사용하는 설정 객체

    Raises:
        RuntimeError: REDIS_URL이 없거나 올바른 Redis 주소가 아닌 경우
    """
    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is required for the analysis queue")

    try:
        return RedisSettings.from_dsn(redis_url)
    except (TypeError, ValueError, RuntimeError) as error:
        raise RuntimeError("REDIS_URL must be a valid Redis DSN") from error
