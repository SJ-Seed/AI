"""분석 작업을 비동기 Queue에 등록하기 위한 인터페이스"""

from typing import Protocol


class AnalysisQueue(Protocol):
    """Application 계층에서 사용하는 분석 Queue 인터페이스"""

    async def enqueue(self, analysis_id: int) -> None:
        """분석 ID를 비동기 작업 Queue에 등록"""
        ...
