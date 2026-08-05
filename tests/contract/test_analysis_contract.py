import asyncio
import json
import unittest

from app.api.routes.analysis import analyze_endpoint
from app.api.schemas import AnalyzeRequest


class FakeDownloader:
    def __init__(self, path="local.jpg", error=None):
        self.path = path
        self.error = error

    def download(self, image_path):
        return self.path, self.error


class FakeService:
    def __init__(self, result):
        self.result = result

    def diagnose(self, image_path, temperature, humidity):
        return self.result


def response_json(result, downloader=None):
    response = asyncio.run(analyze_endpoint(
        AnalyzeRequest(image_path="https://example/image.jpg", temperature="28", humidity="85"),
        FakeService(result),
        downloader or FakeDownloader(),
    ))
    return response.status_code, json.loads(response.body.decode("utf-8"))


class AnalysisContractTest(unittest.TestCase):
    def test_not_a_plant_response_is_unchanged(self):
        self.assertEqual(response_json(("식물아님", None, None, None)), (200, {
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!",
        }))

    def test_healthy_response_is_unchanged(self):
        self.assertEqual(response_json(("정상", None, None, None)), (200, {
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!",
        }))

    def test_disease_response_is_unchanged(self):
        self.assertEqual(response_json(("잎곰팡이병", "설명", "원인", "치료")), (200, {
            "photo": True,
            "state": "잎곰팡이병",
            "message": "식물이 아파요",
            "explain": "설명",
            "cause": "원인",
            "cure": "치료",
        }))

    def test_download_error_response_is_unchanged(self):
        self.assertEqual(
            response_json(None, FakeDownloader(path=None, error="이미지를 불러올 수 없습니다.")),
            (200, {"photo": "이미지를 불러올 수 없습니다."}),
        )


if __name__ == "__main__":
    unittest.main()
