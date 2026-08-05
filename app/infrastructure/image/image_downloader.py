"""
외부에서 전달 받은 이미지 URL을 다운로드한 뒤, 임시 파일로 저장하여 경로를 반환
"""

import tempfile

import requests


class ImageDownloader:
    def download(self, image_path: str) -> tuple[str | None, str | None]:
        try:
            response = requests.get(image_path)
            if response.status_code != 200:
                return None, "이미지를 불러올 수 없습니다."

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(response.content)
                return tmp.name, None
        except Exception as e:
            return None, f"이미지 다운로드 오류: {str(e)}"
