"""분석 요청 접수 및 분석 결과 조회 API"""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_analysis_queue, get_analysis_repository
from app.api.schemas import AnalysisResponse, AnalyzeAcceptedResponse, AnalyzeRequest
from app.application.ports.analysis_queue import AnalysisQueue
from app.application.ports.analysis_repository import AnalysisRepository
from app.core.logging import get_logger, log_analysis_status_change
from app.domain.enums import AnalysisStatus


router = APIRouter()
logger = get_logger(__name__)

QUEUE_ENQUEUE_ERROR_CODE = "QUEUE_ENQUEUE_FAILED"
MAX_PERSISTED_ERROR_MESSAGE_LENGTH = 255
SAFE_QUEUE_ERROR_MESSAGE = "Analysis queue is temporarily unavailable"


# 분석 ID로 저장된 분석 이력 조회
@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    name="get_analysis_endpoint",
)
async def get_analysis_endpoint(
    analysis_id: int,
    repository: AnalysisRepository = Depends(get_analysis_repository),
) -> dict[str, object]:
    # DB에서 분석 ID에 해당하는 분석 작업과 결과를 조회
    analysis = await repository.get_by_id(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


# 분석 요청을 접수하고 비동기 큐에 등록
@router.post(
    "/analyze",
    response_model=AnalyzeAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_endpoint(
    body: AnalyzeRequest,
    response: Response,
    repository: AnalysisRepository = Depends(get_analysis_repository),
    queue: AnalysisQueue = Depends(get_analysis_queue),
) -> AnalyzeAcceptedResponse:
    """
    분석 요청을 접수하고 분석 ID를 Queue에 등록한다.
    이 API에서는 이미지 다운로드나 AI 분석을 직접 실행하지 않는다.
    """

    # 1. 요청 정보를 PENDING 상태의 분석 작업으로 DB에 저장
    analysis_id = await repository.create(
        image_path=body.image_path,
        temperature=body.temperature,
        humidity=body.humidity,
    )
    # PENDING 상태가 된 순간 로그를 남기는 호출
    log_analysis_status_change(
        logger,
        analysis_id=analysis_id,
        status=AnalysisStatus.PENDING.value,
        duration_ms=0,
        retry_count=0,
    )

    try:
        # 2. Worker가 처리할 수 있도록 큐에는 분석 ID만 등록
        await queue.enqueue(analysis_id)
    except Exception as error:
        # DB에 남아 있는 PENDING 작업을 FAILED 상태로 변경
        logger.error(
            "Failed to enqueue analysis because the queue is unavailable",
            extra={"analysis_id": analysis_id},
        )
        try:
            compensated = await repository.mark_enqueue_failed(
                analysis_id,
                error_code=QUEUE_ENQUEUE_ERROR_CODE,
                error_message=SAFE_QUEUE_ERROR_MESSAGE[
                    :MAX_PERSISTED_ERROR_MESSAGE_LENGTH
                ],
            )
            # 이미 상태가 바뀌었거나 작업을 찾지 못해 보상 처리 되지 않은 경우
            if not compensated:
                logger.error(
                    "Analysis enqueue failure compensation was not applied",
                    extra={"analysis_id": analysis_id},
                )
            else:
                # 분석 작업의 큐 등록이 실패해서 DB 상태를 FAILED로 변경한 뒤 남기는 구조화 로그
                log_analysis_status_change(
                    logger,
                    analysis_id=analysis_id,
                    status=AnalysisStatus.FAILED.value,
                    duration_ms=0,
                    retry_count=0,
                    failure_reason=QUEUE_ENQUEUE_ERROR_CODE,
                )
        except Exception:
            # 큐 등록 실패를 DB에 기록하는 작업까지 실패한 경우
            logger.error(
                "Failed to persist analysis queue failure",
                extra={"analysis_id": analysis_id},
            )

        # 큐가 현재 요청을 받을 수 없으므로 503 반환
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis queue unavailable",
        ) from error

    # Redis 등록이 확인된 작업은 reconciliation 대상에서 제외
    try:
        marked_enqueued = await repository.mark_enqueued(analysis_id)
        if not marked_enqueued:
            logger.info(
                "Analysis Queue registration was already recorded",
                extra={"analysis_id": analysis_id},
            )
    except Exception:
        # 큐 등록 후 DB 기록에 실패한 경우, 후속 복구를 위해 작업 ID와 함께 오류를 기록
        logger.error(
            "Failed to record analysis queue registration",
            extra={"analysis_id": analysis_id},
        )

    # 3. 클라이언트가 분석 상태를 조회할 수 있는 API 주소 생성
    status_url = f"/analyses/{analysis_id}"
    response.headers["Location"] = status_url

    # 4. 분석 완료를 기다리지 않고 접수 결과를 즉시 반환
    return AnalyzeAcceptedResponse(
        analysis_id=analysis_id,
        status=AnalysisStatus.PENDING,
        status_url=status_url,
    )
