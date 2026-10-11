---
name: hermes-skill-creator
description: "Use when creating, testing, or iteratively improving a Hermes Agent skill — 'create a skill for X', 'turn this workflow into a skill', 'make a skill that does Y', 'improve/test/evaluate this skill', or a draft SKILL.md to be tested and iterated. Runs the full lifecycle (intent capture → drafting → test-case creation → multi-run evaluation with and without the skill → grading → HTML review viewer → blind A/B comparison → iteration → description optimization → validation and packaging), using agy (antigravity CLI) as the coding engine and Hermes delegate_task for parallel evaluation. Always prefer this over ad-hoc skill creation."
tags:
  - meta-skill
  - skill-creation
  - agy
  - antigravity
  - evaluation
  - benchmarking
  - iteration
hermes_requires: ">=0.21"
related_skills:
  - agy-antigravity-cli
compatibility:
  requires_agy: true
  agy_model_default: "Gemini 3.8 Flash (Medium)"
---
<!-- adapted from anthropics/skills (Apache-2.0) -->

# Hermes Skill Creator

A skill for creating new Hermes skills and iteratively improving them. Code
generation and baseline runs use `agy` (antigravity CLI); parallel with-skill
runs and graders use Hermes `delegate_task`.

At a high level:

1. **Capture intent** — what the skill should do and when it should trigger
2. **Interview & research** — edge cases, I/O formats, existing skills, dependencies
3. **Draft the SKILL.md** — Hermes progressive-disclosure conventions
4. **Create test cases** — 2-3 realistic prompts in `evals/evals.json`
5. **Run evaluations** — parallel with-skill (`delegate_task`) + baseline (`agy`), several runs each
6. **Grade & aggregate** — grader subagent → `grading.json` → `benchmark.json` (mean ± stddev)
7. **Review with the user** — generate the HTML eval viewer and get the human in the loop
8. **Iterate** — improve from feedback, rerun into the next iteration, repeat
9. **Optional** — blind A/B comparison between versions; description optimization
10. **Finalize** — validate and package

Your job is to figure out where the user is in this process and jump in.

---

## Trigger conditions

- "create a skill for X" / "make a skill that does Y" / "turn this into a skill"
- "improve this skill" / "test this skill" / "evaluate this skill"
- A draft SKILL.md that the user wants tested/iterated
- "let's build a skill" / "ho bisogno di una skill per..."
- A pasted workflow the user wants captured as a skill

---

## Communicating with the user

Users range from non-technical to expert. Read the context cues. "evaluation"
and "benchmark" are usually fine; explain "JSON", "assertion", or "stddev"
briefly if you're unsure the user knows them. When in doubt, a one-line
definition costs nothing.

---

## Phase 1: Capture Intent

Extract from conversation history first if the workflow is already there — the
tools used, step sequence, corrections the user made, observed I/O formats.

Confirm (or infer) before proceeding:

1. **What should this skill enable Hermes to do?**
2. **When should it trigger?** — user phrases and contexts
3. **Expected output format?** — file types, structure, style
4. **Test cases?** — skills with objectively verifiable outputs (code gen, data
   extraction, file transforms) benefit from tests. Subjective skills (writing
   style, design) often don't. Suggest the default, let the user decide.

---

## Phase 2: Interview & Research

Proactively research edge cases, I/O formats, success criteria, and
dependencies before drafting. Use `web_search()` for technologies/APIs you need
to understand. Check existing skills via `skills_list()` — never recreate
something that already exists.

**Before researching a comparison target** (e.g. "compare this skill with X"):
check whether a skill for X exists first. If `skills_list()` shows no skill for
the target, there is nothing to compare against — drop the tangent.

---

## Phase 3: Write the SKILL.md

Create the skill at `~/.hermes/skills/<category>/<skill-name>/SKILL.md`.

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

### Frontmatter

```yaml
---
name: skill-name
description: "What it does AND when to use it — the primary trigger mechanism. Make it a bit 'pushy' (models under-trigger skills). Include specific context cues."
tags:
  - relevant-tags
related_skills:
  - existing-skill-name
---
```

### Progressive disclosure

