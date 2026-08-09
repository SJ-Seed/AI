import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from app.core.config import Settings
from app.domain.models import DiagnosisOutcome
from app.infrastructure.image.image_downloader import ImageDownloadResult
from app.worker.tasks import (
    AI_ANALYSIS_ERROR,
    IMAGE_DOWNLOAD_ERROR,
    WORKER_INTERNAL_ERROR,
    ImageDownloadFailure,
    WorkerInternalFailure,
    process_analysis,
    shutdown,
    startup,
)


class AsyncSessionContext:
    async def __aenter__(self):
        return Mock()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class SessionFactory:
    def __call__(self):
        return AsyncSessionContext()


class WorkerTaskTest(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.repository.claim_pending = AsyncMock(return_value=True)
        self.repository.get_by_id = AsyncMock(return_value={
            "id": 11,
            "image_path": "https://example/image.jpg",
            "temperature": "28",
            "humidity": "85",
        })
        self.repository.mark_completed = AsyncMock(return_value=True)
        self.repository.mark_failed = AsyncMock(return_value=True)
        self.downloader = Mock()
        self.diagnosis_service = Mock()
        self.diagnosis_service.diagnose_with_details.return_value = DiagnosisOutcome(
            True,
            "Leaf_mold",
            "leaf mold",
            "explain",
            "cause",
            "cure",
        )
        self.ctx = {
            "session_factory": SessionFactory(),
            "image_downloader": self.downloader,
            "diagnosis_service": self.diagnosis_service,
            "model_version": "classifier-v1",
        }
        self.repository_patch = patch(
            "app.worker.tasks.SqlAlchemyAnalysisRepository",
            return_value=self.repository,
        )
        self.repository_patch.start()

    def tearDown(self):
        self.repository_patch.stop()

    def test_unclaimed_analysis_is_skipped(self):
        self.repository.claim_pending.return_value = False

        result = asyncio.run(process_analysis(self.ctx, 11))

        self.assertFalse(result)
        self.repository.get_by_id.assert_not_awaited()
        self.downloader.download.assert_not_called()
        self.diagnosis_service.diagnose_with_details.assert_not_called()
        self.repository.mark_completed.assert_not_awaited()
        self.repository.mark_failed.assert_not_awaited()

    def test_success_completes_analysis_and_removes_owned_temporary_file(self):
        path = self._temporary_file()
        self.downloader.download.return_value = ImageDownloadResult(path, None, True)

        with patch("app.worker.tasks.perf_counter", side_effect=[100.0, 101.25]):
            result = asyncio.run(process_analysis(self.ctx, 11))

        self.assertTrue(result)
        self.assertFalse(Path(path).exists())
        self.diagnosis_service.diagnose_with_details.assert_called_once_with(
            path,
            "28",
            "85",
        )
        kwargs = self.repository.mark_completed.await_args.kwargs
        self.assertEqual(kwargs["disease_code"], "Leaf_mold")
        self.assertEqual(kwargs["model_version"], "classifier-v1")
        self.assertEqual(kwargs["latency_ms"], 1250)

    def test_download_error_uses_fixed_code_and_safe_message(self):
        secret = "signed-url-secret"
        self.downloader.download.return_value = ImageDownloadResult(None, secret, False)

        with self.assertLogs("app.worker.tasks", level="ERROR") as logs:
            with self.assertRaises(ImageDownloadFailure):
                asyncio.run(process_analysis(self.ctx, 11))

        self.assertTrue(any(secret in entry for entry in logs.output))
        kwargs = self.repository.mark_failed.await_args.kwargs
        self.assertEqual(kwargs["error_code"], IMAGE_DOWNLOAD_ERROR)
        self.assertEqual(kwargs["error_message"], "Image download failed")
        self.assertNotIn(secret, kwargs["error_message"])

    def test_unexpected_downloader_exception_is_logged_safely_and_reraised(self):
        secret = "downloader-secret"
        error = RuntimeError(secret)
        self.downloader.download.side_effect = error

        with self.assertLogs("app.worker.tasks", level="ERROR") as logs:
            with self.assertRaises(RuntimeError) as raised:
                asyncio.run(process_analysis(self.ctx, 11))

        self.assertIs(raised.exception, error)
        self.assertTrue(any(secret in entry for entry in logs.output))
        kwargs = self.repository.mark_failed.await_args.kwargs
        self.assertEqual(kwargs["error_code"], IMAGE_DOWNLOAD_ERROR)
        self.assertEqual(kwargs["error_message"], "Image download failed")
        self.assertNotIn(secret, kwargs["error_message"])

    def test_ai_error_uses_fixed_code_preserves_local_file_and_reraises(self):
        local_path = self._temporary_file()
        secret = "provider-secret"
        error = RuntimeError(secret)
        self.downloader.download.return_value = ImageDownloadResult(local_path, None, False)
        self.diagnosis_service.diagnose_with_details.side_effect = error

        try:
            with self.assertLogs("app.worker.tasks", level="ERROR") as logs:
                with self.assertRaises(RuntimeError) as raised:
                    asyncio.run(process_analysis(self.ctx, 11))

            self.assertIs(raised.exception, error)
            self.assertTrue(Path(local_path).exists())
            self.assertTrue(any(secret in entry for entry in logs.output))
            kwargs = self.repository.mark_failed.await_args.kwargs
            self.assertEqual(kwargs["error_code"], AI_ANALYSIS_ERROR)
            self.assertEqual(kwargs["error_message"], "AI analysis failed")
            self.assertNotIn(secret, kwargs["error_message"])
        finally:
            Path(local_path).unlink(missing_ok=True)

    def test_rejected_completion_uses_internal_error(self):
        local_path = self._temporary_file()
        self.downloader.download.return_value = ImageDownloadResult(local_path, None, False)
        self.repository.mark_completed.return_value = False

        try:
            with self.assertLogs("app.worker.tasks", level="ERROR"):
                with self.assertRaises(WorkerInternalFailure):
                    asyncio.run(process_analysis(self.ctx, 11))

            kwargs = self.repository.mark_failed.await_args.kwargs
            self.assertEqual(kwargs["error_code"], WORKER_INTERNAL_ERROR)
            self.assertEqual(kwargs["error_message"], "Worker processing failed")
        finally:
            Path(local_path).unlink(missing_ok=True)

    def test_completion_storage_exception_uses_internal_code_and_reraises(self):
        local_path = self._temporary_file()
        secret = "database-secret"
        error = RuntimeError(secret)
        self.downloader.download.return_value = ImageDownloadResult(local_path, None, False)
        self.repository.mark_completed.side_effect = error

        try:
            with self.assertLogs("app.worker.tasks", level="ERROR") as logs:
                with self.assertRaises(RuntimeError) as raised:
                    asyncio.run(process_analysis(self.ctx, 11))

            self.assertIs(raised.exception, error)
            self.assertTrue(any(secret in entry for entry in logs.output))
            kwargs = self.repository.mark_failed.await_args.kwargs
            self.assertEqual(kwargs["error_code"], WORKER_INTERNAL_ERROR)
            self.assertEqual(kwargs["error_message"], "Worker processing failed")
            self.assertNotIn(secret, kwargs["error_message"])
        finally:
            Path(local_path).unlink(missing_ok=True)

    @staticmethod
    def _temporary_file() -> str:
        with tempfile.NamedTemporaryFile(delete=False) as temporary:
            return temporary.name


class WorkerLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            openai_api_key="key",
            database_url="postgresql+asyncpg://database",
            redis_url="redis://redis:6379/0",
            analysis_queue_name="analysis",
            model_path=Path("model"),
            model_version="v1",
            openai_timeout_seconds=30,
            max_retry_count=5,
            max_image_size_mb=10,
        )

    def test_startup_initializes_and_shutdown_closes_worker_resources(self):
        asyncio.run(self._run_lifecycle())

    async def _run_lifecycle(self):
        engine = Mock()
        engine.dispose = AsyncMock()
        client = Mock()
        service = Mock()
        session_factory = object()
        ctx = {}

        with patch("app.worker.tasks.load_settings", return_value=self.settings), patch(
            "app.worker.tasks.create_async_engine", return_value=engine
        ), patch(
            "app.worker.tasks.async_sessionmaker", return_value=session_factory
        ) as make_sessions, patch(
            "app.worker.tasks.build_ai_resources", return_value=(client, service)
        ) as build_ai, patch("app.worker.tasks.ImageDownloader") as downloader:
            await startup(ctx)

        build_ai.assert_called_once_with(self.settings)
        make_sessions.assert_called_once_with(engine, expire_on_commit=False)
        self.assertIs(ctx["diagnosis_service"], service)
        self.assertIs(ctx["session_factory"], session_factory)
        self.assertIs(ctx["image_downloader"], downloader.return_value)
        self.assertEqual(ctx["model_version"], "v1")

        await shutdown(ctx)

        client.close.assert_called_once_with()
        engine.dispose.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
