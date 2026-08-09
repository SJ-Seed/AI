"""
FastAPI 의존성 주입에 사용되는 객체 제공
"""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.analysis_queue import AnalysisQueue
from app.application.ports.analysis_repository import AnalysisRepository
from app.infrastructure.persistence.analysis_repository import SqlAlchemyAnalysisRepository


def get_analysis_queue(request: Request) -> AnalysisQueue:
    return request.app.state.analysis_queue


# 요청마다 사용할 비동기 DB 세션 제공
async def _get_db_session() -> AsyncIterator[AsyncSession]:
    # 실제 DB 설정은 필요할 때만 로드
    from app.infrastructure.persistence.database import get_db_session

    async for session in get_db_session():
        yield session


# DB 세션을 사용해 Analysis Repository 생성
def get_analysis_repository(
    session: AsyncSession = Depends(_get_db_session),
) -> AnalysisRepository:
    return SqlAlchemyAnalysisRepository(session)
