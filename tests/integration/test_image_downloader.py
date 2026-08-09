import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from requests.exceptions import Timeout

from app.infrastructure.image.image_downloader import ImageDownloader


class ImageDownloaderTest(unittest.TestCase):
    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_non_200_response_has_no_owned_file(self, get):
        get.return_value = Mock(status_code=404)

        result = ImageDownloader().download("https://example/image.jpg")

        self.assertIsNone(result.path)
        self.assertEqual(result.error, "이미지를 불러올 수 없습니다.")
        self.assertFalse(result.is_temporary)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_exception_has_no_owned_file(self, get):
        get.side_effect = RuntimeError("failure")

        result = ImageDownloader().download("https://example/image.jpg")

        self.assertIsNone(result.path)
        self.assertEqual(result.error, "이미지 다운로드 오류: failure")
        self.assertFalse(result.is_temporary)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_timeout_does_not_create_temporary_file(self, get):
        get.side_effect = Timeout("timed out")

        with patch("app.infrastructure.image.image_downloader.tempfile.NamedTemporaryFile") as named:
            result = ImageDownloader().download("https://example/image.jpg")

        self.assertEqual(result.error, "이미지 다운로드 오류: timed out")
        self.assertFalse(result.is_temporary)
        named.assert_not_called()

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_success_creates_owned_temporary_file(self, get):
        get.return_value = Mock(status_code=200, content=b"image")
        temporary_path = None

        try:
            result = ImageDownloader().download("https://example/image.jpg")
            temporary_path = result.path
            path = Path(temporary_path)

            self.assertIsNone(result.error)
            self.assertTrue(result.is_temporary)
            self.assertTrue(path.exists())
            self.assertEqual(path.suffix, ".jpg")
            self.assertEqual(path.read_bytes(), b"image")
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
