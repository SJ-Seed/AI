"""원격 이미지를 다운로드하여 Worker가 소유하는 임시 파일로 저장"""

import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError


class ImageDownloadFailureKind(str, Enum):
    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    INVALID_IMAGE = "INVALID_IMAGE"
    PERMANENT_DOWNLOAD = "PERMANENT_DOWNLOAD"


@dataclass(frozen=True)
class ImageDownloadResult:
    """이미지 다운로드 결과와 생성된 파일의 소유권 정보"""
    path: str | None
    error: str | None
    is_temporary: bool
    failure_kind: ImageDownloadFailureKind | None = None


class ImageDownloader:
    """원격 이미지를 다운로드해 로컬 임시 파일로 저장"""
    CHUNK_SIZE = 64 * 1024

    def __init__(self, *, max_size_mb: int = 10, timeout_seconds: float = 10) -> None:
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.timeout_seconds = timeout_seconds

    def download(self, image_path: str) -> ImageDownloadResult:
        temporary_path: str | None = None
        try:
            with requests.get(
                image_path, stream=True, timeout=self.timeout_seconds
            ) as response:
                failure = self._http_failure(response.status_code)
                if failure is not None:
                    return failure

                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        if int(content_length) > self.max_size_bytes:
                            return self._invalid("Image exceeds the maximum allowed size")
                    except ValueError:
                        pass

                with tempfile.NamedTemporaryFile(delete=False, suffix=".img") as temporary:
                    temporary_path = temporary.name
                    total = 0
                    for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > self.max_size_bytes:
                            raise _ImageTooLarge
                        temporary.write(chunk)

            try:
                with Image.open(temporary_path) as image:
                    image.verify()
            except (UnidentifiedImageError, OSError, ValueError):
                Path(temporary_path).unlink(missing_ok=True)
                return self._invalid("Downloaded content is not a valid image")

            return ImageDownloadResult(temporary_path, None, True)
        except _ImageTooLarge:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
            return self._invalid("Image exceeds the maximum allowed size")
        except (requests.Timeout, requests.ConnectionError) as error:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
            return ImageDownloadResult(
                None, str(error), False, ImageDownloadFailureKind.TRANSIENT_NETWORK
            )
        except requests.RequestException as error:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
            return ImageDownloadResult(
                None, str(error), False, ImageDownloadFailureKind.PERMANENT_DOWNLOAD
            )

    @staticmethod
    def _http_failure(status_code: int) -> ImageDownloadResult | None:
        if status_code == 200:
            return None
        kind = (
            ImageDownloadFailureKind.TRANSIENT_NETWORK
            if status_code in (408, 409, 429) or status_code >= 500
            else ImageDownloadFailureKind.PERMANENT_DOWNLOAD
        )
        return ImageDownloadResult(None, f"Image server returned {status_code}", False, kind)

    @staticmethod
    def _invalid(message: str) -> ImageDownloadResult:
        return ImageDownloadResult(
            None, message, False, ImageDownloadFailureKind.INVALID_IMAGE
        )


class _ImageTooLarge(Exception):
    pass
