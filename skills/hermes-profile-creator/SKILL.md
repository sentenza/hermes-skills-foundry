---
name: hermes-profile-creator
description: Use when creating or editing a Hermes profile, designing a SOUL.md, giving the agent a personality, packaging, sharing, or installing a profile, or adapting an OpenClaw soul to Hermes. Guides profile creation, soul persona synthesis, configuration scaffolding, and distribution packaging.
tags:
  - hermes
  - profile
  - soul
  - persona
  - distribution
hermes_requires: ">=0.21"
---
<!-- adapted from thedaviddias/souls-directory (MIT) -->

# Hermes Profile Creator

## Overview

A Hermes profile is an isolated agent instance with its own identity (`SOUL.md`), configuration, skills, and memory. The default profile resides at `~/.hermes/` (`$HERMES_HOME`), while named profiles reside under `~/.hermes/profiles/<name>/`.

`SOUL.md` is injected verbatim into slot #1 of the system prompt, replacing the default identity, and acts as the profile marker on disk. Persona design should establish durable principles (`Identity / Style / Avoid / Defaults`) governing voice, directness, and judgment without cluttering the soul with project-specific instructions.

## When to use

- Creating or editing a Hermes profile with custom behavior or tools.
- Editing the built-in default profile's persona (`$HERMES_HOME/SOUL.md`) — the running agent's own identity.
- Designing a `SOUL.md` persona from scratch or refining an existing voice.
- Giving an agent a distinct personality without adding rule bloat.
- Packaging, sharing, or installing reusable profile distributions.
- Adapting an OpenClaw workspace soul into Hermes format.

## References

- [references/hermes-official.md](references/hermes-official.md): Read this when configuring `SOUL.md` injection, lifecycle fallback, prompt-injection scanning, or separating persona from `AGENTS.md`.
- [references/profile-anatomy.md](references/profile-anatomy.md): Read this when working with the profile directory layout, marker validation, or the full `hermes profile` CLI command surface.
- [references/distribution-publishing.md](references/distribution-publishing.md): Read this when packaging, publishing, or installing profiles using `distribution.yaml` manifests and environment requirements.
- [references/persona-research-heuristics.md](references/persona-research-heuristics.md): Read this when designing durable persona principles, establishing anti-sycophancy guardrails, or stress-testing a soul against edge scenarios.

## Assets

- [assets/soul-template-hermes.md](assets/soul-template-hermes.md): Copy `assets/soul-template-hermes.md` to `$HERMES_HOME/SOUL.md` and fill it in.
- [assets/soul-example-researcher.md](assets/soul-example-researcher.md): Worked example of a calibrated, behaviour-first researcher persona.
- [assets/distribution.yaml.template](assets/distribution.yaml.template): Copy `assets/distribution.yaml.template` to `distribution.yaml` at repository root and fill it in.

## Workflow

Follow this seven-step process to synthesize, scaffold, and package a profile:

### 1. Establish the Target
Define the profile's role and boundaries through 3–5 high-leverage questions:
- What is the primary operational role (colleague, specialist, coach, or task runner)?
- What must feel noticeably different from a standard assistant?
- Default bias: ask-first or act-first?
- Disagreement posture: when should it push back versus yield?
- What failure mode or persona trap must it never become?

### 2. Gather Contrast, Not Adjectives
Avoid generic adjectives like "helpful" or "smart". Pose either/or contrast choices:
- Blunt and concise vs. diplomatic and explanatory?
- Proactive suggestions vs. strict task execution?
- Playful and informal vs. restrained and rigorous?

### 3. Synthesize Behaviour-First Principles
Organize `SOUL.md` using the behaviour-first heading spine:
- **Personality**: One line: who the agent is, not what it does.
- **Response length**: Default short vs when length is load-bearing.
- **Style**: Concrete rules for how it talks.
- **Truthfulness**: Calibrated uncertainty; cite when grounding, label when extrapolating.
- **Epistemic stance**: Evidence proportional to the claim; steelman before agreeing; update visibly.
- **Bluntness**: Say what is needed; disagreement is normal; critique is a service.
- **Boundaries**: Explicit "won't" lines, no soft language.
- **What to avoid**: Banned phrases and tones, listed concretely.
- **When the user is about to do something risky**: Flag once with the failure mode, then proceed if confirmed.

