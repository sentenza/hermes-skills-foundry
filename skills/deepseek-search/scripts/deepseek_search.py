#!/usr/bin/env python3
"""
DeepSeek Search & Fetch API helper.

Usage (CLI):
    python deepseek_search.py search "query" [--count N] [--need-content] [--ori-question STR]
                                   [--localization IP] [--max-content-chars N] [--json]
    python deepseek_search.py fetch "url" [--max-content-chars N] [--json]

Usage (library):
    from deepseek_search import search, fetch
    results = search("DeepSeek V4", count=5, need_content=True)
    page = fetch("https://example.com")

Environment:
    DEEPSEEK_API_KEY (required) — DeepSeek platform API key, not OpenRouter.
    The value is read from the environment only. It is never logged, printed,
    written to disk, or included in an error message.

Exit codes (CLI):
    0 ok · 1 API error · 2 transient error (retryable) · 3 invalid input
"""

import argparse
import json
import os
import sys
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import requests

__all__ = ["search", "fetch", "DeepSeekAPIError", "DeepSeekRetryableError"]

BASE_URL = "https://api.deepseek.com"
SEARCH_ENDPOINT = "/v1/tools/search"
FETCH_ENDPOINT = "/v1/tools/fetch"

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds
RETRYABLE_STATUSES = (408, 429, 500, 502, 503, 504)
MAX_RETRY_AFTER = 30.0  # seconds; cap on a server-suggested wait
MAX_ERROR_TEXT = 500  # chars of raw response body echoed back in an error
NEED_CONTENT_COUNT_WARN = 20  # above this, need_content returns whole page bodies
TRUNCATION_MARKER = "... [truncated]"

# Transport failures worth retrying. SSLError and ProxyError subclass
# ConnectionError but are permanent, so they are excluded explicitly.
_RETRYABLE_EXCEPTIONS = (
    requests.Timeout,
    requests.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.ContentDecodingError,
)
_PERMANENT_EXCEPTIONS = (
    requests.exceptions.SSLError,
    requests.exceptions.ProxyError,
    requests.exceptions.InvalidURL,
    requests.exceptions.MissingSchema,
    requests.exceptions.InvalidSchema,
)


