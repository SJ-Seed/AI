import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.infrastructure.queue.redis_connection import (
    RedisConnectionManager,
    RedisUnavailableError,
)


class RedisConnectionManagerTest(unittest.TestCase):
    def test_failed_connection_is_retried_and_recovers(self):
        asyncio.run(self._run_recovery())

    async def _run_recovery(self):
        redis = AsyncMock()
        create_pool = AsyncMock(side_effect=[RuntimeError("password=secret"), redis])
        manager = RedisConnectionManager("redis://user:secret@redis:6379/0")

        with patch(
            "app.infrastructure.queue.redis_connection.create_pool", create_pool
        ):
            with self.assertRaisesRegex(RedisUnavailableError, "Redis is unavailable") as raised:
                await manager.ping()
            self.assertNotIn("secret", str(raised.exception))

            await manager.ping()
            redis.ping.assert_awaited_once_with()
            await manager.close()

        self.assertEqual(create_pool.await_count, 2)
        redis.aclose.assert_awaited_once_with()

    def test_ping_failure_discards_cached_connection(self):
        asyncio.run(self._run_ping_failure())

    async def _run_ping_failure(self):
        redis = AsyncMock()
        redis.ping.side_effect = RuntimeError("secret connection details")
        manager = RedisConnectionManager("redis://redis:6379/0")

        with patch(
            "app.infrastructure.queue.redis_connection.create_pool",
            AsyncMock(return_value=redis),
        ):
            with self.assertRaises(RedisUnavailableError):
                await manager.ping()

        redis.aclose.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
