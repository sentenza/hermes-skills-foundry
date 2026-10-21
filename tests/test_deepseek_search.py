#!/usr/bin/env python3
"""Tests for skills/deepseek-search/scripts/deepseek_search.py.

The transport is standard library only (urllib), so these tests need no
third-party packages.

Run: python3 -m unittest discover -s tests
"""

import importlib.util
import io
import json
import os
import socket
import ssl
import sys
import unittest
import urllib.error
import urllib.request
import warnings
from pathlib import Path
from unittest import mock

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "deepseek-search"
    / "scripts"
    / "deepseek_search.py"
)

_spec = importlib.util.spec_from_file_location("deepseek_search", SCRIPT)
ds = importlib.util.module_from_spec(_spec)
sys.modules["deepseek_search"] = ds
_spec.loader.exec_module(ds)

warnings.simplefilter("ignore", ResourceWarning)

URL = "https://api.deepseek.com/v1/tools/search"


class FakeResponse:
    """Minimal stand-in for an urllib response object."""

    def __init__(self, body, status=200, headers=None):
        self.status = status
        self.headers = headers or {}
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """Replacement for urllib's opener: returns queued items or raises queued errors."""

    def __init__(self, items):
        self.items = list(items)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        item = self.items.pop(0)
        if callable(item) and not isinstance(item, Exception):
            item = item()
        if isinstance(item, Exception):
            raise item
        return item


class _Body(io.BytesIO):
    """BytesIO that survives the implicit cleanup urllib does on an error body."""

    def close(self):
        pass


def http_error(status, body, headers=None):
    """Build the HTTPError urllib raises for a non-2xx response."""
    return urllib.error.HTTPError(
        URL, status, "error", headers or {}, _Body(body.encode("utf-8"))
    )


def api_error_body(message="boom", code="bad_request"):
    return json.dumps({"error": {"message": message, "code": code}})


