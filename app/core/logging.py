import logging

from pythonjsonlogger.json import JsonFormatter


# 동일한 JSON 핸들러가 여러 번 등록되는 것을 방지하기 위한 식별자
_HANDLER_MARKER = "_sjseed_json_handler"


def configure_logging() -> None:
    """외부 라이브러리에 영향을 주지 않고 애플리케이션 로거를 설정"""

    app_logger = logging.getLogger("app")
    if any(getattr(handler, _HANDLER_MARKER, False) for handler in app_logger.handlers):
        return

    # 로그를 표준 오류 스트림으로 출력
    handler = logging.StreamHandler()

    # CloudWatch에서 각 필드를 검색할 수 있도록 JSON 형식으로 출력
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    # 이 함수에서 생성한 핸들러임을 표시
    setattr(handler, _HANDLER_MARKER, True)
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)

    # 루트 로거로 다시 전달되어 같은 로그가 중복 출력되는 것을 방지
    app_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """공통 JSON 설정이 적용된 애플리케이션 로거를 반환한다."""

    # 로거를 사용하기 전에 공통 설정이 한 번 이상 실행되도록 보장
    configure_logging()
    return logging.getLogger(name)


def log_analysis_status_change(
    logger: logging.Logger,
    *,
    analysis_id: int,
    status: str,
    duration_ms: int,
    retry_count: int,
    failure_reason: str | None = None,
) -> None:
    """허용된 필드만 사용해 분석 상태 변경 이벤트를 기록"""

    logger.info(
        "Analysis status changed",
        extra={
            # CloudWatch에서 상태 변경 로그를 식별하기 위한 고정 이벤트명
            "event": "analysis_status_changed",

            # 상태가 변경된 분석 작업의 식별자
            "analysis_id": analysis_id,

            # 변경된 현재 상태: PENDING, PROCESSING, COMPLETED 또는 FAILED
            "status": status,

            # 현재 분석 처리 시도에 걸린 시간
            "duration_ms": max(0, duration_ms),

            # 현재 상태까지 수행된 재시도 횟수
            "retry_count": max(0, retry_count),

            # 실패 또는 재시도 원인을 나타내는 안전한 내부 오류 코드
            "failure_reason": failure_reason,
        },
    )
