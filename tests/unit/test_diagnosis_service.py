import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
