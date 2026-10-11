# Hermes Skill Standard

This document defines the normative specification for skills hosted in the Hermes Skills Foundry. All skills admitted to this repository must conform to this standard.

## 1. Skill Directory Layout

Each skill must reside in its own subdirectory under `skills/`:

```text
skills/<skill-name>/
├── SKILL.md
├── distribution.yaml     (optional: distribution and compatibility metadata)
├── LICENSE-<upstream>    (ports only: a copy of the upstream licence text)
├── NOTICE                (ports only: upstream attribution and modification record)
├── references/           (optional: supplementary reference documents)
│   └── ...
├── assets/               (optional: static templates, schemas, and data files)
│   └── ...
├── scripts/              (optional: executable code for deterministic/repetitive tasks)
│   └── ...
├── agents/               (optional: sub-agent role prompts referenced from SKILL.md)
│   └── ...
├── eval-viewer/          (optional: tooling that renders evaluation results for review)
│   └── ...
└── evals/                (required: test-fixture prompts and an honest result status)
    ├── prompts.md
    └── results.json
```

## 2. Naming Conventions

The skill name:
- MUST consist only of lowercase alphanumeric characters and hyphens (`^[a-z0-9][a-z0-9-]*$`).
- MUST start with an alphanumeric character.
- MUST match the enclosing directory name exactly (for example, `skills/hermes-profile-creator/` must define `name: hermes-profile-creator`).

## 3. Frontmatter Specification

Every `SKILL.md` MUST begin with a YAML frontmatter block delimited by opening and closing `---` markers. The frontmatter MUST include:

- `name`: The skill identifier, matching directory naming rules.
- `description`: A concise explanation of at most 1024 characters. It MUST follow the standard trigger-action phrasing:
  `Use when <trigger>. <behaviour>.`
- `tags`: A list of classification tags categorising the skill.

Example:

```yaml
---
name: sample-skill
description: Use when debugging network latency. Diagnoses DNS, route, and TCP socket bottlenecks.
tags:
  - networking
  - diagnostics
---
```

## 4. Hermes Compatibility Declaration

Every skill MUST specify its supported Hermes Agent version range through a `hermes_requires` declaration.

The declaration MAY be placed in either of two locations:
1. Inside `SKILL.md` YAML frontmatter, either as a top-level key (`hermes_requires: ">=0.20"`) or under nested metadata (`metadata.hermes.hermes_requires`).
2. Inside a sibling `distribution.yaml` file located in the skill directory root (`hermes_requires: ">=0.20"`).

Declarations MUST use semver constraints (for example `>=0.20` or `^0.20.1`). Unconstrained values such as `latest` or `*` are prohibited.

## 5. Progressive Disclosure and References

Skills must remain concise. Deep background knowledge, extensive API tables, and code templates should not clutter `SKILL.md` directly. Instead:

- Place secondary documentation in `references/`.
- Place reusable templates, schemas, and static data in `assets/`.
- Place executable code for deterministic or repetitive tasks in `scripts/`.
- Place sub-agent role prompts (referenced from `SKILL.md`) in `agents/`.
- Place tooling that renders evaluation results for human review in `eval-viewer/`.
- Link or reference files using relative paths from the skill root.
- All file paths mentioned under `references/`, `assets/`, `scripts/`, `agents/`, or `eval-viewer/` in `SKILL.md` MUST resolve to valid files on disk.

## 6. Provenance and Attribution for Ports

Skills adapted from external agent harnesses (such as Claude Code, OpenClaw, Codex, or pi) are welcomed, provided they respect copyright:

- An attribution line of the form `adapted from <repo> (<LICENSE>)` MUST appear immediately following the closing `---` of the frontmatter.
- A copy of the upstream licence text MUST be shipped in the skill directory (for example `LICENSE-APACHE-2.0`).
- A `NOTICE` file MUST name the upstream repository, its licence, the derived files, and the nature of the modifications.
- Every file modified from upstream MUST carry a prominent notice that it was changed (for example a header comment).
- Ported skills MUST be rewritten to adhere to Hermes conventions and tool abstractions rather than copied verbatim.
- Content MUST NOT be ported from upstream repositories that lack an explicit open-source licence.

Example:

```text
---
name: sample-port
description: Use when generating changelogs. Formats commits into semantic releases.
tags:
  - git
---
<!-- adapted from upstream-org/repo (MIT) -->

# Sample Port
```

## 7. Evaluation Structure

Every skill MUST include an `evals/` directory containing repeatable verification fixtures:

- Evaluative prompts or invocation scenarios that test skill workflows.
- Expected outputs or acceptance assertions.
- A result record (`results.json`) whose `status` is either `complete`, with a measured pass rate, or `pending`, with the reason it has not been recorded.

A recorded pass rate is required where the skill's output is objectively verifiable (code generation, data extraction, file transforms). Where the deliverable is subjective or is itself a document (a persona, prose, a design), a with/without benchmark cannot discriminate between the two configurations; there an honest `pending` record MUST be used instead of a fabricated or padded result. Never record a pass rate that was not measured.

## 8. Normative Gates

Admission to the repository requires satisfying four mandatory gates:

1. **Structure Gate**: The skill MUST adhere to the directory layout, YAML frontmatter schema, length constraints, naming rules, and reference integrity checked by `scripts/validate.py`.
2. **Behaviour Gate**: The skill MUST provide an actual eval fixture in `evals/` (`prompts.md` and `results.json`). A recorded, measured pass rate is expected for objectively verifiable skills; for document- or judgment-producing skills an honest `pending` status, with the reason stated, satisfies the gate. Fabricated, padded, or non-discriminating results do not.
3. **Provenance Gate**: If the skill is ported, it MUST include a valid attribution header and upstream licence citation immediately beneath the frontmatter.
4. **Compatibility Gate**: The skill MUST declare an explicit, tested `hermes_requires` version constraint.

> The step-by-step procedure for landing a skill in this repository ships with the [`hermes-skill-creator`](../skills/hermes-skill-creator/) skill, at [`references/foundry-contribution.md`](../skills/hermes-skill-creator/references/foundry-contribution.md). This document remains the normative rule; the skill's reference is the operational procedure.
