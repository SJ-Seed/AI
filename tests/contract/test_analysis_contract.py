import asyncio
import json
import unittest

from app.api.routes.analysis import analyze_endpoint
from app.api.schemas import AnalyzeRequest
from app.domain.models import DiagnosisOutcome


class FakeDownloader:
    def __init__(self, path="local.jpg", error=None):
        self.path = path
        self.error = error

    def download(self, image_path):
        return self.path, self.error


class FakeService:
    def __init__(self, result):
        self.result = result

    def diagnose_with_details(self, image_path, temperature, humidity):
        return self.result


class FakeRepository:
    async def create(self, **kwargs):
        return 1

    async def mark_processing(self, analysis_id):
        return True

    async def mark_completed(self, analysis_id, **kwargs):
        return True

    async def mark_failed(self, analysis_id, **kwargs):
        return True


def response_json(result, downloader=None):
    response = asyncio.run(analyze_endpoint(
        AnalyzeRequest(image_path="https://example/image.jpg", temperature="28", humidity="85"),
        FakeService(result),
        downloader or FakeDownloader(),
        FakeRepository(),
        "classifier-v1",
    ))
    return response.status_code, json.loads(response.body.decode("utf-8"))


class AnalysisContractTest(unittest.TestCase):
    def test_not_a_plant_response_is_unchanged(self):
        result = DiagnosisOutcome(False, None, None, None, None, None)
        self.assertEqual(response_json(result), (200, {
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!",
        }))

    def test_healthy_response_is_unchanged(self):
        result = DiagnosisOutcome(True, "Healthy", "정상", None, None, None)
        self.assertEqual(response_json(result), (200, {
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!",
        }))

    def test_disease_response_is_unchanged(self):
        result = DiagnosisOutcome(
            True, "Leaf_mold", "잎곰팡이병", "설명", "원인", "치료",
        )
        self.assertEqual(response_json(result), (200, {
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
