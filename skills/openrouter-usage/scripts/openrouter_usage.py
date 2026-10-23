#!/usr/bin/env python3
"""
OpenRouter Activity & Usage Tracker

Recupera dati di consumo token e costi da OpenRouter API
per intervalli temporali prefissati.

Endpoints usati:
  - GET /api/v1/activity     → activity per model/endpoint (ultimi 30 giorni, management key)
  - GET /api/v1/credits      → crediti totali (management key)
  - GET /api/v1/generation   → stats per singola generation (regular key)

Uso:
  export OPENROUTER_MANAGEMENT_KEY="sk-or-v1-..."
  python openrouter_usage.py --days 7
  python openrouter_usage.py --start 2026-05-01 --end 2026-05-25
  python openrouter_usage.py --credits
  python openrouter_usage.py --summary --days 30
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("❌ Richiesto: pip install requests", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://openrouter.ai/api/v1"


# ──────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────

def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def get_activity(
    management_key: str,
    date_filter: Optional[str] = None,
    api_key_hash: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    GET /api/v1/activity
    Returns daily user activity grouped by model/endpoint for the last 30 UTC days.

    Query params (all optional):
      date         – single UTC date YYYY-MM-DD
      api_key_hash – SHA-256 hex of API key
      user_id      – org member user ID
    """
    params: dict[str, str] = {}
    if date_filter:
        params["date"] = date_filter
    if api_key_hash:
        params["api_key_hash"] = api_key_hash
    if user_id:
        params["user_id"] = user_id

    resp = requests.get(
        f"{BASE_URL}/activity",
        headers=_headers(management_key),
        params=params,
        timeout=30,
    )
    if resp.status_code != 200:
        # 400 = date outside the last 30 completed UTC days; 403 = regular key.
        detail = resp.text[:300]
        raise SystemExit(f"❌ OpenRouter /activity returned {resp.status_code}: {detail}")
    return resp.json()


