"""Shared output paths, filename handling, and serialization."""

import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from utils.logging_utils import log_info


def safe_filename(value):
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def safe_filename_from_url(url):
    parsed_url = urlparse(str(url))
    path_parts = [part for part in parsed_url.path.split("/") if part]
    slug = "_".join(path_parts[-2:]) if len(path_parts) >= 2 else parsed_url.netloc
    return safe_filename(slug)


def _write_output(directory, filename, serialize):
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = Path(filename)
    stem = safe_filename(base.stem)[:160] or "output"
    for _ in range(10):
        output_path = output_dir / f"{stem}_{uuid4().hex}{base.suffix}"
        try:
            output_file = output_path.open("x", encoding="utf-8")
        except FileExistsError:
            continue
        try:
            with output_file:
                output_file.write(serialize(output_path))
        except Exception:
            output_path.unlink(missing_ok=True)
            raise
        log_info("output_saved", output_path=str(output_path), format=base.suffix)
        return output_path
    raise FileExistsError("Could not allocate a unique output filename.")


def write_text_file(directory, filename, content):
    return _write_output(directory, filename, lambda path: content)


def write_json_file(directory, filename, content):
    def serialize(output_path):
        payload = content
        if isinstance(content, dict) and "output_path" in content:
            payload = {**content, "output_path": str(output_path)}
        return json.dumps(payload, indent=2, ensure_ascii=False)

    return _write_output(directory, filename, serialize)


def save_result(directory, filename, result):
    payload = {**result, "output_path": None}
    result["output_path"] = str(write_json_file(directory, filename, payload))
    return result
