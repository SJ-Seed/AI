"""API 프로세스에서 공유하며 장애 후 재연결할 수 있는 Redis 연결을 관리"""

import asyncio

from arq.connections import ArqRedis, create_pool

from app.infrastructure.queue.redis_settings import build_redis_settings


class RedisUnavailableError(RuntimeError):
    """접속 세부 정보를 노출하지 않고 Redis 장애를 전달하는 예외"""


class RedisConnectionManager:
    """Redis 연결을 지연 생성하고 장애 발생 시 폐기하는 연결 관리자"""

    def __init__(self, redis_url: str | None, *, timeout_seconds: float = 2.0) -> None:
        self._redis_url = redis_url
        self._timeout_seconds = timeout_seconds
        self._redis: ArqRedis | None = None

        # 여러 요청이 동시에 최초 연결을 생성하지 못하도록 보호
        self._lock = asyncio.Lock()

    async def get_connection(self) -> ArqRedis:
        """활성 연결을 반환하거나, 연결이 없다면 새로 생성"""

        # 이미 생성된 연결이 있으면 잠금을 사용하지 않고 바로 반환
        if self._redis is not None:
            return self._redis

        async with self._lock:
            # 잠금을 기다리는 동안 다른 요청이 연결을 생성했을 수 있으므로 잠금 획득 후 연결 상태 확인
            if self._redis is not None:
                return self._redis
            # Redis URL이 설정되지 않은 경우 연결 시도 X
            if not self._redis_url:
                raise RedisUnavailableError("Redis is unavailable")

            try:
                # Redis 장애로 API 요청이 장시간 대기하지 않도록 연결 생성에도 제한 시간 적용
                self._redis = await asyncio.wait_for(
                    create_pool(build_redis_settings(self._redis_url)),
                    timeout=self._timeout_seconds,
                )
            except Exception:
                raise RedisUnavailableError("Redis is unavailable") from None
            return self._redis

    async def ping(self) -> None:
        """Redis 연결과 명령 처리 가능 여부 확인"""

        try:
            redis = await self.get_connection()

            # 연결 객체의 존재만 확인하지 않고 실제 PING 명령을 실행
            await asyncio.wait_for(redis.ping(), timeout=self._timeout_seconds)
        except Exception:
            # PING 또는 연결 생성에 실패한 연결은 재사용하지 않는다
            await self.invalidate()
            raise RedisUnavailableError("Redis is unavailable") from None

    async def invalidate(self) -> None:
        """현재 연결을 공유 상태에서 제거하고 안전하게 종료"""
        async with self._lock:
            # 잠금 안에서는 공유 참조만 빠르게 제거
            redis, self._redis = self._redis, None
        if redis is not None:
            try:
                # 네트워크 종료를 기다리는 동안 연결 생성을 막지 않도록 실제 종료 작업은 잠금 밖에서 수행
                await redis.aclose()
            except Exception:
                pass

    async def close(self) -> None:
        """애플리케이션 종료 시 현재 Redis 연결을 정리"""
        await self.invalidate()
