"""
토마토 질병 진단의 핵심 비즈니스 로직을 담당한다.
"""

import time

from app.application.ports.classifier import DiseaseClassifier
from app.application.ports.detector import PlantDetector
from app.application.ports.explainer import DiseaseExplainer
from app.domain.enums import DISEASE_NAMES_KO
from app.domain.models import DiagnosisOutcome, DiagnosisResult


class DiagnosisService:
    """ 식물 여부 확인, 질병 분류, 질병 설명 생성을 수행하는 서비스 """

    def __init__(self, detector: PlantDetector, classifier: DiseaseClassifier, explainer: DiseaseExplainer) -> None:
        self.detector = detector
        self.classifier = classifier
        self.explainer = explainer

    # 기존 API에서 사용하는 최종 진단 결과 반환
    def diagnose(self, image_path: str, temperature: str, humidity: str) -> DiagnosisResult:
        outcome = self.diagnose_with_details(image_path, temperature, humidity)
        if outcome.is_plant is False:
            return "식물아님", None, None, None

        return (
            outcome.disease_name or outcome.disease_code or "",
            outcome.explain,
            outcome.cause,
            outcome.cure,
        )

    # DB 저장에 필요한 상세 정보를 포함한 진단 결과 반환
    def diagnose_with_details(
        self,
        image_path: str,
        temperature: str,
        humidity: str,
    ) -> DiagnosisOutcome:
        is_plant_result: bool | None = None

        # OpenAI를 통해 식물 여부 판별 (유효한 응답이 없으면 최대 5회 시도)
        for _ in range(0, 5):
            is_plant = self.detector.analyze_image(image_path)
            if is_plant in ["True", "False"]:
                is_plant_result = is_plant == "True"
                break
            time.sleep(1.5)

        # 식물이 아닌 경우 질병 분석 없이 종료
        if is_plant == "False":
            return DiagnosisOutcome(False, None, None, None, None, None)

        # DSPy classifier를 통해 영문 질병 코드 분류
        disease_code = self.classifier.analyze_disease(image_path)

        # 정상 식물인 경우 추가 설명 생성 없이 종료
        if disease_code == "Healthy":
            return DiagnosisOutcome(True, "Healthy", "정상", None, None, None)

        # 질병인 경우 설명, 원인, 치료 방법 생성
        explained, cause, cure = self.explainer.explain(
            disease_code,
            temperature,
            humidity,
        )

        # DB 저장에 사용할 상세 진단 결과 반환
        return DiagnosisOutcome(
            is_plant_result,
            disease_code,
            DISEASE_NAMES_KO.get(disease_code, disease_code),
            explained,
            cause,
            cure,
        )
