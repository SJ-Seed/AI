"""
DSPy 모델을 이용하여 토마토 질병을 분류하는 구현체이다.
"""

import base64

import dspy
from dspy import Image

"""
이미지 파일을 DSPy에서 사용할 수 있는 Image 객체로 변환한다.
"""
def image_to_dspy_image(image_path: str) -> Image:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return Image(url=f"data:image/jpeg;base64,{b64}")

"""
DiseaseClassifier 인터페이스의 DSPy 구현체
"""
class DspyDiseaseClassifier:
    def __init__(self, compiled_program, lm) -> None:
        self.compiled_program = compiled_program
        self.lm = lm

    def analyze_disease(self, image_path):
        img = image_to_dspy_image(image_path)
        with dspy.context(lm=self.lm):
            result = self.compiled_program(image=img)
        return result.answer
