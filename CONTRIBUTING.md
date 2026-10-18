# Contributing to Hermes Skills Foundry

## Welcome and Scope

Hermes Skills Foundry is a curated repository of tested, version-pinned skills for Hermes Agent. Contributions of new skills, improvements to existing skills, documentation refinements, and tooling updates are welcome. The foundry prioritises verification, reproducible evals, and transparent provenance over raw skill count.

## The One Rule

The gate comes before the skill. A contribution that does not pass `scripts/validate.py` or fails to satisfy compatibility and provenance requirements will not be merged, regardless of how useful the skill might be.

## What a Contribution Must Contain

Every new skill contribution must include:

- A dedicated skill directory under `skills/<name>/` containing `SKILL.md` with complete YAML frontmatter.
- An `evals/` directory within the skill folder, containing evaluation prompts and a `results.json` (a measured pass rate, or an honest `pending` status with the reason).
- An attribution header placed immediately under the frontmatter if the skill is ported from another harness.
- A one-line entry added to the Skills table in `README.md`.

## Dev Setup

The repository requires only standard Python 3. No third-party dependencies or virtual environments are required.

To run the local verification gate before submitting changes:

```bash
python3 scripts/validate.py
```

Pass `--verbose` to inspect detailed validation output.

## The Four Gates

All skills must pass four distinct gates before admission:

- **Structure**: `SKILL.md` frontmatter, naming conventions, and internal file references must validate cleanly via `scripts/validate.py`.
- **Behaviour**: An eval fixture must be defined in `evals/` (`prompts.md` and `results.json`). A measured pass rate is documented for objectively verifiable skills; where the deliverable is itself a document or a judgement, an honest `pending` status with the reason satisfies the gate.
- **Provenance**: Any ported content must cite its origin repository and upstream licence, ship that licence text, and include a `NOTICE` of modifications.
- **Compatibility**: Every skill must declare an explicit `hermes_requires` range tested against supported Hermes releases.
- **Adapter skills (exception)**: a skill whose declared purpose is to pilot or operate an external coding agent may depend on it — but it must state the dependency and a `command -v <tool>` preflight up front, keep the engine configurable (for example `AGY_BIN`), and report plainly — never a success claim — when the tool is absent.

> The practical, step-by-step procedure for contributing a skill ships with the `hermes-skill-creator` skill: [`skills/hermes-skill-creator/references/foundry-contribution.md`](skills/hermes-skill-creator/references/foundry-contribution.md). This guide is the rule; that reference is the procedure.

## Running Evaluations

The `evals/` directory in each skill contains `prompts.md` (test scenarios) and `results.json` (recorded status: `complete` | `manual` | `pending`).

Gate checks: `evals/` exists with both files; `results.json` has valid schema and honest status; `pending` requires `reason`; `manual`/`complete` require `tested_hermes_version` and should include `reason`.

Full procedure: [`skills/hermes-skill-creator/references/foundry-contribution.md`](skills/hermes-skill-creator/references/foundry-contribution.md)
## Porting Rules


Skills adapted from external agent frameworks (such as Claude Code, OpenClaw, Codex, or pi) are welcome, subject to five strict requirements:

1. Place an `adapted from <repo> (<LICENSE>)` header immediately under the YAML frontmatter.
2. Ship the upstream licence text in the skill directory and a `NOTICE` naming the upstream, its licence, the derived files, and the modifications.
3. Mark every modified file with a prominent change notice.
4. Rewrite instructions and tool patterns to Hermes conventions rather than copying upstream text verbatim.
5. Never port material from a repository that carries no licence.

## Licence and Inbound Equals Outbound

All contributions to this repository are submitted under the MIT Licence (inbound = outbound). Contributors do not need to sign a Contributor Licence Agreement (CLA). Ported skills retain their original upstream licences, acknowledged in their attribution headers.

## Commit and Pull-Request Conventions

- Write clear, imperative commit messages (for example, `feat(skills): add hermes-profile-creator` or `fix(gate): handle nested metadata`).
- Open pull requests against the default repository branch.
- Keep pull requests focused on a single skill or functional change.
- Ensure `python3 scripts/validate.py` passes cleanly on your branch before opening the pull request.

## How to Report a Problem

To report a bug, request a skill, or suggest a change to the foundry standard, open an issue on GitHub at `https://github.com/sentenza/hermes-skills-foundry/issues`. Provide reproducible details, Hermes version information, and relevant terminal logs where applicable.
