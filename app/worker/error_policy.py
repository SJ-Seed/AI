"""발생한 오류를 재시도할지 즉시 실패시킬지 판단"""

from dataclasses import dataclass

import httpx
import requests
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.domain.exceptions import InvalidDiagnosisResponse


@dataclass(frozen=True)
class ErrorDisposition:
    retryable: bool     # 이 오류를 재시도할지 여부
    error_code: str     # 최종 실패 시 DB에 저장할 오류 코드


def classify_ai_error(error: BaseException) -> ErrorDisposition:
    for current in _exception_chain(error):
        if isinstance(current, AuthenticationError) or _status_code(current) == 401:
            return ErrorDisposition(False, "AI_AUTHENTICATION_ERROR")
        if isinstance(current, InvalidDiagnosisResponse):
            return ErrorDisposition(False, "AI_ANALYSIS_ERROR")
        if isinstance(
            current,
            (
                APIConnectionError,
                APITimeoutError,
                RateLimitError,
                InternalServerError,
                requests.Timeout,
                requests.ConnectionError,
                httpx.TimeoutException,
                httpx.TransportError,
            ),
        ):
            return ErrorDisposition(True, "AI_ANALYSIS_ERROR")
        status = _status_code(current)
        if status is not None:
            if status in (408, 409, 429) or status >= 500:
                return ErrorDisposition(True, "AI_ANALYSIS_ERROR")
            if isinstance(current, APIStatusError) or status in (400, 403, 404, 422):
                return ErrorDisposition(False, "AI_ANALYSIS_ERROR")
    return ErrorDisposition(False, "WORKER_INTERNAL_ERROR")


def _status_code(error: BaseException) -> int | None:
    value = getattr(error, "status_code", None)
    if value is None:
        response = getattr(error, "response", None)
        value = getattr(response, "status_code", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _exception_chain(error: BaseException):
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__
