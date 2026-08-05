import unittest
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    unittest.main()
