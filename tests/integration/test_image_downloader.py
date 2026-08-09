import io
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image
from requests.exceptions import Timeout

from app.infrastructure.image.image_downloader import (
    ImageDownloader,
    ImageDownloadFailureKind,
)


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1, 1)).save(output, format="PNG")
    return output.getvalue()


def response(*, status=200, chunks=(), headers=None):
    value = Mock(status_code=status, headers=headers or {})
    value.iter_content.return_value = iter(chunks)
    value.__enter__ = Mock(return_value=value)
    value.__exit__ = Mock(return_value=False)
    return value


class ImageDownloaderTest(unittest.TestCase):
    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_valid_image_is_streamed_to_owned_file(self, get):
        get.return_value = response(chunks=[png_bytes()])
        result = ImageDownloader().download("https://example/image.png")
        try:
            self.assertIsNone(result.error)
            self.assertTrue(result.is_temporary)
            self.assertTrue(Path(result.path).exists())
            get.assert_called_once_with(
                "https://example/image.png", stream=True, timeout=10
            )
        finally:
            if result.path:
                Path(result.path).unlink(missing_ok=True)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_content_length_limit_stops_before_streaming(self, get):
        remote = response(headers={"Content-Length": "11"})
        get.return_value = remote

        result = ImageDownloader(max_size_mb=0.00001).download("https://example/image")

        self.assertEqual(result.failure_kind, ImageDownloadFailureKind.INVALID_IMAGE)
        remote.iter_content.assert_not_called()

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_chunk_limit_stops_immediately_and_removes_partial_file(self, get):
        consumed = []

        def chunks():
            for chunk in (b"12345678", b"12345678", b"unconsumed"):
                consumed.append(chunk)
                yield chunk

        get.return_value = response(chunks=chunks())
        result = ImageDownloader(max_size_mb=0.00001).download("https://example/image")

        self.assertEqual(result.failure_kind, ImageDownloadFailureKind.INVALID_IMAGE)
        self.assertEqual(len(consumed), 2)
        self.assertFalse(result.is_temporary)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_timeout_is_transient(self, get):
        get.side_effect = Timeout("timed out")
        result = ImageDownloader().download("https://example/image")
        self.assertEqual(result.failure_kind, ImageDownloadFailureKind.TRANSIENT_NETWORK)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_404_is_permanent_and_503_is_transient(self, get):
        get.return_value = response(status=404)
        permanent = ImageDownloader().download("https://example/image")
        get.return_value = response(status=503)
        transient = ImageDownloader().download("https://example/image")
        self.assertEqual(permanent.failure_kind, ImageDownloadFailureKind.PERMANENT_DOWNLOAD)
        self.assertEqual(transient.failure_kind, ImageDownloadFailureKind.TRANSIENT_NETWORK)

    @patch("app.infrastructure.image.image_downloader.requests.get")
    def test_corrupt_content_is_invalid_and_partial_file_is_removed(self, get):
        get.return_value = response(chunks=[b"not an image"])
        result = ImageDownloader().download("https://example/image")
        self.assertEqual(result.failure_kind, ImageDownloadFailureKind.INVALID_IMAGE)
        self.assertIsNone(result.path)


if __name__ == "__main__":
    unittest.main()
