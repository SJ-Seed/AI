import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.infrastructure.ai.openai_detector import OpenAIPlantDetector


class OpenAIPlantDetectorTest(unittest.TestCase):
    def test_request_and_response_contract_are_unchanged(self):
        create = Mock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="True"))],
        ))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as image:
            image.write(b"image")
            image_path = image.name
        try:
            result = OpenAIPlantDetector(client).analyze_image(image_path)
        finally:
            Path(image_path).unlink()

        self.assertEqual(result, "True")
        create.assert_called_once()
        request = create.call_args.kwargs
        self.assertEqual(request["model"], "gpt-4o")
        self.assertEqual(request["temperature"], 0.0)
        self.assertEqual(request["messages"][0], {
            "role": "system",
            "content": "You are a plant detector.",
        })
        self.assertEqual(
            request["messages"][1]["content"][0]["text"],
            "식물(잎)이 중심인 사진이면 'True', 다른 객체 중심인 사진이면 'False'라고 답하세요설명은 덧붙이지 마세요.",
        )


if __name__ == "__main__":
    unittest.main()
