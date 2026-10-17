---
name: agy-antigravity-cli
description: "Use when running, scripting, or troubleshooting the Antigravity `agy` CLI. Covers non-interactive print mode, model names and tiers, plugin and MCP management, quota inspection, and diagnosing a run that exited 0 with empty output."
hermes_requires: ">=0.21"
tags:
  - cli-tools
  - agy
  - antigravity
  - gemini
  - delegation
---

# agy (antigravity CLI) — Usage Guide

## Overview

`agy` (antigravity CLI) is an AI agent CLI you can call directly from Hermes via `terminal()`. It supports the current Gemini 3.8 Flash variants (Low, Medium, High), creates and edits files, runs code, and manages plugins. Use agy when you want to **delegate a task to a Gemini model** without switching your Hermes provider, or when you need **fast non-interactive prompt execution** for the `hermes-skill-creator` evaluation workflow.

**Why agy instead of a direct Hermes call?** You stay on your primary Hermes model while agy handles parallel work using Gemini. agy is a complementary leaf tool — it does not delegate back to Hermes.

## Prerequisites

This is an **adapter skill**: it pilots the `agy` command-line tool, and that is its declared purpose.

**It is inert without `agy`.** If the binary is not available, report that `agy` is not installed and stop — never claim success, never fabricate output.

Resolve the binary as `AGY_BIN` if that environment variable is set, otherwise `agy` on `PATH`. The official installer's default location (`~/.local/bin/agy`) is an example only, not a requirement.

The first workflow step of every job is the preflight:
```bash
command -v "${AGY_BIN:-agy}"
```

## Model guidance

This skill defaults to the newest Gemini Flash at Medium effort — currently `Gemini 3.8 Flash (Medium)`.

- **Default: the newest Gemini Flash at Medium effort** — currently `"Gemini 3.8 Flash (Medium)"`. Use it for every agy delegation unless configured otherwise.
- Never switch model or tier on your own; do so only when the user explicitly asks. A task looking hard is not a reason to switch.
- Run `agy models` to confirm which models the installed CLI currently offers.

## Trigger conditions

- User asks to use `agy`, "antigravity CLI", or "the CLI tool"
- User wants to delegate a task to a Gemini model (Gemini 3.8 Flash variants — run `agy models` for the live list)
- User wants to run a quick non-interactive prompt via shell
- User asks about available models, quota, credits, or plugin management
- User mentions "antigravity" or "antigravity CLI"
- **Skill evaluation runs** — agy is the baseline coding engine for the `hermes-skill-creator` workflow (running eval prompts, grading outputs, testing triggers)

## Installation & Setup

`agy` is resolved on `PATH`, overridable via the `AGY_BIN` environment variable (the official installer places it at `~/.local/bin/agy` by default as an example location; add to `PATH` if needed). If not installed:

```bash
# Install via the official script
curl -sSf https://antigravity.sh/install | sh

# Or configure shell integration after install
agy install
agy install --skip-path   # Only set aliases, skip PATH
agy install --skip-aliases  # Only set PATH, skip aliases
```

## Commands Reference

### Execution modes

| Mode | Flag | Description |
|------|------|-------------|
| **Non-interactive** | `--print "prompt"` or `-p "prompt"` or `--prompt "prompt"` | Run a single prompt, print response, exit. Best for Hermes delegation. |
| **Interactive** | `--prompt-interactive` or `-i` | Start with an initial prompt, then continue interactively. **Not suitable for Hermes terminal()** — use pty=true. |
| **Continue last** | `--continue` or `-c` | Resume the most recent conversation by ID. |
| **Resume specific** | `--conversation <id>` | Resume a specific conversation by ID. |

### Model selection

