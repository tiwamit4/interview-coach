"""HTTP timeouts and bounded retries for transient GET failures."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config


def get_url(url, **kwargs):
    retries = Retry(
        total=config.HTTP_MAX_RETRIES,
        allowed_methods=frozenset({"GET"}),
        status_forcelist=(429, 500, 502, 503, 504),
        backoff_factor=config.HTTP_RETRY_BACKOFF_SECONDS,
        backoff_max=config.HTTP_RETRY_BACKOFF_MAX_SECONDS,
        respect_retry_after_header=False,
        raise_on_status=False,
    )
    with requests.Session() as session:
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session.get(
            url,
            timeout=(
                config.HTTP_CONNECT_TIMEOUT_SECONDS,
                config.HTTP_READ_TIMEOUT_SECONDS,
            ),
            **kwargs,
        )
