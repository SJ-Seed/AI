"""분석 Queue 작업 처리와 Worker가 소유하는 자원의 생명주기 관리."""

import asyncio
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.services.diagnosis_service import DiagnosisService
from app.core.config import Settings, load_settings, require_openai_api_key
from app.core.logging import get_logger
from app.infrastructure.image.image_downloader import (
    ImageDownloader,
    ImageDownloadResult,
)
from app.infrastructure.persistence.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


logger = get_logger(__name__)

# Worker 실패 원인을 DB에 저장할 때 사용하는 고정 오류 코드
IMAGE_DOWNLOAD_ERROR = "IMAGE_DOWNLOAD_ERROR"
AI_ANALYSIS_ERROR = "AI_ANALYSIS_ERROR"
WORKER_INTERNAL_ERROR = "WORKER_INTERNAL_ERROR"
MAX_PERSISTED_ERROR_MESSAGE_LENGTH = 255

# 실제 예외 내용 대신 DB에 저장할 안전한 고정 메시지
SAFE_ERROR_MESSAGES = {
    IMAGE_DOWNLOAD_ERROR: "Image download failed",
    AI_ANALYSIS_ERROR: "AI analysis failed",
    WORKER_INTERNAL_ERROR: "Worker processing failed",
}


class ImageDownloadFailure(RuntimeError):
    """이미지 다운로드 결과가 실패일 때 발생하는 Worker 예외."""
    pass


class WorkerInternalFailure(RuntimeError):
    """Worker 내부 상태 전이 또는 제어 흐름에 문제가 있을 때 발생하는 예외."""
    pass


def build_ai_resources(settings: Settings) -> tuple[Any, DiagnosisService]:
    """
    Worker가 사용할 OpenAI client와 AI 진단 서비스를 생성한다.
    API 프로세스에서는 AI 객체를 생성하지 않고, 실제 분석을 수행하는 Worker가 시작될 때 한 번만 생성한다.
    """
    import dspy
    from openai import OpenAI

    from app.infrastructure.ai.disease_explainer import DspyDiseaseExplainer, GenerateAnswer
    from app.infrastructure.ai.dspy_classifier import DspyDiseaseClassifier
    from app.infrastructure.ai.openai_detector import OpenAIPlantDetector

    api_key = require_openai_api_key(settings)
    openai_client = OpenAI(
        api_key=api_key,
        timeout=settings.openai_timeout_seconds,
    )
    try:
        classifier_lm = dspy.LM(
            model="gpt-4o",
            api_key=api_key,
            temperature=0.0,
        )
        explainer_lm = dspy.LM(
            model="gpt-4o",
            api_key=api_key,
            temperature=0.5,
        )
        compiled_program = dspy.load(str(settings.model_path))
        diagnosis_service = DiagnosisService(
            detector=OpenAIPlantDetector(openai_client),
            classifier=DspyDiseaseClassifier(compiled_program, classifier_lm),
            explainer=DspyDiseaseExplainer(GenerateAnswer(), explainer_lm),
        )
        return openai_client, diagnosis_service
    except Exception:
        openai_client.close()
        raise


