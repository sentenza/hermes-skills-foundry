<h1 align="center">Hermes Skills Foundry</h1>

<p align="center">
  <strong>Hermes Agent skills that ship with honest evaluation, provenance, and a version-pinned compatibility matrix.</strong>
</p>

<p align="center">
  <a href="https://github.com/sentenza/hermes-skills-foundry/actions/workflows/validate.yml"><img alt="Validate" src="https://github.com/sentenza/hermes-skills-foundry/actions/workflows/validate.yml/badge.svg"></a>
  <img alt="Hermes" src="https://img.shields.io/badge/Hermes-%E2%89%A50.21-purple">
  <img alt="Skills" src="https://img.shields.io/badge/skills-2-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<p align="center">
  <sub>An independent community project — not affiliated with or endorsed by Nous Research.</sub>
</p>

---

## Why another skills repo

Most skill collections optimise for **count**. This one optimises for the thing a list can never give you: **evidence that a skill works, on the Hermes version you actually run.**

Every skill here answers three questions up front.

| Question | Answer you get |
|---|---|
| Does it work? | It ships with an eval fixture and an honest result status — a measured pass rate where one is meaningful, not a promise. |
| Where did it come from? | Authored here, or ported from another harness with explicit attribution and licence. |
| Will it run on my Hermes? | A declared, tested `hermes_requires` version range — not "latest". |

If a skill cannot answer all three, it does not belong in this repo.

---

## What "verified" means here

A skill enters the foundry only if it clears four gates.

| Gate | Check |
|---|---|
| **Structure** | `SKILL.md` frontmatter and layout validated by `scripts/validate.py` |
| **Behaviour** | An eval fixture defined in `evals/`, with a measured pass rate or a documented `pending` status where a benchmark cannot discriminate |
| **Provenance** | Every ported skill carries an `adapted from <repo> (<LICENSE>)` header, the upstream licence, and a `NOTICE` of modifications |
| **Compatibility** | `hermes_requires` declares a Hermes version range the skill was tested against |

Gates 1, 3 and 4 run in CI on every push. Gate 2 lives in the skill's own `evals/` directory and is surfaced in the table below. A recorded pass rate is only meaningful for objectively verifiable skills; document- or judgment-producing skills ship an honest `pending` fixture rather than a fabricated number.

---

## Install a skill into Hermes

Skills install straight from this repo — no clone needed. Hermes pulls the **whole skill
directory** (`SKILL.md`, `references/`, `assets/`, `scripts/`, `agents/`, `eval-viewer/`,
`evals/`), not just `SKILL.md`.

Preview one without installing:

```bash
hermes skills inspect sentenza/hermes-skills-foundry/skills/<skill-name>
```

Install it:

```bash
hermes skills install sentenza/hermes-skills-foundry/skills/<skill-name> --category <category> -y
```

- `--category` chooses the folder under `~/.hermes/skills/` (for example `software-development`);
  without it Hermes picks one.
- `-y` skips the confirmation prompt (needed in TUI mode).

Confirm it is actually live — a passing frontmatter check says nothing about whether the skill is
installed or enabled:

```bash
hermes skills list --enabled-only      # what a session will really load
```

Register the repo as a source if you want `update` to track it:

```bash
hermes skills tap add sentenza/hermes-skills-foundry
```

After a push to this repo, refresh your installed copy — a push is not a deploy, and the repo is the
source of truth:

```bash
hermes skills update <skill-name>
```

Do not edit the installed copy under `~/.hermes/skills/` in place: the next `update` overwrites it.
Change the repo here, push, then update.

### Clone the whole foundry

Useful if you want to read the skills, run the gate, or contribute:

```bash
git clone https://github.com/sentenza/hermes-skills-foundry.git
cd hermes-skills-foundry
python3 scripts/validate.py          # run the same gate CI runs
```

You can also point Hermes at a single skill directory, or copy it into `~/.hermes/skills/`.

---

## Skills

