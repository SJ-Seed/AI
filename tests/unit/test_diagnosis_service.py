import unittest
from unittest.mock import Mock

from app.application.services.diagnosis_service import DiagnosisService
from app.domain.exceptions import InvalidDiagnosisResponse


class DiagnosisServiceTest(unittest.TestCase):
    def setUp(self):
        self.detector = Mock()
        self.classifier = Mock()
        self.explainer = Mock()
        self.service = DiagnosisService(self.detector, self.classifier, self.explainer)

    def test_detector_is_called_once_without_internal_retry(self):
        self.detector.analyze_image.return_value = "invalid"

        with self.assertRaises(InvalidDiagnosisResponse):
            self.service.diagnose("image", "28", "85")

        self.detector.analyze_image.assert_called_once_with("image")
        self.classifier.analyze_disease.assert_not_called()

    def test_not_a_plant_short_circuits(self):
        self.detector.analyze_image.return_value = "False"

        self.assertEqual(
            self.service.diagnose("image", "28", "85"),
            ("식물아님", None, None, None),
        )
        self.classifier.analyze_disease.assert_not_called()

    def test_healthy_short_circuits_explainer(self):
        self.detector.analyze_image.return_value = "True"
        self.classifier.analyze_disease.return_value = "Healthy"

        self.assertEqual(
            self.service.diagnose("image", "28", "85"),
            ("정상", None, None, None),
        )
        self.explainer.explain.assert_not_called()

    def test_known_disease_is_explained(self):
        self.detector.analyze_image.return_value = "True"
        self.classifier.analyze_disease.return_value = "Leaf_mold"
        self.explainer.explain.return_value = ("explain", "cause", "cure")

        outcome = self.service.diagnose_with_details("image", "28", "85")

        self.assertEqual(outcome.disease_code, "Leaf_mold")
        self.assertEqual((outcome.explain, outcome.cause, outcome.cure), ("explain", "cause", "cure"))

    def test_unknown_disease_is_permanent_invalid_response(self):
        self.detector.analyze_image.return_value = "True"
        self.classifier.analyze_disease.return_value = "Unknown"

        with self.assertRaises(InvalidDiagnosisResponse):
            self.service.diagnose("image", "28", "85")
        self.explainer.explain.assert_not_called()


if __name__ == "__main__":
    unittest.main()
