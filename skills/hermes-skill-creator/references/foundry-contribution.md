# Contributing a skill to the Hermes Skills Foundry

How to land a skill you created with this skill-creator into the foundry repository.

- **Repository:** <https://github.com/sentenza/hermes-skills-foundry>
- **Normative spec:** <https://github.com/sentenza/hermes-skills-foundry/blob/main/docs/standard.md>
- **Contribution guide:** <https://github.com/sentenza/hermes-skills-foundry/blob/main/CONTRIBUTING.md>

If this file and the standard disagree, **the standard wins** — this is the step-by-step
procedure, the standard is the rule. This file ships inside the skill on purpose: an installed
skill has no access to the foundry's `docs/`, so anything the workflow needs at runtime travels
with it.

## 1. Place the skill in the repository

The skill lives at `skills/<skill-name>/`. The directory name MUST equal the frontmatter `name`
and match `^[a-z0-9][a-z0-9-]*$`.

```text
skills/<skill-name>/
├── SKILL.md
├── distribution.yaml     (optional)
├── references/ assets/ scripts/ agents/ eval-viewer/   (optional, as needed)
└── evals/
    ├── prompts.md
    └── results.json
```

## 2. Frontmatter

- `name` — matches the directory.
- `description` — `Use when <trigger>. <behaviour>.` in at most 1024 characters.
- `tags` — classification tags.
- `hermes_requires: ">=X.Y"` — an explicit semver constraint (never `latest` or `*`).

## 2b. No external requirement

A skill MUST NOT depend on an external code assistant or CLI to accomplish its
job. The Hermes agent is the engine. If a skill optionally integrates such a
tool, make it opt-in and configurable, document it, and make sure the skill still
works — and says so honestly — when the tool is not installed.

**Adapter skills (exception).** A skill whose declared purpose is to pilot or operate an
external coding agent is the one legitimate exception to §2b. It MAY require that agent,
provided it (a) states the dependency explicitly with a `command -v <tool>` preflight as its
first workflow step, (b) keeps the engine configurable — an explicit binary/env override such
as `AGY_BIN`, never a hardcoded absolute path — and (c) documents that it is inert without the
tool and reports that plainly instead of a success claim. It must never report success when the
tool is absent.

## 3. Evals fixture

Ship `evals/prompts.md` and `evals/results.json`. The result `status` is either `complete`, with
a **measured** pass rate, or `pending`, with the reason it was not run. A measured rate is
required where the output is objectively verifiable; for document- or judgment-producing skills
an honest `pending` is correct. Never record a number you did not measure.

## 4. Ports: attribution, licence, and change notices

Only for skills adapted from another source:

- an attribution line immediately under the frontmatter: `<!-- adapted from <repo> (<LICENSE>) -->`;
- a copy of the upstream licence text in the skill directory (for example `LICENSE-APACHE-2.0`);
- a `NOTICE` naming the upstream, its licence, the derived files, and the modifications;
- a prominent change notice in every file modified from upstream;
- divergences recorded in a trailing HTML comment at the end of `SKILL.md`.

Never port from a repository that carries no licence.

## 5. Run the gate

```bash
python3 scripts/validate.py -v      # must end with "N passed, 0 failed"
```

## 6. Register the skill

Add a one-line row to the skills table in `README.md`, and bump the `skills-N` badge if the count
changed.

## 7. Open the pull request

Branch `feat/<skill-name>`; CI runs the same `scripts/validate.py` on every push and PR, so the
PR must be green. Keep the PR to a single skill or one functional change.

## Before you call it done

- the gate is green and `scripts/quick_validate.py` passes on the skill;
- bundled scripts compile (`python3 -m compileall`);
- the skill has a row in the README;
- for a port: licence text, `NOTICE`, and per-file change notices are present.