**Default (use this):**

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print "prompt"
```

**Available models** (live `agy models` on v1.4.0):

| Model | Variants | Status |
|-------|----------|--------|
| Gemini 3.8 Flash | Low, Medium, High | **Default (Medium)** |

> Run `agy models` for the live list — the CLI adds and removes models between releases.

### Mode flags

```bash
agy --mode accept-edits    # Auto-apply edits suggested by the model
agy --mode plan            # Plan mode — only propose changes, don't apply
```

### Other flags

| Flag | Description |
|------|-------------|
| `--dangerously-skip-permissions` | Auto-approve all tool permission requests (use with caution) |
| `--sandbox` | Enforce terminal restrictions (sandboxed execution) |
| `--project <id>` | Project ID for the session |
| `--new-project` | Create a new project for this session |
| `--add-dir <path>` | Add a directory to the workspace (repeatable) |
| `--log-file <path>` | Override CLI log file path |
| `--print-timeout <duration>` | Timeout for print mode. `0` (the default) waits until the turn completes. Set a finite value and agy is cut off mid-turn. |
| `--output-format <text\|json\|stream-json>` | Output format for print mode (default text). Use `json` for structured output with `denied_actions`, v1.2.1+ |

### Subcommands

```bash
agy models          # List available models (live, updates with new releases)
agy agent           # List available agents
agy mcp             # Manage MCP servers (add, remove, list, enable, disable)
agy plugin list     # List imported plugins
agy plugin import <source>  # Import plugins from gemini or claude
agy plugin install <target>  # Install a plugin (supports plugin@marketplace)
agy plugin uninstall <name>  # Uninstall a plugin
agy plugin enable <name>     # Enable a plugin
agy plugin disable <name>    # Disable a plugin
agy plugin validate [path]   # Validate a plugin
agy plugin link <mp> <target> # Generate a marketplace link
agy remote-control start|status|stop  # Run CLI as background service (v1.2.0+)
agy changelog       # Show changelog and release notes
agy update          # Update CLI
```

**In-CLI slash commands** (not subcommands — use inside the interactive TUI):

```bash
/usage    # Live real-time consumption stats (reloads quota immediately)
/quota    # Live real-time remaining quota per model
/credits  # Panel with link to purchase G1 credits (v1.0.3+)
/model <name> [prompt]  # Run a single prompt on another model, then switch back (v1.1.27+)
/changelog # List of CLI changes from inside the TUI
/settings # Configure Verbosity, color scheme, UseG1Credits, etc.
```

## Usage Patterns for Hermes Delegation

Each pattern below follows the same rule: **always use `--print` (non-interactive) from Hermes `terminal()`**. Interactive mode (`-i`) requires `pty=true` or it will hang indefinitely.

### Pattern 1: Run a prompt and get the response

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print "List the top 5 Italian pasta shapes with their regions"
```

**Input:** A question or task as a string.  
**Output:** agy prints the answer to stdout and returns exit code 0.

### Pattern 2: Create a file on disk

agy writes files you specify in the prompt. **Always verify the file exists afterward.**

```bash
agy --model "Gemini 3.8 Flash (High)" --print \
  "Write a Python script to <workspace>/fizzbuzz.py that prints numbers 1-100, replacing multiples of 3 with 'Fizz' and 5 with 'Buzz'"
```

**Input:** Instructions including the target file path.  
**Output:** agy confirms file creation → verify with `read_file(path)`.

### Pattern 3: Let long tasks finish — use `--print-timeout 0`

Anything that reads files, runs commands, or writes artefacts takes minutes, not seconds.

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print-timeout 0 --print="$(cat brief.md)"
```

**Why:** `0` waits for the turn to complete. Any finite value is a hard cut mid-turn, and
the failure is quiet in the worst way: agy exits **0** and prints only
`[agy] print timeout after <d> with turn in progress; returning partial output` — so it
looks like success — while **none of the requested artefacts exist**. A skill-following or
file-writing job routinely runs past 6–8 minutes, so even a "generous" finite timeout is a
coin flip. Bound the run by making the job small (one deliverable per invocation), not by
the clock.

### Pattern 4: Interactive session (only with pty=true)

```bash
# ALWAYS use pty=true for interactive mode
terminal("agy --model 'Gemini 3.8 Flash (High)' -i", pty=True)
```

**Why pty is required:** Without a pseudo-terminal, interactive CLI apps block waiting for stdin that never arrives. `pty=true` simulates a real terminal so agy can read your keystrokes. Note: `-i` (or `--prompt-interactive`) takes the first positional arg as its prompt — put `--model` BEFORE `-i` on the command line or it errors.

### Pattern 5: Skill evaluation baseline (for hermes-skill-creator)

agy serves as the baseline coding engine for the `hermes-skill-creator` evaluation workflow. Run eval prompts **without any skill context** to measure what the model produces unaided. There are two baseline shapes, and they measure different things:

**Acting baseline** — the eval grades artefacts on disk, so the baseline must be able to write them. It needs `--dangerously-skip-permissions`: headless print mode auto-denies every tool it cannot prompt for, so without that flag the run exits **0** having produced no output and no artefacts.

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print-timeout 0 --dangerously-skip-permissions \
  --print="$(cat baseline-prompt.txt)"
```

