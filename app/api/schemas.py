"""
API 요청 및 응답에 사용되는 데이터 모델 정의
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import AnalysisStatus


class AnalyzeRequest(BaseModel):
    """클라이언트가 분석을 요청할 때 전달하는 데이터"""
    image_path: str
    temperature: str
    humidity: str


class AnalyzeAcceptedResponse(BaseModel):
    """분석 요청이 Queue에 정상적으로 접수됐을 때 반환하는 데이터"""
    analysis_id: int
    status: AnalysisStatus
    status_url: str


class AnalysisResponse(BaseModel):
    """저장된 분석 작업의 진행 상태와 결과를 조회할 때 반환하는 데이터"""
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
