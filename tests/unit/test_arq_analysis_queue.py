import asyncio
import unittest
from unittest.mock import AsyncMock

from app.infrastructure.queue.arq_analysis_queue import ArqAnalysisQueue


class ArqAnalysisQueueTest(unittest.TestCase):
    def setUp(self):
        self.redis = AsyncMock()
        self.queue = ArqAnalysisQueue(self.redis, "analysis")

    def test_enqueue_sends_only_analysis_id_as_payload(self):
        self.redis.enqueue_job.return_value = object()

        result = asyncio.run(self.queue.enqueue(17))

        self.assertIsNone(result)
        self.redis.enqueue_job.assert_awaited_once_with(
            "process_analysis",
            17,
            _job_id="analysis:17",
            _queue_name="analysis",
        )

    def test_duplicate_job_is_treated_as_success(self):
        self.redis.enqueue_job.return_value = None

        self.assertIsNone(asyncio.run(self.queue.enqueue(17)))

    def test_enqueue_error_is_propagated(self):
        error = RuntimeError("redis unavailable")
        self.redis.enqueue_job.side_effect = error

        with self.assertRaises(RuntimeError) as raised:
            asyncio.run(self.queue.enqueue(17))

        self.assertIs(raised.exception, error)

    def test_queue_does_not_close_caller_owned_connection(self):
        self.redis.enqueue_job.return_value = object()

        asyncio.run(self.queue.enqueue(17))

        self.redis.aclose.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
