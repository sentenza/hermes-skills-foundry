---
name: deepseek-search
description: "Use when you need to search the live web with DeepSeek's native search engine — 'search for X', 'find recent info about Y', 'look up Z on the web'. Triggers on: search, find, look up, query, research, latest, recent, current. Uses DeepSeek's in-house search API directly (not OpenRouter) for query operators (site:, lang:, after:/before:, exact phrases), relevance scoring (rerank_score), authority tiers, and optional full-page Markdown fetch. Requires DEEPSEEK_API_KEY env var."
tags:
  - search
  - web
  - deepseek
  - research
  - live-data
hermes_requires: ">=0.21"
---
<!-- adapted from DeepSeek API docs (DeepSeek-proprietary) -->

# DeepSeek Search

This skill gives Hermes direct access to **DeepSeek's native Search and Fetch APIs** — not a proxy, not OpenRouter's Exa fallback. You get:

## Prerequisites

- `DEEPSEEK_API_KEY` environment variable set (DeepSeek platform API key, **not** OpenRouter)
- Python 3.10+ with `requests` (`pip install requests`)

The skill bundles a helper script at `scripts/deepseek_search.py` — call it from the shell or import its functions. No external tool binary required.

## When to use this skill

| User says… | You do… |
|------------|---------|
| "search for…" / "find…" / "look up…" | Call `scripts/deepseek_search.py search …` |
| "fetch this URL" / "get the content of…" | Call `scripts/deepseek_search.py fetch …` |
| "recent news about…" / "latest on…" | Use `after:` operator in query |
| "only from GitHub" / "exclude Reddit" | Use `site:` / `-site:` operators |

## Quick reference

```bash
# Search (JSON output)
python scripts/deepseek_search.py search "DeepSeek V4 release" --count 5 --need-content

# Search with operators
python scripts/deepseek_search.py search "DeepSeek site:github.com OR site:huggingface.co lang:en after:2025" --count 10

# Fetch single page as Markdown
python scripts/deepseek_search.py fetch "https://example.com/article"
```

### Search arguments

| Flag | Description | Default |
|------|-------------|---------|
| `query` (positional) | Search query, 1–128 chars, supports operators | — |
| `--count` | Results to return (1–50) | `10` |
| `--need-content` | Include full page Markdown in `content` field | `false` |
| `--ori-question` | Original user question for better query understanding | — |
| `--localization` | IP address for localized results | — |
| `--json` | Output raw JSON (default: pretty table) | `false` |

### Fetch arguments

| Flag | Description |
|------|-------------|
| `url` (positional) | Page URL to fetch (HTTP/HTTPS, ≤8192 chars) |
| `--json` | Output raw JSON (default: prints title + Markdown) |

## Search query operators

Combine freely in one query string:

| Operator | Example | Effect |
|----------|---------|--------|
| `site:` | `site:github.com` | Restrict to domain (multi: `site:a.com OR site:b.com`) |
| `-site:` | `-site:example.com` | Exclude domain |
| `-` | `-advertisement` | Exclude term |
| `-"..."` | `-"release notes"` | Exclude exact phrase |
| `"..."` | `"exact phrase"` | Match exact phrase |
| `lang:` | `lang:zh,en` | Restrict languages (comma-separated) |
| `after:` | `after:2025-01-01` | Published after date (year or full date) |
| `before:` | `before:2026-06-01` | Published before date |

## Response structure (Search)

```json
{
  "results": [
    {
      "rerank_score": 2.4,
      "title": "DeepSeek V4 released",
      "url": "https://example.com/deepseek-v4",
      "snippet": "Short summary ~100–200 chars",
      "summary": "Long summary ~600–800 chars for model consumption",
      "content": "Full page Markdown (when need_content=true)",
      "site_name": "Example News",
      "site_icon": "https://example.com/favicon.ico",
      "date": "2026-06-01T00:00:00+00:00",
      "authority": 3
    }
  ]
}
```

**Key fields for decision-making:**
- `rerank_score ≥ 1.5` → high-quality result
- `authority ≥ 3` → highly authoritative source
- `content` → only populated when `need_content=true` and content available

## Response structure (Fetch)

```json
{
  "title": "Example article",
  "content": "# Example article\n\nArticle content as Markdown."
}
```

## Error handling

| HTTP | Meaning | Action |
|------|---------|--------|
| 400 | Invalid request (bad JSON, field out of range) | Fix request, don't retry blindly |
| 401 | Missing/invalid API key | Check `DEEPSEEK_API_KEY` |
| 402 | Insufficient balance | Top up DeepSeek account |
| 403 | Fetch rejected by security policy | Try different URL |
| 404 | Fetch: no extractable content | URL unavailable/blocked |
| 429 | QPS limit exceeded | Wait, retry with backoff |
| 5xx / 504 | Server / downstream timeout | Wait, retry |

**Retry policy:** Only retry 408, 429, 5xx. Do NOT retry other 4xx without changing the request.

## Billing

- Search: $0.75 per 1,000 successful requests (non-empty `results`)
- Fetch: $0.75 per 1,000 successful requests (returns content)
- Failed requests, empty results, timeouts = **not billed**
- `count` does not affect price

## Rate limits

Independent quotas for Search and Fetch. Check `X-RateLimit-*` headers on responses.

## Usage from Hermes

1. User asks a question requiring live data
2. You construct the query (apply operators if user implies filters)
3. Run `python scripts/deepseek_search.py search "query" [flags]`
4. Parse results — cite sources with `[site_name](url)` format
5. If user needs full page, run `fetch` on the URL

**Example flow:**

```
User: "What's the latest on DeepSeek V4, only from GitHub or HuggingFace, English, after 2025?"
You: python scripts/deepseek_search.py search "DeepSeek V4 site:github.com OR site:huggingface.co lang:en after:2025" --count 10
→ Parse results, pick top by rerank_score/authority
→ If user wants full text: python scripts/deepseek_search.py fetch "https://..."
```

## Implementation notes

- The helper script handles auth headers, error parsing, retries (408/429/5xx with exponential backoff, max 3)
- Set `DEEPSEEK_API_KEY` in your shell or `.env` — the script reads `os.environ["DEEPSEEK_API_KEY"]`
- For programmatic use, import `search()` / `fetch()` from the script instead of shelling out
- All network calls have a 30s timeout

## References

- `references/api.md` — full request/response schemas, error codes, rate limits
- DeepSeek API docs: https://api-docs.deepseek.com/guides/search