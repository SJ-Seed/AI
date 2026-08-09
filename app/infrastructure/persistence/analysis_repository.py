"""Analysis Repository의 SQLAlchemy 구현체"""

from datetime import datetime, timezone

from sqlalchemy import update
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
        """Compatibility wrapper for the current synchronous API."""
        return await self.claim_pending(analysis_id)

    # PENDING 상태의 분석 작업을 원자적으로 선점
    async def claim_pending(self, analysis_id: int) -> bool:
        statement = (
            update(Analysis)
            .where(
                Analysis.id == analysis_id,
                Analysis.status == AnalysisStatus.PENDING,
            )
            .values(
                status=AnalysisStatus.PROCESSING,
                started_at=datetime.now(timezone.utc),
            )
        )
        return await self._execute_transition(statement)

    # 일시적 오류가 발생한 분석 작업을 재시도 대기 상태로 변경
    async def reschedule_for_retry(
        self, analysis_id: int, *, max_retry_count: int
    ) -> int | None:
        statement = (
            update(Analysis)
            .where(
                Analysis.id == analysis_id,
                Analysis.status == AnalysisStatus.PROCESSING,
                Analysis.retry_count < max_retry_count,
            )
            .values(
                status=AnalysisStatus.PENDING,
                retry_count=Analysis.retry_count + 1,
                started_at=None,
                completed_at=None,
                error_code=None,
                error_message=None,
            )
            .returning(Analysis.retry_count)
        )
        try:
            result = await self.session.execute(statement)
            retry_count = result.scalar_one_or_none()
            if retry_count is None:
                await self.session.rollback()
                return None
            await self.session.commit()
            return int(retry_count)
        except Exception:
            await self.session.rollback()
            raise

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
        """
        처리 중인 분석 작업의 결과를 저장하고 COMPLETED 상태로 변경한다.
        PROCESSING 상태인 작업만 완료 처리할 수 있으며, 분석 결과와 완료 시각을 하나의 조건부 UPDATE로 저장한다.

        Args:
            analysis_id: 완료 처리할 분석 작업의 ID
            is_plant: 이미지의 식물 여부
            disease_code: 진단된 질병 코드
            disease_name: 진단된 질병 이름
            explain: 분석 결과 설명
            cause: 질병의 원인
            cure: 질병의 치료 또는 관리 방법
            model_version: 분석에 사용된 AI 모델 버전
            latency_ms: 분석 처리에 걸린 시간(ms)

        Returns:
            PROCESSING에서 COMPLETED로 변경되면 True,
            작업이 없거나 PROCESSING 상태가 아니면 False
        """
        statement = (
            update(Analysis)
            .where(
                Analysis.id == analysis_id,
                Analysis.status == AnalysisStatus.PROCESSING,
            )
            .values(
                status=AnalysisStatus.COMPLETED,
                is_plant=is_plant,
                disease_code=disease_code,
                disease_name=disease_name,
                explain=explain,
                cause=cause,
                cure=cure,
                model_version=model_version,
                latency_ms=latency_ms,
                completed_at=datetime.now(timezone.utc),
            )
        )
        return await self._execute_transition(statement)

    # 분석이 실패했을 때 실패 상태와 오류 정보 저장
    async def mark_failed(
        self,
        analysis_id: int,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        """
        Worker가 처리 중인 분석을 FAILED 상태로 변경한다.
        Worker가 선점한 PROCESSING 상태의 작업에만 적용된다.
        """
        return await self._mark_failed_from(
            analysis_id,
            expected_status=AnalysisStatus.PROCESSING,
            error_code=error_code,
            error_message=error_message,
        )

    async def mark_enqueue_failed(
        self,
        analysis_id: int,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        """
        Queue 등록에 실패한 분석을 FAILED 상태로 변경한다.
        Worker가 아직 선점하지 않은 PENDING 상태의 작업에만 적용된다.
        """
        return await self._mark_failed_from(
            analysis_id,
            expected_status=AnalysisStatus.PENDING,
            error_code=error_code,
            error_message=error_message,
        )

    async def _mark_failed_from(
        self,
        analysis_id: int,
        *,
        expected_status: AnalysisStatus,
        error_code: str,
        error_message: str,
    ) -> bool:
        """
        지정된 상태의 분석을 FAILED로 변경하고 오류 정보를 저장한다.

        Args:
            analysis_id: 실패 처리할 분석 작업의 ID
            expected_status: 실패 처리를 허용할 현재 상태
            error_code: 실패 원인을 구분하는 오류 코드
            error_message: 실패 원인에 대한 상세 메시지

        Returns:
            FAILED 상태 변경에 성공하면 True, 작업이 없거나 예상한 상태가 아니면 False
        """
        statement = (
            update(Analysis)
            .where(
                Analysis.id == analysis_id,
                Analysis.status == expected_status,
            )
            .values(
                status=AnalysisStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                completed_at=datetime.now(timezone.utc),
            )
        )
        return await self._execute_transition(statement)

    async def _execute_transition(self, statement) -> bool:
        """
        상태 전이 UPDATE를 실행하고 성공 여부를 반환한다.
        한 행만 변경된 경우 상태 전이에 성공한 것으로 판단한다.
        대상이 없거나 상태 조건이 맞지 않으면 변경하지 않고 False를 반환한다.
        실행 또는 commit 중 예외가 발생하면 rollback한 뒤 예외를 전파한다.

        Args:
            statement: 실행할 SQLAlchemy UPDATE 문

        Returns:
            정확히 한 행이 변경되면 True, 그렇지 않으면 False
        """
        try:
            result = await self.session.execute(statement)
            if result.rowcount != 1:
                await self.session.rollback()
                return False
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise

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
