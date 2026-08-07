import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class HealthHttpTest(unittest.TestCase):
    def test_health_response_over_http(self):
        client = TestClient(create_app())
        response = client.get("/health")
        client.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
