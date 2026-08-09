import os
import unittest
from unittest.mock import patch

from app.core.config import load_settings


class SettingsTest(unittest.TestCase):
    def test_environment_variables_are_loaded(self):
        values = {
            "OPENAI_API_KEY": "key",
            "DATABASE_URL": "database",
            "REDIS_URL": "redis",
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
        self.assertEqual(settings.redis_url, "redis")
        self.assertEqual(settings.analysis_queue_name, "priority-analysis")
        self.assertEqual(str(settings.model_path), "model")
        self.assertEqual(settings.openai_timeout_seconds, 12.5)
        self.assertEqual(settings.max_retry_count, 7)
        self.assertEqual(settings.max_image_size_mb, 20)

    def test_api_key_is_required_at_startup(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                load_settings()

    def test_analysis_queue_name_has_default(self):
        values = {
            "OPENAI_API_KEY": "key",
            "DATABASE_URL": "database",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = load_settings()

        self.assertIsNone(settings.redis_url)
        self.assertEqual(settings.analysis_queue_name, "analysis")


if __name__ == "__main__":
    unittest.main()
