"""
애플리케이션에서 사용하는 도메인 모델 및 공통 타입을 정의한다.
"""

from typing import TypeAlias

# 질병 진단 결과 (질병명, 설명, 원인, 해결 방법)
DiagnosisResult: TypeAlias = tuple[
    str,
    str | None,
    str | None,
    str | None,
]
