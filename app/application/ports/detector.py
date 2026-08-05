"""
식물 판별 기능을 위한 인터페이스를 정의한다.
"""

from typing import Protocol


class PlantDetector(Protocol):
    def analyze_image(self, image_path: str) -> str:
        ...