class DeepSeekScriptTest(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.env = mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sleep = mock.patch.object(ds.time, "sleep")
        self.sleep_mock = self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def opener(self, items):
        fake = FakeOpener(items)
        patcher = mock.patch.object(ds, "_OPENER", fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    # --- request shape -----------------------------------------------------

    def test_request_carries_bearer_token_and_json_payload(self):
        fake = self.opener([FakeResponse(json.dumps({"results": []}))])
        ds.search("DeepSeek V4", count=3)
        request = fake.requests[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["query"], "DeepSeek V4")
        self.assertEqual(payload["count"], 3)
        self.assertFalse(payload["need_content"])
        self.assertEqual(request.get_method(), "POST")

    def test_redirect_to_other_host_drops_authorization(self):
        handler = ds._SafeRedirectHandler()
        request = urllib.request.Request(URL, headers={"Authorization": "Bearer test-key"})

        moved = handler.redirect_request(
            request, None, 302, "Found", {}, "https://elsewhere.example.com/x"
        )
        self.assertIsNotNone(moved)
        self.assertNotIn("Authorization", moved.headers)

        same_host = handler.redirect_request(
            request, None, 302, "Found", {}, "https://api.deepseek.com/v1/tools/other"
        )
        self.assertEqual(same_host.get_header("Authorization"), "Bearer test-key")

    # --- error body shapes -------------------------------------------------

    def test_error_body_shapes_raise_api_error(self):
        bodies = [
            json.dumps({"error": "unauthorized"}),
            json.dumps([1, 2]),
            json.dumps("plain string"),
            json.dumps({"message": "boom"}),
            json.dumps({}),
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.opener([http_error(400, body)])
                with self.assertRaises(ds.DeepSeekAPIError):
                    ds.search("q")

    def test_error_body_not_json_raises_api_error(self):
        self.opener(
            [lambda: http_error(502, "<html>gateway</html>")] * (ds.MAX_RETRIES + 1)
        )
        with self.assertRaises(ds.DeepSeekRetryableError) as ctx:
            ds.search("q")
        self.assertIn("gateway", str(ctx.exception))

    def test_error_message_truncated(self):
        self.opener([http_error(400, "x" * 5000)])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertLess(len(ctx.exception.message), 600)

    def test_request_id_reported(self):
        self.opener([http_error(400, api_error_body(), {"x-request-id": "req-42"})])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertEqual(ctx.exception.request_id, "req-42")
        self.assertIn("request_id=req-42", str(ctx.exception))

    def test_request_id_from_body(self):
        self.opener([http_error(400, json.dumps({"error": "x", "request_id": "req-7"}))])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertEqual(ctx.exception.request_id, "req-7")

    # --- success path ------------------------------------------------------

    def test_non_dict_success_raises_api_error(self):
        self.opener([FakeResponse(json.dumps([1, 2]))])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertIn("Unexpected response shape", str(ctx.exception))

    def test_invalid_json_success_raises_api_error(self):
        self.opener([FakeResponse("not json")])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_success_returns_dict(self):
        self.opener([FakeResponse(json.dumps({"results": []}))])
        self.assertEqual(ds.search("q"), {"results": []})

    # --- retry semantics ---------------------------------------------------

    def test_429_retries_then_succeeds(self):
        fake = self.opener(
            [http_error(429, api_error_body("rate limited")), FakeResponse(json.dumps({"results": []}))]
        )
        self.assertEqual(ds.search("q"), {"results": []})
        self.assertEqual(len(fake.requests), 2)

    def test_retry_after_header_is_honored(self):
        self.opener(
            [
                http_error(429, api_error_body("rate limited"), {"Retry-After": "5"}),
                FakeResponse(json.dumps({"results": []})),
            ]
        )
        ds.search("q")
        self.assertGreaterEqual(self.sleep_mock.call_args_list[0].args[0], 5.0)

    def test_retry_after_is_capped(self):
        self.opener(
            [
                http_error(429, api_error_body("rate limited"), {"Retry-After": "600"}),
                FakeResponse(json.dumps({"results": []})),
            ]
        )
        ds.search("q")
        self.assertLessEqual(self.sleep_mock.call_args_list[0].args[0], ds.MAX_RETRY_AFTER)

    def test_retryable_status_exhausts_to_retryable_error(self):
        fake = self.opener(
            [lambda: http_error(503, api_error_body("down"))] * (ds.MAX_RETRIES + 1)
        )
        with self.assertRaises(ds.DeepSeekRetryableError):
            ds.search("q")
        self.assertEqual(len(fake.requests), ds.MAX_RETRIES + 1)

    def test_timeout_is_retried_then_retryable_error(self):
        fake = self.opener(
            [lambda: urllib.error.URLError(socket.timeout("timed out"))]
            * (ds.MAX_RETRIES + 1)
        )
        with self.assertRaises(ds.DeepSeekRetryableError):
            ds.search("q")
        self.assertEqual(len(fake.requests), ds.MAX_RETRIES + 1)

    def test_ssl_error_is_not_retried(self):
        fake = self.opener(
            [urllib.error.URLError(ssl.SSLCertVerificationError("bad cert"))]
        )
        with self.assertRaises(ds.DeepSeekAPIError):
            ds.search("q")
        self.assertEqual(len(fake.requests), 1)

    def test_dns_error_is_not_retried(self):
        fake = self.opener([urllib.error.URLError(socket.gaierror("unknown host"))])
        with self.assertRaises(ds.DeepSeekAPIError):
            ds.search("q")
        self.assertEqual(len(fake.requests), 1)

    # --- content cap -------------------------------------------------------

    def test_max_content_chars_truncates_results(self):
        body = json.dumps({"results": [{"title": "t", "content": "y" * 5000}]})
        self.opener([FakeResponse(body)])
        data = ds.search("q", need_content=True, count=1, max_content_chars=100)
        self.assertTrue(data["results"][0]["content"].startswith("y" * 100))
        self.assertIn("truncated", data["results"][0]["content"])
        self.assertLess(len(data["results"][0]["content"]), 200)

    def test_max_content_chars_truncates_fetch(self):
        self.opener([FakeResponse(json.dumps({"title": "t", "content": "z" * 5000}))])
        data = ds.fetch("https://example.com", max_content_chars=50)
        self.assertTrue(data["content"].startswith("z" * 50))

    def test_content_untouched_without_cap(self):
        body = json.dumps({"results": [{"content": "y" * 5000}]})
        self.opener([FakeResponse(body)])
        data = ds.search("q", count=1)
        self.assertEqual(len(data["results"][0]["content"]), 5000)

    def test_need_content_with_high_count_warns(self):
        self.opener([FakeResponse(json.dumps({"results": []}))])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ds.search("q", need_content=True, count=50)
        self.assertTrue(any("full page bodies" in str(w.message) for w in caught))

    def test_need_content_with_low_count_does_not_warn(self):
        self.opener([FakeResponse(json.dumps({"results": []}))])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ds.search("q", need_content=True, count=5)
        self.assertFalse(any("full page bodies" in str(w.message) for w in caught))

    # --- input validation --------------------------------------------------

    def test_missing_api_key_raises_runtime_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                ds.search("q")

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            ds.search("")
        with self.assertRaises(ValueError):
            ds.search("q", count=0)
        with self.assertRaises(ValueError):
            ds.search("q", count=51)
        with self.assertRaises(ValueError):
            ds.fetch("http://example.com")
        with self.assertRaises(ValueError):
            ds.fetch("")
        with self.assertRaises(ValueError):
            ds.search("q", ori_question=" ")


if __name__ == "__main__":
    unittest.main()
