import unittest

from app.infrastructure.queue.redis_settings import build_redis_settings


class RedisSettingsTest(unittest.TestCase):
    def test_builds_arq_settings_from_dsn(self):
        settings = build_redis_settings("redis://user:secret@redis.example:6380/4")

        self.assertEqual(settings.host, "redis.example")
        self.assertEqual(settings.port, 6380)
        self.assertEqual(settings.database, 4)
        self.assertEqual(settings.username, "user")
        self.assertEqual(settings.password, "secret")
        self.assertFalse(settings.ssl)

    def test_supports_tls_dsn(self):
        settings = build_redis_settings("rediss://redis.example/2")

        self.assertTrue(settings.ssl)
        self.assertEqual(settings.database, 2)

    def test_missing_url_is_rejected(self):
        for value in (None, ""):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "REDIS_URL environment variable"):
                    build_redis_settings(value)

    def test_invalid_dsn_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "valid Redis DSN"):
            build_redis_settings("http://redis.example")


if __name__ == "__main__":
    unittest.main()
