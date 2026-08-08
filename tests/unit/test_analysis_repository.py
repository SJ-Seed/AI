import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AnalysisStatus
from app.infrastructure.persistence.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from app.infrastructure.persistence.models import Analysis


class AnalysisRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.session = Mock(spec=AsyncSession)
        self.session.get = AsyncMock()
        self.session.commit = AsyncMock()
        self.session.rollback = AsyncMock()
        self.session.flush = AsyncMock()
        self.session.refresh = AsyncMock()
        self.repository = SqlAlchemyAnalysisRepository(self.session)

    def test_create_commits_pending_analysis_and_returns_id(self):
        def assign_id(analysis):
            analysis.id = 17

        self.session.add.side_effect = assign_id

        result = asyncio.run(self.repository.create(
            image_path="https://example.com/leaf.jpg",
            temperature="28",
            humidity="85",
        ))

        self.assertEqual(result, 17)
        analysis = self.session.add.call_args.args[0]
        self.assertEqual(analysis.status, AnalysisStatus.PENDING)
        self.assertEqual(analysis.retry_count, 0)
        self.assertEqual(analysis.image_path, "https://example.com/leaf.jpg")
        self.assertEqual(analysis.temperature, "28")
        self.assertEqual(analysis.humidity, "85")
        self.session.commit.assert_awaited_once_with()
        self.session.flush.assert_not_awaited()
        self.session.refresh.assert_not_awaited()

    def test_get_by_id_returns_snapshot_without_commit(self):
        created_at = datetime.now(timezone.utc)
        analysis = Analysis(
            id=3,
            status=AnalysisStatus.PENDING,
            image_path="image",
            temperature="28",
            humidity="85",
            retry_count=0,
            created_at=created_at,
        )
        self.session.get.return_value = analysis

        result = asyncio.run(self.repository.get_by_id(3))

        self.assertEqual(result["id"], 3)
        self.assertEqual(result["status"], AnalysisStatus.PENDING)
        self.assertEqual(result["created_at"], created_at)
        self.assertEqual(set(result), set(Analysis.__table__.columns.keys()))
        self.session.commit.assert_not_awaited()

    def test_get_by_id_returns_none_when_missing(self):
        self.session.get.return_value = None

        self.assertIsNone(asyncio.run(self.repository.get_by_id(404)))
        self.session.commit.assert_not_awaited()

    def test_mark_processing_updates_status_and_started_at(self):
        analysis = self._analysis()
        self.session.get.return_value = analysis

        result = asyncio.run(self.repository.mark_processing(1))

        self.assertTrue(result)
        self.assertEqual(analysis.status, AnalysisStatus.PROCESSING)
        self.assertEqual(analysis.started_at.tzinfo, timezone.utc)
        self.session.commit.assert_awaited_once_with()

    def test_mark_completed_records_all_results(self):
        analysis = self._analysis()
        self.session.get.return_value = analysis

        result = asyncio.run(self.repository.mark_completed(
            1,
            is_plant=True,
            disease_code="Leaf_mold",
            disease_name="잎곰팡이병",
            explain="설명",
            cause="원인",
            cure="치료",
            model_version="classifier-v1",
            latency_ms=1250,
        ))

        self.assertTrue(result)
        self.assertEqual(analysis.status, AnalysisStatus.COMPLETED)
        self.assertTrue(analysis.is_plant)
        self.assertEqual(analysis.disease_code, "Leaf_mold")
        self.assertEqual(analysis.disease_name, "잎곰팡이병")
        self.assertEqual(analysis.explain, "설명")
        self.assertEqual(analysis.cause, "원인")
        self.assertEqual(analysis.cure, "치료")
        self.assertEqual(analysis.model_version, "classifier-v1")
        self.assertEqual(analysis.latency_ms, 1250)
        self.assertEqual(analysis.completed_at.tzinfo, timezone.utc)
        self.session.commit.assert_awaited_once_with()

    def test_mark_failed_records_error_and_job_retry_count(self):
        analysis = self._analysis()
        self.session.get.return_value = analysis

        result = asyncio.run(self.repository.mark_failed(
            1,
            error_code="MODEL_ERROR",
            error_message="classification failed",
            retry_count=2,
        ))

        self.assertTrue(result)
        self.assertEqual(analysis.status, AnalysisStatus.FAILED)
        self.assertEqual(analysis.error_code, "MODEL_ERROR")
        self.assertEqual(analysis.error_message, "classification failed")
        self.assertEqual(analysis.retry_count, 2)
        self.assertEqual(analysis.completed_at.tzinfo, timezone.utc)
        self.session.commit.assert_awaited_once_with()

    def test_missing_update_returns_false_without_commit(self):
        self.session.get.return_value = None

        self.assertFalse(asyncio.run(self.repository.mark_processing(404)))
        self.session.commit.assert_not_awaited()

    def test_commit_error_rolls_back_and_propagates(self):
        error = RuntimeError("commit failed")
        self.session.get.return_value = self._analysis()
        self.session.commit.side_effect = error

        with self.assertRaises(RuntimeError) as raised:
            asyncio.run(self.repository.mark_processing(1))

        self.assertIs(raised.exception, error)
        self.session.rollback.assert_awaited_once_with()
        self.session.flush.assert_not_awaited()

    @staticmethod
    def _analysis() -> Analysis:
        return Analysis(
            id=1,
            status=AnalysisStatus.PENDING,
            image_path="image",
            temperature="28",
            humidity="85",
            retry_count=0,
        )


if __name__ == "__main__":
    unittest.main()
