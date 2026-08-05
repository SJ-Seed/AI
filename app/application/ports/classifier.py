"""
질병 분류 기능을 위한 인터페이스를 정의한다.
"""

from typing import Protocol


class DiseaseClassifier(Protocol):
    def analyze_disease(self, image_path: str) -> str:
        ...
