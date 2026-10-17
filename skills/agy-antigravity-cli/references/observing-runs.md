# Observing an agy run

How to see what a running (or finished) agy job is actually doing, instead of inferring it
from whether output files appeared.

## The session log (live)

`~/.gemini/antigravity-cli/cli.log` is a **symlink to the log of the most recent invocation**:

```bash
tail -f ~/.gemini/antigravity-cli/cli.log
```

It shows the model's HTTP activity — `streamGenerateContent` calls, response IDs, timestamps —
so it proves liveness and progress. It does not show the model's prose. One log file per
invocation lives under `~/.gemini/antigravity-cli/log/`, so the symlink follows whichever run
started last; pin a specific run with `--log-file <path>`.

## The step transcript (what it actually did)

The real record is per conversation:

```
~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/
├── logs/transcript.jsonl        # one JSON record per step, LONG CONTENT TRUNCATED
├── logs/transcript_full.jsonl   # same records, untruncated content
├── logs/chunks/transcript{,_full}/NNNNNNNN.jsonl   # the same stream, chunked
├── steps/<n>/output.txt         # output of step n — only exists for steps that ran a tool
└── tasks/task-<n>.log           # background-task logs (note the `task-` prefix)
```

**`transcript.jsonl` truncates long fields at ~4 KB and flags it.** A record whose `content`
(or `thinking`) was cut carries `"truncated_fields": ["content"]`; the full text is in
`transcript_full.jsonl` under the same `step_index`. Reading the short file and treating it as
complete silently loses the end of tool output — exactly the part that would explain the
failure. Rule: if a record has `truncated_fields`, re-read that step from
`transcript_full.jsonl`.

**Step types:** `USER_INPUT` (the prompt), `PLANNER_RESPONSE` (carries `tool_calls` and
sometimes `thinking`), `GENERIC` (tool output), and `SYSTEM_MESSAGE` — an injected system
notice that can be several KB and reads like user prose. Never quote a `SYSTEM_MESSAGE` step
back to the user as their own request.

**`created_at` is UTC** (`...Z`) while tool output quoted inside `content` often carries a
local offset (`+02:00`). Use `created_at` for durations and leave the local strings alone; do
not subtract one from the other.

### Finding the conversation id

`~/.gemini/antigravity-cli/conversations/<cid>.db` holds one file per run and the basename **is**
the conversation id, 1:1 with `brain/<cid>/`. That is more reliable than scraping the live log:

```bash
ls -t ~/.gemini/antigravity-cli/conversations/*.db | head -1 | xargs -n1 basename | sed 's/\.db$//'
```

Then summarise the tail of the transcript:

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/logs/transcript.jsonl")
rows = [json.loads(l) for l in open(p, errors="replace") if l.strip()]
print("entries:", len(rows))
for r in rows[-10:]:
    print(r.get("step_index"), r.get("type"), r.get("status"),
          str(r.get("tool_calls") or r.get("thinking") or r.get("content") or "")[:200])
PY
```

This is how you tell "working methodically" from "stuck polling a background task" without
seeing the TUI — read it before reporting that a run is fine. `thinking` is present on only
some `PLANNER_RESPONSE` steps, so fall back to `tool_calls` when it is absent.

## Why redirected stdout looks empty

`agy --print "..." > out.txt` writes nothing until the run ends: agy buffers stdout when it is
not a TTY. A 0-byte `out.txt` mid-run means "still working", not "failed". For live content use
`--output-format stream-json` (NDJSON, emitted as the model produces it) so a `tail -f` shows
the work. Interactive mode (`-i`) shows everything live but needs a PTY.

## Background-task stalls

agy offloads long commands to a background task and then polls it. When the step transcript
shows repeated `manage_task status` calls with no new artefacts, read `tasks/task-<n>.log` —
the task's own log names the real blocker (an installer still running, a hung command) far
more directly than the conversation log does. Report that blocker, not the symptom.

## When a run produced nothing: read the per-run log, not the exit code

agy exits **0 with empty stdout** on fatal errors, so an empty result never explains itself.
Give every invocation its own log and grep it:

```bash
agy --log-file /tmp/agy-run.log --print="$(cat brief.md)" >out.txt 2>err.txt
[ -s out.txt ] || grep -E "agent executor error|not logged into Antigravity|RESOURCE_EXHAUSTED" /tmp/agy-run.log
```

Discriminate by what the log says:

| Log evidence | Meaning | Action |
|---|---|---|
| `error getting token source: You are not logged into Antigravity.` (`errorreport.go:224` prefix) | OAuth session expired | Run `agy` once interactively to re-login; retrying is pointless |
| `RESOURCE_EXHAUSTED` / 429 | Quota spent | Stop and check `/quota`; do not retry |
| `UNAVAILABLE` (code 502/503) | Transient backend outage | One retry after a pause is reasonable |
| `jetski: no output produced — a tool required the "command" permission …` | Headless auto-deny | Add `--dangerously-skip-permissions` |
| empty log and no output | Process never really started (bad path, shadowed binary, stdin wait) | Check the command line and stdin redirection |

The token-source string is what agy actually writes; do not grep for `Failed to get OAuth
token` — that needle belongs to third-party wrappers, not to agy's own output.

## Do not read a crash file as a verdict

`~/.gemini/antigravity-cli/crashes/crash_<pid>_*.log` can exist at **0 bytes** while the run is
perfectly healthy — the pid in the filename is a *live* agy process, not a dead one. Check the
process and the step transcript before telling the user anything crashed: an empty crash file plus a
moving transcript means the run is fine.