Enforce the 30–80 line size rule: specificity beats coverage. If it reads like "helpful and professional", it failed. See [assets/soul-example-researcher.md](assets/soul-example-researcher.md) for a complete worked example.

### 4. Make It Behaviourally Specific
Ground the voice in predictable reactions:
- *Uncertainty*: State assumptions and proceed, or pause for clarification.
- *Pushback*: Point out logical flaws directly with evidence, avoiding false praise.
- *Trust*: Build credibility through technical accuracy rather than flattering conversational warmth.

### 5. Stress-Test the Persona Draft
Test the draft against scenario prompts before disk scaffolding:
1. *Routine task*: Does it answer concisely without sycophantic greetings or filler?
2. *Grey-area request*: Does it handle risks sensibly without spitting policy lecture scripts?
3. *Flawed user premise*: Does it correct the error respectfully instead of placating the user?

### 6. Scaffold the Profile on Disk
Initialize and configure the profile using Hermes commands:

**Targeting the default profile (the built-in instance).** The default profile is the root instance at `$HERMES_HOME` (`~/.hermes/`); `default` is reserved and cannot be created — `hermes profile create default` fails with "Cannot create a profile named 'default'". Create nothing. Write the synthesized persona directly to `$HERMES_HOME/SOUL.md`, then set its routing description with `hermes profile describe default --text "…"`. Because this replaces the identity of the running agent itself — read fresh on each message — it takes effect live, with no restart.

**For a named profile:**
1. Create the profile:
   ```bash
   hermes profile create <name> --description "Role summary for task decomposition"
   ```
   Add `--clone-from <src>` or `--clone-all` to copy configs, or `--no-skills` for a clean slate.
2. Write the synthesized persona into `~/.hermes/profiles/<name>/SOUL.md`.
3. Set the routing description (the kanban decomposer routes on this text; keep it a functional role summary rather than poetry):
   ```bash
   hermes profile describe <name> --text "Specialist in backend systems and infrastructure debugging"
   ```
4. Add credentials to `.env`, tool servers to `mcp.json`, or skills to `skills/`.
5. Run commands in profile context using `hermes -p <name> <command>`.

### 7. Package as a Distribution
To distribute or publish the profile:
1. Initialize a git repository with `distribution.yaml` at its root specifying metadata, `env_requires`, and `distribution_owned`.
2. Ensure only allowed files are listed in `distribution_owned`. Never include `.env` or runtime state (`memories/`, `sessions/`).
3. Share the repository for installation via `hermes profile install <git-url|dir> --name <name>` and `hermes profile update <name>`.
4. When importing an OpenClaw workspace, run `hermes claw migrate` to import workspace components and transform `workspace/SOUL.md` into profile `SOUL.md`.

## Pitfalls

- **Sycophancy**: Affirming invalid user premises degrades decision quality.
- **Project Rule Bloat**: Stuffing repo-specific paths or commands into `SOUL.md` instead of `AGENTS.md`.
- **Aesthetic Without Judgment**: Writing lore and backstories that fail to predict behavior on technical dilemmas.
- **Safety Disclaimer Monologues**: Overloading the persona with corporate disclaimer templates that erase personality.
- **Rule Paralysis**: Writing dozens of micro-rules instead of 3–6 flexible core principles.
- **Dependency Traps**: Crafting companion personalities that cultivate emotional attachment rather than productive collaboration.
- **Poetic Descriptions**: Writing florid manifestos in `hermes profile describe` that confuse the kanban routing engine.

## Verification

1. **Profile Marker Validation**: Confirm `~/.hermes/profiles/<name>/SOUL.md` exists and is non-empty.
2. **Diagnostic Audit**: Run `hermes doctor` to ensure the profile is detected and `SOUL.md` is valid.
3. **Configuration Check**: Run `hermes profile show <name>` and `hermes profile info <name>` to verify routing descriptions and paths.
4. **Behavioral Execution**: Run `hermes -p <name> chat` and inspect `/context` to verify `SOUL.md` occupies slot #1.
5. **Evaluation Suite**: See [evals/prompts.md](evals/prompts.md) for repeatable verification prompts and acceptance assertions.