Skills load in three levels:

1. **Metadata** (name + description) — always in context (~100 words)
2. **SKILL.md body** — loaded when the skill triggers (<500 lines ideal)
3. **Bundled resources** — as needed (unlimited; scripts run without loading)

Key patterns:
- Keep SKILL.md under ~500 lines; if approaching it, add a layer of hierarchy
  with clear pointers to reference files.
- Reference files explicitly from SKILL.md with when-to-read guidance.
- For reference files >300 lines, include a table of contents.
- For multi-domain skills, split by variant (one reference file per domain).

### Writing patterns

- **Imperative form** in instructions.
- **Define output formats** with exact templates ("ALWAYS use this exact template: ...").
- **Include examples** (Input → Output).
- **Explain the why** — prefer reasoning over heavy-handed MUSTs; LLMs have
  good theory of mind and a good harness beats rote instruction.
- **Avoid overfitting** — make the skill general, not tied to your few test cases.
- **Look for repeated work** — if test subagents all wrote the same helper
  script, bundle it in `scripts/`.
- **No surprise / no malware** — skills must be safe and must not mislead the
  user about their intent.

Hermes specifics: land the skill with `skill_manage(action='create')`; keep
category folders; use `references/`, `scripts/`, `assets/`. See
`references/schemas.md` for eval JSON shapes.

---

## Phase 4: Create Test Cases

Write 2-3 realistic prompts in `evals/evals.json` (prompts only — add
assertions later):

```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 0,
      "name": "descriptive-name",
      "prompt": "Realistic user prompt — file paths, casual speech, context",
      "expected_output": "What success looks like",
      "files": [],
      "assertions": []
    }
  ]
}
```

Share with the user: "Here are test cases. Do these look right?" Adjust before running.

**Good test prompts are realistic** — file paths, personal context, URLs,
column names, mixed formality, typos, casual speech. **Do NOT write simple
one-step queries** — the model handles those directly and they won't trigger
the skill regardless of description quality.

---

## Phase 5: Run & Evaluate

This is one continuous sequence; don't stop partway. Do NOT use another testing skill.

Create `<skill-name>-workspace/` as a sibling of the skill directory, organized
by iteration, with short descriptive eval names and **multiple runs per config**
so you can measure variance:

```
<skill-name>-workspace/
├── iteration-1/
│   ├── eval-0-<name>/
│   │   ├── eval_metadata.json
│   │   ├── with_skill/run-1/{outputs/,grading.json,timing.json}
│   │   ├── with_skill/run-2/...
│   │   ├── without_skill/run-1/...
│   │   └── without_skill/run-2/...
│   ├── benchmark.json
│   └── eval_viewer.html
├── iteration-2/
└── skill-snapshot/          # when improving an existing skill
```

⚠️ `scripts/aggregate_benchmark.py` discovers config dirs by the presence of
`run-*` subdirectories and reads `run-*/grading.json`. Use `eval-N/<config>/run-K/`
— not a flat layout — or you get empty results.

### Step 1: Spawn all runs (with-skill AND baseline) in the same turn

Launch everything at once so it finishes together. Do not spawn with-skill runs
first and come back for baselines.

**With-skill run** — Hermes `delegate_task()` with `context`:
```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/run-<K>/outputs/
- Outputs to save: <what the user cares about — e.g. "the .docx file">
```

**Baseline run** — same prompt, engine depends on context:
- New skill: no skill at all → `without_skill/run-<K>/outputs/`.
- Improving an existing skill: snapshot it first
  (`cp -r <skill-path> <workspace>/skill-snapshot/`) and point the baseline at
  the snapshot.
- Fall back to `agy --print` for the baseline when `delegate_task` isn't
  available; save stdout to `outputs/response.txt`.

Write `eval_metadata.json` per eval (assertions may be empty for now):
```json
{"eval_id": 0, "eval_name": "descriptive-name", "prompt": "...", "assertions": []}
```

### Step 2: While runs progress, draft assertions

Don't wait idly. Draft **objectively verifiable** assertions with descriptive
names, explain them to the user, and write them into `eval_metadata.json` and
`evals/evals.json`. Subjective skills are graded qualitatively — don't force
assertions onto things needing human judgment.

