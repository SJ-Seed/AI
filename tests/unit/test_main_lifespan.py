import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI

from app.core.config import Settings
from app.infrastructure.queue.redis_connection import RedisUnavailableError
from app.main import lifespan


class MainLifespanTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            openai_api_key=None,
            database_url="database",
            redis_url="redis://redis:6379/0",
            analysis_queue_name="analysis",
            model_path=Path("model"),
            model_version="",
            openai_timeout_seconds=30,
            max_retry_count=5,
            max_image_size_mb=10,
        )
        self.connections = Mock()
        self.connections.ping = AsyncMock()
        self.connections.close = AsyncMock()

    def test_lifespan_builds_queue_and_closes_redis_connections(self):
        asyncio.run(self._run_successful_lifespan())

    async def _run_successful_lifespan(self):
        application = FastAPI()
        with patch("app.main.load_settings", return_value=self.settings), patch(
            "app.main.RedisConnectionManager", return_value=self.connections
        ):
            async with lifespan(application):
                self.assertIs(application.state.redis_connections, self.connections)
                self.assertTrue(hasattr(application.state, "analysis_queue"))
                self.assertFalse(hasattr(application.state, "diagnosis_service"))

        self.connections.ping.assert_awaited_once_with()
        self.connections.close.assert_awaited_once_with()

    def test_redis_startup_failure_does_not_prevent_application_start(self):
        asyncio.run(self._run_redis_failure_lifespan())

    async def _run_redis_failure_lifespan(self):
        self.connections.ping.side_effect = RedisUnavailableError("safe")
        application = FastAPI()
        with patch("app.main.load_settings", return_value=self.settings), patch(
            "app.main.RedisConnectionManager", return_value=self.connections
        ), self.assertLogs("app.main", level="WARNING") as logs:
            async with lifespan(application):
                self.assertTrue(hasattr(application.state, "analysis_queue"))

        self.assertFalse(any(self.settings.redis_url in entry for entry in logs.output))
        self.connections.close.assert_awaited_once_with()

    def test_lifespan_closes_connections_when_application_raises(self):
        asyncio.run(self._run_failing_lifespan())

    async def _run_failing_lifespan(self):
        application = FastAPI()
        with patch("app.main.load_settings", return_value=self.settings), patch(
            "app.main.RedisConnectionManager", return_value=self.connections
        ):
            with self.assertRaisesRegex(RuntimeError, "startup consumer failed"):
                async with lifespan(application):
                    raise RuntimeError("startup consumer failed")

        self.connections.close.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
