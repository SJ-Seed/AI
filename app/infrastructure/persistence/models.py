from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import AnalysisStatus
from app.infrastructure.persistence.base import Base


""" AI 분석 작업 및 결과 이력을 저장하는 ORM 모델 (Analysis 객체와 PostgreSQL의 analyses 테이블 매핑) """
class Analysis(Base):
    __tablename__ = "analyses"

    # 자동 증가 PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 분석 작업의 현재 상태
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        nullable=False,
        default=AnalysisStatus.PENDING,
        server_default=AnalysisStatus.PENDING.value,
    )

    # 분석 요청에 포함된 원본 이미지 경로 또는 URL
    image_path: Mapped[str] = mapped_column(String, nullable=False)

    # 현재 API 요청 스키마에서 문자열로 전달되는 온도와 습도
    temperature: Mapped[str] = mapped_column(String, nullable=False)
    humidity: Mapped[str] = mapped_column(String, nullable=False)

    # OpenAI detector의 식물 판별 결과
    is_plant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # DSPy classifier가 반환한 영문 질병 레이블
    disease_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # 사용자에게 표시하는 한글 질병명
    disease_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # DSPy가 생성한 질병 설명, 원인, 치료 방법
    explain: Mapped[str | None] = mapped_column(Text, nullable=True)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    cure: Mapped[str | None] = mapped_column(Text, nullable=True)

    # compiled DSPy classifier artifact의 애플리케이션 관리 버전
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)

    # 분석 처리에 걸린 시간 (ms)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 향후 비동기 Analysis Job 자체의 재시도 횟수
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # 분석 실패를 구분하기 위한 오류 코드
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # 분석 실패에 대한 상세 오류 메시지
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 분석 요청이 생성된 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Worker가 실제 분석을 시작한 시각
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 분석이 성공 또는 실패로 종료된 시각
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