### Step 3: As runs complete, capture timing

Each delegate completion returns `total_tokens` and `duration_ms`. Save
immediately to `<run-dir>/timing.json` — it isn't persisted elsewhere:
```json
{"total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3}
```

### Step 4: Grade each run

Spawn a grader subagent (or grade inline) that reads `agents/grader.md` and
evaluates each assertion against the outputs. Save `<run-dir>/grading.json`.
The expectations array MUST use exactly `text`, `passed`, `evidence` — the
viewer depends on these field names. For programmatically checkable
assertions, write and run a script via `terminal()` instead of eyeballing —
faster, more reliable, reusable across iterations.

### Step 5: Aggregate into benchmark

```bash
python3 <skill-creator-path>/scripts/aggregate_benchmark.py \
  <workspace>/iteration-N --skill-name "<skill-name>"
```
This writes `benchmark.json` and `benchmark.md` with pass_rate / time / tokens
per configuration, mean ± stddev, and the delta.

### Step 6: Analyst pass

Read the benchmark and surface patterns aggregates hide — assertions that
always pass in both configs (non-discriminating), high-variance evals (possibly
flaky), time/token tradeoffs. See `agents/analyzer.md` ("Analyzing Benchmark
Results") for what to look for. Add findings to `benchmark.json`'s `notes`.

### Step 7: Generate and deliver the eval viewer

```bash
python3 <skill-creator-path>/eval-viewer/generate_review.py \
  <workspace>/iteration-N \
  --skill-name "<skill-name>" \
  --benchmark <workspace>/iteration-N/benchmark.json \
  --static <workspace>/iteration-N/eval_viewer.html
```
For iteration 2+, add `--previous-workspace <workspace>/iteration-<N-1>`.
Use `--static` in headless/CLI contexts; it writes a standalone HTML file.
Use `generate_review.py` rather than hand-writing HTML.

**Deliver to the user:** on a gateway platform (Telegram etc.) reference the
file with the `MEDIA:` path convention; on the CLI give the absolute path.
Tell them: "The viewer has two tabs — 'Outputs' lets you compare each test case
with and without the skill and leave feedback, 'Benchmark' shows the
quantitative comparison (pass rates, timing, tokens). Tell me what you'd change."

### Step 8: Read the feedback

Feedback is saved to `<workspace>/iteration-N/feedback.json`:
```json
{"reviews": [{"run_id": "eval-0-with_skill", "feedback": "missing axis labels", "timestamp": "..."}], "status": "complete"}
```
Empty feedback means it was fine. Focus improvements on test cases with
specific complaints.

---

## Phase 6: Iterate

### How to think about improvements

- **Generalize from feedback** — don't overfit to the few test examples. The
  skill will run many times; if it only works for the tests, it's useless.
- **Keep the prompt lean** — remove what isn't pulling its weight; read the
  transcripts (not just outputs) for wasted effort.
- **Explain the why** — if you're writing ALWAYS/NEVER in caps, reframe with
  reasoning instead.
- **Look for repeated work** — bundle scripts that every run reinvents.
- **Take your time** — draft, then re-read with fresh eyes.

### The loop

1. Apply improvements via `skill_manage(action='patch', ...)`
2. Rerun all test cases into `iteration-<N+1>/`
3. Regenerate the viewer with `--previous-workspace`
4. Wait for feedback, improve again, repeat

Stop when the user is happy, all feedback is empty, or you stop making progress.

---

## Phase 7 (optional): Blind A/B comparison

For "is the new version actually better?", run the blind comparison: hand two
outputs (A and B) to an independent agent without telling it which skill
produced which. Use `agents/comparator.md` for the judging rubric and
`agents/analyzer.md` for the post-hoc "why did the winner win" (unblinding,
reading both skills and transcripts, generating prioritized improvement
suggestions). Write `comparison-N.json` and `analysis.json` (see
`references/schemas.md`). Optional, requires subagents; the human review loop
is usually sufficient.

---

## Phase 8: Description optimization (optional, final step)

The `description` field is the primary trigger mechanism. Optimize it with the
agy-backed loop. (Upstream's `run_eval.py`/`run_loop.py`/`improve_description.py`
are hardwired to `claude -p`; this skill uses `agy` instead.)

### Step 1: Generate trigger eval queries

Create ~20 realistic queries (8-10 should-trigger, 8-10 should-not-trigger):
```json
[
  {"query": "Realistic user prompt that should trigger", "should_trigger": true},
  {"query": "Near-miss that should NOT trigger", "should_trigger": false}
]
```
Negatives must be genuine near-misses, not obviously irrelevant. Queries must
be substantive — one-step queries won't trigger skills regardless of description.

### Step 2: Review with the user

```python
template = read_file("<skill-creator-path>/assets/eval_review.html")
template = template.replace("__EVAL_DATA_PLACEHOLDER__", json.dumps(eval_set))
template = template.replace("__SKILL_NAME_PLACEHOLDER__", skill_name)
template = template.replace("__SKILL_DESCRIPTION_PLACEHOLDER__", description)
write_file("<scratch-dir>/eval_review.html", template)
```
Deliver it (MEDIA: on gateway platforms, path on CLI). The user edits queries,
toggles trigger/no-trigger, then clicks "Export Eval Set" to download `eval_set.json`.

### Step 3: Run the optimization loop

```bash
python3 <skill-creator-path>/scripts/run_description_optimization.py \
  --eval-set eval_set.json \
  --skill-path <path/to/skill> \
  --model "Gemini 3.8 Flash (Medium)" \
  --max-iterations 5 \
  --runs-per-query 3
```
This splits 60% train / 40% held-out test, evaluates the current description
(running each query several times for a reliable trigger rate), proposes
improvements via agy on failures, re-evaluates on train and test, and selects
the best description by **test** score (not train — avoids overfitting). It
updates the SKILL.md frontmatter and writes
`description_optimization_report.{json,html}` (render the HTML report for the user).

### Step 4: Apply the result

Show the user before/after and the scores.

---

## Phase 9: Validate & package

```bash
python3 <skill-creator-path>/scripts/quick_validate.py <skill-dir>
python3 <skill-creator-path>/scripts/package_skill.py <skill-dir> [output-dir]
```
`quick_validate.py` checks frontmatter (name kebab-case ≤64 chars, description
≤1024 chars, no angle brackets, allowed keys incl. Hermes `tags`/`related_skills`).
`package_skill.py` validates then zips the skill into `<name>.skill` (excludes
`__pycache__`, `.pyc`, root `evals/`).

Tell the user the skill is ready and how to use it.

### Shipping it: repo → tap → install → retire

A skill is only usable once it is *installed* — a written directory under `~/.hermes/skills/` that
came from nowhere in particular will be treated as an agent-created skill and is fair game for the
curator. For a skill that is meant to be shared and stable, publish the directory to a git repo and
install from it. Commands, provenance fields and the curator semantics are in
`references/install-and-curate.md`; two rules change what you do next and belong here:

- **A green validator does not prove the skill triggers.** `quick_validate.py` checks frontmatter
  shape only. Confirm the real thing: `hermes skills list --enabled-only`, one matching request in a
  **fresh** session, then check that the skill's `use_count` in `~/.hermes/skills/.usage.json` moved.
- **The repo is the source of truth for an installed skill.** Hand-editing the copy under
  `~/.hermes/skills/` goes nowhere — the next `hermes skills update` overwrites it. Edit the repo,
  push, then update.

When one skill replaces another, **archive** the old one (`hermes curator archive <skill>`), never
delete it — archiving is reversible and the fallback is always available.

---

## Aligning with an upstream skill

When the ask is "align/extend this skill with <upstream>" (e.g. Anthropic's
`skills/skill-creator`) — or to base a new Hermes skill on one from a *different
agent ecosystem* (e.g. OpenClaw's `souls-directory` `soul-md-creator`) — do a
**selective port, not a copy**. Two passes:

1. **Map concepts first when the upstream is another ecosystem** — its concepts
   do not map 1:1 (a file may have no Hermes counterpart; the unit of work may
   differ, e.g. a bare `SOUL.md` vs a whole profile). Verify Hermes' real
   capabilities against `hermes <cmd> --help`, the source under
   `~/.hermes/hermes-agent/`, and the docs before designing; a skill built on
   assumed capabilities references files Hermes does not have.
2. **Classify each upstream file** as *engine-agnostic* (port verbatim) or
   *engine-coupled* (rewrite for Hermes). Engine-coupled = anything that shells
   out to a specific CLI or relies on a host feature Hermes lacks. For upstream
   Anthropic skill-creator this means: `run_eval.py`, `run_loop.py`,
   `improve_description.py` are hardwired to `claude -p` and `.claude/commands/`
   → rewrite on `agy`; `package_skill.py` assumed `scripts.quick_validate`
   import style → fix the import. See `references/upstream-alignment.md` for the
   full classification and procedure.
3. **Record the divergences** in an HTML comment at the end of SKILL.md
   (`<!-- upstream: derived from <repo> <path>. Divergences: ... -->`) so the
   next session knows the source and what was deliberately changed.

Keep the Hermes-specific choices already in the skill (agy engine,
`delegate_task` for runs, `MEDIA:`/CLI-path delivery, Hermes frontmatter keys in
validation). A wholesale replacement breaks them.

---

## Skill provenance — where a skill came from

Before trusting, editing, or replacing a skill, establish whether a human wrote it or the
agent did. Two local files answer it without guessing:

- `~/.hermes/skills/.usage.json` — per skill, `created_at` and `created_by` (`"agent"` vs a
  human author).
- `~/.hermes/skills/.curator_ledger.jsonl` — one JSON record per change: `actor`, `action`
  (`create` / `patch` / `write_file`), `skill`, and `evidence.session_id` naming the session
  that triggered it.

The background self-improvement / curator loop distils a session into a skill on its own, so
a skill can appear mid-conversation with no human involved and no hub install. Treat a
curator-authored skill as an unreviewed first draft: read it before relying on it, and prefer
refining it over authoring a second skill that duplicates it.

## Pitfalls

- **Bundled scripts must run on Hermes's Python with the stdlib only** — do not
  hard-depend on third-party packages (e.g. `import yaml` / PyYAML, which is not
  guaranteed present). Wrap the import in `try/except ImportError` and fall back
  to a minimal stdlib parser for the narrow case you need (e.g. line-based
  `key: value` frontmatter), so a validation or aggregation step never blocks
  the whole workflow on a missing package. Only if you truly need the full
  library, document `pip install <pkg>` as a prerequisite.
- **Bundled scripts that generate HTML/JS must avoid f-string nesting** — on
  Python ≤3.11, JS template literals (`${var}`) inside f-strings raise
  `SyntaxError`. Use raw strings with `.replace()` placeholders.
- **Eval layout must match the scripts** — `eval-N/<config>/run-K/grading.json`.
  A flat layout makes the aggregator produce empty results.
- **grading.json field names are fixed** — `text`, `passed`, `evidence`.
  Renaming them (`name`/`met`/`details`) makes the viewer show empty values.
- **benchmark.json field names are fixed too** — `configuration` (not `config`)
  and `pass_rate` nested under `result`; see `references/schemas.md`.
- **Don't skip the viewer** — generate it *before* revising the skill yourself.
  Get the human in the loop ASAP.
- **Don't skip baseline runs** — without them you can't measure the skill's value.
- **Create eval directories as you go** — don't scaffold every eval dir upfront.
- **timing.json must be captured on completion** — it isn't persisted elsewhere.
- **No nested delegation** — `delegate_task` subagents cannot call `delegate_task`.
- **agy**: always `--print` for non-interactive runs (default 5m timeout; use
  `--print-timeout 10m` for long tasks); verify claimed outputs with
  `read_file()` before reporting; model names are case-sensitive
  (`"Gemini 3.8 Flash (Medium)"`).
- **Assertions must be objectively verifiable** — subjective quality is for
  human review, not automated grading.
- **A test prompt that states the target structure measures the prompt, not the skill.** If the
  eval prompt spells out the method ("organize it into the four sections X/Y/Z", "write it to
  <path>"), an unaided baseline follows the spec just as well, every assertion passes in both
  configurations, and the run reports a zero delta — the whole evaluation budget is spent to
  learn nothing. State the *goal* in the prompt and keep the method in the assertions. If
  baseline and with-skill already score identically, fix the prompts before iterating the skill.
- **For a deliverable that is itself a document** (a persona, a `SOUL.md`, prose, a design), say
  up front that the with/without benchmark is the wrong instrument and the user will judge by
  reading. Skipping Phases 5-8 is legitimate and far cheaper: running the full loop on a writing
  task burns hours to produce a number that cannot discriminate.
- **Never let an evaluation record claim more than it measured.** A run with no delta must not be
  written up as `"status": "complete"` with all-green numbers; duplicated expectation blocks
  padded with generic evidence strings ("content audit confirmed…") are worse than a minimal
  `status: "pending"` placeholder. A truthful stub is the correct artefact for an unrun
  evaluation, and it survives review.
- **Don't research/compare against targets that don't exist as skills** — check
  `skills_list()` first.
- **Never isolate `HERMES_HOME` to make an eval "safe" when the skill drives the Hermes
  CLI** — a fresh `HERMES_HOME` is a *new data root*, and Hermes bootstraps a complete
  Python environment into it: hundreds of MB and many minutes per run, while the eval looks
  hung on a background "preparing dependencies" task and produces its first artefact as a
  0-byte placeholder. Evaluate against the real home instead: record `hermes profile list`
  before starting and remove only the profiles the eval created.
- **Run the baseline before the evaluating agent reads the skill** — a `without_skill` run
  executed after the agent has opened `SKILL.md` answers from the skill while claiming to be
  unaided, and the comparison silently measures nothing. Order the phases explicitly
  (baselines first) or run the baseline in a separate session.
- **A timed-out agy eval run exits 0 and looks like success** — it returns only a
  partial-output warning and no artefacts. Use `--print-timeout 0` for any run that must
  read the skill or write files, and verify by reading the artefacts, never by exit code.

## Verification

Before declaring a skill ready:

1. Tested against at least 2-3 realistic prompts, with baseline runs?
2. The user reviewed outputs via the viewer?
3. At least one iteration of improvement happened?
4. `quick_validate.py` passes?
5. Are there broken references or missing files?

## References

- `references/schemas.md` — JSON schemas: evals, grading, benchmark, comparison, analysis
- `references/upstream-alignment.md` — how to port/align a skill with an upstream (Anthropic, or another agent ecosystem): concept mapping, file classification, engine swaps, verification order
- `agents/grader.md` — how to grade assertions against outputs
- `agents/comparator.md` — blind A/B comparison rubric
- `agents/analyzer.md` — post-hoc analysis + benchmark pattern analysis
- `eval-viewer/generate_review.py` — generate the HTML eval viewer (`--static` for headless)
- `eval-viewer/viewer.html` — the viewer template that generate_review.py fills with embedded eval data
- `assets/eval_review.html` — HTML template for reviewing trigger eval queries
- `scripts/aggregate_benchmark.py` — multi-run aggregation (mean ± stddev, delta)
- `scripts/run_description_optimization.py` — agy-backed trigger-accuracy optimization
- `scripts/generate_report.py` — HTML report for description optimization
- `scripts/quick_validate.py` — frontmatter validation
- `scripts/package_skill.py` — validate + zip a skill for sharing
- `references/install-and-curate.md` — publish a skill to a git repo, install it as a tap, verify it truly triggers (enabled + usage counter), and retire it safely (curator pin vs archive)
- `references/foundry-contribution.md` — land a created skill in the Hermes Skills Foundry: layout, frontmatter, evals fixture, port attribution and licence, running the gate, opening the PR
- The `agy-antigravity-cli` skill for agy CLI usage

<!-- upstream: derived from anthropics/skills skills/skill-creator.
     Divergences: agy instead of `claude -p`; delegate_task instead of Claude
     Code subagents; MEDIA:/CLI path delivery instead of a browser server;
     Hermes frontmatter keys (tags, related_skills) in validation. -->