def get_credits(management_key: str) -> dict[str, Any]:
    """
    GET /api/v1/credits
    Returns total credits purchased and used.
    """
    resp = requests.get(
        f"{BASE_URL}/credits",
        headers=_headers(management_key),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_generation(api_key: str, generation_id: str) -> dict[str, Any]:
    """
    GET /api/v1/generation?id=<id>
    Returns token counts and cost for a single generation.
    """
    resp = requests.get(
        f"{BASE_URL}/generation",
        headers=_headers(api_key),
        params={"id": generation_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ──────────────────────────────────────────────
# Date helpers
# ──────────────────────────────────────────────

def date_range(start: date, end: date) -> list[str]:
    """Return list of YYYY-MM-DD strings from start to end (inclusive)."""
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def last_n_days(n: int) -> tuple[date, date]:
    """Return (start, end) for the last n completed UTC days."""
    today = datetime.now(tz=timezone.utc).date()
    end = today - timedelta(days=1)  # last completed day
    start = end - timedelta(days=n - 1)
    return start, end


# ──────────────────────────────────────────────
# Aggregation & formatting
# ──────────────────────────────────────────────

def aggregate_activity(items: list[dict]) -> dict[str, Any]:
    """Aggregate a list of ActivityItem dicts into summary stats."""
    total_prompt = 0
    total_completion = 0
    total_reasoning = 0
    total_requests = 0
    total_usage = 0.0
    total_byok = 0.0

    by_model: dict[str, dict[str, Any]] = {}
    by_date: dict[str, dict[str, Any]] = {}

    for item in items:
        pt = item.get("prompt_tokens", 0)
        ct = item.get("completion_tokens", 0)
        rt = item.get("reasoning_tokens", 0)
        req = item.get("requests", 0)
        usg = item.get("usage", 0.0)
        byok = item.get("byok_usage_inference", 0.0)

        total_prompt += pt
        total_completion += ct
        total_reasoning += rt
        total_requests += req
        total_usage += usg
        total_byok += byok

        # By model
        model = item.get("model", "unknown")
        if model not in by_model:
            by_model[model] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "requests": 0,
                "usage_usd": 0.0,
            }
        m = by_model[model]
        m["prompt_tokens"] += pt
        m["completion_tokens"] += ct
        m["reasoning_tokens"] += rt
        m["requests"] += req
        m["usage_usd"] += usg

        # By date (API may return a datetime string; keep the UTC day only)
        d = str(item.get("date", "unknown"))[:10]
        if d not in by_date:
            by_date[d] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "requests": 0,
                "usage_usd": 0.0,
            }
        dd = by_date[d]
        dd["prompt_tokens"] += pt
        dd["completion_tokens"] += ct
        dd["reasoning_tokens"] += rt
        dd["requests"] += req
        dd["usage_usd"] += usg

    return {
        "totals": {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "reasoning_tokens": total_reasoning,
            "total_tokens": total_prompt + total_completion + total_reasoning,
            "requests": total_requests,
            "usage_usd": round(total_usage, 6),
            "byok_usage_inference_usd": round(total_byok, 6),
        },
        "by_model": dict(
            sorted(by_model.items(), key=lambda x: x[1]["usage_usd"], reverse=True)
        ),
        "by_date": dict(sorted(by_date.items())),
    }


def format_report(data: dict[str, Any], start: date, end: date) -> str:
    """Format aggregated data into a human-readable report."""
    t = data["totals"]
    lines: list[str] = []

    lines.append(f"📊 OpenRouter Usage Report")
    lines.append(f"   Period: {start.isoformat()} → {end.isoformat()}")
    lines.append(f"")
    lines.append(f"🔢 Totals:")
    lines.append(f"   Requests:              {t['requests']:,}")
    lines.append(f"   Prompt tokens:         {t['prompt_tokens']:,}")
    lines.append(f"   Completion tokens:     {t['completion_tokens']:,}")
    lines.append(f"   Reasoning tokens:      {t['reasoning_tokens']:,}")
    lines.append(f"   Total tokens:          {t['total_tokens']:,}")
    lines.append(f"   Cost (OR credits):     ${t['usage_usd']:.4f}")
    if t["byok_usage_inference_usd"] > 0:
        lines.append(f"   Cost (BYOK):           ${t['byok_usage_inference_usd']:.4f}")
    lines.append(f"")

    if data["by_model"]:
        lines.append(f"🤖 By Model:")
        for model, stats in data["by_model"].items():
            lines.append(
                f"   {model:<45}  req={stats['requests']:>5,}  "
                f"tok={stats['prompt_tokens']+stats['completion_tokens']+stats['reasoning_tokens']:>10,}  "
                f"${stats['usage_usd']:.4f}"
            )
        lines.append("")

    if data["by_date"]:
        lines.append(f"📅 By Date:")
        for d, stats in data["by_date"].items():
            total_tok = (
                stats["prompt_tokens"] + stats["completion_tokens"] + stats["reasoning_tokens"]
            )
            lines.append(
                f"   {d}  req={stats['requests']:>5,}  "
                f"tok={total_tok:>10,}  "
                f"${stats['usage_usd']:.4f}"
            )

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenRouter Activity & Usage Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --days 7
  %(prog)s --start 2026-05-01 --end 2026-05-25
  %(prog)s --credits
  %(prog)s --days 30 --json
  %(prog)s --date 2026-05-24
        """,
    )
    parser.add_argument("--days", type=int, help="Last N completed UTC days")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--date", type=str, help="Single date (YYYY-MM-DD)")
    parser.add_argument("--credits", action="store_true", help="Show credits summary")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output raw JSON")
    parser.add_argument(
        "--api-key-hash", type=str, default=None, help="Filter by API key hash (SHA-256)"
    )
    parser.add_argument(
        "--user-id", type=str, default=None, help="Filter by org member user ID"
    )
    parser.add_argument(
        "--management-key",
        type=str,
        default=os.environ.get("OPENROUTER_MANAGEMENT_KEY"),
        help="OpenRouter management API key (or OPENROUTER_MANAGEMENT_KEY env var)",
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Write output to file (JSON only)"
    )

    args = parser.parse_args()

    if not args.management_key:
        print(
            "❌ Management key required. Set OPENROUTER_MANAGEMENT_KEY or use --management-key.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Credits mode ──
    if args.credits:
        data = get_credits(args.management_key)
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            key_data = data.get("data", data)
            print(f"💰 OpenRouter Credits")
            for k, v in key_data.items():
                print(f"   {k}: {v}")
        return

    # ── Activity mode ──
    # Determine date range
    if args.date:
        start = end = parse_date(args.date)
    elif args.start and args.end:
        start, end = parse_date(args.start), parse_date(args.end)
    elif args.days:
        start, end = last_n_days(args.days)
    else:
        start, end = last_n_days(7)  # default: last 7 days

    # Clamp to 30-day window. The activity API only exposes COMPLETED UTC days:
    # passing today (or a future date) yields 400, so fail with a readable message.
    today = datetime.now(tz=timezone.utc).date()
    if end >= today:
        print(
            f"⚠️  {end.isoformat()} is not a completed UTC day. The activity API "
            f"only returns completed days; latest available is "
            f"{(today - timedelta(days=1)).isoformat()}.",
            file=sys.stderr,
        )
        sys.exit(2)
    max_start = today - timedelta(days=30)
    if start < max_start:
        print(
            f"⚠️  OpenRouter activity API covers max 30 days. "
            f"Clamping start from {start} to {max_start}.",
            file=sys.stderr,
        )
        start = max_start

    # Fetch data day by day (API supports single date filter or full 30-day dump)
    all_items: list[dict] = []
    dates = date_range(start, end)

    if len(dates) == 1:
        # Single date — one call
        resp = get_activity(
            args.management_key,
            date_filter=dates[0],
            api_key_hash=args.api_key_hash,
            user_id=args.user_id,
        )
        all_items.extend(resp.get("data", []))
    elif len(dates) <= 5:
        # Few dates — one call per date for precision
        for d in dates:
            resp = get_activity(
                args.management_key,
                date_filter=d,
                api_key_hash=args.api_key_hash,
                user_id=args.user_id,
            )
            all_items.extend(resp.get("data", []))
    else:
        # Many dates — fetch full window and filter client-side
        resp = get_activity(
            args.management_key,
            api_key_hash=args.api_key_hash,
            user_id=args.user_id,
        )
        all_items.extend(resp.get("data", []))
        date_set = set(dates)
        all_items = [i for i in all_items if i.get("date") in date_set]

    if args.as_json:
        output = json.dumps(all_items, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"✅ Written {len(all_items)} records to {args.output}")
        else:
            print(output)
    else:
        aggregated = aggregate_activity(all_items)
        report = format_report(aggregated, start, end)
        print(report)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(aggregated, f, indent=2)
            print(f"\n✅ JSON data written to {args.output}")


if __name__ == "__main__":
    main()
