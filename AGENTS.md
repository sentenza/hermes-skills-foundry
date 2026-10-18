# AGENTS.md — Hermes Skills Foundry

This file guides coding agents (omp, Claude Code, etc.) working in this repository.

## Quick Start

```bash
python3 scripts/validate.py          # run the gate (CI runs this)
```

## Repository Purpose

Curated, version-pinned skills for Hermes Agent. Every skill must pass four gates:
1. **Structure** — valid `SKILL.md` frontmatter, layout, reference integrity
2. **Behaviour** — `evals/prompts.md` + `evals/results.json` with honest status
3. **Provenance** — attribution header + upstream licence for ports
4. **Compatibility** — `hermes_requires` semver range, works on stock Hermes

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

## Adapter Skills Exception

Skills whose purpose is to pilot an external agent (e.g., `omp`, `agy-antigravity-cli`) may require that tool, but must:
- State dependency + `command -v <tool>` preflight
- Keep binary configurable via env var (`OMP_BIN`, `AGY_BIN`)
- Report plainly when tool absent — never claim success

## References

- Full standard: `docs/standard.md`
- Contribution procedure: `skills/hermes-skill-creator/references/foundry-contribution.md`