class AppError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(AppError):
    """Required local configuration is missing or invalid."""


class JobDescriptionFetchError(AppError):
    """A job description URL could not be fetched."""


class EmptyJobDescriptionError(AppError):
    """A job description page was fetched but yielded no useful text."""


class GroqServiceError(AppError):
    """A Groq API request failed."""


class GeneratedResultError(GroqServiceError):
    """AI output is invalid JSON or does not satisfy its response model."""


class UploadTooLargeError(AppError):
    """An uploaded resume or audio file exceeds its configured limit."""


class InputTooLongError(AppError):
    """The complete prompt exceeds the configured input budget."""


class SessionNotFoundError(AppError):
    """The requested interview session does not exist."""


class SessionConflictError(AppError):
    """An answer is stale or the session has already completed."""
