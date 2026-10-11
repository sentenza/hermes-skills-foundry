# Aligning the skill with an upstream

How to extend/align this skill (or another Hermes skill) with an upstream
version. Two flavours, same discipline:

- **Same engine family, different host** — e.g. Anthropic's
  `anthropics/skills` → `skills/skill-creator`. Files are engine-agnostic or
  engine-coupled (Claude Code / Claude.ai / Cowork).
- **Different agent ecosystem** — e.g. OpenClaw's `souls-directory`
  `soul-md-creator`. Here the *concepts themselves* diverge, not just the
  engine: the upstream may have a file Hermes lacks, and the unit of work may be
  different (a bare `SOUL.md` upstream vs a whole Hermes profile).

Do a **selective port**, never a wholesale copy: a straight copy breaks the
Hermes-specific choices.

## Procedure

1. **Fetch the upstream tree, not the rendered page.** The GitHub web UI and
   `web_extract` may fail on these repos. Get the file list from the API and the
   raw bytes from `raw.githubusercontent.com`:
   ```bash
   # file list
   curl -sSL "https://api.github.com/repos/<org>/<repo>/git/trees/main?recursive=1"
   # raw file
   curl -sSL "https://raw.githubusercontent.com/<org>/<repo>/main/<path>" -o <file>
   ```
   Download the whole skill subtree into scratch before comparing — do not
   reason from a truncated page.

2. **Map concepts before porting** (mandatory when the upstream is a different
   agent ecosystem). Its concepts do not map 1:1 onto Hermes: a name may have no
   counterpart (OpenClaw `IDENTITY.md` → no Hermes file), and the unit of work
   may differ (bare `SOUL.md` vs a whole Hermes profile with `SOUL.md` +
   `config.yaml` + `skills/` + a `distribution.yaml` manifest). Verify what the
   target can actually do against ground truth — `hermes <cmd> --help`, `grep`
   the source under `~/.hermes/hermes-agent/`, and the official docs — then
   write the mapping table (upstream concept → target equivalent, or "no
   equivalent"). Designing against assumed capabilities produces a skill that
   references files and commands Hermes does not have.

3. **Classify every upstream file** as engine-agnostic (port verbatim) or
   engine-coupled (rewrite). Grep the scripts for the engine and host markers
   (`claude`, `subprocess`, `.claude/commands`, `webbrowser`, `nous`, `agy`).

4. **Port the engine-agnostic files verbatim**, then **adapt the coupled ones**.

5. **Verify before declaring done**: `python3 -m py_compile` on every ported
   script; run each standalone script against a small synthetic fixture
   (build a fake `eval-N/<config>/run-K/` workspace with dummy `grading.json` /
   `timing.json` / `eval_metadata.json` and confirm the aggregator and viewer
   produce real output); run the validator on the skill itself. Only then report
   the port as working.

6. **Record divergences** in an HTML comment at the end of SKILL.md.

## Classification for Anthropic skill-creator

Port **verbatim** (engine-agnostic, stdlib-only or pure prose):

- `references/schemas.md` — pure JSON reference
- `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md` — subagent
  role prompts
- `eval-viewer/generate_review.py` + `eval-viewer/viewer.html` — stdlib HTTP/HTML;
  use `--static` for headless/CLI (writes a standalone HTML file, no server)
- `assets/eval_review.html` — placeholder template for trigger-eval review
- `scripts/aggregate_benchmark.py` — multi-run aggregation (mean ± stddev, delta)
- `scripts/generate_report.py` — HTML report from optimizer JSON
- `scripts/utils.py` — `parse_skill_md` helper

Rewrite for Hermes (engine-coupled):

- `scripts/run_eval.py`, `scripts/run_loop.py`, `scripts/improve_description.py`
  — hardwired to `claude -p` and `.claude/commands/`. Replace with the
  agy-backed `scripts/run_description_optimization.py` (splits train/test,
  `--runs-per-query` for a reliable trigger rate, picks best by *test* score,
  emits a `generate_report.py`-compatible history + HTML).
- `scripts/package_skill.py` — fix the import (`sys.path.insert` to the sibling
  dir instead of `from scripts.quick_validate import ...`) so it runs both as a
  script and as a module.
- `scripts/quick_validate.py` — allow Hermes frontmatter keys (`tags`,
  `related_skills`, ...) in addition to the upstream set; drop the hard `yaml`
  dependency (PyYAML is not guaranteed present) with a stdlib fallback.

## Layout / contract details that carry over

- Multi-run workspace layout the scripts expect:
  `eval-N/<config>/run-K/{outputs/,grading.json,timing.json}` with
  `eval_metadata.json` at `eval-N/`. The viewer searches `eval_metadata.json` in
  the run dir, its parent, and its grandparent — keep that grandparent lookup or
  the multi-run layout shows no prompts.
- `grading.json` expectation fields are fixed at exactly `text` / `passed` /
  `evidence`; `benchmark.json` uses `configuration` (not `config`) and nests
  `pass_rate` under `result`. The viewer reads these names literally.
