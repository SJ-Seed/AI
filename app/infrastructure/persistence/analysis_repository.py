"""Analysis Repository의 SQLAlchemy 구현체"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.analysis_repository import AnalysisRepository
from app.domain.enums import AnalysisStatus
from app.infrastructure.persistence.models import Analysis


class SqlAlchemyAnalysisRepository(AnalysisRepository):
    """
    AnalysisRepository 인터페이스를 SQLAlchemy를 사용해 구현한다.
    전달받은 AsyncSession을 통해 analyses 테이블에 분석 작업을 생성, 조회하고 상태 및 결과를 변경한다.
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 새로운 분석 요청을 PENDING 상태로 DB에 저장하고 생성된 ID 반환
    async def create(
        self,
        *,
        image_path: str,
        temperature: str,
        humidity: str,
    ) -> int:
        analysis = Analysis(
            status=AnalysisStatus.PENDING,
            image_path=image_path,
            temperature=temperature,
            humidity=humidity,
            retry_count=0,
        )
        self.session.add(analysis)
        await self._commit()
        return analysis.id

    # ID에 해당하는 분석 작업을 DB에서 조회
    async def get_by_id(self, analysis_id: int) -> dict[str, object] | None:
        analysis = await self.session.get(Analysis, analysis_id)
        if analysis is None:
            return None
        return self._to_snapshot(analysis)

    # 분석이 실제로 시작되었음을 기록
    async def mark_processing(self, analysis_id: int) -> bool:
        analysis = await self.session.get(Analysis, analysis_id)
        if analysis is None:
            return False

        analysis.status = AnalysisStatus.PROCESSING
        analysis.started_at = datetime.now(timezone.utc)
        await self._commit()
        return True

    # 분석이 성공적으로 완료되었을 때 결과 저장
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
        analysis = await self.session.get(Analysis, analysis_id)
        if analysis is None:
            return False

        # 분석 상태를 완료로 변경
        analysis.status = AnalysisStatus.COMPLETED
        analysis.is_plant = is_plant
        analysis.disease_code = disease_code
        analysis.disease_name = disease_name
        analysis.explain = explain
        analysis.cause = cause
        analysis.cure = cure
        analysis.model_version = model_version
        analysis.latency_ms = latency_ms
        analysis.completed_at = datetime.now(timezone.utc)
        await self._commit()
        return True

    # 분석이 실패했을 때 실패 상태와 오류 정보 저장
    async def mark_failed(
        self,
        analysis_id: int,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        analysis = await self.session.get(Analysis, analysis_id)
        if analysis is None:
            return False

        analysis.status = AnalysisStatus.FAILED
        analysis.error_code = error_code
        analysis.error_message = error_message
        analysis.completed_at = datetime.now(timezone.utc)
        await self._commit()
        return True

    # DB 변경사항을 확정하는 공통 메서드
    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    # SQLAlchemy ORM 객체를 application 계층에서 사용할 단순 dict로 변환
    @staticmethod
    def _to_snapshot(analysis: Analysis) -> dict[str, object]:
        return {
            "id": analysis.id,
            "status": analysis.status,
            "image_path": analysis.image_path,
            "temperature": analysis.temperature,
            "humidity": analysis.humidity,
            "is_plant": analysis.is_plant,
            "disease_code": analysis.disease_code,
            "disease_name": analysis.disease_name,
            "explain": analysis.explain,
            "cause": analysis.cause,
            "cure": analysis.cure,
            "model_version": analysis.model_version,
            "latency_ms": analysis.latency_ms,
            "retry_count": analysis.retry_count,
            "error_code": analysis.error_code,
            "error_message": analysis.error_message,
            "created_at": analysis.created_at,
            "started_at": analysis.started_at,
            "completed_at": analysis.completed_at,
        }
