import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes.health import get_readiness_checker
from app.main import create_app


class HealthHttpTest(unittest.TestCase):
    def setUp(self):
        self.checker = AsyncMock()
        self.app = create_app()
        self.app.dependency_overrides[get_readiness_checker] = lambda: self.checker
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_health_is_ready_when_postgresql_and_redis_are_up(self):
        self.checker.check.return_value = ("up", "up")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self._response("healthy", "up", "up"))

    def test_health_is_unavailable_when_only_postgresql_is_down(self):
        self.checker.check.return_value = ("down", "up")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), self._response("unhealthy", "down", "up"))

    def test_health_is_unavailable_when_only_redis_is_down(self):
        self.checker.check.return_value = ("up", "down")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), self._response("unhealthy", "up", "down"))

    def test_ready_has_the_same_contract_as_health(self):
        self.checker.check.return_value = ("up", "up")

        response = self.client.get("/health/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self._response("healthy", "up", "up"))

    def test_live_does_not_check_dependencies(self):
        response = self.client.get("/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "healthy",
            "services": {"api": {"status": "up"}},
        })
        self.checker.check.assert_not_awaited()

    @staticmethod
    def _response(overall: str, postgresql: str, redis: str) -> dict[str, object]:
        return {
            "status": overall,
            "services": {
                "api": {"status": "up"},
                "postgresql": {"status": postgresql},
                "redis": {"status": redis},
            },
        }


if __name__ == "__main__":
    unittest.main()
