# Installing, updating, and retiring a skill

Depth for the half that comes after a skill is written: getting it out of a repo, into Hermes,
proven live, and back out again without losing it.

## Publish to a repo, then tap and install

A shared skill lives in a repo as `<repo>/skills/<name>/` — `SKILL.md` plus `references/`,
`assets/`, `evals/`. Registering the repo and installing from it:

```bash
hermes skills tap add <owner>/<repo>                    # register the repo as a skill source
hermes skills tap list                                  # shows the repo and the path it exposes
hermes skills inspect <owner>/<repo>/skills/<name>      # preview; installs nothing
hermes skills install <owner>/<repo>/skills/<name> --category <cat> -y
```

- `install` pulls the **whole skill directory**, not just `SKILL.md` — `references/`, `assets/`
  and `evals/` come with it. Installing from a bare `SKILL.md` URL gets you one file and a skill
  whose reference links dangle.
- `--category` picks the folder under `~/.hermes/skills/`; without it the installer chooses.
- A hub install is scanned like any third-party skill; `--force` overrides a blocked scan verdict
  (don't — fix the content instead).

`hermes skills tap list` reports the path the repo exposes (conventionally `skills/`), which is what
the identifier in `install` is built from.

## Update after a push

```bash
hermes skills update <name>      # re-pulls from the tap the skill came from
```

The installed copy does not track the repo by itself. A push is not a deploy: until `update` runs,
Hermes still loads the old copy.

## Verify it is actually live

Shape checks are not behaviour checks — a passing frontmatter validator says nothing about whether
the skill is installed, enabled, or ever selected.

```bash
hermes skills list --enabled-only      # what a session will really load
hermes skills list --source hub        # confirm provenance
```

Then trigger it for real: one request in a **fresh** session that its description should match
(a fresh session matters — an already-running one built its skill list at startup), and confirm the
counter moved:

```bash
python3 -c "import json;d=json.load(open('$HOME/.hermes/skills/.usage.json'));print(d['<name>'])"
```

A rising `use_count` / `view_count` proves the skill was loaded and used. An unchanged counter after
a request that should have triggered it means the *description*, not the body, needs work.

## Provenance and state

`~/.hermes/skills/.usage.json` holds, per skill: `created_by` (`agent` = written by Hermes itself,
`installed` = came from a hub or tap), `state` (`active` / `archived`), `pinned`, and the use/view
counters. It is the fastest way to answer "who made this, and is it live?". Pair it with
`~/.hermes/skills/.curator_ledger.jsonl` for *how* it changed.

## Curator: what it does and does not manage

- The curator manages **agent-created skills only**. Bundled and hub-installed skills are never
  touched — no stale-marking, no archiving, no consolidation.
- Therefore `hermes curator pin <skill>` **refuses an installed skill**: "only agent-created skills
  participate in curation". The refusal is not an error to work around — an installed skill already
  has the protection a pin would grant, and a pin is only meaningful for a skill the agent authored
  itself. Say this plainly rather than hunting for another way to pin.
- Editing an installed copy in place is the trap: the repo is the source of truth and the next
  `update` overwrites your edit. Change the repo, push, then update.

## Retire a skill without deleting it

```bash
hermes curator archive <skill>     # → ~/.hermes/skills/.archive/<name>; stops loading
hermes curator restore <skill>     # brings it back
```

Archiving is the reversible move and the right default when one skill replaces another. Never delete
a skill to take it out of the catalogue. Confirm afterwards with `hermes skills list --enabled-only`:
the retired name should be gone and exactly one replacement should remain — a duplicate is the
failure mode this exists to prevent.
