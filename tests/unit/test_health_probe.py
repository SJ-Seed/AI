import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from deploy.monitoring import health_probe


class _Response:
    def __init__(self, status: int, payload: bytes):
        self.status = status
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._payload


class HealthProbeTest(unittest.TestCase):
    def test_all_services_up(self):
        with patch.object(
            health_probe,
            "urlopen",
            return_value=_Response(200, self._payload("up", "up")),
        ):
            metrics = health_probe.collect_health_metrics("http://local/health")

        self.assertEqual(metrics, self._metrics(1, 1, 1))

    def test_postgresql_failure_from_503_is_reported_separately(self):
        error = HTTPError(
            "http://local/health",
            503,
            "Service Unavailable",
            {},
            io.BytesIO(self._payload("down", "up")),
        )
        with patch.object(health_probe, "urlopen", side_effect=error):
            metrics = health_probe.collect_health_metrics("http://local/health")

        self.assertEqual(metrics, self._metrics(1, 0, 1))

    def test_redis_failure_from_503_is_reported_separately(self):
        error = HTTPError(
            "http://local/health",
            503,
            "Service Unavailable",
            {},
            io.BytesIO(self._payload("up", "down")),
        )
        with patch.object(health_probe, "urlopen", side_effect=error):
            metrics = health_probe.collect_health_metrics("http://local/health")

        self.assertEqual(metrics, self._metrics(1, 1, 0))

    def test_connection_failure_reports_only_api_down(self):
        with patch.object(
            health_probe,
            "urlopen",
            side_effect=URLError("secret upstream detail"),
        ):
            metrics = health_probe.collect_health_metrics("http://local/health")

        self.assertEqual(metrics, {health_probe.METRIC_API: 0})

    def test_timeout_reports_only_api_down(self):
        with patch.object(
            health_probe,
            "urlopen",
            side_effect=TimeoutError("secret timeout detail"),
        ):
            metrics = health_probe.collect_health_metrics("http://local/health")

        self.assertEqual(metrics, {health_probe.METRIC_API: 0})

    def test_invalid_json_reports_only_api_down(self):
        with patch.object(
            health_probe,
            "urlopen",
            return_value=_Response(200, b"not-json-with-secret"),
        ):
            metrics = health_probe.collect_health_metrics("http://local/health")

        self.assertEqual(metrics, {health_probe.METRIC_API: 0})

    def test_statsd_payload_contains_only_metric_names_and_values(self):
        payload = health_probe.format_statsd(self._metrics(1, 0, 1))

        self.assertEqual(
            payload,
            b"HealthApi:1|g\nHealthPostgresql:0|g\nHealthRedis:1|g",
        )

    @staticmethod
    def _payload(postgresql: str, redis: str) -> bytes:
        return (
            '{"status":"healthy","services":{'
            '"api":{"status":"up"},'
            f'"postgresql":{{"status":"{postgresql}"}},'
            f'"redis":{{"status":"{redis}"}}'
            "}}"
        ).encode()

    @staticmethod
    def _metrics(api: int, postgresql: int, redis: int) -> dict[str, int]:
        return {
            health_probe.METRIC_API: api,
            health_probe.METRIC_POSTGRESQL: postgresql,
            health_probe.METRIC_REDIS: redis,
        }


if __name__ == "__main__":
    unittest.main()