**Text-only baseline** — the eval grades the answer itself. Cheaper and much faster, but it produces no artefacts, so file-based assertions cannot apply.

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print-timeout 0 --disable-slash-commands \
  --print="Do not call any tools; answer in text.

$(cat baseline-prompt.txt)"
```

Redirect stdout to `<workspace>/iteration-1/eval-0/without_skill/outputs/response.txt` to keep the comparison. Use `--print-timeout 0` in both shapes (a finite timeout cuts the turn mid-run and returns exit 0 with only a partial-output warning — see Pattern 3). Run the with-skill half in the **same shape** as the baseline: an acting with-skill run scored against a text-only baseline compares nothing.

### Pattern 6: Description optimization testing

The description-optimisation script shipped with the `hermes-skill-creator` skill calls agy programmatically to test whether a skill description triggers correctly for a given query:

```python
# Called internally by the description optimization script
import subprocess
result = subprocess.run(
    ["agy", "--model", "Gemini 3.8 Flash (Medium)", "--print", prompt],
    capture_output=True, text=True, timeout=120
)
```

### Pattern 7: Automated grading in evaluation pipelines

For skills with programmatically verifiable assertions, pipe agy output to a grading script:

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print "Generate a CSV with columns: Name, Email, Role" \
  | python3 -c "
import sys, json
content = sys.stdin.read()
lines = [l for l in content.strip().split(chr(10)) if l.strip()]
header = lines[0].lower() if lines else ''
assert 'name' in header and 'email' in header, 'Missing required columns'
print(json.dumps({'grading': [{'text': 'Has header with Name, Email', 'passed': True, 'evidence': header}]}))
"
```

**Why pipe to a script instead of LLM grading:** Scripts are deterministic, faster, and cheaper than LLM-based evaluation. Use them for every assertion that can be expressed as a regex, file check, or data validation.

### Pattern 8: Structured JSON output (v1.2.1+)

For machine-readable results or to inspect `denied_actions`, use `--output-format json`:

```bash
agy --model "Gemini 3.8 Flash (Medium)" --output-format json --print "Summarize this file in 1 line: README.md"
```

**Why:** JSON output is easier to parse in Hermes pipelines and exposes fields like `denied_actions` (v1.1.27+ reports refused tool actions as `denied_actions` instead of silently skipping them).

### Pattern 9: Feed a large prompt from a file (reviews, long context)

`--print` takes its prompt as a **flag argument**, not from stdin. Attach the file's contents to the flag:

```bash
agy --model "Gemini 3.8 Flash (Medium)" --print="$(cat prompt_and_context.txt)"
```

A bare `--print` with stdin redirection and `--input-format text` fails: agy reports `--print took "--input-format" as its prompt, so the intended prompt was left as an argument and ignored`. Keep `--input-format` / `--output-format` **before** `--print`, and always give `--print` its value.

### Pattern 10: Orchestrate agy to author artefacts in an existing repo

When the user wants **agy** to do the authoring and Hermes only to orchestrate:

Before the first write, check whether the target directory is already a git repository and
whether the file you are about to create or move is tracked there (`git status`, `git ls-files`).
Moving a file into a cloned repo **overwrites the tracked copy silently** — `mv` has no
would-clobber guard — and the loss surfaces only later. When it happens, `git status` shows
` M <file>` and the original is still in HEAD: restore it with `git checkout HEAD -- <file>`
rather than rewriting it from memory.

1. **Run agy with the target repo as its working directory** (`cd <repo> && agy …`) so it
   reads the repo's own normative files — the standard doc, the section template, the CI
   config — itself. Never paraphrase a standard that is already on disk into the prompt.
2. **Read the repo's own gate first and put its rules into the prompt.** Open the repository's
   own validator, the CI workflow and any linter config, then state the constraints as
   "the gate fails if …". One artefact the gate rejects costs a whole agy run, and a broken
   intermediate state makes the next step harder for the user to review.
3. **Pass the brief as a file, not inline:**
   `agy --model "Gemini 3.8 Flash (Medium)" --print-timeout 8m --dangerously-skip-permissions --print="$(cat /path/brief.md)"`.
   The headless-write flag matters here: `--print` auto-denies any tool it cannot prompt
   for, so a job whose whole purpose is writing files needs `--dangerously-skip-permissions`
   (or explicit allow-rules) or it silently produces no output at all.
