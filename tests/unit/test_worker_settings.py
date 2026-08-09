import importlib
import os
import sys
import unittest
from unittest.mock import patch


class WorkerSettingsTest(unittest.TestCase):
    def test_worker_settings_register_worker_with_five_total_attempts(self):
        environment = {
            "DATABASE_URL": "postgresql+asyncpg://database",
            "REDIS_URL": "redis://redis:6379/4",
            "ANALYSIS_QUEUE_NAME": "analysis-test",
        }
        sys.modules.pop("app.worker.settings", None)

        with patch.dict(os.environ, environment, clear=True):
            module = importlib.import_module("app.worker.settings")

        settings = module.WorkerSettings
        self.assertEqual([function.__name__ for function in settings.functions], ["process_analysis"])
        self.assertEqual(settings.queue_name, "analysis-test")
        self.assertEqual(settings.redis_settings.database, 4)
        self.assertEqual(settings.max_jobs, 1)
        self.assertEqual(settings.max_tries, 5)
        self.assertTrue(settings.retry_jobs)


if __name__ == "__main__":
    unittest.main()
