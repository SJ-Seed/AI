import asyncio
from typing import Protocol

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.queue.redis_connection import RedisConnectionManager


router = APIRouter()

# 각 의존성 점검이 장시간 응답을 지연시키지 않도록 제한
DEPENDENCY_TIMEOUT_SECONDS = 2.0


class ReadinessChecker(Protocol):
    """Readliness 엔드포인트에서 사용하는 의존성 점검 인터페이스"""
    async def check(self) -> tuple[str, str]: ...


class DependencyReadinessChecker:
    """PostgreSQL과 Redis가 요청을 처리할 수 있는 상태인지 점검"""

    def __init__(
        self,
        database_engine: AsyncEngine,
        redis_connections: RedisConnectionManager,
    ) -> None:
        self._database_engine = database_engine
        self._redis_connections = redis_connections

    async def check(self) -> tuple[str, str]:
        # 두 서비스 점검을 동시에 실행해 전체 응답 시간을 줄인다
        postgresql, redis = await asyncio.gather(
            self._check_postgresql(),
            self._check_redis(),
        )
        return postgresql, redis

    async def _check_postgresql(self) -> str:
        try:
            # 실제 쿼리 실행이 가능한지 가벼운 SELECT 문으로 확인
            async with asyncio.timeout(DEPENDENCY_TIMEOUT_SECONDS):
                async with self._database_engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            return "up"
        except Exception:
            return "down"

    async def _check_redis(self) -> str:
        try:
            # 연결 생성 또는 재연결을 포함해 Redis 응답 가능 여부를 반환
            async with asyncio.timeout(DEPENDENCY_TIMEOUT_SECONDS):
                await self._redis_connections.ping()
            return "up"
        except Exception:
            return "down"


def get_readiness_checker(request: Request) -> ReadinessChecker:
    """애플리케이션 자원으로 실제 readliness 검사기를 구성"""
    from app.infrastructure.persistence.database import engine

    return DependencyReadinessChecker(engine, request.app.state.redis_connections)


def _health_response(postgresql: str, redis: str) -> dict[str, object]:
    """의존성 점검 결과를 공개 헬스체크 응답 형식으로 변환"""

    healthy = postgresql == "up" and redis == "up"
    return {
        "status": "healthy" if healthy else "unhealthy",
        "services": {
            # 이 함수가 실행되었다는 것은 API 프로세스가 응답 중이라는 의미
            "api": {"status": "up"},
            "postgresql": {"status": postgresql},
            "redis": {"status": redis},
        },
    }


@router.get("/health")
@router.get("/health/ready")
async def readiness_endpoint(
    response: Response,
    checker: ReadinessChecker = Depends(get_readiness_checker),
):
    """API가 PostgreSQL 및 Redis를 포함해 요청을 처리할 준비가 되었는지 확인"""

    postgresql, redis = await checker.check()
    if postgresql != "up" or redis != "up":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return _health_response(postgresql, redis)


@router.get("/health/live")
async def liveness_endpoint():
    """외부 의존성을 확인하지 않고 API 프로세스의 생존 여부만 반환"""
    
    return {
        "status": "healthy",
        "services": {"api": {"status": "up"}},
    }
