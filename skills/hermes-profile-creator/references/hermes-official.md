# SOUL.md Identity Specification

## System Prompt Injection
- **Slot #1 Injection**: Hermes injects `SOUL.md` verbatim into Slot #1 of the system prompt. No wrapper language, preamble, or system commentary is added around it.
- **Source of Truth**: Read exclusively from `HERMES_HOME` (`~/.hermes/SOUL.md` or `$HERMES_HOME/SOUL.md`). Hermes never searches working directories or Git roots for `SOUL.md`.
- **Precedence**: Replaces the built-in default identity completely.

## Lifecycle and Seeding
- **First-Run Seeding**: Automatically generated on initial startup if absent.
- **Preservation**: An existing non-empty `SOUL.md` is never overwritten automatically.
- **Fallback Conditions**: Empty, whitespace-only, or unreadable files automatically fall back to the built-in default identity.
- **Size Limits**: If `SOUL.md` exceeds context limits, truncation applies. Keep the file focused and concise.

## Security Scanning
- **Injection Heuristics**: Hermes scans `SOUL.md` for known prompt-injection patterns during startup and reload.
- **Non-Blocking**: Hits do NOT prevent the file from loading; Hermes treats it as the user's explicit local configuration and loads it anyway.
- **Diagnostics**: A hit logs a warning to stderr and marks the file with a warning badge (`⚠`) in `/context`.

## Recommended Shape
Structure `SOUL.md` using the behaviour-first heading spine:
- **# Personality**: One line stating who the agent is, not what it does.
- **## Response length**: Default short vs when length is load-bearing.
- **## Style**: Concrete rules for how it talks.
- **## Truthfulness**: Calibrated uncertainty; cite when grounding, label when extrapolating.
- **## Epistemic stance**: Evidence proportional to the claim; steelman before agreeing; update visibly.
- **## Bluntness**: Say what is needed; disagreement is normal; critique is a service.
- **## Boundaries**: Explicit "won't" lines, no soft language.
- **## What to avoid**: Banned phrases and tones, listed concretely.
- **## When the user is about to do something risky**: Flag once with the failure mode, then proceed if confirmed.

Hermes' documented minimal shape (`Identity / Style / Avoid / Defaults`) represents the FLOOR, not the ceiling. A strong soul covers the behaviour-first dimensions in 30–80 lines.

## Content Boundaries
- **What Belongs**: Voice, tone, directness, uncertainty posture, disagreement boundaries, ambiguity handling, decision heuristics.
- **What Does Not Belong**: Absolute paths, network ports, CLI commands, repo conventions, workflow details, or task instructions.
- **Stance vs. Configuration Carve-Out**: `expertise` and `memory policy` are STANCE, never configuration. Tools live in `config.yaml`/toolsets, and memory lives in `memories/` and the memory system. Never teach putting config into system-prompt slot #1.

## Scope Separation
- **SOUL.md vs. AGENTS.md**: `SOUL.md` governs universal persona and voice across all workspaces and sessions. `AGENTS.md` governs repository-specific instructions, conventions, tools, and workflows.
- **SOUL.md vs. `/personality`**: `/personality` applies an ephemeral, session-specific style overlay. `SOUL.md` is the durable baseline across all sessions.
- **No IDENTITY.md**: Hermes does not recognize or support OpenClaw's `IDENTITY.md`. Profile names, `hermes profile describe`, and `SOUL.md` handle all identity responsibilities.
