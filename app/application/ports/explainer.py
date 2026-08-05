"""
질병 설명 생성 기능을 위한 인터페이스를 정의한다.
"""

from typing import Protocol


class DiseaseExplainer(Protocol):
    def explain(
        self,
        disease: str,
        temperature: str,
        humidity: str,
    ) -> tuple[str, str, str]:
        ...
