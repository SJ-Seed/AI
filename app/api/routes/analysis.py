from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_diagnosis_service, get_image_downloader
from app.api.schemas import AnalyzeRequest
from app.application.services.diagnosis_service import DiagnosisService
from app.infrastructure.image.image_downloader import ImageDownloader


router = APIRouter()


@router.post("/analyze")
async def analyze_endpoint(
    body: AnalyzeRequest,
    service: DiagnosisService = Depends(get_diagnosis_service),
    image_downloader: ImageDownloader = Depends(get_image_downloader),
):
    image_path = body.image_path
    temperature = body.temperature
    humidity = body.humidity

    local_image_path, download_error = image_downloader.download(image_path)
    if download_error is not None:
        return JSONResponse(content={"photo": download_error})

    result = service.diagnose(local_image_path, temperature, humidity)
    disease, explained, cause, cure = result

    if disease == "식물아님":
        return JSONResponse(content={
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!",
        })
    elif disease == "정상":
        return JSONResponse(content={
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!",
        })
    else:
        return JSONResponse(content={
            "photo": True,
            "state": disease,
            "message": "식물이 아파요",
            "explain": explained,
            "cause": cause,
            "cure": cure,
        })
