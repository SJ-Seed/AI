import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from openai import APITimeoutError, InternalServerError, RateLimitError

from app.infrastructure.ai.openai_detector import OpenAIPlantDetector


class OpenAIPlantDetectorTest(unittest.TestCase):
    def analyze_with_create(self, create):
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as image:
            image.write(b"image")
            image_path = image.name
        try:
            return OpenAIPlantDetector(client).analyze_image(image_path)
        finally:
            Path(image_path).unlink()

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


    def test_missing_choices_attribute_raises_attribute_error(self):
        create = Mock(return_value=SimpleNamespace())

        with self.assertRaises(AttributeError):
            self.analyze_with_create(create)

    def test_empty_choices_raises_index_error(self):
        create = Mock(return_value=SimpleNamespace(choices=[]))

        with self.assertRaises(IndexError):
            self.analyze_with_create(create)

    def test_none_message_content_is_returned_unchanged(self):
        create = Mock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
        ))

        self.assertIsNone(self.analyze_with_create(create))

    def test_whitespace_and_mixed_case_content_is_returned_unchanged(self):
        for content in (" true ", "FALSE", "\nTrUe\t"):
            with self.subTest(content=content):
                create = Mock(return_value=SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                ))

                self.assertEqual(self.analyze_with_create(create), content)

    def test_openai_errors_are_propagated(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        errors = (
            APITimeoutError(request=request),
            RateLimitError(
                "rate limit",
                response=httpx.Response(429, request=request),
                body=None,
            ),
            InternalServerError(
                "server error",
                response=httpx.Response(500, request=request),
                body=None,
            ),
        )

        for error in errors:
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(type(error)) as raised:
                    self.analyze_with_create(Mock(side_effect=error))

                self.assertIs(raised.exception, error)


if __name__ == "__main__":
    unittest.main()
