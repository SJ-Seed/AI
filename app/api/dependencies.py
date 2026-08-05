"""
FastAPI 의존성 주입에 사용되는 객체 제공
"""

from fastapi import Request

from app.application.services.diagnosis_service import DiagnosisService
from app.infrastructure.image.image_downloader import ImageDownloader


def get_diagnosis_service(request: Request) -> DiagnosisService:
    return request.app.state.diagnosis_service


def get_image_downloader(request: Request) -> ImageDownloader:
    return request.app.state.image_downloader