4. **One bounded job per deliverable** — one file-set per agy run, so a bad run costs one
   step instead of the whole task. Order the steps so the gate can stay green at each
   checkpoint (e.g. never link a `references/` path before the file exists). When the user
   asks for the remaining steps "in one go", chain the jobs without pausing for approval.
5. **Verify by reading the artefact** with `read_file` and report what agy actually produced.
   Never relay agy's own claim that it wrote a file, and never treat a green gate as proof
   the content is right — the gate checks shape, not correctness. Reading is what catches a
   wrong command or a soft claim.

**Do not re-run the repo's verification gate after every step when the user is reviewing the
artefacts themselves.** They own that gate and said so; running it on their behalf is noise
that reads as stalling. Read the artefact, report, move on.

## Known Limitations

- **No local token usage tracking** — agy does not expose a `stats` or `usage` subcommand. Token consumption is tracked server-side by Antigravity/Google. To view usage: check Google AI Studio dashboard (aistudio.google.com) or Google Cloud Console.
- **No direct Gemini API key** — agy uses OAuth tokens, not raw API keys. These tokens cannot query Google APIs directly.
- **Conversation logs are server-side** — local SQLite DBs store conversation IDs but no token counts or cost data.
- **agy path varies** — resolved on `PATH` or via `AGY_BIN`; installed at `~/.local/bin/agy` by default as an example location, not `/usr/local/bin/agy`. Use `command -v "${AGY_BIN:-agy}"` to locate.
- **Model names change frequently** — new models roll out regularly — run `agy models` for the live list rather than relying on this skill's table.

## Pitfalls

- **Don't use interactive mode without pty=true** in Hermes terminal() — it will hang waiting for stdin.
- **`--print` has no default deadline: `--print-timeout 0` (the default) waits for the turn to complete.** Any finite value you pass is a hard cut mid-turn that still exits 0 — see Pattern 3. Do not "raise" a timeout that was never limiting you; bound the job instead.
- **agy creates files on disk** — the file path is reported in its output. Always verify with Hermes read_file() before reporting success to the user.
- **Model names are case-sensitive** and include the tier suffix (e.g., `"Gemini 3.8 Flash (Medium)"` not just `"Gemini 3.8 Flash"`).
- **`--dangerously-skip-permissions`** skips all tool permission prompts. Only use for fully automated, trusted workflows.
- **Plugin management** is per-install, not per-session. Modifying plugins affects future agy sessions.
- **No nested delegation** — agy cannot delegate back to Hermes. It's a leaf tool.
- **`--sandbox`** restricts terminal capabilities — useful for untrusted prompts but may break file operations.
- **`--print` needs its prompt as an argument, not stdin.** `agy ... --print --input-format text < file` errors because `--print` swallows the next flag as its prompt. Pass the text inline (`--print="$(cat file)"`); put `--input-format`/`--output-format` before `--print`.
- **Headless print mode auto-denies any tool it cannot prompt for**, then reports no output at all (e.g. `jetski: no output produced — a tool required the "command" permission that headless mode cannot prompt for, so it was auto-denied`). **`--disable-slash-commands` alone does not prevent this:** any run that must run a command or write a file needs `--dangerously-skip-permissions` (or explicit allow-rules), or it returns zero output and zero artefacts while exiting 0. For a prompt whose answer is fully self-contained, keep `--disable-slash-commands` and add "Do not call any tools; answer from the text provided" — and expect no artefacts from it, because it was never allowed to act.
- **Empty stdout with exit 0 has three different causes, and only the log tells them apart.** (1) *headless tool auto-deny* — the default for any write/command job, fixed by `--dangerously-skip-permissions`; (2) *quota exhausted* (`RESOURCE_EXHAUSTED` / 429) — do NOT retry, it will fail the same way; (3) *session expired* — needs one interactive `agy` run to re-login. Grep the `--log-file` of that invocation instead of trusting the exit code; see `references/observing-runs.md`.
- **Pass `stdin=DEVNULL` (`< /dev/null`) whenever agy runs non-interactively** — from cron, a service, or `subprocess`. Otherwise it inherits a stdin that never delivers a line and the run hangs with no output and no error. Only the interactive TUI needs a real (or PTY) stdin.
- **Never let anything named `agy` shadow the real binary.** The official CLI is one ~220 MB executable (installed at `~/.local/bin/agy` by default). A `pip install` of a third-party "agy" package (e.g. one registering `agy = <wrapper>:main`) or a hand-rolled wrapper silently replaces it; every call then fails with an empty log and no output, or exit 127 if the wrapper execs a missing `agy.original`. Confirm with `ls -l "$(command -v "${AGY_BIN:-agy}")"` (must be the large binary) before blaming the model or the quota, and prefer calling `agy` directly over installing a wrapper.

