"""arq를 사용해 분석 작업을 Redis Queue에 등록하는 구현체"""

from arq.connections import ArqRedis

from app.infrastructure.queue.redis_connection import (
    RedisConnectionManager,
    RedisUnavailableError,
)


# Worker가 Queue에서 작업을 가져왔을 때 실행할 함수 이름
ANALYSIS_JOB_FUNCTION = "process_analysis"


class ArqAnalysisQueue:
    """
    분석 ID를 arq 기반 Redis Queue에 등록
    Redis 연결은 외부에서 생성해 주입하며, 이 클래스에서는 연결을 직접 생성하거나 종료하지 않는다.
    """

    def __init__(self, redis: ArqRedis, queue_name: str) -> None:
        """
        redis: 외부에서 생성한 arq Redis 연결
        queue_name: 분석 작업을 등록할 Queue 이름
        """
        self._redis = redis
        self._queue_name = queue_name

    async def enqueue(self, analysis_id: int) -> None:
        """
        분석 ID를 비동기 작업 Queue에 등록
        동일한 analysis_id는 같은 job ID를 사용하므로 중복 작업 등록을 방지할 수 있다
        """
        await self._redis.enqueue_job(
            ANALYSIS_JOB_FUNCTION,
            analysis_id,
            # 같은 분석 작업의 중복 등록을 방지하기 위한 고유 작업 ID
            _job_id=f"analysis:{analysis_id}",
            # 작업을 등록할 Redis Queue 이름
            _queue_name=self._queue_name,
        )


class ManagedArqAnalysisQueue:
    """일시적인 Redis 장애 발생 시 연결을 폐기하고 재연결을 지원하는 분석 큐"""

    def __init__(self, connections: RedisConnectionManager, queue_name: str) -> None:
        self._connections = connections
        self._queue_name = queue_name

    async def enqueue(self, analysis_id: int) -> None:
        try:
            # 기존 연결이 유효하면 재사용, 없으면 RedisConnectManager 통해 새 연결 생성
            redis = await self._connections.get_connection()

            # 현재 연결을 이용하여 분석 작업을 ARQ 큐에 등록
            await ArqAnalysisQueue(redis, self._queue_name).enqueue(analysis_id)

        except Exception:
            # 실패한 연결을 재사용하지 않도록 폐기
            await self._connections.invalidate()
            raise RedisUnavailableError("Analysis queue is unavailable") from None
