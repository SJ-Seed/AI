"""Application 계층에서 분석 작업의 저장/조회에 사용하기 위한 Repository 인터페이스"""

from typing import Protocol


class AnalysisRepository(Protocol):
    """
    분석 작업의 생성, 조회 및 상태 변경 기능을 정의한다.
    실제 PostgreSQL/SQLAlchemy 구현은 infrastructure 계층에서 담당하며,
    application 계층은 구체적인 DB 구현을 알지 않고 이 인터페이스만 사용한다.
    """

    # 새로운 분석 작업을 PENDING 상태로 생성하고 생성된 분석 ID를 반환
    async def create(
        self,
        *,
        image_path: str,
        temperature: str,
        humidity: str,
    ) -> int:
        ...

    # 분석 ID로 저장된 분석 작업을 조회
    async def get_by_id(self, analysis_id: int) -> dict[str, object] | None:
        ...

    # 분석 작업을 PROCESSING 상태로 변경하고 분석 시작 시각을 기록 (변경할 작업이 존재하면 True)
    async def mark_processing(self, analysis_id: int) -> bool:
        ...

    # PENDING 상태의 분석 작업을 원자적으로 선점
    async def claim_pending(self, analysis_id: int) -> bool:
        """Atomically change a pending analysis to processing."""
        ...

    # 분석이 정상적으로 끝났을 떄 결과를 저장하고 COMPLETED 상태로 변경
    async def mark_completed(
        self,
        analysis_id: int,
        *,
        is_plant: bool | None,
        disease_code: str | None = None,
        disease_name: str | None = None,
        explain: str | None = None,
        cause: str | None = None,
        cure: str | None = None,
        model_version: str | None = None,
        latency_ms: int | None = None,
    ) -> bool:
        ...

    # 분석에 실패했을 때 오류 정보를 저장하고 FAILED 상태로 변경
    async def mark_failed(
        self,
        analysis_id: int,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        ...

    # 큐 등록에 실패한 PENDING 분석을 FAILED 상태로 변경
    async def mark_enqueue_failed(
        self,
        analysis_id: int,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        """Fail a pending analysis when it could not be enqueued."""
        ...
