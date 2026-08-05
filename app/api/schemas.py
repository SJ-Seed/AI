"""
API 요청 및 응답에 사용되는 데이터 모델 정의
"""

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    image_path: str
    temperature: str
    humidity: str
