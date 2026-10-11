# Contributing to Hermes Skills Foundry

## Welcome and Scope

Hermes Skills Foundry is a curated repository of tested, version-pinned skills for Hermes Agent. Contributions of new skills, improvements to existing skills, documentation refinements, and tooling updates are welcome. The foundry prioritises verification, reproducible evals, and transparent provenance over raw skill count.

## The One Rule

The gate comes before the skill. A contribution that does not pass `scripts/validate.py` or fails to satisfy compatibility and provenance requirements will not be merged, regardless of how useful the skill might be.

## What a Contribution Must Contain

Every new skill contribution must include:

- A dedicated skill directory under `skills/<name>/` containing `SKILL.md` with complete YAML frontmatter.
- An `evals/` directory within the skill folder, containing evaluation prompts and recorded results.
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
- **Behaviour**: Realistic evals must be defined in `evals/`, executed, and documented with verifiable pass criteria.
- **Provenance**: Any ported content must clearly cite its origin repository and upstream licence.
- **Compatibility**: Every skill must declare an explicit `hermes_requires` range tested against supported Hermes releases.

## Porting Rules

Skills adapted from external agent frameworks (such as Claude Code, OpenClaw, Codex, or pi) are welcome, subject to three strict requirements:

1. Place an `adapted from <repo> (<LICENSE>)` header immediately under the YAML frontmatter.
2. Rewrite instructions and tool patterns to Hermes conventions rather than copying upstream text verbatim.
3. Never port material from a repository that carries no licence.

## Licence and Inbound Equals Outbound

All contributions to this repository are submitted under the MIT Licence (inbound = outbound). Contributors do not need to sign a Contributor Licence Agreement (CLA). Ported skills retain their original upstream licences, acknowledged in their attribution headers.

## Commit and Pull-Request Conventions

- Write clear, imperative commit messages (for example, `feat(skills): add hermes-profile-creator` or `fix(gate): handle nested metadata`).
- Open pull requests against the default repository branch.
- Keep pull requests focused on a single skill or functional change.
- Ensure `python3 scripts/validate.py` passes cleanly on your branch before opening the pull request.

## How to Report a Problem

To report a bug, request a skill, or suggest a change to the foundry standard, open an issue on GitHub at `https://github.com/sentenza/hermes-skills-foundry/issues`. Provide reproducible details, Hermes version information, and relevant terminal logs where applicable.