async def startup(ctx: dict[str, Any]) -> None:
    """
    Worker 시작 시 필요한 자원을 한 번 초기화한다.
    생성한 자원은 arq의 ctx에 저장되며, 각 분석 작업에서 재사용한다.
    """
    settings = load_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    openai_client = None

    try:
        openai_client, diagnosis_service = build_ai_resources(settings)
        ctx.update({
            "settings": settings,
            "engine": engine,
            "session_factory": async_sessionmaker(engine, expire_on_commit=False),
            "openai_client": openai_client,
            "diagnosis_service": diagnosis_service,
            "image_downloader": ImageDownloader(),
            "model_version": settings.model_version or None,
        })
    except Exception:
        if openai_client is not None:
            openai_client.close()
        await engine.dispose()
        raise


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker 종료 시 Worker가 소유한 OpenAI, DB 자원을 정리한다."""
    openai_client = ctx.get("openai_client")
    if openai_client is not None:
        openai_client.close()

    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


async def process_analysis(ctx: dict[str, Any], analysis_id: int) -> bool:
    """
    Queue에서 전달받은 분석 ID에 해당하는 작업을 처리한다.

    처리 흐름:
        PENDING 작업 선점
        → 이미지 다운로드
        → AI 분석
        → 결과 저장
        → 임시 파일 삭제

    Returns:
        정상 완료하면 True, 이미 선점된 작업이면 False
    """
    session_factory = ctx["session_factory"]

    # PENDING 작업을 PROCESSING으로 변경하고 입력 데이터 조회
    analysis = await _claim_and_load(session_factory, analysis_id)

    # 다른 Worker가 이미 선점되었거나 처리된 작업이면 중복 처리하지 않음
    if analysis is None:
        logger.info(
            "Analysis was already claimed or is no longer pending",
            extra={"analysis_id": analysis_id},
        )
        return False

    download_result: ImageDownloadResult | None = None

    # Worker의 실제 처리 시간 측정 시작
    started_at = perf_counter()

    try:
        try:
            # 동기 request 호출이 이벤트 루프를 막지 않도록 별도 스레드에서 실행
            download_result = await asyncio.to_thread(
                ctx["image_downloader"].download,
                analysis["image_path"],
            )
        except Exception:
            # Downloader 자체에서 예상하지 못한 예외가 발생한 경우
            logger.exception(
                "Image downloader raised unexpectedly",
                extra={"analysis_id": analysis_id},
            )
            await _persist_failure(session_factory, analysis_id, IMAGE_DOWNLOAD_ERROR)
            raise

        # Downloader가 정상적으로 실패 결과를 반환한 경우
        if download_result.error is not None or download_result.path is None:
            logger.error(
                "Image download failed: %s",
                download_result.error,
                extra={"analysis_id": analysis_id},
            )
            await _persist_failure(session_factory, analysis_id, IMAGE_DOWNLOAD_ERROR)
            raise ImageDownloadFailure(download_result.error or "Image download failed")

        try:
            # 동기 AI 분석도 이벤트 루프를 막지 않도록 별도 스레드에서 실행
            outcome = await asyncio.to_thread(
                ctx["diagnosis_service"].diagnose_with_details,
                download_result.path,
                analysis["temperature"],
                analysis["humidity"],
            )
        except Exception:
            logger.exception(
                "AI analysis failed",
                extra={"analysis_id": analysis_id},
            )
            await _persist_failure(session_factory, analysis_id, AI_ANALYSIS_ERROR)
            raise

        # 다운로드 시작부터 AI 분석 완료까지 걸린 시간
        latency_ms = int((perf_counter() - started_at) * 1000)
        try:
            # AI 분석 결과를 DB에 저장하고 PROCESSING + COMPLETED로 변경
            completed = await _persist_completion(
                session_factory,
                analysis_id,
                outcome,
                ctx.get("model_version"),
                latency_ms,
            )
        except Exception:
            logger.exception(
                "Failed to persist completed analysis",
                extra={"analysis_id": analysis_id},
            )
            await _persist_failure(session_factory, analysis_id, WORKER_INTERNAL_ERROR)
            raise

        # 상태 조건 불일치로 완료 전이가 거부된 경우
        if not completed:
            error = WorkerInternalFailure("Analysis completion transition was rejected")
            logger.error(str(error), extra={"analysis_id": analysis_id})
            await _persist_failure(session_factory, analysis_id, WORKER_INTERNAL_ERROR)
            raise error
        return True
    finally:
        # 성공, 실패와 상관 없이 Worker가 생성한 임시 파일 삭제
        _remove_owned_temporary_file(download_result, analysis_id)


async def _claim_and_load(session_factory, analysis_id: int):
    """
    PENDING 작업을 원자적으로 선점하고 분석 입력 데이터를 조회한다.
    선점에 실패하면 다른 Worker가 이미 처리 중인 것으로 보고 None을 반환한다.
    """
    claimed = False
    try:
        async with session_factory() as session:
            repository = SqlAlchemyAnalysisRepository(session)
            claimed = await repository.claim_pending(analysis_id)
            if not claimed:
                return None
            analysis = await repository.get_by_id(analysis_id)
    except Exception:
        logger.exception(
            "Failed while claiming or loading analysis",
            extra={"analysis_id": analysis_id},
        )
        # 선점 후 조회 과정에서 실패했다면 PROCESSING 작업을 FAILED로 변경
        if claimed:
            await _persist_failure(session_factory, analysis_id, WORKER_INTERNAL_ERROR)
        raise

    # 선점은 성공했지만 데이터를 조회하지 못한 비정상 상황
    if analysis is None:
        error = WorkerInternalFailure("Claimed analysis could not be loaded")
        logger.error(str(error), extra={"analysis_id": analysis_id})
        await _persist_failure(session_factory, analysis_id, WORKER_INTERNAL_ERROR)
        raise error
    return analysis


async def _persist_completion(
    session_factory,
    analysis_id: int,
    outcome,
    model_version: str | None,
    latency_ms: int,
) -> bool:
    """AI 분석 결과를 저장하고 PROCESSING 작업을 COMPLETED로 변경한다."""
    async with session_factory() as session:
        repository = SqlAlchemyAnalysisRepository(session)
        return await repository.mark_completed(
            analysis_id,
            is_plant=outcome.is_plant,
            disease_code=outcome.disease_code,
            disease_name=outcome.disease_name,
            explain=outcome.explain,
            cause=outcome.cause,
            cure=outcome.cure,
            model_version=model_version,
            latency_ms=latency_ms,
        )


async def _persist_failure(
    session_factory,
    analysis_id: int,
    error_code: str,
) -> None:
    """
    PROCESSING 작업을 FAILED로 변경한다.
    원본 예외는 로그에만 남기고 DB에는 고정된 안전 메시지만 저장한다.
    실패 상태 저장이 다시 실패하더라도 원래 예외 처리를 방해하지 않는다.
    """
    safe_message = SAFE_ERROR_MESSAGES[error_code][:MAX_PERSISTED_ERROR_MESSAGE_LENGTH]
    try:
        async with session_factory() as session:
            repository = SqlAlchemyAnalysisRepository(session)
            failed = await repository.mark_failed(
                analysis_id,
                error_code=error_code,
                error_message=safe_message,
            )
        if not failed:
            logger.error(
                "Analysis failure transition was rejected",
                extra={"analysis_id": analysis_id, "error_code": error_code},
            )
    except Exception:
        logger.exception(
            "Failed to persist worker failure",
            extra={"analysis_id": analysis_id, "error_code": error_code},
        )


def _remove_owned_temporary_file(
    download_result: ImageDownloadResult | None,
    analysis_id: int,
) -> None:
    """Worker가 이번 작업에서 생성한 임시 이미지 파일만 삭제한다."""
    if (
        download_result is None
        or not download_result.is_temporary
        or download_result.path is None
    ):
        return

    try:
        Path(download_result.path).unlink(missing_ok=True)
    except Exception:
        logger.warning(
            "Failed to remove temporary analysis image",
            exc_info=True,
            extra={"analysis_id": analysis_id},
        )
