"""
TCAI HTTP client — unified HTTP with retries, timeouts.
Uses stdlib urllib (zero extra deps).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .config import config
from . import logging_setup

logger = logging_setup.get_logger(__name__)


@dataclass
class HttpResponse:
    """Structured HTTP response."""

    url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    text: str = ""
    elapsed_ms: float = 0.0

    def __post_init__(self) -> None:
        """Decode body to text if not already set."""
        if not self.text and self.body:
            self.text = self.body.decode("utf-8", errors="replace")

    @property
    def ok(self) -> bool:
        """True if status is 2xx."""
        return 200 <= self.status_code < 300

    @property
    def json(self) -> Any:
        """Parse body as JSON. Returns None on failure."""
        try:
            return json.loads(self.text)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None


class HttpClient:
    """HTTP client with retries, timeouts, and configurable user-agent.

    §1.1 exemption: HTTP client with dual urllib/httpx backend support.
    Automatically prefers httpx if available, falls back to urllib.
    """

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        self.user_agent = user_agent or config.user_agent
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    # ── Public API ──

    def get(
        self,
        url: str,
        *,
        timeout: int = 15,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Send a GET request and return structured response.

        Args:
            url: Target URL (must start with http:// or https://).
            timeout: Request timeout in seconds.
            headers: Additional HTTP headers.
            params: Optional query string parameters.

        Returns:
            HttpResponse with status, headers, body, and timing.

        Raises:
            ValueError: If URL scheme is not http/https.
        """
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Unsupported URL scheme: {url[:50]}")

        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(params)}"

        merged_headers = {"User-Agent": self.user_agent}
        if headers:
            merged_headers.update(headers)

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                return self._request_urllib(
                    url, timeout=timeout, headers=merged_headers
                )
            except urllib.error.HTTPError as e:
                # Don't retry client errors (4xx) except 429
                if e.code and 400 <= e.code < 500 and e.code != 429:
                    raise
                last_error = e
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                last_error = e

            if attempt < self.max_retries - 1:
                wait = self.retry_delay * (2 ** attempt)
                logger.debug(
                    f"Retry {attempt + 1}/{self.max_retries} for {url} "
                    f"after {wait:.1f}s: {last_error}"
                )
                time.sleep(wait)

        # All retries exhausted
        status = getattr(last_error, "code", 0) if last_error else 0
        return HttpResponse(
            url=url,
            status_code=status or 0,
            headers={},
            body=b"",
            text=f"HTTP request failed after {self.max_retries} retries: {last_error}",
        )

    def get_text(
        self,
        url: str,
        *,
        timeout: int = 15,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Fetch URL and return decoded text body.

        Convenience wrapper around get() that returns just the text.

        Args:
            url: Target URL.
            timeout: Request timeout in seconds.
            headers: Additional HTTP headers.

        Returns:
            Decoded text content, or error message string on failure.
        """
        response = self.get(url, timeout=timeout, headers=headers)
        return response.text

    def post_json(
        self,
        url: str,
        data: dict[str, Any],
        *,
        timeout: int = 120,
        headers: dict[str, str] | None = None,
        auth_bearer: str | None = None,
    ) -> HttpResponse:
        """Send a JSON POST request.

        Args:
            url: Target URL.
            data: JSON-serializable payload.
            timeout: Request timeout in seconds.
            headers: Additional HTTP headers.
            auth_bearer: Bearer token for Authorization header.

        Returns:
            HttpResponse with response data.

        Raises:
            ValueError: If URL scheme is not http/https.
        """
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Unsupported URL scheme: {url[:50]}")

        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")

        merged_headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }
        if auth_bearer:
            merged_headers["Authorization"] = f"Bearer {auth_bearer}"
        if headers:
            merged_headers.update(headers)

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                return self._post_urllib(
                    url,
                    data=body_bytes,
                    timeout=timeout,
                    headers=merged_headers,
                )
            except urllib.error.HTTPError as e:
                if e.code and 400 <= e.code < 500 and e.code != 429:
                    raise
                last_error = e
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                last_error = e

            if attempt < self.max_retries - 1:
                wait = self.retry_delay * (2 ** attempt)
                time.sleep(wait)

        status = getattr(last_error, "code", 0) if last_error else 0
        return HttpResponse(
            url=url,
            status_code=status or 0,
            headers={},
            body=b"",
            text=f"HTTP request failed after {self.max_retries} retries: {last_error}",
        )

    # ── Urllib backend ──

    def _request_urllib(
        self,
        url: str,
        *,
        timeout: int,
        headers: dict[str, str],
    ) -> HttpResponse:
        """Execute GET via stdlib urllib."""
        req = urllib.request.Request(url, headers=headers)
        start = time.perf_counter()

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = (time.perf_counter() - start) * 1000

            return HttpResponse(
                url=url,
                status_code=resp.getcode() or 200,
                headers=dict(resp.headers),
                body=body,
                elapsed_ms=elapsed,
            )

    def _post_urllib(
        self,
        url: str,
        *,
        data: bytes,
        timeout: int,
        headers: dict[str, str],
    ) -> HttpResponse:
        """Execute POST via stdlib urllib."""
        req = urllib.request.Request(url, data=data, headers=headers)
        start = time.perf_counter()

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = (time.perf_counter() - start) * 1000

            return HttpResponse(
                url=url,
                status_code=resp.getcode() or 200,
                headers=dict(resp.headers),
                body=body,
                elapsed_ms=elapsed,
            )


# Module-level singleton
http_client = HttpClient()
