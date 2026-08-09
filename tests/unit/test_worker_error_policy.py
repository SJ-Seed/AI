import unittest

import requests

from app.domain.exceptions import InvalidDiagnosisResponse
from app.worker.error_policy import classify_ai_error


class StatusError(RuntimeError):
    def __init__(self, status_code):
        self.status_code = status_code


class WorkerErrorPolicyTest(unittest.TestCase):
    def test_network_and_temporary_status_errors_are_retryable(self):
        for error in (
            requests.Timeout("timeout"),
            requests.ConnectionError("connection"),
            StatusError(408),
            StatusError(409),
            StatusError(429),
            StatusError(503),
        ):
            with self.subTest(error=error):
                self.assertTrue(classify_ai_error(error).retryable)

    def test_wrapped_provider_status_is_inspected(self):
        inner = StatusError(503)
        outer = RuntimeError("DSPy wrapper")
        outer.__cause__ = inner
        self.assertTrue(classify_ai_error(outer).retryable)

    def test_auth_invalid_response_and_unknown_errors_are_permanent(self):
        auth = classify_ai_error(StatusError(401))
        invalid = classify_ai_error(InvalidDiagnosisResponse("bad output"))
        unknown = classify_ai_error(RuntimeError("bug"))
        self.assertFalse(auth.retryable)
        self.assertEqual(auth.error_code, "AI_AUTHENTICATION_ERROR")
        self.assertFalse(invalid.retryable)
        self.assertEqual(invalid.error_code, "AI_ANALYSIS_ERROR")
        self.assertFalse(unknown.retryable)
        self.assertEqual(unknown.error_code, "WORKER_INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
