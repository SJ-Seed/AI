import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_analysis_repository,
    get_diagnosis_service,
    get_image_downloader,
    get_model_version,
)
from app.domain.models import DiagnosisOutcome
from app.main import create_app


class AnalysisHttpTest(unittest.TestCase):
    def setUp(self):
        # 실제 외부 의존성 대신 Mock 객체 사용
        self.service = Mock()
        self.downloader = Mock()
        self.downloader.download.return_value = ("local.jpg", None)
        self.repository = Mock()
        self.repository.create = AsyncMock(return_value=11)
        self.repository.mark_processing = AsyncMock(return_value=True)
        self.repository.mark_completed = AsyncMock(return_value=True)
        self.repository.mark_failed = AsyncMock(return_value=True)

        # Dependency Override를 적용한 테스트용 FastAPI 앱 생성
        self.app = create_app()
        self.app.dependency_overrides[get_diagnosis_service] = lambda: self.service
        self.app.dependency_overrides[get_image_downloader] = lambda: self.downloader
        self.app.dependency_overrides[get_analysis_repository] = lambda: self.repository
        self.app.dependency_overrides[get_model_version] = lambda: "classifier-v1"
        self.client = TestClient(self.app, raise_server_exceptions=False)

        self.valid_request = {
            "image_path": "https://example/image.jpg",
            "temperature": "28",
            "humidity": "85",
        }

    def tearDown(self):
        # 테스트 간 Override와 Client 상태가 공유되지 않도록 정리
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_healthy_response_over_http(self):
        # 정상 식물 진단 결과의 HTTP 응답 계약 검증
        self.service.diagnose_with_details.return_value = DiagnosisOutcome(
            True, "Healthy", "정상", None, None, None,
        )

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!",
        })
        self.downloader.download.assert_called_once_with("https://example/image.jpg")
        self.service.diagnose_with_details.assert_called_once_with("local.jpg", "28", "85")
        completed = self.repository.mark_completed.await_args.kwargs
        self.assertEqual(completed["disease_code"], "Healthy")
        self.assertEqual(completed["model_version"], "classifier-v1")

    def test_not_a_plant_response_over_http(self):
        # 비식물 이미지 진단 결과의 HTTP 응답 계약 검증
        self.service.diagnose_with_details.return_value = DiagnosisOutcome(
            False, None, None, None, None, None,
        )

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!",
        })
        self.assertFalse(self.repository.mark_completed.await_args.kwargs["is_plant"])

    @patch("app.api.routes.analysis.perf_counter", side_effect=[100.0, 101.25])
    def test_disease_response_over_http(self, perf_counter):
        # 질병 진단 결과의 상세 응답 계약 검증
        self.service.diagnose_with_details.return_value = DiagnosisOutcome(
            True,
            "Leaf_mold",
            "잎곰팡이병",
            "설명",
            "원인",
            "치료",
        )

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "photo": True,
            "state": "잎곰팡이병",
            "message": "식물이 아파요",
            "explain": "설명",
            "cause": "원인",
            "cure": "치료",
        })
        self.repository.create.assert_awaited_once_with(**self.valid_request)
        self.repository.mark_processing.assert_awaited_once_with(11)
        completed = self.repository.mark_completed.await_args.kwargs
        self.assertEqual(completed["disease_code"], "Leaf_mold")
        self.assertEqual(completed["disease_name"], "잎곰팡이병")
        self.assertEqual(completed["explain"], "설명")
        self.assertEqual(completed["latency_ms"], 1250)

    def test_download_error_marks_analysis_failed_and_preserves_response(self):
        self.downloader.download.return_value = (
            None,
            "이미지를 불러올 수 없습니다.",
        )

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "photo": "이미지를 불러올 수 없습니다.",
        })
        self.repository.mark_failed.assert_awaited_once_with(
            11,
            error_code="IMAGE_DOWNLOAD_ERROR",
            error_message="이미지를 불러올 수 없습니다.",
        )
        self.repository.mark_completed.assert_not_awaited()

    def test_each_required_field_is_rejected_when_missing(self):
        # 필수 필드가 하나라도 누락되면 422를 반환하는지 검증
        for field in self.valid_request:
            with self.subTest(field=field):
                payload = dict(self.valid_request)
                del payload[field]

                response = self.client.post("/analyze", json=payload)

                self.assertEqual(response.status_code, 422)
                self.assertTrue(any(
                    error["type"] == "missing"
                    and error["loc"] == ["body", field]
                    for error in response.json()["detail"]
                ))

        # 요청 검증 실패 시 실제 처리 로직은 호출되지 않아야 함
        self.downloader.download.assert_not_called()
        self.service.diagnose_with_details.assert_not_called()
        self.repository.create.assert_not_awaited()

    def test_non_string_fields_are_rejected(self):
        # 문자열 필드에 숫자가 전달되면 422를 반환하는지 검증
        response = self.client.post("/analyze", json={
            "image_path": 123,
            "temperature": 28,
            "humidity": 85,
        })

        self.assertEqual(response.status_code, 422)
        errors = response.json()["detail"]
        self.assertEqual(
            {(error["loc"][-1], error["type"]) for error in errors},
            {
                ("image_path", "string_type"),
                ("temperature", "string_type"),
                ("humidity", "string_type"),
            },
        )
        self.downloader.download.assert_not_called()
        self.service.diagnose_with_details.assert_not_called()
        self.repository.create.assert_not_awaited()

    def test_empty_strings_preserve_current_behavior(self):
        # 빈 문자열을 허용하는 현재 API 동작을 고정
        self.service.diagnose_with_details.return_value = DiagnosisOutcome(
            True, "Healthy", "정상", None, None, None,
        )

        response = self.client.post("/analyze", json={
            "image_path": "",
            "temperature": "",
            "humidity": "",
        })

        self.assertEqual(response.status_code, 200)
        self.downloader.download.assert_called_once_with("")
        self.service.diagnose_with_details.assert_called_once_with("local.jpg", "", "")

    def test_service_exception_returns_internal_server_error(self):
        # 처리되지 않은 서비스 예외가 기본 500 응답으로 변환되는지 검증
        self.service.diagnose_with_details.side_effect = RuntimeError("service failure")

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 500)
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertEqual(response.text, "Internal Server Error")
        self.repository.mark_failed.assert_awaited_once_with(
            11,
            error_code="RuntimeError",
            error_message="service failure",
        )


if __name__ == "__main__":
    unittest.main()
