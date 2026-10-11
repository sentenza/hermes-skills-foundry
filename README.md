<h1 align="center">Hermes Skills Foundry</h1>

<p align="center">
  <strong>Hermes Agent skills that ship with tests, provenance, and a version-pinned compatibility matrix.</strong>
</p>

<p align="center">
  <a href="https://github.com/sentenza/hermes-skills-foundry/actions/workflows/validate.yml"><img alt="Validate" src="https://github.com/sentenza/hermes-skills-foundry/actions/workflows/validate.yml/badge.svg"></a>
  <img alt="Hermes" src="https://img.shields.io/badge/Hermes-%E2%89%A50.20-purple">
  <img alt="Skills" src="https://img.shields.io/badge/skills-1-blue">
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
| Does it work? | It ships with evals and a recorded pass rate — not a promise. |
| Where did it come from? | Authored here, or ported from another harness with explicit attribution and licence. |
| Will it run on my Hermes? | A declared, tested `hermes_requires` version range — not "latest". |

If a skill cannot answer all three, it does not belong in this repo.

---

## What "verified" means here

A skill enters the foundry only if it clears four gates.

| Gate | Check |
|---|---|
| **Structure** | `SKILL.md` frontmatter and layout validated by `scripts/validate.py` |
| **Behaviour** | Evals defined and passing; the pass rate is recorded per skill |
| **Provenance** | Every ported skill carries an `adapted from <repo> (<LICENSE>)` header |
| **Compatibility** | `hermes_requires` declares a Hermes version range the skill was tested against |

Gates 1, 3 and 4 run in CI on every push. Gate 2 is recorded in the skill's own `evals/` directory and surfaced in the table below.

---

## Install

**One skill** — install it straight from this repo's path:

```bash
hermes skills install sentenza/hermes-skills-foundry/skills/<skill-name>
```

**Clone the whole foundry** — useful if you want to read, run the evals, or contribute:

```bash
git clone https://github.com/sentenza/hermes-skills-foundry.git
cd hermes-skills-foundry
python3 scripts/validate.py          # run the same gate CI runs
```

Then point Hermes at a single skill directory, or copy it into `~/.hermes/skills/`.

---

## Skills

| Skill | What it does | Hermes | Evals |
|---|---|---|---|
| `hermes-profile-creator` (planned) | Create and edit Hermes profiles and `SOUL.md`: persona design, profile scaffolding, distribution packaging | ≥0.20 | — |

> Add one row per skill. Keep the "What it does" cell to one line — the detail belongs in the skill itself.

---

## The standard

The rules a skill must follow to live here — frontmatter shape, `references/` layout, the attribution header, the `hermes_requires` range, and how evals are structured — are written down in [`docs/standard.md`](docs/standard.md).

That document is the actual product of this repo. The skills are what it produces.

---

## Borrowing from other harnesses

Skills are portable. The Agent Skills open standard (`SKILL.md` + `references/`) is shared with OpenClaw, the pi coding agent, Claude Code, Codex and others, so good work elsewhere can be brought here — **as a port, never a mirror.**

A ported skill must:

1. carry an `adapted from <repo> (<LICENSE>)` header right under the frontmatter;
2. be rewritten to Hermes' conventions, not copied verbatim;
3. pass all four gates, exactly like an authored skill.

The upstream project keeps its licence; the credit stays visible. Nothing is ported from a repo that carries no licence.

---

## Contributing

Pull requests are welcome, with one rule: **the gate comes before the skill.** A new skill that does not pass `scripts/validate.py` and does not declare a `hermes_requires` range will not be merged, however good it is.

A contribution should contain:

- `skills/<name>/SKILL.md` with valid frontmatter;
- `skills/<name>/evals/` — at least the prompts, ideally with recorded results;
- an attribution header if it is a port;
- a one-line row added to the skills table above.

Contributions are accepted under this repo's MIT licence (inbound = outbound) — there is no CLA to sign.

---

## Roadmap

- [x] Repository skeleton
- [x] `docs/standard.md` — the written standard
- [x] CI gate wired to `scripts/validate.py`
- [ ] `hermes-profile-creator` — profile and `SOUL.md` creation and editing
- [ ] Per-skill eval badges

---

## Licence

MIT — see [`LICENSE`](LICENSE).

Ported skills keep their upstream licence, credited in the skill's attribution header.

---

## Credits

Built for [Hermes Agent](https://github.com/NousResearch/hermes-agent), the self-improving agent.