| Skill | What it does | Hermes | Evals |
|---|---|---|---|
| [`hermes-profile-creator`](skills/hermes-profile-creator/) | Create and edit Hermes profiles and `SOUL.md`: persona design, profile scaffolding, distribution packaging | ≥0.21 | — |
| [`hermes-skill-creator`](skills/hermes-skill-creator/) | Create, test, and iteratively improve Hermes skills: drafting, eval runs with/without the skill, benchmarking, review viewer | ≥0.21 | — |

> Add one row per skill. Keep the "What it does" cell to one line — the detail belongs in the skill itself.

---

## Create a skill, then contribute it

The [`hermes-skill-creator`](skills/hermes-skill-creator/) skill is the foundry's own authoring
tool: it walks the full lifecycle — intent capture, drafting, test cases, evaluation with and
without the skill, iteration, packaging.

```bash
hermes skills install sentenza/hermes-skills-foundry/skills/hermes-skill-creator --category software-development -y
```

Then ask it to "create a skill for X". Once the skill is drafted and tested, land it here:

- follow the four gates in [`docs/standard.md`](docs/standard.md);
- the concrete procedure — layout, frontmatter, evals fixture, port attribution and licence,
  running the gate, opening the PR — is in the skill's own
  [`references/foundry-contribution.md`](skills/hermes-skill-creator/references/foundry-contribution.md);
- add a one-line row to the skills table above, then open a PR.

```bash
git clone https://github.com/sentenza/hermes-skills-foundry.git
cd hermes-skills-foundry
python3 scripts/validate.py          # CI runs this exact gate
```

That procedure ships inside the skill's `references/` on purpose: an installed skill has no
access to this repo's `docs/`, so anything its workflow needs at runtime travels with it. The
foundry docs *link* to those references rather than copying them — one source, no drift.

---

## The standard

The rules a skill must follow to live here — frontmatter shape, `references/` layout, the attribution header, the `hermes_requires` range, and how evals are structured — are written down in [`docs/standard.md`](docs/standard.md).

That document is the actual product of this repo. The skills are what it produces.

---

## Borrowing from other harnesses

Skills are portable. The Agent Skills open standard (`SKILL.md` + `references/`) is shared with OpenClaw, the pi coding agent, Claude Code, Codex and others, so good work elsewhere can be brought here — **as a port, never a mirror.**

A ported skill must:

1. carry an `adapted from <repo> (<LICENSE>)` header right under the frontmatter;
2. ship the upstream licence text in its own directory and a `NOTICE` recording the upstream, the licence, and the modifications;
3. mark each file it changed with a prominent change notice;
4. be rewritten to Hermes' conventions, not copied verbatim;
5. pass all four gates, exactly like an authored skill.

The upstream project keeps its licence; the credit stays visible. Nothing is ported from a repo that carries no licence.

---

## Contributing

Pull requests are welcome, with one rule: **the gate comes before the skill.** A new skill that does not pass `scripts/validate.py` and does not declare a `hermes_requires` range will not be merged, however good it is.

A contribution should contain:

- `skills/<name>/SKILL.md` with valid frontmatter;
- `skills/<name>/evals/` — the prompts plus a `results.json` that is either a measured pass rate or an honest `pending` with the reason it was not run;
- an attribution header if it is a port;
- a one-line row added to the skills table above.

Contributions are accepted under this repo's MIT licence (inbound = outbound) — there is no CLA to sign.

---

## Roadmap

- [x] Repository skeleton
- [x] `docs/standard.md` — the written standard
- [x] CI gate wired to `scripts/validate.py`
- [x] `hermes-profile-creator` — profile and `SOUL.md` creation and editing
- [x] `hermes-skill-creator` — skill creation, evaluation, and iteration
- [ ] Per-skill eval badges

---

## Licence

MIT — see [`LICENSE`](LICENSE).

Ported skills keep their upstream licence. A port ships that licence in its own directory (for example `LICENSE-APACHE-2.0`) alongside a `NOTICE` recording the upstream and the modifications, and credits it in the skill's attribution header. Licensing is therefore per skill: the foundry is MIT, while an individual ported skill may carry its upstream licence (Apache-2.0, for instance).

---

## Credits

Built for [Hermes Agent](https://github.com/NousResearch/hermes-agent), the self-improving agent.

