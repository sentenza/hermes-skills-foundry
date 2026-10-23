---
name: openrouter-usage
description: Use when checking OpenRouter spend, credits, token consumption or per-model activity. Queries the management-key Activity and Credits APIs over completed UTC days and reports cost, token and request totals per model and per day.
tags:
  - openrouter
  - api
  - monitoring
  - cost
  - tokens
hermes_requires: ">=0.21"
---

# OpenRouter Usage & Activity Tracker

Query OpenRouter for token consumption, credit balance and cost breakdowns, per model and per UTC day.

## Prerequisites

- A **management API key** — the `/activity` and `/credits` endpoints reject regular keys with
  `403 Only management keys can fetch activity for an account`. Create one at
  <https://openrouter.ai/settings/keys> ("Create Management Key").
- Export it as `OPENROUTER_MANAGEMENT_KEY`, or pass `--management-key`.
- `pip install requests`.

Preflight before the first query — report the missing key plainly instead of guessing a spend:

```bash
[ -n "$OPENROUTER_MANAGEMENT_KEY" ] || echo "OPENROUTER_MANAGEMENT_KEY not set — cannot query OpenRouter"
```

## Usage

The tracker is `scripts/openrouter_usage.py`; run it from the skill root.

```bash
python scripts/openrouter_usage.py --days 7              # last 7 completed UTC days
python scripts/openrouter_usage.py --days 30             # full API window
python scripts/openrouter_usage.py --date 2026-10-22     # one completed UTC day
python scripts/openrouter_usage.py --start 2026-10-01 --end 2026-10-22
python scripts/openrouter_usage.py --credits             # purchased / consumed totals
python scripts/openrouter_usage.py --days 14 --json --output report.json
```

Filters: `--api-key-hash <sha256>`, `--user-id <org-member-id>`.

## Reporting rules

- **Only completed UTC days exist.** Asking for today returns
  `400 Date must be within the last 30 (completed) UTC days`; the script refuses early with
  exit code 2 and names the latest available day. When the user asks for "today", say the data
  is not published yet and report the latest completed day instead — never present yesterday's
  number as today's.
- **Always name the period and the UTC basis** in the answer, plus the credit balance when the
  question is about spend.
- Activity data lags roughly 30 minutes after the UTC day boundary; a fresh day can come back
  empty rather than missing.
- `usage` is cost in USD charged as OpenRouter credits; `byok_usage_inference` is spend on
  bring-your-own-key inference and is reported separately.

## Reference

`references/openrouter-activity-api.md` — endpoints, auth, query parameters, full response
schema and field meanings.
