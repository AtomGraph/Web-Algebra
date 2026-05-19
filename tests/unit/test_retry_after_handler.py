"""Tests for RetryAfterHandler — HTTP 429 retry logic (src/web_algebra/client.py).

Not in formal-semantics.md (client infrastructure, not an operation).
Behaviour spec: on 429, sleep Retry-After seconds then retry; raise HTTPError
after max_retries exhausted.
"""

from __future__ import annotations

import urllib.error
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import MagicMock, patch

import pytest

from web_algebra.client import RetryAfterHandler


def _req(url: str = "http://example.org/resource") -> MagicMock:
    req = MagicMock()
    req.full_url = url
    return req


class TestRetryAfterHandlerNumericDelay:
    def test_sleeps_numeric_retry_after(self):
        handler = RetryAfterHandler()
        handler.parent = MagicMock()
        handler.parent.open.return_value = "ok"

        with patch("web_algebra.client.time.sleep") as mock_sleep:
            result = handler.http_error_429(
                _req(), None, 429, "Too Many Requests", {"Retry-After": "2"}
            )

        mock_sleep.assert_called_once_with(2.0)
        assert result == "ok"

    def test_defaults_to_1s_when_header_absent(self):
        handler = RetryAfterHandler()
        handler.parent = MagicMock()
        handler.parent.open.return_value = "ok"

        with patch("web_algebra.client.time.sleep") as mock_sleep:
            handler.http_error_429(_req(), None, 429, "Too Many Requests", {})

        mock_sleep.assert_called_once_with(1.0)


class TestRetryAfterHandlerDateDelay:
    def test_sleeps_computed_seconds_for_future_http_date(self):
        handler = RetryAfterHandler()
        handler.parent = MagicMock()
        handler.parent.open.return_value = "ok"

        future = datetime.now(tz=timezone.utc) + timedelta(seconds=5)
        hdrs = {"Retry-After": format_datetime(future)}

        with patch("web_algebra.client.time.sleep") as mock_sleep:
            handler.http_error_429(_req(), None, 429, "Too Many Requests", hdrs)

        delay = mock_sleep.call_args[0][0]
        assert 4.0 <= delay <= 6.0

    def test_clamps_past_http_date_to_zero(self):
        handler = RetryAfterHandler()
        handler.parent = MagicMock()
        handler.parent.open.return_value = "ok"

        past = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
        hdrs = {"Retry-After": format_datetime(past)}

        with patch("web_algebra.client.time.sleep") as mock_sleep:
            handler.http_error_429(_req(), None, 429, "Too Many Requests", hdrs)

        mock_sleep.assert_called_once_with(0.0)


class TestRetryAfterHandlerRetryLimit:
    def test_raises_http_error_when_max_retries_exhausted(self):
        handler = RetryAfterHandler(max_retries=2)
        handler.parent = MagicMock()
        req = _req()
        handler._retry_counts[req.full_url] = 2

        with patch("web_algebra.client.time.sleep"):
            with pytest.raises(urllib.error.HTTPError):
                handler.http_error_429(req, None, 429, "Too Many Requests", {})

    def test_clears_retry_count_after_exhaustion(self):
        handler = RetryAfterHandler(max_retries=1)
        handler.parent = MagicMock()
        req = _req()
        handler._retry_counts[req.full_url] = 1

        with patch("web_algebra.client.time.sleep"):
            with pytest.raises(urllib.error.HTTPError):
                handler.http_error_429(req, None, 429, "Too Many Requests", {})

        assert req.full_url not in handler._retry_counts

    def test_increments_retry_count_on_each_attempt(self):
        handler = RetryAfterHandler(max_retries=3)
        handler.parent = MagicMock()
        handler.parent.open.return_value = "ok"
        req = _req()

        with patch("web_algebra.client.time.sleep"):
            handler.http_error_429(req, None, 429, "Too Many Requests", {"Retry-After": "0"})

        assert handler._retry_counts[req.full_url] == 1

    def test_retries_up_to_but_not_exceeding_max_retries(self):
        handler = RetryAfterHandler(max_retries=2)
        handler.parent = MagicMock()
        handler.parent.open.return_value = "ok"
        req = _req()

        with patch("web_algebra.client.time.sleep"):
            handler.http_error_429(req, None, 429, "Too Many Requests", {"Retry-After": "0"})
            handler.http_error_429(req, None, 429, "Too Many Requests", {"Retry-After": "0"})
            with pytest.raises(urllib.error.HTTPError):
                handler.http_error_429(req, None, 429, "Too Many Requests", {"Retry-After": "0"})
