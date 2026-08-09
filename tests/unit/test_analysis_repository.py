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
        self.session.execute = AsyncMock()
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

    def test_claim_pending_atomically_changes_pending_to_processing(self):
        self._set_rowcounts(1)

        result = asyncio.run(self.repository.claim_pending(7))

        self.assertTrue(result)
        params = self._executed_params()
        self.assertEqual(params["id_1"], 7)
        self.assertEqual(params["status_1"], AnalysisStatus.PENDING)
        self.assertEqual(params["status"], AnalysisStatus.PROCESSING)
        self.assertEqual(params["started_at"].tzinfo, timezone.utc)
        self.session.commit.assert_awaited_once_with()
        self.session.rollback.assert_not_awaited()

    def test_claim_pending_returns_false_when_state_does_not_match(self):
        self._set_rowcounts(0)

        self.assertFalse(asyncio.run(self.repository.claim_pending(7)))

        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once_with()

    def test_claim_pending_or_stale_reclaims_expired_processing_analysis(self):
        self._set_rowcounts(1)
        stale_before = datetime(2026, 1, 1, tzinfo=timezone.utc)

        result = asyncio.run(
            self.repository.claim_pending_or_stale(7, stale_before=stale_before)
        )

        self.assertTrue(result)
        params = self._executed_params()
        self.assertIn(AnalysisStatus.PENDING, params.values())
        self.assertIn(AnalysisStatus.PROCESSING, params.values())
        self.assertIn(stale_before, params.values())
        self.session.commit.assert_awaited_once_with()

    def test_only_first_of_two_claims_succeeds(self):
        self._set_rowcounts(1, 0)

        first = asyncio.run(self.repository.claim_pending(7))
        second = asyncio.run(self.repository.claim_pending(7))

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(self.session.execute.await_count, 2)
        self.session.commit.assert_awaited_once_with()
        self.session.rollback.assert_awaited_once_with()

    def test_mark_processing_delegates_to_claim_pending(self):
        self.repository.claim_pending = AsyncMock(return_value=False)

        result = asyncio.run(self.repository.mark_processing(7))

        self.assertFalse(result)
        self.repository.claim_pending.assert_awaited_once_with(7)

    def test_reschedule_for_retry_atomically_increments_and_returns_count(self):
        result = Mock()
        result.scalar_one_or_none.return_value = 2
        self.session.execute.return_value = result

        retry_count = asyncio.run(
            self.repository.reschedule_for_retry(7, max_retry_count=4)
        )

        self.assertEqual(retry_count, 2)
        params = self._executed_params()
        self.assertEqual(params["id_1"], 7)
        self.assertEqual(params["status_1"], AnalysisStatus.PROCESSING)
        self.assertEqual(params["retry_count_1"], 1)
        self.assertEqual(params["retry_count_2"], 4)
        self.assertEqual(params["status"], AnalysisStatus.PENDING)
        self.assertIsNone(params["started_at"])
        self.assertIsNone(params["error_code"])
        self.session.commit.assert_awaited_once_with()

    def test_reschedule_for_retry_returns_none_when_state_or_limit_rejects(self):
        result = Mock()
        result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = result

        retry_count = asyncio.run(
            self.repository.reschedule_for_retry(7, max_retry_count=4)
        )

        self.assertIsNone(retry_count)
        self.session.rollback.assert_awaited_once_with()
        self.session.commit.assert_not_awaited()

    def test_mark_completed_requires_processing_and_records_all_results(self):
        self._set_rowcounts(1)

        result = asyncio.run(self.repository.mark_completed(
            1,
            is_plant=True,
            disease_code="Leaf_mold",
            disease_name="leaf mold",
            explain="explain",
            cause="cause",
            cure="cure",
            model_version="classifier-v1",
            latency_ms=1250,
        ))

        self.assertTrue(result)
        params = self._executed_params()
        self.assertEqual(params["status_1"], AnalysisStatus.PROCESSING)
        self.assertEqual(params["status"], AnalysisStatus.COMPLETED)
        self.assertTrue(params["is_plant"])
        self.assertEqual(params["disease_code"], "Leaf_mold")
        self.assertEqual(params["disease_name"], "leaf mold")
        self.assertEqual(params["explain"], "explain")
        self.assertEqual(params["cause"], "cause")
        self.assertEqual(params["cure"], "cure")
        self.assertEqual(params["model_version"], "classifier-v1")
        self.assertEqual(params["latency_ms"], 1250)
        self.assertEqual(params["completed_at"].tzinfo, timezone.utc)

    def test_mark_completed_rejects_non_processing_analysis(self):
        self._set_rowcounts(0)

        result = asyncio.run(self.repository.mark_completed(1, is_plant=True))

        self.assertFalse(result)
        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once_with()

    def test_mark_failed_only_accepts_processing_analysis(self):
        self._set_rowcounts(1)

        result = asyncio.run(self.repository.mark_failed(
            1,
            error_code="MODEL_ERROR",
            error_message="classification failed",
        ))

        self.assertTrue(result)
        params = self._executed_params()
        self.assertEqual(params["status_1"], AnalysisStatus.PROCESSING)
        self._assert_failure_params(params)

    def test_mark_enqueue_failed_only_accepts_pending_analysis(self):
        self._set_rowcounts(1)

        result = asyncio.run(self.repository.mark_enqueue_failed(
            1,
            error_code="QUEUE_ERROR",
            error_message="enqueue failed",
        ))

        self.assertTrue(result)
        params = self._executed_params()
        self.assertEqual(params["status_1"], AnalysisStatus.PENDING)
        self.assertEqual(params["error_code"], "QUEUE_ERROR")
        self.assertEqual(params["error_message"], "enqueue failed")
        self.assertNotIn("retry_count", params)

    def test_failure_transitions_return_false_for_disallowed_state(self):
        for method_name in ("mark_failed", "mark_enqueue_failed"):
            with self.subTest(method=method_name):
                self.session.reset_mock()
                self._set_rowcounts(0)
                method = getattr(self.repository, method_name)

                result = asyncio.run(method(
                    1,
                    error_code="ERROR",
                    error_message="failed",
                ))

                self.assertFalse(result)
                self.session.commit.assert_not_awaited()
                self.session.rollback.assert_awaited_once_with()

    def test_execute_error_rolls_back_and_propagates(self):
        error = RuntimeError("execute failed")
        self.session.execute.side_effect = error

        with self.assertRaises(RuntimeError) as raised:
            asyncio.run(self.repository.claim_pending(1))

        self.assertIs(raised.exception, error)
        self.session.rollback.assert_awaited_once_with()
        self.session.commit.assert_not_awaited()

    def test_transition_commit_error_rolls_back_and_propagates(self):
        self._set_rowcounts(1)
        error = RuntimeError("commit failed")
        self.session.commit.side_effect = error

        with self.assertRaises(RuntimeError) as raised:
            asyncio.run(self.repository.claim_pending(1))

        self.assertIs(raised.exception, error)
        self.session.rollback.assert_awaited_once_with()

    def test_create_commit_error_rolls_back_and_propagates(self):
        error = RuntimeError("commit failed")
        self.session.commit.side_effect = error

        with self.assertRaises(RuntimeError) as raised:
            asyncio.run(self.repository.create(
                image_path="image",
                temperature="28",
                humidity="85",
            ))

        self.assertIs(raised.exception, error)
        self.session.rollback.assert_awaited_once_with()

    def _set_rowcounts(self, *rowcounts: int) -> None:
        results = [Mock(rowcount=rowcount) for rowcount in rowcounts]
        self.session.execute.side_effect = results

    def _executed_params(self) -> dict[str, object]:
        statement = self.session.execute.await_args.args[0]
        return statement.compile().params

    def _assert_failure_params(self, params: dict[str, object]) -> None:
        self.assertEqual(params["status"], AnalysisStatus.FAILED)
        self.assertEqual(params["error_code"], "MODEL_ERROR")
        self.assertEqual(params["error_message"], "classification failed")
        self.assertEqual(params["completed_at"].tzinfo, timezone.utc)
        self.assertNotIn("retry_count", params)


if __name__ == "__main__":
    unittest.main()
