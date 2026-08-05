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
            "MODEL_PATH": "model",
            "MODEL_VERSION": "v1",
            "OPENAI_TIMEOUT_SECONDS": "12.5",
            "MAX_RETRY_COUNT": "7",
            "MAX_IMAGE_SIZE_MB": "20",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = load_settings()
        self.assertEqual(settings.openai_api_key, "key")
        self.assertEqual(str(settings.model_path), "model")
        self.assertEqual(settings.openai_timeout_seconds, 12.5)
        self.assertEqual(settings.max_retry_count, 7)
        self.assertEqual(settings.max_image_size_mb, 20)

    def test_api_key_is_required_at_startup(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                load_settings()


if __name__ == "__main__":
    unittest.main()
