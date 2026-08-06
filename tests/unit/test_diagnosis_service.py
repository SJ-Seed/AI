import unittest
from unittest.mock import Mock, patch

from app.application.services.diagnosis_service import DiagnosisService


class FakeDetector:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = 0

    def analyze_image(self, image_path):
        self.calls += 1
        return next(self.results)


class FakeClassifier:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def analyze_disease(self, image_path):
        self.calls += 1
        return self.result


class FakeExplainer:
    def __init__(self):
        self.calls = 0

    def explain(self, disease, temperature, humidity):
        self.calls += 1
        return "설명", "원인", "치료"


class DiagnosisServiceTest(unittest.TestCase):
    def test_not_a_plant_preserves_result_and_short_circuits(self):
        detector = FakeDetector(["False"])
        classifier = FakeClassifier("Healthy")
        explainer = FakeExplainer()
        service = DiagnosisService(detector, classifier, explainer)

        self.assertEqual(service.diagnose("image", "temp", "humidity"), ("식물아님", None, None, None))
        self.assertEqual(classifier.calls, 0)
        self.assertEqual(explainer.calls, 0)

    def test_healthy_preserves_result_and_skips_explanation(self):
        classifier = FakeClassifier("Healthy")
        explainer = FakeExplainer()
        service = DiagnosisService(FakeDetector(["True"]), classifier, explainer)

        self.assertEqual(service.diagnose("image", "temp", "humidity"), ("정상", None, None, None))
        self.assertEqual(explainer.calls, 0)

    def test_disease_preserves_translation_and_explanation(self):
        service = DiagnosisService(
            FakeDetector(["True"]),
            FakeClassifier("Leaf_mold"),
            FakeExplainer(),
        )
        self.assertEqual(
            service.diagnose("image", "temp", "humidity"),
            ("잎곰팡이병", "설명", "원인", "치료"),
        )

    @patch("app.application.services.diagnosis_service.time.sleep")
    def test_detector_retries_exactly_as_before(self, sleep):
        detector = FakeDetector(["invalid", "invalid", "True"])
        service = DiagnosisService(detector, FakeClassifier("Healthy"), FakeExplainer())
        service.diagnose("image", "temp", "humidity")
        self.assertEqual(detector.calls, 3)
        self.assertEqual(sleep.call_args_list[0].args, (1.5,))
        self.assertEqual(sleep.call_count, 2)

    @patch("app.application.services.diagnosis_service.time.sleep")
    def test_detector_retry_exhaustion_preserves_current_behavior(self, sleep):
        # detector가 유효하지 않은 값을 5번만 반환하도록 설정
        detector = FakeDetector(["invalid"] * 5)
        classifier = FakeClassifier("Unknown_disease")
        explainer = FakeExplainer()
        service = DiagnosisService(detector, classifier, explainer)

        # 재시도 횟수를 모두 소진한 뒤에도 classifier와 explainer가 호출되는지 확인
        self.assertEqual(
            service.diagnose("image", "temp", "humidity"),
            ("Unknown_disease", "설명", "원인", "치료"),
        )
        self.assertEqual(detector.calls, 5)
        self.assertEqual(sleep.call_count, 5)
        sleep.assert_called_with(1.5)
        self.assertEqual(classifier.calls, 1)
        self.assertEqual(explainer.calls, 1)

    def test_detector_exception_is_propagated(self):
        # detector에서 발생한 예외가 그대로 상위로 전달되는지 확인
        error = RuntimeError("detector failure")
        detector = Mock()
        detector.analyze_image.side_effect = error
        classifier = Mock()
        explainer = Mock()
        service = DiagnosisService(detector, classifier, explainer)

        with self.assertRaises(RuntimeError) as raised:
            service.diagnose("image", "temp", "humidity")

        # 새 예외로 감싸지 않고 동일한 예외 객체가 전달되어야 함
        self.assertIs(raised.exception, error)
        classifier.analyze_disease.assert_not_called()
        explainer.explain.assert_not_called()

    def test_classifier_exception_is_propagated(self):
        # classifier에서 발생한 예외가 그대로 전달되는지 확인
        error = RuntimeError("classifier failure")
        classifier = Mock()
        classifier.analyze_disease.side_effect = error
        explainer = Mock()
        service = DiagnosisService(FakeDetector(["True"]), classifier, explainer)

        with self.assertRaises(RuntimeError) as raised:
            service.diagnose("image", "temp", "humidity")

        self.assertIs(raised.exception, error)
        explainer.explain.assert_not_called()

    def test_explainer_exception_is_propagated(self):
        # explainer에서 발생한 예외가 그대로 전달되는지 확인
        error = RuntimeError("explainer failure")
        explainer = Mock()
        explainer.explain.side_effect = error
        service = DiagnosisService(
            FakeDetector(["True"]),
            FakeClassifier("Unknown_disease"),
            explainer,
        )

        with self.assertRaises(RuntimeError) as raised:
            service.diagnose("image", "temp", "humidity")

        self.assertIs(raised.exception, error)

    def test_unknown_disease_name_is_returned_unchanged(self):
        # 등록되지 않은 질병명은 번역하지 않고 그대로 반환되는지 확인
        explainer = Mock()
        explainer.explain.return_value = ("explanation", "cause", "cure")
        service = DiagnosisService(
            FakeDetector(["True"]),
            FakeClassifier("Unknown_disease"),
            explainer,
        )

        self.assertEqual(
            service.diagnose("image", "28", "85"),
            ("Unknown_disease", "explanation", "cause", "cure"),
        )
        explainer.explain.assert_called_once_with("Unknown_disease", "28", "85")

    def test_all_disease_names_are_translated_to_korean(self):
        # 지원하는 모든 영문 질병명이 올바른 한글명으로 변환되는지 확인
        disease_names = {
            "Bacterial_spot": "세균성 점무늬병",
            "Early_blight": "반점병",
            "Late_blight": "잎마름병",
            "Leaf_mold": "잎곰팡이병",
            "Mosaic_virus": "모자이크병",
            "Septoria_leaf_spot": "흰별무늬병",
            "Spider_mites_two_spotted_spider_mite": "점박이응애로 인한 피해",
            "Yellowleaf_curl_virus": "황화잎말림 바이러스",
        }

        for english_name, korean_name in disease_names.items():
            with self.subTest(disease=english_name):
                explainer = Mock()
                explainer.explain.return_value = ("explanation", "cause", "cure")
                service = DiagnosisService(
                    FakeDetector(["True"]),
                    FakeClassifier(english_name),
                    explainer,
                )

                self.assertEqual(
                    service.diagnose("image", "28", "85"),
                    (korean_name, "explanation", "cause", "cure"),
                )
                explainer.explain.assert_called_once_with(english_name, "28", "85")


if __name__ == "__main__":
    unittest.main()
