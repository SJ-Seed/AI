import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies import get_diagnosis_service, get_image_downloader
from app.main import create_app


class AnalysisHttpTest(unittest.TestCase):
    def setUp(self):
        # 실제 외부 의존성 대신 Mock 객체 사용
        self.service = Mock()
        self.downloader = Mock()
        self.downloader.download.return_value = ("local.jpg", None)

        # Dependency Override를 적용한 테스트용 FastAPI 앱 생성
        self.app = create_app()
        self.app.dependency_overrides[get_diagnosis_service] = lambda: self.service
        self.app.dependency_overrides[get_image_downloader] = lambda: self.downloader
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
        self.service.diagnose.return_value = ("정상", None, None, None)

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "photo": True,
            "state": "정상",
            "message": "식물이 건강해요!",
        })
        self.downloader.download.assert_called_once_with("https://example/image.jpg")
        self.service.diagnose.assert_called_once_with("local.jpg", "28", "85")

    def test_not_a_plant_response_over_http(self):
        # 비식물 이미지 진단 결과의 HTTP 응답 계약 검증
        self.service.diagnose.return_value = ("식물아님", None, None, None)

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "photo": False,
            "state": None,
            "message": "식물이 잘 보이지 않아요. 다시 촬영해주세요!",
        })

    def test_disease_response_over_http(self):
        # 질병 진단 결과의 상세 응답 계약 검증
        self.service.diagnose.return_value = (
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
        self.service.diagnose.assert_not_called()

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
        self.service.diagnose.assert_not_called()

    def test_empty_strings_preserve_current_behavior(self):
        # 빈 문자열을 허용하는 현재 API 동작을 고정
        self.service.diagnose.return_value = ("정상", None, None, None)

        response = self.client.post("/analyze", json={
            "image_path": "",
            "temperature": "",
            "humidity": "",
        })

        self.assertEqual(response.status_code, 200)
        self.downloader.download.assert_called_once_with("")
        self.service.diagnose.assert_called_once_with("local.jpg", "", "")

    def test_service_exception_returns_internal_server_error(self):
        # 처리되지 않은 서비스 예외가 기본 500 응답으로 변환되는지 검증
        self.service.diagnose.side_effect = RuntimeError("service failure")

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 500)
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertEqual(response.text, "Internal Server Error")


if __name__ == "__main__":
    unittest.main()