import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, call

from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_queue, get_analysis_repository
from app.domain.enums import AnalysisStatus
from app.main import create_app


class AnalysisHttpTest(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.repository.create = AsyncMock(return_value=11)
        self.repository.get_by_id = AsyncMock()
        self.repository.mark_processing = AsyncMock(return_value=True)
        self.repository.mark_completed = AsyncMock(return_value=True)
        self.repository.mark_failed = AsyncMock(return_value=True)
        self.repository.mark_enqueue_failed = AsyncMock(return_value=True)
        self.repository.mark_enqueued = AsyncMock(return_value=True)
        self.queue = Mock()
        self.queue.enqueue = AsyncMock(return_value=None)

        self.app = create_app()
        self.app.dependency_overrides[get_analysis_repository] = lambda: self.repository
        self.app.dependency_overrides[get_analysis_queue] = lambda: self.queue
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.valid_request = {
            "image_path": "https://example/image.jpg",
            "temperature": "28",
            "humidity": "85",
        }

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_analyze_creates_and_enqueues_pending_analysis(self):
        calls = Mock()
        calls.attach_mock(self.repository.create, "create")
        calls.attach_mock(self.queue.enqueue, "enqueue")
        calls.attach_mock(self.repository.mark_enqueued, "mark_enqueued")

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {
            "analysis_id": 11,
            "status": "PENDING",
            "status_url": "/analyses/11",
        })
        self.assertEqual(response.headers["location"], "/analyses/11")
        self.assertEqual(calls.mock_calls, [
            call.create(**self.valid_request),
            call.enqueue(11),
            call.mark_enqueued(11),
        ])
        self.repository.mark_processing.assert_not_awaited()
        self.repository.mark_completed.assert_not_awaited()
        self.repository.mark_failed.assert_not_awaited()
        self.repository.mark_enqueue_failed.assert_not_awaited()

    def test_enqueue_tracking_failure_still_returns_accepted(self):
        self.repository.mark_enqueued.side_effect = RuntimeError("database unavailable")

        with self.assertLogs("app.api.routes.analysis", level="ERROR"):
            response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 202)
        self.queue.enqueue.assert_awaited_once_with(11)

    def test_queue_failure_is_compensated_with_safe_error_and_returns_503(self):
        secret = "redis password=do-not-persist"
        self.queue.enqueue.side_effect = RuntimeError(secret)

        with self.assertLogs("app.api.routes.analysis", level="ERROR") as logs:
            response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Analysis queue unavailable"})
        self.assertTrue(any(secret in entry for entry in logs.output))
        kwargs = self.repository.mark_enqueue_failed.await_args.kwargs
        self.assertEqual(kwargs["error_code"], "QUEUE_ENQUEUE_FAILED")
        self.assertEqual(kwargs["error_message"], "Analysis queue is temporarily unavailable")
        self.assertLessEqual(len(kwargs["error_message"]), 255)
        self.assertNotIn(secret, kwargs["error_message"])
        self.repository.mark_enqueued.assert_not_awaited()

    def test_queue_failure_returns_503_when_compensation_is_not_applied(self):
        self.queue.enqueue.side_effect = RuntimeError("redis unavailable")
        self.repository.mark_enqueue_failed.return_value = False

        with self.assertLogs("app.api.routes.analysis", level="ERROR"):
            response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 503)
        self.repository.mark_enqueue_failed.assert_awaited_once()

    def test_queue_failure_returns_503_when_compensation_raises(self):
        self.queue.enqueue.side_effect = RuntimeError("redis unavailable")
        self.repository.mark_enqueue_failed.side_effect = RuntimeError("database unavailable")

        with self.assertLogs("app.api.routes.analysis", level="ERROR"):
            response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 503)
        self.repository.mark_enqueue_failed.assert_awaited_once()

    def test_database_create_failure_does_not_enqueue(self):
        self.repository.create.side_effect = RuntimeError("database unavailable")

        response = self.client.post("/analyze", json=self.valid_request)

        self.assertEqual(response.status_code, 500)
        self.queue.enqueue.assert_not_awaited()
        self.repository.mark_enqueue_failed.assert_not_awaited()

    def test_each_required_field_is_rejected_before_database_or_queue(self):
        for field in self.valid_request:
            with self.subTest(field=field):
                payload = dict(self.valid_request)
                del payload[field]
                response = self.client.post("/analyze", json=payload)
                self.assertEqual(response.status_code, 422)

        self.repository.create.assert_not_awaited()
        self.queue.enqueue.assert_not_awaited()

    def test_non_string_fields_are_rejected_before_database_or_queue(self):
        response = self.client.post("/analyze", json={
            "image_path": 123,
            "temperature": 28,
            "humidity": 85,
        })

        self.assertEqual(response.status_code, 422)
        self.repository.create.assert_not_awaited()
        self.queue.enqueue.assert_not_awaited()

    def test_get_analysis_returns_every_lifecycle_status(self):
        for analysis_status in AnalysisStatus:
            with self.subTest(status=analysis_status):
                self.repository.get_by_id.return_value = self._analysis_snapshot(analysis_status)
                response = self.client.get("/analyses/11")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], analysis_status.value)

    def test_get_analysis_returns_not_found(self):
        self.repository.get_by_id.return_value = None

        response = self.client.get("/analyses/404")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Analysis not found"})

    def _analysis_snapshot(self, analysis_status: AnalysisStatus) -> dict[str, object]:
        return {
            "id": 11,
            "status": analysis_status,
            "image_path": self.valid_request["image_path"],
            "temperature": "28",
            "humidity": "85",
            "is_plant": None,
            "disease_code": None,
            "disease_name": None,
            "explain": None,
            "cause": None,
            "cure": None,
            "model_version": None,
            "latency_ms": None,
            "retry_count": 0,
            "error_code": None,
            "error_message": None,
            "created_at": datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc),
            "started_at": None,
            "completed_at": None,
        }


if __name__ == "__main__":
    unittest.main()
