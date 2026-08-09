"""원격 이미지를 다운로드하여 Worker가 소유하는 임시 파일로 저장"""

import tempfile
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class ImageDownloadResult:
    """이미지 다운로드 결과와 생성된 파일의 소유권 정보"""
    path: str | None
    error: str | None
    is_temporary: bool


class ImageDownloader:
    """원격 이미지를 다운로드해 로컬 임시 파일로 저장"""
    def download(self, image_path: str) -> ImageDownloadResult:
        try:
            response = requests.get(image_path)
            if response.status_code != 200:
                return ImageDownloadResult(
                    path=None,
                    error="이미지를 불러올 수 없습니다.",
                    is_temporary=False,
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temporary:
                temporary.write(response.content)
                return ImageDownloadResult(
                    path=temporary.name,
                    error=None,
                    is_temporary=True,
                )
        except Exception as error:
            return ImageDownloadResult(
                path=None,
                error=f"이미지 다운로드 오류: {error}",
                is_temporary=False,
            )
