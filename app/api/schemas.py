"""
API 요청 및 응답에 사용되는 데이터 모델 정의
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import AnalysisStatus


class AnalyzeRequest(BaseModel):
    image_path: str
    temperature: str
    humidity: str


class AnalysisResponse(BaseModel):
    id: int
    status: AnalysisStatus
    image_path: str
    temperature: str
    humidity: str
    is_plant: bool | None
    disease_code: str | None
    disease_name: str | None
    explain: str | None
    cause: str | None
    cure: str | None
    model_version: str | None
    latency_ms: int | None
    retry_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