## Verification

After delegating to agy:

1. Read the file agy claims to have created: `read_file(path)`
2. Run/verify the output: `terminal(command)`
3. Compare against the user's requirements before reporting completion

## References

- `references/quick-ref.md` — Quick reference card (commands, models, patterns)
- `references/observing-runs.md` — how to watch a live or finished agy run: the session log, the per-conversation step transcript (and where it is truncated), how to find the conversation id, and how to diagnose a run that produced nothing from its per-run log
- `scripts/agy_run_reader.py` — read-only viewer for agy's run artifacts under `~/.gemini/antigravity-cli`; renders a live TUI of a run. It does not invoke agy.
- Official site: https://antigravity.sh
- The `tool-evaluation` skill for evaluating third-party CLI tools
- The `hermes-skill-creator` meta-skill for using agy as a skill evaluation engine

## Usage & Quota Tracking

agy does **not** expose per-request token counts locally. Usage is tracked server-side by Google's Antigravity/Cloud Code backend.

### Local language server (quota only)

When agy is running (interactive mode), it serves a **local language server** on two loopback ports (HTTP + HTTPS). Query it for account plan and per-model remaining quota:

```bash
# Find agy's listening ports
ss -tlnp | grep agy

# Query quota status
curl -sk -X POST "https://127.0.0.1:<PORT>/exa.language_server_pb.LanguageServerService/GetUserStatus" \
  -H 'Content-Type: application/json' \
  -H 'Connect-Protocol-Version: 1' \
  -d '{"metadata":{"ideName":"antigravity","extensionName":"antigravity","locale":"en"}}'
```

The response includes:
- **Plan info**: plan name, tier, monthly credits
- **Available credits**: remaining prompt and flow credits
- **Per-model quota**: `quotaInfo.remainingFraction` (0.0–1.0) and `resetTime` per model

### Limitations

- ❌ No per-request token count exposed locally
- ❌ No historical usage data available via CLI
- ✅ Quota/remaining credits per model available via the local language server
- ✅ Account plan info available via the local language server
- For detailed token-level analytics, check **Google AI Studio** (aistudio.google.com) or **Google Cloud Console**

### Account Tier & Credit Troubleshooting

If agy credits deplete faster than expected, check the account tier via the language server:

```bash
curl -sk ...GetUserStatus | python3 -c "import json,sys; d=json.load(sys.stdin)['userStatus']; print(d.get('userTier',{}).get('name','N/A'))"
```

Two separate systems control usage:

| Layer | Source | What it shows |
|-------|--------|---------------|
| **Plan** (`planStatus.planInfo`) | Cloud Code billing | `planName: "Pro"`, monthly credits (observed on one host: e.g. 50k prompt, 150k flow) |
| **Tier** (`userTier`) | Antigravity access tier | `"Antigravity Starter Quota"` — may differ from the plan name |

If the tier is **"Antigravity Starter Quota"** (free tier) while the plan says "Pro", the effective rate limits and quota pool come from the Starter tier, not the Pro plan. This causes fast depletion and the upgrade text `"This account is ineligible for higher rate limits through a Google AI plan at this time."`

**Steps to diagnose and fix:**

1. **Check tier** — query the language server as shown above
2. **Use `/quota` and `/usage` inside agy** — these reload live consumption immediately (v1.0.1+)
3. **Use `/credits`** — opens a panel with a link to buy G1 credits (v1.0.3+)
4. **Enable `UseG1Credits`** — in `/settings` or by adding to `~/.gemini/antigravity-cli/settings.json`:
   ```json
   { "useG1Credits": true }
   ```
   This lets agy spend G1 credits when the standard quota runs out.
5. **Check Google AI Studio** — aistudio.google.com shows Gemini API quota under the linked billing account
6. **Check Google Cloud Console** — the Cloud Code / Antigravity API quota dashboard at console.cloud.google.com
