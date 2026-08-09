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
        self.assertEqual(settings.max_retry_count, 7)
        self.assertEqual(settings.max_image_size_mb, 20)

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
        self.assertEqual(settings.max_retry_count, 4)
        self.assertEqual(settings.retry_base_delay_seconds, 2)
        self.assertEqual(settings.retry_max_delay_seconds, 60)
        self.assertEqual(settings.image_download_timeout_seconds, 10)
        self.assertEqual(settings.processing_timeout_seconds, 300)
        self.assertEqual(settings.reconciliation_min_age_seconds, 30)
        self.assertEqual(settings.reconciliation_claim_timeout_seconds, 300)
        self.assertEqual(settings.reconciliation_batch_size, 100)

    def test_invalid_worker_limits_are_rejected(self):
        invalid_values = (
            {"MAX_RETRY_COUNT": "-1"},
            {"MAX_IMAGE_SIZE_MB": "0"},
            {"IMAGE_DOWNLOAD_TIMEOUT_SECONDS": "0"},
            {"PROCESSING_TIMEOUT_SECONDS": "0"},
            {"RECONCILIATION_MIN_AGE_SECONDS": "0"},
            {"RECONCILIATION_CLAIM_TIMEOUT_SECONDS": "0"},
            {"RECONCILIATION_BATCH_SIZE": "0"},
            {"RETRY_BASE_DELAY_SECONDS": "3", "RETRY_MAX_DELAY_SECONDS": "2"},
        )
        for values in invalid_values:
            with self.subTest(values=values), patch.dict(
                os.environ, {"DATABASE_URL": "database", **values}, clear=True
            ):
                with self.assertRaises(RuntimeError):
                    load_settings()

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
