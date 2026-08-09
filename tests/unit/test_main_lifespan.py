import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI

from app.core.config import Settings
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
        self.redis = AsyncMock()

    def test_lifespan_builds_queue_without_ai_resources_and_closes_pool(self):
        asyncio.run(self._run_successful_lifespan())

    async def _run_successful_lifespan(self):
        application = FastAPI()
        with patch("app.main.load_settings", return_value=self.settings), patch(
            "app.main.create_pool", AsyncMock(return_value=self.redis)
        ) as create_pool:
            async with lifespan(application):
                self.assertTrue(hasattr(application.state, "analysis_queue"))
                self.assertFalse(hasattr(application.state, "diagnosis_service"))
                self.assertFalse(hasattr(application.state, "image_downloader"))
                self.assertFalse(hasattr(application.state, "model_version"))

        create_pool.assert_awaited_once()
        self.redis.aclose.assert_awaited_once_with()

    def test_lifespan_closes_pool_when_application_raises(self):
        asyncio.run(self._run_failing_lifespan())

    async def _run_failing_lifespan(self):
        application = FastAPI()
        with patch("app.main.load_settings", return_value=self.settings), patch(
            "app.main.create_pool", AsyncMock(return_value=self.redis)
        ):
            with self.assertRaisesRegex(RuntimeError, "startup consumer failed"):
                async with lifespan(application):
                    raise RuntimeError("startup consumer failed")

        self.redis.aclose.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
