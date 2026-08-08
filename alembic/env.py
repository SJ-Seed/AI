import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Analysis 같은 ORM 모델을 import해서 Base.metadata에 등록한다.
# Alembic은 Base.metadata를 보고 현재 코드에 어떤 테이블이 정의되어 있는지 확인한다.
from app.infrastructure.persistence import models  # noqa: F401
from app.infrastructure.persistence.base import Base


# alembic.ini의 설정을 가져온다.
config = context.config

# alembic.ini에 정의된 로그 설정을 적용한다.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DB 접속 정보는 alembic.ini에 직접 작성하지 않고 환경변수 DATABASE_URL에서 가져온다.
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is required")

# DATABASE_URL을 Alembic의 sqlalchemy.url 설정에 주입한다.
# ConfigParser에서는 %가 특수문자로 사용되므로 비밀번호 등에 URL 인코딩된 %가 포함된 경우 %%로 이스케이프한다.
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Alembic이 migration을 자동 생성할 때 비교 기준으로 사용할 ORM 메타데이터
# 현재는 Base를 상속한 Analysis 모델의 analyses 테이블 정보가 여기에 포함된다.
target_metadata = Base.metadata


"""
실제 DB에 연결하지 않고 migration SQL을 생성할 때 사용한다.
"""
def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    # 하나의 트랜잭션 안에서 migration을 실행한다.
    with context.begin_transaction():
        context.run_migrations()


"""
실제 DB 연결을 전달받아 migration을 실행
"""
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


"""
현재 프로젝트의 async SQLAlchemy 설정에 맞게 비동기 DB Engine을 생성하고 PostgreSQL에 연결
"""
async def run_async_migrations() -> None:
    """Run migrations with SQLAlchemy's async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


"""
실제 PostgreSQL에 연결해서 migration을 실행
"""
def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

