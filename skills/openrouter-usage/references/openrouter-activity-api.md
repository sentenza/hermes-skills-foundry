# OpenRouter Activity API — Reference

Source: `GET /api/v1/activity` (from official OpenAPI spec, retrieved 2026-05-25)

## Endpoint

```
GET https://openrouter.ai/api/v1/activity
```

## Authentication

**Management API key** required in `Authorization: Bearer <key>` header.
Regular keys return 403. Create a management key at:
https://openrouter.ai/settings/keys → "Create Management Key"

## Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | string | No | Filter by single UTC date, YYYY-MM-DD, within last 30 days |
| `api_key_hash` | string | No | Filter by SHA-256 hex of API key (as returned by keys API) |
| `user_id` | string | No | Filter by org member user ID (organization accounts only) |

If no `date` is specified, returns data for all last 30 completed UTC days.

## Response Schema

```json
{
  "data": [
    {
      "byok_usage_inference": 0.0,
      "completion_tokens": 6789,
      "date": "2026-05-24",
      "endpoint_id": "abc123",
      "model": "openai/gpt-4.1",
      "model_permaslug": "openai/gpt-4.1-2025-04-14",
      "prompt_tokens": 12345,
      "provider_name": "OpenAI",
      "reasoning_tokens": 0,
      "requests": 42,
      "usage": 0.0523
    }
  ]
}
```

## Full OpenAPI Schema Fragment

```yaml
ActivityItem:
  type: object
  required:
    - byok_usage_inference
    - completion_tokens
    - date
    - endpoint_id
    - model
    - model_permaslug
    - prompt_tokens
    - provider_name
    - reasoning_tokens
    - requests
    - usage

ActivityResponse:
  type: object
  required:
    - data
```

## Other Relevant Endpoints

### Credits
```
GET /api/v1/credits
```
Returns `{ "data": { "total_credits": ..., "used_credits": ... } }`. Management key required.

### Single Generation
```
GET /api/v1/generation?id=<generation_id>
```
Returns token counts and cost for a single API call. Regular key works. The `id` comes from the `id` field in any chat completion response.

## Rate Limits & Behavior

- Data covers **last 30 completed UTC days only**
- Events aggregated by request start time
- Recommended: wait ~30 min after UTC day boundary before querying previous day
- Pagination not documented — likely returns all data in one response when no date filter
