# DeepSeek Search & Fetch API Reference

Source: https://api-docs.deepseek.com/guides/search

---

## Base URL

```
https://api.deepseek.com
```

---

## Authentication

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <DEEPSEEK_API_KEY>` |
| `Content-Type` | `application/json` |

---

## Search API

### Endpoint

```
POST /v1/tools/search
```

### Request

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | — | 1–128 Unicode chars, not all whitespace |
| `count` | integer | No | `10` | 1–50 |
| `ori_question` | string | No | — | 1–128 chars, `null` = not provided |
| `localization` | string | No | `""` | IP address for geo-localization |
| `need_content` | boolean | No | `false` | Include full page Markdown |

Unknown fields are ignored.

### Query Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `site:` | `site:github.com` | Restrict to domain; multi: `site:a.com OR site:b.com` |
| `-site:` | `-site:example.com` | Exclude domain; multi with spaces |
| `-` | `-advertisement` | Exclude term; multi with spaces |
| `-"..."` | `-"release notes"` | Exclude exact phrase; multi with spaces |
| `"..."` | `"exact phrase"` | Match exact phrase; multi with spaces |
| `lang:` | `lang:zh,en` | Restrict languages; comma-separated codes |
| `after:` | `after:2025` or `after:2025-01-01` | Published after date (year or RFC3339 date) |
| `before:` | `before:2026` or `before:2026-06-01` | Published before date |

### Response (HTTP 200)

```json
{
  "results": [
    {
      "rerank_score": 2.4,
      "title": "string",
      "url": "string",
      "snippet": "string",
      "summary": "string",
      "content": "string",
      "site_name": "string|null",
      "site_icon": "string|null",
      "date": "string|null",
      "authority": -1
    }
  ]
}
```

#### Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `rerank_score` | number | Relevance 0–3; ≥1.5 = high quality |
| `title` | string | Result title |
| `url` | string | Result URL |
| `snippet` | string | Short summary ~100–200 chars (UI display) |
| `summary` | string | Long summary ~600–800 chars (model consumption) |
| `content` | string | Full page Markdown; empty if `need_content=false` or unavailable |
| `site_name` | string\|null | Site name or null |
| `site_icon` | string\|null | Favicon URL or null |
| `date` | string\|null | Publication time UTC RFC3339 or null |
| `authority` | integer | Authority tier 0–4; -1 = unknown; ≥3 = highly authoritative |

Empty `results` array = no matches (not an error).

---

## Fetch API

### Endpoint

```
POST /v1/tools/fetch
```

### Request

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `url` | string | Yes | ≤8192 chars, HTTP/HTTPS, host required, no user:pass |

### Response (HTTP 200)

```json
{
  "title": "string",
  "content": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title; empty if unavailable |
| `content` | string | Page content as Markdown |

Fetching subject to target site availability/policies.

---

## Error Format

All errors follow OpenAI-compatible format:

```json
{
  "error": {
    "message": "string",
    "type": "string",
    "param": null,
    "code": "string"
  }
}
```

### HTTP Status Codes

| Status | Description | Retry? |
|--------|-------------|--------|
| 400 | Invalid headers/body (malformed JSON, bad field value) | No |
| 401 | Missing/invalid API key | No |
| 402 | Insufficient balance | No (top up first) |
| 403 | Fetch rejected by security policy | No |
| 404 | Fetch: no extractable content (blocked, error, unsupported type, no Markdown) | No |
| 408 | Request body read timeout | **Yes** |
| 413 | Request body too large | No |
| 429 | QPS limit exceeded | **Yes** |
| 500 | Internal server error | **Yes** |
| 504 | Downstream timeout | **Yes** |

**Retry policy:** Only retry 408, 429, 5xx. Do not retry other 4xx without changing request.

### Request ID

Error responses carry `x-request-id` (some responses also include a `request_id` field in the body). The helper surfaces it in every raised error as `request_id=…` — quote it in support requests, it is how a call is traced.

### Helper error taxonomy

| Class | Raised for | CLI exit |
|-------|-----------|----------|
| `DeepSeekAPIError` | 4xx other than 408/429, permanent transport errors (SSL, proxy, invalid URL), malformed or non-object 200 responses | 1 |
| `DeepSeekRetryableError` | 408/429/5xx after 3 retries, and transport timeouts or connection errors after 3 retries | 2 |
| `ValueError` / `RuntimeError` | Invalid arguments, `DEEPSEEK_API_KEY` not set | 3 |

Transient transport failures (timeout, connection reset, truncated chunk) are retried; permanent ones (certificate, proxy, malformed URL) are not. A `Retry-After` header on 429/503 is honored, capped at 30 s.

Error bodies are parsed defensively: `error` may be an object, a string, or absent, and the body may not be JSON at all. Raw body text is truncated to 500 characters in the error message.

---

## Billing

| API | Unit | Price |
|-----|------|-------|
| Search | Per 1,000 successful requests | $0.75 |
| Fetch | Per 1,000 successful requests | $0.75 |

- Billable only on HTTP 200 + result produced
- Search: non-empty `results` array
- Fetch: returns page content
- Failed requests, empty results, timeouts = **not billed**
- `count` does not affect price
- Price is per request, not per byte — a large response costs tokens and context, not more money
- A request that succeeded server-side but whose response was lost is billed again, which is why the retry loop belongs to the helper and not to the caller

> Free when used via DeepSeek Harness, Claude Code, or Codex until 2026-11-01 00:00 Beijing time.

---

## Response Size

`need_content=true` returns the full page Markdown for **every** result, so `count=50` with `need_content` returns 50 full pages. The API does not cap this.

| Control | Effect |
|---------|--------|
| `count` (1–50, default 10) | Number of results returned |
| `need_content` (default false) | Adds full page bodies to each result |
| `max_content_chars` (helper-side, optional) | Truncates each page body to N characters with a `... [truncated]` marker |

The helper warns when `need_content` is combined with `count > 20`. The cap is applied client-side after the response arrives — it does not reduce what the API transfers.

---

## Rate Limits

- Search and Fetch have independent quotas
- Traffic to one does not consume the other's quota
- Check `X-RateLimit-*` response headers

---

## Example Requests

### Search with operators

```bash
curl https://api.deepseek.com/v1/tools/search \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DeepSeek site:github.com OR site:huggingface.co lang:en after:2025",
    "count": 10,
    "need_content": true
  }'
```

### Fetch single page

```bash
curl https://api.deepseek.com/v1/tools/fetch \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api-docs.deepseek.com/quick_start/pricing"}'
```

---

## Python Example

Standard library only:

```python
import json
import os
import urllib.request

HEADERS = {
    "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
    "Content-Type": "application/json",
}


def post(path, payload):
    request = urllib.request.Request(
        f"https://api.deepseek.com{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


results = post("/v1/tools/search", {"query": "DeepSeek V4", "count": 5, "need_content": True})
page = post("/v1/tools/fetch", {"url": results["results"][0]["url"]})
print(page["content"])
```

---

## Notes for Skill Implementation

- The helper script `scripts/deepseek_search.py` wraps these endpoints using only the Python standard library (`urllib`) — no third-party dependency
- Implements retry with exponential backoff (base 1.5s, max 3 retries) for 408/429/5xx, honoring `Retry-After` (capped at 30s)
- Retries only transient transport failures; certificate, proxy and malformed-URL failures fail immediately
- Follows redirects, but strips the `Authorization` header when the redirect target is a different host — the credential is never forwarded off-host
- Validates input constraints before sending
- Returns structured errors distinguishing retryable vs non-retryable, each carrying the API `request_id`
- `max_content_chars` caps page bodies client-side; without it the response is passed through unchanged
- Requires `DEEPSEEK_API_KEY` env var (DeepSeek platform, not OpenRouter); the value is never logged, printed, or written to disk