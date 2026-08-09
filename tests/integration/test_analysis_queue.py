import asyncio
import os
import unittest
from uuid import uuid4

from arq.connections import create_pool

from app.infrastructure.queue.arq_analysis_queue import ArqAnalysisQueue
from app.infrastructure.queue.redis_settings import build_redis_settings


TEST_REDIS_URL = os.getenv("TEST_REDIS_URL")


@unittest.skipUnless(TEST_REDIS_URL, "TEST_REDIS_URL is required for Redis integration tests")
class AnalysisQueueIntegrationTest(unittest.TestCase):
    def test_enqueues_one_idempotent_job_in_real_redis(self):
        asyncio.run(self._test_enqueues_one_idempotent_job_in_real_redis())

    async def _test_enqueues_one_idempotent_job_in_real_redis(self):
        redis = await create_pool(build_redis_settings(TEST_REDIS_URL))
        suffix = uuid4().hex
        queue_name = f"test:analysis:{suffix}"
        analysis_id = int(suffix[:8], 16)
        job_id = f"analysis:{analysis_id}"
        queue = ArqAnalysisQueue(redis, queue_name)

        try:
            await queue.enqueue(analysis_id)
            await queue.enqueue(analysis_id)

            jobs = await redis.queued_jobs(queue_name=queue_name)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].function, "process_analysis")
            self.assertEqual(jobs[0].args, (analysis_id,))
            self.assertEqual(jobs[0].kwargs, {})
            self.assertEqual(jobs[0].job_id, job_id)
        finally:
            await redis.delete(
                queue_name,
                f"arq:job:{job_id}",
                f"arq:result:{job_id}",
                f"arq:retry:{job_id}",
            )
            await redis.aclose()


if __name__ == "__main__":
    unittest.main()
