#!/usr/bin/env python3
"""로컬 readiness 상태를 CloudWatch Agent의 StatsD 리스너로 전송"""

from __future__ import annotations

import argparse
import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# CloundWatch에 기록될 StatsD 지표 이름
METRIC_API = "HealthApi"
METRIC_POSTGRESQL = "HealthPostgresql"
METRIC_REDIS = "HealthRedis"


def _read_health(url: str, timeout_seconds: float) -> tuple[int, bytes]:
    """Health API를 호출하고 HTTP 상태 코드와 응답 본문을 반환"""

    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.read()
    except HTTPError as error:
        if error.code == 503:
            return error.code, error.read()
        raise


def _is_up(service: Any) -> bool:
    """서비스 정보가 객체이고 status 값이 up인지 확인"""
    return isinstance(service, dict) and service.get("status") == "up"


def collect_health_metrics(
    url: str,
    timeout_seconds: float = 5.0,
) -> dict[str, int]:
    """Health API 결과를 외부 정보가 없는 안정적인 0/1 지표로 변환"""

    try:
        status_code, body = _read_health(url, timeout_seconds)

        # 예상하지 못한 HTTP 상태이면 API 장애로 처리
        if status_code not in {200, 503}:
            return {METRIC_API: 0}

        # JSON 응답을 Python 객체로 변환
        payload = json.loads(body)
        services = payload.get("services")

        # services가 없거나 API 자체가 정상 상태가 아니면 다른 서비스 지표는 보내지 않고 API 장애만 기록
        if not isinstance(services, dict) or not _is_up(services.get("api")):
            return {METRIC_API: 0}

        postgresql = services.get("postgresql")
        redis = services.get("redis")

        # 필수 서비스 정보의 형식이 잘못된 경우 응답 전체 신뢰 X
        if not isinstance(postgresql, dict) or not isinstance(redis, dict):
            return {METRIC_API: 0}

        # 정상은 1, 비정상은 0으로 변환
        return {
            METRIC_API: 1,
            METRIC_POSTGRESQL: int(_is_up(postgresql)),
            METRIC_REDIS: int(_is_up(redis)),
        }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
        return {METRIC_API: 0}


def format_statsd(metrics: dict[str, int]) -> bytes:
    """지표를 StatsD gauge 형식의 ASCII 바이트로 변환"""

    return "\n".join(
        f"{name}:{value}|g" for name, value in metrics.items()
    ).encode("ascii")


def emit_metrics(metrics: dict[str, int], host: str, port: int) -> None:
    """UDP를 통해 StatsD 리스너로 지표를 전송"""

    # StatsD는 일반적으로 UDP를 사용
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.sendto(format_statsd(metrics), (host, port))


def parse_args() -> argparse.Namespace:
    """명령행 실행 옵션을 정의하고 읽기"""
    parser = argparse.ArgumentParser(description=__doc__)

    # readiness 상태를 확인할 API 주소
    parser.add_argument("--url", default="http://localhost:8000/health")

    # Health API 응답을 기다릴 최대 시간
    parser.add_argument("--timeout-seconds", type=float, default=5.0)

    # CloudWatch Agent StatsD 리스너 주소
    parser.add_argument("--statsd-host", default="127.0.0.1")

    # CloudWatch Agent StatsD 리스너 포트
    parser.add_argument("--statsd-port", type=int, default=8125)
    return parser.parse_args()


def main() -> int:
    """상태를 수집하고 StatsD로 전송"""
    args = parse_args()

    # Health API 결과를 0/1 지표로 변환
    metrics = collect_health_metrics(args.url, args.timeout_seconds)
    try:
        # 변환된 지표를 CloudWatch Agent로 전송
        emit_metrics(metrics, args.statsd_host, args.statsd_port)
    except OSError:
        # systemd 로그에는 민감할 수 있는 네트워크 주소나 응답 본문 없이 간단한 오류만
        print("Health metrics could not be delivered", flush=True)
        return 1
    return 0


# 이 파일을 직접 실행했을 때만 main()을 호출
if __name__ == "__main__":
    raise SystemExit(main())
