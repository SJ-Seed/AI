import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.api.routes.health import DependencyReadinessChecker


class HealthReadinessCheckerTest(unittest.TestCase):
    def setUp(self):
        self.connection = AsyncMock()
        self.connection_context = AsyncMock()
        self.connection_context.__aenter__.return_value = self.connection
        self.engine = Mock()
        self.engine.connect.return_value = self.connection_context
        self.redis_connections = Mock()
        self.redis_connections.ping = AsyncMock()
        self.checker = DependencyReadinessChecker(
            self.engine,
            self.redis_connections,
        )

    def test_checks_postgresql_with_select_one_and_redis_with_ping(self):
        result = asyncio.run(self.checker.check())

        self.assertEqual(result, ("up", "up"))
        self.engine.connect.assert_called_once_with()
        self.assertEqual(str(self.connection.execute.await_args.args[0]), "SELECT 1")
        self.redis_connections.ping.assert_awaited_once_with()

    def test_postgresql_failure_does_not_hide_healthy_redis(self):
        self.connection.execute.side_effect = RuntimeError("database secret")

        result = asyncio.run(self.checker.check())

        self.assertEqual(result, ("down", "up"))
        self.redis_connections.ping.assert_awaited_once_with()

    def test_redis_failure_does_not_hide_healthy_postgresql(self):
        self.redis_connections.ping.side_effect = RuntimeError("redis secret")

        result = asyncio.run(self.checker.check())

        self.assertEqual(result, ("up", "down"))
        self.connection.execute.assert_awaited_once()

    def test_each_dependency_has_a_timeout(self):
        async def never_finishes(*_args, **_kwargs):
            await asyncio.sleep(1)

        self.connection.execute.side_effect = never_finishes
        self.redis_connections.ping.side_effect = never_finishes

        with patch("app.api.routes.health.DEPENDENCY_TIMEOUT_SECONDS", 0.01):
            result = asyncio.run(self.checker.check())

        self.assertEqual(result, ("down", "down"))


if __name__ == "__main__":
    unittest.main()