class DeepSeekAPIError(Exception):
    """Raised for non-retryable API errors (4xx except 408/429, malformed responses)."""

    def __init__(
        self,
        status: int,
        message: str,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.status = status
        self.message = message
        self.code = code
        self.request_id = request_id
        detail = f"HTTP {status}: {message}"
        if request_id:
            detail += f" (request_id={request_id})"
        super().__init__(detail)


class DeepSeekRetryableError(Exception):
    """Raised for retryable errors (408, 429, 5xx) and exhausted transport retries."""

    def __init__(self, status: int, message: str, request_id: Optional[str] = None):
        self.status = status
        self.message = message
        self.request_id = request_id
        detail = f"HTTP {status} (retryable): {message}"
        if request_id:
            detail += f" (request_id={request_id})"
        super().__init__(detail)


def _get_headers() -> Dict[str, str]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY environment variable not set")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _truncate(text: Any, limit: int = MAX_ERROR_TEXT) -> str:
    """Shorten a value for inclusion in an error message."""
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = text.strip()
    if not text:
        return "unknown error"
    return text if len(text) <= limit else text[:limit] + "..."


def _as_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _header_request_id(resp: Any) -> Optional[str]:
    headers = getattr(resp, "headers", None) or {}
    try:
        return headers.get("x-request-id") or headers.get("request-id")
    except AttributeError:
        return None


def _extract_error(resp: Any) -> Tuple[str, Optional[str], Optional[str]]:
    """Return (message, code, request_id) from an error response. Never raises."""
    request_id = _header_request_id(resp)
    text = _truncate(getattr(resp, "text", "") or "")
    try:
        data = resp.json()
    except ValueError:
        return text, None, request_id

    if isinstance(data, dict):
        request_id = request_id or _as_str(data.get("request_id"))
        err = data.get("error")
        if isinstance(err, dict):
            message = err.get("message") or err.get("detail") or text
            return _truncate(message), _as_str(err.get("code")), request_id
        if isinstance(err, str):
            return _truncate(err), None, request_id
        message = data.get("message") or data.get("detail") or text
        return _truncate(message), None, request_id
    if isinstance(data, str):
        return _truncate(data), None, request_id
    return text, None, request_id


def _classify_exception(e: Exception) -> str:
    """Classify a transport exception as 'retryable' or 'permanent'."""
    if isinstance(e, _PERMANENT_EXCEPTIONS):
        return "permanent"
    if isinstance(e, _RETRYABLE_EXCEPTIONS):
        return "retryable"
    return "permanent"


def _retry_after_seconds(resp: Any) -> Optional[float]:
    """Server-suggested wait from the Retry-After header (delta-seconds form only)."""
    headers = getattr(resp, "headers", None) or {}
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def _sleep_before_retry(attempt: int, resp: Any = None) -> None:
    """Back off exponentially, honoring Retry-After when the server sets it."""
    delay = RETRY_BACKOFF_BASE**attempt
    if resp is not None:
        retry_after = _retry_after_seconds(resp)
        if retry_after is not None:
            delay = max(delay, min(retry_after, MAX_RETRY_AFTER))
    time.sleep(delay)


def _parse_success(resp: Any) -> Dict[str, Any]:
    """Parse a 200 response into a dict, or raise a clean error."""
    request_id = _header_request_id(resp)
    try:
        data = resp.json()
    except ValueError:
        raise DeepSeekAPIError(
            200, f"Invalid JSON in response: {_truncate(getattr(resp, 'text', ''))}", request_id=request_id
        )
    if not isinstance(data, dict):
        raise DeepSeekAPIError(
            200,
            f"Unexpected response shape: {type(data).__name__} (expected object)",
            request_id=request_id,
        )
    return data


def _cap_content(data: Dict[str, Any], max_content_chars: Optional[int]) -> Dict[str, Any]:
    """Truncate page bodies in place when a cap is requested."""
    if not max_content_chars or max_content_chars <= 0:
        return data
    results = data.get("results")
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                content = item.get("content")
                if isinstance(content, str) and len(content) > max_content_chars:
                    item["content"] = content[:max_content_chars] + TRUNCATION_MARKER
    content = data.get("content")
    if isinstance(content, str) and len(content) > max_content_chars:
        data["content"] = content[:max_content_chars] + TRUNCATION_MARKER
    return data


def _request_with_retry(
    method: str,
    endpoint: str,
    payload: Dict[str, Any],
    retryable_statuses: tuple = RETRYABLE_STATUSES,
) -> Dict[str, Any]:
    """Execute request with exponential backoff on retryable statuses."""
    url = BASE_URL + endpoint
    headers = _get_headers()

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.request(
                method, url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT
            )
        except requests.RequestException as e:
            kind = _classify_exception(e)
            if kind == "retryable":
                if attempt < MAX_RETRIES:
                    _sleep_before_retry(attempt)
                    continue
                raise DeepSeekRetryableError(
                    0, f"Network error after {MAX_RETRIES} retries: {_truncate(str(e))}"
                )
            raise DeepSeekAPIError(0, f"Network error (permanent): {_truncate(str(e))}")

        if resp.status_code == 200:
            return _parse_success(resp)

        err_msg, err_code, request_id = _extract_error(resp)

        if resp.status_code in retryable_statuses:
            if attempt < MAX_RETRIES:
                _sleep_before_retry(attempt, resp)
                continue
            raise DeepSeekRetryableError(resp.status_code, err_msg, request_id)

        raise DeepSeekAPIError(resp.status_code, err_msg, err_code, request_id)

    # Should not reach here
    raise DeepSeekRetryableError(0, "Max retries exceeded")


def search(
    query: str,
    count: int = 10,
    need_content: bool = False,
    ori_question: Optional[str] = None,
    localization: Optional[str] = None,
    max_content_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Search the web via DeepSeek Search API.

    Args:
        query: Search query (1-128 chars, supports operators).
        count: Number of results (1-50). Default 10.
        need_content: Include full page Markdown in results. Default False.
        ori_question: Original user question for better understanding (1-128 chars, non-empty).
        localization: IP address for localized results (IPv4 or IPv6).
        max_content_chars: Truncate each result's page body to this many characters.
            None (default) leaves bodies untouched.

    Returns:
        Parsed JSON response with 'results' list.

    Raises:
        DeepSeekAPIError: On non-retryable HTTP error or malformed response.
        DeepSeekRetryableError: On retryable error after max retries.
        ValueError: On invalid arguments.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > 128:
        raise ValueError("query must be 1-128 characters")
    if not 1 <= count <= 50:
        raise ValueError("count must be between 1 and 50")
    if ori_question is not None:
        if not ori_question.strip():
            raise ValueError("ori_question must not be empty if provided")
        if len(ori_question) > 128:
            raise ValueError("ori_question must be 1-128 characters")
    if localization is not None:
        if not localization.strip():
            raise ValueError("localization must not be empty if provided")
        # Basic IP validation (IPv4 or IPv6)
        import ipaddress
        try:
            ipaddress.ip_address(localization)
        except ValueError:
            raise ValueError("localization must be a valid IP address")
    if need_content and count > NEED_CONTENT_COUNT_WARN:
        warnings.warn(
            f"need_content=True with count={count} returns {count} full page bodies. "
            "Cap the size with max_content_chars, or use fetch() on selected URLs.",
            UserWarning,
            stacklevel=2,
        )

    payload: Dict[str, Any] = {"query": query, "count": count, "need_content": need_content}
    if ori_question:
        payload["ori_question"] = ori_question
    if localization:
        payload["localization"] = localization

    data = _request_with_retry("POST", SEARCH_ENDPOINT, payload)
    return _cap_content(data, max_content_chars)


def fetch(url: str, max_content_chars: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch a single page as Markdown via DeepSeek Fetch API.

    Args:
        url: Page URL (HTTPS, max 8192 chars, no auth in URL).
        max_content_chars: Truncate the page body to this many characters.
            None (default) leaves the body untouched.

    Returns:
        Parsed JSON with 'title' and 'content' (Markdown).

    Raises:
        DeepSeekAPIError: On non-retryable HTTP error (403, 404, etc.) or malformed response.
        DeepSeekRetryableError: On retryable error after max retries.
        ValueError: On invalid URL.
    """
    if not url or not url.strip():
        raise ValueError("url must not be empty")
    if len(url) > 8192:
        raise ValueError("url must be at most 8192 characters")
    if not url.startswith("https://"):
        raise ValueError("url must be HTTPS")

    payload = {"url": url}
    data = _request_with_retry("POST", FETCH_ENDPOINT, payload)
    return _cap_content(data, max_content_chars)


# --- CLI ---


def _print_search_results(data: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    results = data.get("results", [])
    if not results:
        print("No results.")
        return

    for i, r in enumerate(results, 1):
        score = r.get("rerank_score", 0)
        auth = r.get("authority", -1)
        title = r.get("title", "(no title)")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        site = r.get("site_name") or "unknown"
        date = r.get("date") or "unknown date"

        print(f"\n[{i}] {title}")
        print(f"    URL: {url}")
        print(f"    Source: {site} | Date: {date} | Score: {score} | Authority: {auth}")
        print(f"    {snippet}")

        summary = r.get("summary")
        if summary:
            print(f"    Summary: {summary[:200]}{'...' if len(summary) > 200 else ''}")

        content = r.get("content")
        if content:
            preview = content[:300].replace("\n", " ")
            print(f"    Content preview: {preview}...")


def _print_fetch_result(data: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    title = data.get("title", "(no title)")
    content = data.get("content", "")
    print(f"# {title}\n")
    print(content)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DeepSeek Search & Fetch API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deepseek_search.py search "DeepSeek V4 release" --count 5 --need-content
  python deepseek_search.py search "DeepSeek site:github.com OR site:huggingface.co lang:en after:2025" --count 10
  python deepseek_search.py fetch "https://example.com/article"
  python deepseek_search.py search "query" --count 50 --need-content --max-content-chars 2000
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search subcommand
    search_p = subparsers.add_parser("search", help="Search the web")
    search_p.add_argument("query", help="Search query (supports operators)")
    search_p.add_argument("--count", type=int, default=10, help="Number of results (1-50)")
    search_p.add_argument("--need-content", action="store_true", help="Include full page Markdown")
    search_p.add_argument("--ori-question", help="Original user question")
    search_p.add_argument("--localization", help="IP address for localized results")
    search_p.add_argument(
        "--max-content-chars",
        type=int,
        default=None,
        help="Truncate each page body to N characters (default: no cap)",
    )
    search_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # fetch subcommand
    fetch_p = subparsers.add_parser("fetch", help="Fetch a single page as Markdown")
    fetch_p.add_argument("url", help="Page URL to fetch")
    fetch_p.add_argument(
        "--max-content-chars",
        type=int,
        default=None,
        help="Truncate the page body to N characters (default: no cap)",
    )
    fetch_p.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    try:
        if args.command == "search":
            data = search(
                query=args.query,
                count=args.count,
                need_content=args.need_content,
                ori_question=args.ori_question,
                localization=args.localization,
                max_content_chars=args.max_content_chars,
            )
            _print_search_results(data, args.json)
        elif args.command == "fetch":
            data = fetch(args.url, max_content_chars=args.max_content_chars)
            _print_fetch_result(data, args.json)
        else:
            parser.error(f"Unknown command: {args.command}")
        return 0
    except DeepSeekAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except DeepSeekRetryableError as e:
        print(f"Error (retryable, max retries exceeded): {e}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
