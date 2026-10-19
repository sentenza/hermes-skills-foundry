#!/usr/bin/env python3
"""
DeepSeek Search & Fetch API helper.

Usage (CLI):
    python deepseek_search.py search "query" [--count N] [--need-content] [--ori-question STR] [--localization IP] [--json]
    python deepseek_search.py fetch "url" [--json]

Usage (library):
    from deepseek_search import search, fetch
    results = search("DeepSeek V4", count=5, need_content=True)
    page = fetch("https://example.com")

Environment:
    DEEPSEEK_API_KEY (required) — DeepSeek platform API key, not OpenRouter
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests

__all__ = ["search", "fetch", "DeepSeekAPIError", "DeepSeekRetryableError"]

BASE_URL = "https://api.deepseek.com"
SEARCH_ENDPOINT = "/v1/tools/search"
FETCH_ENDPOINT = "/v1/tools/fetch"

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds


class DeepSeekAPIError(Exception):
    """Raised for non-retryable API errors (4xx except 408/429)."""

    def __init__(self, status: int, message: str, code: Optional[str] = None):
        self.status = status
        self.message = message
        self.code = code
        super().__init__(f"HTTP {status}: {message}")


class DeepSeekRetryableError(Exception):
    """Raised for retryable errors (408, 429, 5xx)."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"HTTP {status} (retryable): {message}")


def _get_headers() -> Dict[str, str]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY environment variable not set")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _is_retryable_exception(e: Exception) -> bool:
    """Check if a requests exception is retryable (transient network issue)."""
    return isinstance(e, (requests.ConnectionError, requests.Timeout))


def _request_with_retry(
    method: str,
    endpoint: str,
    payload: Dict[str, Any],
    retryable_statuses: tuple = (408, 429, 500, 502, 503, 504),
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
            if _is_retryable_exception(e) and attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
                continue
            raise DeepSeekAPIError(0, f"Network error: {e}")

        if resp.status_code == 200:
            return resp.json()

        # Parse error response
        try:
            err_data = resp.json()
            err_msg = err_data.get("error", {}).get("message", resp.text)
            err_code = err_data.get("error", {}).get("code")
        except json.JSONDecodeError:
            err_msg = resp.text
            err_code = None

        if resp.status_code in retryable_statuses:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
                continue
            raise DeepSeekRetryableError(resp.status_code, err_msg)

        raise DeepSeekAPIError(resp.status_code, err_msg, err_code)

    # Should not reach here
    raise DeepSeekRetryableError(0, "Max retries exceeded")


def search(
    query: str,
    count: int = 10,
    need_content: bool = False,
    ori_question: Optional[str] = None,
    localization: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search the web via DeepSeek Search API.

    Args:
        query: Search query (1-128 chars, supports operators).
        count: Number of results (1-50). Default 10.
        need_content: Include full page Markdown in results. Default False.
        ori_question: Original user question for better understanding (1-128 chars, non-empty).
        localization: IP address for localized results (IPv4 or IPv6).

    Returns:
        Parsed JSON response with 'results' list.

    Raises:
        DeepSeekAPIError: On non-retryable HTTP error.
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

    payload: Dict[str, Any] = {"query": query, "count": count, "need_content": need_content}
    if ori_question:
        payload["ori_question"] = ori_question
    if localization:
        payload["localization"] = localization

    return _request_with_retry("POST", SEARCH_ENDPOINT, payload)


def fetch(url: str) -> Dict[str, Any]:
    """
    Fetch a single page as Markdown via DeepSeek Fetch API.

    Args:
        url: Page URL (HTTPS, max 8192 chars, no auth in URL).

    Returns:
        Parsed JSON with 'title' and 'content' (Markdown).

    Raises:
        DeepSeekAPIError: On non-retryable HTTP error (403, 404, etc.).
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
    return _request_with_retry("POST", FETCH_ENDPOINT, payload)
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
    search_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # fetch subcommand
    fetch_p = subparsers.add_parser("fetch", help="Fetch a single page as Markdown")
    fetch_p.add_argument("url", help="Page URL to fetch")
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
            )
            _print_search_results(data, args.json)
        elif args.command == "fetch":
            data = fetch(args.url)
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