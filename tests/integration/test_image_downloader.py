import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from requests.exceptions import Timeout

from app.infrastructure.image.image_downloader import ImageDownloader


class ImageDownloaderTest(unittest.TestCase):
    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_non_200_message_is_unchanged(self, get):
        get.return_value = Mock(status_code=404)
        self.assertEqual(
            ImageDownloader().download("https://example/image.jpg"),
            (None, "이미지를 불러올 수 없습니다."),
        )

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_exception_message_is_unchanged(self, get):
        get.side_effect = RuntimeError("failure")
        self.assertEqual(
            ImageDownloader().download("https://example/image.jpg"),
            (None, "이미지 다운로드 오류: failure"),
        )


    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_timeout_returns_existing_error_without_creating_file(self, get):
        get.side_effect = Timeout("timed out")

        with patch("app.infrastructure.image.image_downloader.tempfile.NamedTemporaryFile") as named_temp:
            self.assertEqual(
                ImageDownloader().download("https://example/image.jpg"),
                (None, "이미지 다운로드 오류: timed out"),
            )

        get.assert_called_once_with("https://example/image.jpg")
        named_temp.assert_not_called()

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_various_non_200_responses_return_existing_error(self, get):
        with patch("app.infrastructure.image.image_downloader.tempfile.NamedTemporaryFile") as named_temp:
            for status_code in (201, 301, 400, 404, 500):
                with self.subTest(status_code=status_code):
                    get.reset_mock()
                    get.return_value = Mock(status_code=status_code)

                    self.assertEqual(
                        ImageDownloader().download("https://example/image.jpg"),
                        (None, "이미지를 불러올 수 없습니다."),
                    )
                    get.assert_called_once_with("https://example/image.jpg")

        named_temp.assert_not_called()

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_empty_response_creates_empty_temporary_file(self, get):
        get.return_value = Mock(status_code=200, content=b"")
        temporary_path = None

        try:
            temporary_path, error = ImageDownloader().download("https://example/image.jpg")
            path = Path(temporary_path)

            self.assertIsNone(error)
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".jpg")
            self.assertEqual(path.read_bytes(), b"")
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_non_image_content_type_preserves_current_behavior(self, get):
        get.return_value = Mock(
            status_code=200,
            content=b"plain text",
            headers={"Content-Type": "text/plain"},
        )
        temporary_path = None

        try:
            temporary_path, error = ImageDownloader().download("https://example/file.txt")
            path = Path(temporary_path)

            self.assertIsNone(error)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), b"plain text")
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_temporary_file_is_created_with_content_and_closed(self, get):
        image_content = b"\xff\xd8image\xff\xd9"
        get.return_value = Mock(status_code=200, content=image_content)
        temporary_path = None

        try:
            temporary_path, error = ImageDownloader().download("https://example/image.jpg")
            path = Path(temporary_path)

            self.assertIsNone(error)
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".jpg")
            self.assertEqual(path.read_bytes(), image_content)

            path.unlink()
            self.assertFalse(path.exists())
            temporary_path = None
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
