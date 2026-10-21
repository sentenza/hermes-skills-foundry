# AGENTS.md — Hermes Skills Foundry

Repository rules for any AI agent working here. The behavioral rules (how to work) live in [HERMES.md](HERMES.md); this file is the *what this repository requires*. Read both.

## Quick Start

```bash
python3 scripts/validate.py                    # admission gate (CI runs this)
python3 scripts/validate.py skills/<name>       # gate for one skill
python3 scripts/test_validate.py               # gate unit tests
python3 -m unittest discover -s tests           # skill script tests
```

A change is done when the gate passes **and** the tests pass. Both are stdlib-only — no install step.

## Repository Purpose

Curated, version-pinned skills for Hermes Agent. Every skill must pass five gates:
1. **Structure** — valid `SKILL.md` frontmatter, layout, reference integrity
2. **Behaviour** — `evals/prompts.md` + `evals/results.json` with honest status
3. **Provenance** — attribution header + upstream licence for ports
4. **Compatibility** — `hermes_requires` semver range, works on stock Hermes
5. **Secret hygiene** — no credential files (`.env`, `*.pem`) or credential literals in a skill directory

## Skill Directory Layout

```
skills/<name>/
├── SKILL.md              # required: frontmatter + instructions
├── distribution.yaml     # optional: compatibility metadata
├── evals/
│   ├── prompts.md        # required: test scenarios
│   └── results.json      # required: status (complete|manual|pending)
├── references/           # optional: deep docs
├── assets/               # optional: templates, schemas
├── scripts/              # optional: deterministic code
├── agents/               # optional: subagent prompts
└── eval-viewer/          # optional: results viewer
```

## Frontmatter Requirements

```yaml
---
name: skill-name              # matches directory, ^[a-z0-9][a-z0-9-]*$
description: Use when ...     # ≤1024 chars, trigger-action phrasing
tags: [tag1, tag2]
hermes_requires: ">=0.21"     # semver constraint, no "latest"
---
```

Ported skills need `<!-- adapted from <repo> (LICENSE) -->` immediately after `---`.

## Eval Status Values

- `complete` — measured pass rate (objectively verifiable skills)
- `manual` — human-verified, includes `reason` + `tested_hermes_version`
- `pending` — not run, includes `reason` explaining why

Never fabricate pass rates.

## Common Tasks

| Task | Command |
|------|---------|
| Validate all skills | `python3 scripts/validate.py` |
| Validate one skill | `python3 scripts/validate.py skills/<name>` |
| Inspect skill | `hermes skills inspect sentenza/hermes-skills-foundry/skills/<name>` |
| Install skill locally | `hermes skills install sentenza/hermes-skills-foundry/skills/<name> -y` |

## Conventions

- Edit `README.md` skills table when adding/removing skills
- Update Hermes badge in README when `hermes_requires` floor changes
- Keep `CONTRIBUTING.md` and `docs/standard.md` in sync
- No empty directories (validation ignores them but they're noise)
- Commit messages: `feat(skills): ...`, `fix(gate): ...`, etc.
- Ship dependencies as standard library where possible — a skill that needs `pip install` fails on a stock host
- Scripts live in the skill's `scripts/` directory and stay runnable from the installed skill path

## Adapter Skills Exception

Skills whose purpose is to pilot an external agent (e.g., `omp`, `agy-antigravity-cli`) may require that tool, but must:
- State dependency + `command -v <tool>` preflight
- Keep binary configurable via env var (`OMP_BIN`, `AGY_BIN`)
- Report plainly when tool absent — never claim success

## References

- Behavioral rules: [HERMES.md](HERMES.md)
- Full standard: `docs/standard.md`
- Contribution procedure: `skills/hermes-skill-creator/references/foundry-contribution.md`
