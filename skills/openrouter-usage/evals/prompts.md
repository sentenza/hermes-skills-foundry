# Evaluation Prompts: OpenRouter Usage

Evaluation scenarios for `openrouter-usage`. Every assertion below is objectively verifiable:
the script is deterministic, so the results are measured against a live management key, not judged.

Environment: Hermes Agent v0.22.5, `OPENROUTER_MANAGEMENT_KEY` set, `requests` installed.
Measurement date: 2026-10-23 (UTC window covering 2026-09-26 → 2026-10-22).

---

## Prompt 1: Spend over a period, per model

- **ID**: 1
- **Short Name**: `spend-last-7-days`

### User Prompt

> How much did I spend on OpenRouter in the last 7 days, and on which models?

### Acceptance Assertions

1. The report names an explicit period with both bounds (e.g. `Period: 2026-10-16 → 2026-10-22`).
2. It prints request, prompt/completion/reasoning token and total-token totals.
3. It prints a cost line in USD taken from the API `usage` field.
4. A per-model breakdown is present, sorted by cost descending, one line per model.

---

## Prompt 2: Credit balance

- **ID**: 2
- **Short Name**: `credits`

### User Prompt

> What's my OpenRouter credit balance?

### Acceptance Assertions

1. The command used is `--credits`, not an activity query.
2. The output contains `total_credits` and `total_usage`; the remaining balance is derivable and stated as purchased minus consumed.
3. No activity table is printed in this mode.

---

## Prompt 3: One completed UTC day

- **ID**: 3
- **Short Name**: `single-day`

### User Prompt

> Show me the OpenRouter activity for 2026-10-22.

### Acceptance Assertions

1. The period line is a single day (`2026-10-22 → 2026-10-22`).
2. Per-model and per-date sections both carry that day only.
3. The date rows are formatted `YYYY-MM-DD` (no `00:00:00` suffix leaking from the API datetime).

---

## Prompt 4: Today is not queryable

- **ID**: 4
- **Short Name**: `today-refused`

### User Prompt

> What have I spent on OpenRouter today?

### Acceptance Assertions

1. The script exits non-zero (2) instead of raising a traceback.
2. It states that the requested day is not a completed UTC day and names the latest available day.
3. The answer to the user reports the latest completed day's figures and labels them as such — it does not present them as "today".

---

## Prompt 5: Raw JSON to file

- **ID**: 5
- **Short Name**: `json-output`

### User Prompt

> Dump the last 3 days of OpenRouter usage as JSON to a file so I can process it.

### Acceptance Assertions

1. `--json --output <file>` writes a JSON array of raw activity records and reports the record count.
2. The written file parses as JSON and each item carries `date`, `model`, `prompt_tokens`, `completion_tokens`, `requests`, `usage`.

---

## Prompt 6: Wrong key type

- **ID**: 6
- **Short Name**: `regular-key-403`

### User Prompt

> (operator error) Query the activity with my normal inference key.

### Acceptance Assertions

1. The 403 body is surfaced verbatim (`Only management keys can fetch activity for an account`) rather than swallowed or retried.
2. The exit is non-zero and no fabricated report is printed.
3. The answer points at creating a management key.
