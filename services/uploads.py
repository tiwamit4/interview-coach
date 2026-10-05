"""Upload validation shared by the API, UI, and extraction services."""

import config
from errors import UploadTooLargeError
from utils.logging_utils import log_info


def validate_upload_size(size, max_bytes, kind):
    if size > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise UploadTooLargeError(
            f"{kind.capitalize()} upload is too large. Maximum size is {limit_mb:g} MiB."
        )


async def read_upload(upload, max_bytes, kind):
    """Check reported size and read at most one byte beyond the allowed limit."""
    reported_size = getattr(upload, "size", None)
    if reported_size is not None:
        validate_upload_size(reported_size, max_bytes, kind)
    content = bytearray()
    while True:
        read_size = min(config.UPLOAD_READ_CHUNK_BYTES, max_bytes - len(content) + 1)
        chunk = await upload.read(read_size)
        if not chunk:
            break
        content.extend(chunk)
        validate_upload_size(len(content), max_bytes, kind)
    log_info("upload_received", kind=kind, size_bytes=len(content))
    return bytes(content)
