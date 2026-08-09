import os
import unittest
from unittest.mock import patch

from app.core.config import (
    load_settings,
    require_openai_api_key,
    require_redis_url,
)


class SettingsTest(unittest.TestCase):
    def test_environment_variables_are_loaded(self):
        values = {
            "OPENAI_API_KEY": "key",
            "DATABASE_URL": "database",
            "REDIS_URL": "redis://redis:6379/0",
            "ANALYSIS_QUEUE_NAME": "priority-analysis",
            "MODEL_PATH": "model",
            "MODEL_VERSION": "v1",
            "OPENAI_TIMEOUT_SECONDS": "12.5",
            "MAX_RETRY_COUNT": "7",
            "MAX_IMAGE_SIZE_MB": "20",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = load_settings()

        self.assertEqual(settings.openai_api_key, "key")
        self.assertEqual(settings.redis_url, "redis://redis:6379/0")
        self.assertEqual(settings.analysis_queue_name, "priority-analysis")
        self.assertEqual(str(settings.model_path), "model")
        self.assertEqual(settings.openai_timeout_seconds, 12.5)

    def test_database_url_is_the_only_common_required_setting(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
                load_settings()

    def test_redis_and_openai_are_optional_in_common_settings(self):
        with patch.dict(os.environ, {"DATABASE_URL": "database"}, clear=True):
            settings = load_settings()

        self.assertIsNone(settings.redis_url)
        self.assertIsNone(settings.openai_api_key)
        self.assertEqual(settings.analysis_queue_name, "analysis")

    def test_require_redis_url_only_validates_redis(self):
        with patch.dict(os.environ, {"DATABASE_URL": "database"}, clear=True):
            settings = load_settings()
        with self.assertRaisesRegex(RuntimeError, "REDIS_URL"):
            require_redis_url(settings)

        with patch.dict(os.environ, {
            "DATABASE_URL": "database",
            "REDIS_URL": "redis://redis:6379/0",
        }, clear=True):
            settings = load_settings()
        self.assertEqual(require_redis_url(settings), "redis://redis:6379/0")

    def test_require_openai_api_key_only_validates_openai(self):
        with patch.dict(os.environ, {"DATABASE_URL": "database"}, clear=True):
            settings = load_settings()
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            require_openai_api_key(settings)

        with patch.dict(os.environ, {
            "DATABASE_URL": "database",
            "OPENAI_API_KEY": "key",
        }, clear=True):
            settings = load_settings()
        self.assertEqual(require_openai_api_key(settings), "key")


if __name__ == "__main__":
    unittest.main()
