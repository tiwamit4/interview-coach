"""Concurrency, SQLite cleanup, and provider input/output limits."""

import asyncio
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from groq import Groq

import config
import sqlite3
from api import app
from api_backend.routes import workflows
from errors import GroqServiceError, InputTooLongError
from utils import groq_service, history
from utils.database import connection


class ConcurrentApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_generation_does_not_block_health_requests(self):
        started, release = Event(), Event()

        def slow_scrape(url):
            started.set()
            if not release.wait(3):
                raise RuntimeError("Worker was not released")
            return "Job description"

        with patch.object(
            workflows, "scrape_job_description", side_effect=slow_scrape
        ), patch.object(
            workflows, "groq_prompt_call", return_value="Questions"
        ), patch.object(
            workflows, "save_history"
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                pending = asyncio.create_task(
                    client.post(
                        "/run",
                        data={
                            "task": "jd_questions",
                            "jd_url": "https://example.com/job",
                            "save_output": "false",
                        },
                    )
                )
                try:
                    for _ in range(100):
                        if started.is_set():
                            break
                        await asyncio.sleep(0.01)
                    self.assertTrue(started.is_set())
                    self.assertFalse(pending.done())
                    response = await asyncio.wait_for(
                        client.get("/health"), timeout=0.5
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertFalse(pending.done())
                finally:
                    release.set()
                    response = await pending
                self.assertEqual(response.status_code, 200, response.text)


class DatabaseTests(unittest.TestCase):
    def test_connection_closes_and_transaction_rolls_back(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            with patch.object(history, "DB_PATH", path):
                with self.assertRaises(RuntimeError):
                    with history.get_connection() as db:
                        db.execute(
                            "INSERT INTO history (event_type, title, payload, created_at) VALUES ('test', 'test', '{}', 'now')"
                        )
                        raise RuntimeError("rollback")
                with self.assertRaises(sqlite3.ProgrammingError):
                    db.execute("SELECT 1")
                self.assertEqual(history.list_history(), [])
                history.save_history("test", "résumé", {"text": "हिंदी"})
                with connection(path) as current:
                    self.assertEqual(
                        current.execute("PRAGMA journal_mode").fetchone()[0], "wal"
                    )
                    self.assertEqual(
                        current.execute("PRAGMA busy_timeout").fetchone()[0],
                        config.SQLITE_BUSY_TIMEOUT_SECONDS * 1000,
                    )
                self.assertEqual(history.get_history(1)["payload"], {"text": "हिंदी"})
                path.unlink()

    def test_concurrent_history_writes(self):
        with TemporaryDirectory() as directory, patch.object(
            history, "DB_PATH", Path(directory) / "history.db"
        ):
            with ThreadPoolExecutor(max_workers=6) as workers:
                ids = list(
                    workers.map(
                        lambda index: history.save_history(
                            "test", str(index), {"index": index}
                        ),
                        range(24),
                    )
                )
            self.assertEqual(len(set(ids)), 24)
            self.assertEqual(len(history.list_history(50)), 24)


class ProviderLimitTests(unittest.TestCase):
    def choice(self, content, finish_reason):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason=finish_reason,
                )
            ]
        )

    def test_long_input_is_rejected_before_creating_client(self):
        with patch.object(config, "MAX_CHAT_PROMPT_BYTES", 8), patch.object(
            groq_service, "get_groq_client"
        ) as client:
            with self.assertRaises(InputTooLongError):
                groq_service.groq_prompt_call(
                    "{text}", text="\u0939\u093f\u0902\u0926\u0940"
                )
            client.assert_not_called()

    def test_truncated_response_expands_budget_without_returning_partial_json(self):
        client = Mock()
        client.chat.completions.create.side_effect = [
            self.choice('{"partial":', "length"),
            self.choice("complete", "stop"),
        ]
        with patch.object(
            groq_service, "get_groq_client", return_value=client
        ), patch.multiple(
            config,
            PROMPT_MAX_COMPLETION_TOKENS=10,
            CHAT_MAX_COMPLETION_TOKENS=40,
            CHAT_COMPLETION_EXPANSIONS=2,
        ):
            self.assertEqual(groq_service.groq_prompt_call("prompt"), "complete")
        self.assertEqual(
            [
                call.kwargs["max_completion_tokens"]
                for call in client.chat.completions.create.call_args_list
            ],
            [10, 20],
        )
        client.close.assert_called_once()

    def test_permanent_truncation_is_bounded_and_closes_client(self):
        client = Mock()
        client.chat.completions.create.return_value = self.choice("partial", "length")
        with patch.object(
            groq_service, "get_groq_client", return_value=client
        ), patch.multiple(
            config,
            PROMPT_MAX_COMPLETION_TOKENS=10,
            CHAT_MAX_COMPLETION_TOKENS=20,
            CHAT_COMPLETION_EXPANSIONS=2,
        ):
            with self.assertRaisesRegex(GroqServiceError, "cut off"):
                groq_service.groq_prompt_call("prompt")
        self.assertEqual(client.chat.completions.create.call_count, 2)
        client.close.assert_called_once()

    def test_sdk_retries_temporary_failures_but_not_authentication_failures(self):
        for status, expected_calls in ((503, 3), (401, 1)):
            calls = []

            def transport(request):
                calls.append(request)
                if len(calls) < 3 or status == 401:
                    return httpx.Response(
                        status,
                        headers={"retry-after-ms": "1"},
                        json={"error": {"message": "service failure"}},
                    )
                return httpx.Response(
                    200,
                    json={
                        "id": "test",
                        "object": "chat.completion",
                        "created": 1,
                        "model": "test",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": "success"},
                            }
                        ],
                    },
                )

            sdk = Groq(
                api_key="test-key",
                max_retries=2,
                timeout=1,
                http_client=httpx.Client(transport=httpx.MockTransport(transport)),
            )
            with self.subTest(status=status), patch.object(
                groq_service, "get_groq_client", return_value=sdk
            ):
                if status == 503:
                    self.assertEqual(groq_service.groq_prompt_call("prompt"), "success")
                else:
                    with self.assertRaises(GroqServiceError):
                        groq_service.groq_prompt_call("prompt")
                self.assertEqual(len(calls), expected_calls)
                self.assertTrue(sdk.is_closed())


if __name__ == "__main__":
    unittest.main()
