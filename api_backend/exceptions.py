"""Translate application errors into HTTP errors."""

from fastapi import HTTPException

from errors import (
    ConfigurationError,
    EmptyJobDescriptionError,
    GroqServiceError,
    InputTooLongError,
    JobDescriptionFetchError,
    SessionConflictError,
    SessionNotFoundError,
    UploadTooLargeError,
)
from utils.logging_utils import log_error


def to_http_exception(exc):
    log_error(exc, event="api_operation_failed")
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, InputTooLongError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, SessionNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, SessionConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, UploadTooLargeError):
        return HTTPException(status_code=413, detail=str(exc))
    if isinstance(exc, JobDescriptionFetchError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, EmptyJobDescriptionError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ConfigurationError):
        return HTTPException(status_code=500, detail=str(exc))
    if isinstance(exc, GroqServiceError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(
        status_code=500, detail="Something went wrong. Please try again."
    )
