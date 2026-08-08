from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import load_settings

# 데이터베이스 읽어오기
settings = load_settings()

# PostgreSQL 비동기 연결을 위한 SQLAlchemy Engine 생성
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# 요청별 DB 세션을 생성하는 비동기 Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# FastAPI Dependency에서 사용할 DB 세션 제공
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session