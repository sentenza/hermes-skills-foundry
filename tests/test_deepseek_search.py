#!/usr/bin/env python3
"""Tests for skills/deepseek-search/scripts/deepseek_search.py.

Run: python3 -m unittest discover -s tests
Requires: requests
"""

import importlib.util
import json
import os
import sys
import unittest
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

INVALID = object()


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.text = text if text is not None else json.dumps(json_data)
        self.headers = headers or {}

    def json(self):
        if self._json is INVALID:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._json


def api_error_body(message="boom", code="bad_request"):
    return {"error": {"message": message, "code": code}}


class DeepSeekScriptTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sleep = mock.patch.object(ds.time, "sleep")
        self.sleep_mock = self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def call(self, responses, side_effect=None):
        patcher = mock.patch.object(ds.requests, "request")
        request = patcher.start()
        self.addCleanup(patcher.stop)
        if side_effect is not None:
            request.side_effect = side_effect
        else:
            request.side_effect = list(responses)
        return request

    # --- error body shapes -------------------------------------------------

    def test_error_body_shapes_raise_api_error(self):
        bodies = [
            {"error": "unauthorized"},
            [1, 2],
            "plain string",
            {"message": "boom"},
            {},
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.call([FakeResponse(400, json_data=body)])
                with self.assertRaises(ds.DeepSeekAPIError):
                    ds.search("q")

    def test_error_body_not_json_raises_api_error(self):
        self.call(
            [FakeResponse(502, json_data=INVALID, text="<html>gateway</html>")]
            * (ds.MAX_RETRIES + 1)
        )
        with self.assertRaises(ds.DeepSeekRetryableError) as ctx:
            ds.search("q")
        self.assertIn("gateway", str(ctx.exception))

    def test_error_message_truncated(self):
        self.call([FakeResponse(400, json_data=INVALID, text="x" * 5000)])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertLess(len(ctx.exception.message), 600)

    def test_request_id_reported(self):
        self.call(
            [
                FakeResponse(
                    400, json_data=api_error_body(), headers={"x-request-id": "req-42"}
                )
            ]
        )
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertEqual(ctx.exception.request_id, "req-42")
        self.assertIn("request_id=req-42", str(ctx.exception))

    def test_request_id_from_body(self):
        self.call([FakeResponse(400, json_data={"error": "x", "request_id": "req-7"})])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertEqual(ctx.exception.request_id, "req-7")

    # --- success path ------------------------------------------------------

    def test_non_dict_success_raises_api_error(self):
        self.call([FakeResponse(200, json_data=[1, 2])])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertIn("Unexpected response shape", str(ctx.exception))

    def test_invalid_json_success_raises_api_error(self):
        self.call([FakeResponse(200, json_data=INVALID, text="not json")])
        with self.assertRaises(ds.DeepSeekAPIError) as ctx:
            ds.search("q")
        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_success_returns_dict(self):
        self.call([FakeResponse(200, json_data={"results": []})])
        self.assertEqual(ds.search("q"), {"results": []})

    # --- retry semantics ---------------------------------------------------

    def test_429_retries_then_succeeds(self):
        request = self.call(
            [
                FakeResponse(429, json_data=api_error_body("rate limited")),
                FakeResponse(200, json_data={"results": []}),
            ]
        )
        self.assertEqual(ds.search("q"), {"results": []})
        self.assertEqual(request.call_count, 2)

    def test_retry_after_header_is_honored(self):
        self.call(
            [
                FakeResponse(
                    429, json_data=api_error_body("rate limited"), headers={"Retry-After": "5"}
                ),
                FakeResponse(200, json_data={"results": []}),
            ]
        )
        ds.search("q")
        self.assertGreaterEqual(self.sleep_mock.call_args_list[0].args[0], 5.0)

    def test_retry_after_is_capped(self):
        self.call(
            [
                FakeResponse(
                    429, json_data=api_error_body("rate limited"), headers={"Retry-After": "600"}
                ),
                FakeResponse(200, json_data={"results": []}),
            ]
        )
        ds.search("q")
        self.assertLessEqual(self.sleep_mock.call_args_list[0].args[0], ds.MAX_RETRY_AFTER)

    def test_retryable_status_exhausts_to_retryable_error(self):
        request = self.call(
            [FakeResponse(503, json_data=api_error_body("down"))] * (ds.MAX_RETRIES + 1)
        )
        with self.assertRaises(ds.DeepSeekRetryableError):
            ds.search("q")
        self.assertEqual(request.call_count, ds.MAX_RETRIES + 1)

    def test_timeout_is_retried_then_retryable_error(self):
        request = self.call(
            [], side_effect=ds.requests.exceptions.Timeout("timed out")
        )
        with self.assertRaises(ds.DeepSeekRetryableError):
            ds.search("q")
        self.assertEqual(request.call_count, ds.MAX_RETRIES + 1)

    def test_ssl_error_is_not_retried(self):
        request = self.call([], side_effect=ds.requests.exceptions.SSLError("bad cert"))
        with self.assertRaises(ds.DeepSeekAPIError):
            ds.search("q")
        self.assertEqual(request.call_count, 1)

    def test_proxy_error_is_not_retried(self):
        request = self.call([], side_effect=ds.requests.exceptions.ProxyError("proxy"))
        with self.assertRaises(ds.DeepSeekAPIError):
            ds.search("q")
        self.assertEqual(request.call_count, 1)

    # --- content cap -------------------------------------------------------

    def test_max_content_chars_truncates_results(self):
        body = {"results": [{"title": "t", "content": "y" * 5000}]}
        self.call([FakeResponse(200, json_data=body)])
        data = ds.search("q", need_content=True, count=1, max_content_chars=100)
        self.assertTrue(data["results"][0]["content"].startswith("y" * 100))
        self.assertIn("truncated", data["results"][0]["content"])
        self.assertLess(len(data["results"][0]["content"]), 200)

    def test_max_content_chars_truncates_fetch(self):
        self.call([FakeResponse(200, json_data={"title": "t", "content": "z" * 5000})])
        data = ds.fetch("https://example.com", max_content_chars=50)
        self.assertTrue(data["content"].startswith("z" * 50))

    def test_content_untouched_without_cap(self):
        body = {"results": [{"content": "y" * 5000}]}
        self.call([FakeResponse(200, json_data=body)])
        data = ds.search("q", count=1)
        self.assertEqual(len(data["results"][0]["content"]), 5000)

    def test_need_content_with_high_count_warns(self):
        self.call([FakeResponse(200, json_data={"results": []})])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ds.search("q", need_content=True, count=50)
        self.assertTrue(any("full page bodies" in str(w.message) for w in caught))

    def test_need_content_with_low_count_does_not_warn(self):
        self.call([FakeResponse(200, json_data={"results": []})])
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
