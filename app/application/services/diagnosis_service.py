"""
토마토 질병 진단의 핵심 비즈니스 로직을 담당한다.
"""

import time

from app.application.ports.classifier import DiseaseClassifier
from app.application.ports.detector import PlantDetector
from app.application.ports.explainer import DiseaseExplainer
from app.domain.models import DiagnosisResult


"""
식물 여부 확인, 질병 분류, 질병 설명 생성을 수행하는 서비스
"""
class DiagnosisService:
    def __init__(self, detector: PlantDetector, classifier: DiseaseClassifier, explainer: DiseaseExplainer) -> None:
        self.detector = detector
        self.classifier = classifier
        self.explainer = explainer

    """
    이미지를 분석하여 최종 진단 결과 반환
    """
    def diagnose(self, image_path: str, temperature: str, humidity: str) -> DiagnosisResult:
        for _ in range(0, 5):
            is_plant = self.detector.analyze_image(image_path)
            if is_plant in ["True", "False"]:
                break
            time.sleep(1.5)
        if is_plant == "False":
            return "식물아님", None, None, None

        disease = self.classifier.analyze_disease(image_path)
        if disease == "Healthy":
            return "정상", None, None, None

        # 모델의 질병명을 사용자에게 보여줄 한글명으로 변환 (TODO: 딕셔너리로 수정)
        explained, cause, cure = self.explainer.explain(disease, temperature, humidity)
        if disease == "Bacterial_spot":
            disease = "세균성 점무늬병"
        elif disease == "Early_blight":
            disease = "반점병"
        elif disease == "Late_blight":
            disease = "잎마름병"
        elif disease == "Leaf_mold":
            disease = "잎곰팡이병"
        elif disease == "Mosaic_virus":
            disease = "모자이크병"
        elif disease == "Septoria_leaf_spot":
            disease = "흰별무늬병"
        elif disease == "Spider_mites_two_spotted_spider_mite":
            disease = "점박이응애로 인한 피해"
        elif disease == "Yellowleaf_curl_virus":
            disease = "황화잎말림 바이러스"
        return disease, explained, cause, cure
