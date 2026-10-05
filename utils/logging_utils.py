"""Terminal JSON logs without request bodies, credentials, or exception inputs."""

import json
import logging
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter

import config

REQUEST_ID = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            **getattr(record, "context", {}),
        }
        return json.dumps(payload, ensure_ascii=False)


def get_logger():
    logger = logging.getLogger("interview_coach")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(config.LOG_LEVEL)
    logger.propagate = False
    return logger


def log_event(event, *, level=logging.ERROR, **context):
    if REQUEST_ID.get():
        context["request_id"] = REQUEST_ID.get()
    get_logger().log(level, event, extra={"context": context})


def log_info(event, **context):
    log_event(event, level=logging.INFO, **context)


@contextmanager
def log_operation(operation, **context):
    started = perf_counter()
    log_info("operation_started", operation=operation, **context)
    yield
    log_info(
        "operation_completed",
        operation=operation,
        duration_ms=round((perf_counter() - started) * 1000, 2),
        **context,
    )


def log_error(exc, *, event, **context):
    frames = traceback.extract_tb(exc.__traceback__)
    context["error_type"] = type(exc).__name__
    context["traceback"] = [
        {"file": frame.filename, "line": frame.lineno, "function": frame.name}
        for frame in frames
    ]
    log_event(event, **context)
