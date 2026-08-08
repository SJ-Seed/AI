from time import perf_counter

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import (
    get_analysis_repository,
    get_diagnosis_service,
    get_image_downloader,
    get_model_version,
)
from app.api.schemas import AnalyzeRequest
from app.application.ports.analysis_repository import AnalysisRepository
from app.application.services.diagnosis_service import DiagnosisService
from app.core.logging import get_logger
from app.infrastructure.image.image_downloader import ImageDownloader


router = APIRouter()
logger = get_logger(__name__)


@router.post("/analyze")
async def analyze_endpoint(
    body: AnalyzeRequest,
    service: DiagnosisService = Depends(get_diagnosis_service),
    image_downloader: ImageDownloader = Depends(get_image_downloader),
    repository: AnalysisRepository = Depends(get_analysis_repository),
    model_version: str | None = Depends(get_model_version),
):
    image_path = body.image_path
    temperature = body.temperature
    humidity = body.humidity

    analysis_id = await repository.create(
        image_path=image_path,
        temperature=temperature,
        humidity=humidity,
    )
    await repository.mark_processing(analysis_id)
    started_at = perf_counter()

    try:
        local_image_path, download_error = image_downloader.download(image_path)
        if download_error is None:
            outcome = service.diagnose_with_details(
                local_image_path,
                temperature,
                humidity,
            )
    except Exception as error:
        try:
            await repository.mark_failed(
                analysis_id,
                error_code=type(error).__name__,
                error_message=str(error),
            )
        except Exception:
            logger.exception(
                "Failed to persist analysis failure",
                extra={"analysis_id": analysis_id},
            )
        raise

    if download_error is not None:
        await repository.mark_failed(
            analysis_id,
            error_code="IMAGE_DOWNLOAD_ERROR",
            error_message=download_error,
        )
        return JSONResponse(content={"photo": download_error})

    latency_ms = int((perf_counter() - started_at) * 1000)
    await repository.mark_completed(
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

    if outcome.is_plant is False:
        return JSONResponse(content={
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!",
        })
    elif outcome.disease_code == "Healthy":
        return JSONResponse(content={
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!",
        })
    else:
        return JSONResponse(content={
            "photo": True,
            "state": outcome.disease_name,
            "message": "식물이 아파요",
            "explain": outcome.explain,
            "cause": outcome.cause,
            "cure": outcome.cure,
        })
