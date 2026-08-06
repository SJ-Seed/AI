import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ["DSPY_CACHEDIR"] = str(Path(tempfile.gettempdir()) / "sjseed-dspy-test-cache")

from app.infrastructure.ai.disease_explainer import DspyDiseaseExplainer
from app.infrastructure.ai.dspy_classifier import DspyDiseaseClassifier


class DspyDiseaseClassifierTest(unittest.TestCase):
    @patch("app.infrastructure.ai.dspy_classifier.dspy.context")
    @patch("app.infrastructure.ai.dspy_classifier.image_to_dspy_image")
    def test_input_and_output_contract(self, image_to_dspy_image, context):
        dspy_image = object()
        image_to_dspy_image.return_value = dspy_image
        compiled_program = Mock(return_value=SimpleNamespace(answer="Leaf_mold"))
        lm = object()
        classifier = DspyDiseaseClassifier(compiled_program, lm)

        result = classifier.analyze_disease("local.jpg")

        self.assertEqual(result, "Leaf_mold")
        image_to_dspy_image.assert_called_once_with("local.jpg")
        context.assert_called_once_with(lm=lm)
        context.return_value.__enter__.assert_called_once_with()
        context.return_value.__exit__.assert_called_once()
        compiled_program.assert_called_once_with(image=dspy_image)


class DspyDiseaseExplainerTest(unittest.TestCase):
    @patch("app.infrastructure.ai.disease_explainer.dspy.context")
    def test_input_and_output_contract(self, context):
        predictor = Mock(return_value=SimpleNamespace(
            explain="explanation",
            cause="cause",
            cure="cure",
        ))
        lm = object()
        explainer = DspyDiseaseExplainer(predictor, lm)

        result = explainer.explain("Leaf_mold", "28", "85")

        self.assertEqual(result, ("explanation", "cause", "cure"))
        context.assert_called_once_with(lm=lm)
        context.return_value.__enter__.assert_called_once_with()
        context.return_value.__exit__.assert_called_once()
        predictor.assert_called_once_with(
            disease="Leaf_mold",
            temperature="28",
            humidity="85",
        )


if __name__ == "__main__":
    unittest.main()
