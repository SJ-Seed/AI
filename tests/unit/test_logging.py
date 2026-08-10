import io
import json
import logging
import unittest

from pythonjsonlogger.json import JsonFormatter

from app.core.logging import log_analysis_status_change


class AnalysisLoggingTest(unittest.TestCase):
    def test_status_event_is_json_and_contains_stable_fields(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(
            JsonFormatter("%(levelname)s %(name)s %(message)s")
        )
        logger = logging.getLogger("test.analysis.status")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        log_analysis_status_change(
            logger,
            analysis_id=11,
            status="FAILED",
            duration_ms=1250,
            retry_count=2,
            failure_reason="AI_ANALYSIS_ERROR",
        )

        event = json.loads(stream.getvalue())
        self.assertEqual(event["event"], "analysis_status_changed")
        self.assertEqual(event["analysis_id"], 11)
        self.assertEqual(event["status"], "FAILED")
        self.assertEqual(event["duration_ms"], 1250)
        self.assertEqual(event["retry_count"], 2)
        self.assertEqual(event["failure_reason"], "AI_ANALYSIS_ERROR")


if __name__ == "__main__":
    unittest.main()
