import asyncio
import unittest
from unittest.mock import AsyncMock

from fastapi import Response

from app.api.routes.analysis import analyze_endpoint
from app.api.schemas import AnalyzeRequest
from app.domain.enums import AnalysisStatus


class AnalysisContractTest(unittest.TestCase):
    def test_analyze_endpoint_returns_accepted_contract(self):
        repository = AsyncMock()
        repository.create.return_value = 21
        queue = AsyncMock()
        response = Response()

        result = asyncio.run(analyze_endpoint(
            AnalyzeRequest(
                image_path="https://example/image.jpg",
                temperature="28",
                humidity="85",
            ),
            response,
            repository,
            queue,
        ))

        self.assertEqual(result.analysis_id, 21)
        self.assertEqual(result.status, AnalysisStatus.PENDING)
        self.assertEqual(result.status_url, "/analyses/21")
        self.assertEqual(response.headers["location"], "/analyses/21")
        queue.enqueue.assert_awaited_once_with(21)


if __name__ == "__main__":
    unittest.main()
