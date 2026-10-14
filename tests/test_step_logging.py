"""Step logs preserve correlation and exclude private arguments and errors."""

import json
import unittest
from backend.utils.logging_utils import logged_step, REQUEST_ID
from backend.api_backend.middleware import RequestLoggingMiddleware


class StepLoggingTests(unittest.IsolatedAsyncioTestCase):
    def test_failed_step_is_logged_without_secret(self):
        @logged_step("example")
        def failing(secret):
            raise ValueError(secret)

        token = REQUEST_ID.set("test-request")
        try:
            with self.assertLogs("interview_coach", level="INFO") as logs:
                with self.assertRaises(ValueError):
                    failing("private-answer")
            self.assertEqual(
                [r.msg for r in logs.records], ["operation_started", "operation_failed"]
            )
            self.assertEqual(logs.records[-1].context["request_id"], "test-request")
            self.assertNotIn("private-answer", json.dumps(logs.records[-1].context))
        finally:
            REQUEST_ID.reset(token)

    async def test_async_step_retains_result(self):
        @logged_step("async_example")
        async def example():
            return 42

        with self.assertLogs("interview_coach", level="INFO") as logs:
            self.assertEqual(await example(), 42)
        self.assertEqual(
            [r.msg for r in logs.records], ["operation_started", "operation_completed"]
        )

    async def test_proxy_correlation_and_invalid_id(self):
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        for incoming in (b"12345678-1234-4234-8234-123456789abc", b"private-answer"):
            messages = []

            async def send(message):
                messages.append(message)

            scope = {
                "type": "http",
                "method": "GET",
                "headers": [(b"x-request-id", incoming)],
            }
            with self.assertLogs("interview_coach", level="INFO") as logs:
                await RequestLoggingMiddleware(app)(scope, None, send)
            identifier = dict(messages[0]["headers"])[b"x-request-id"].decode()
            self.assertEqual(len(identifier), 32)
            if incoming.startswith(b"1234"):
                self.assertEqual(identifier, incoming.decode().replace("-", ""))
            self.assertTrue(
                all(r.context["request_id"] == identifier for r in logs.records)
            )
            self.assertIsNone(REQUEST_ID.get())
