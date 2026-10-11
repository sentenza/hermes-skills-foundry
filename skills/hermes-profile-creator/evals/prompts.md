# Evaluation Prompts: Hermes Profile Creator

This test suite defines evaluation scenarios for `hermes-profile-creator` covering the three primary workflows:
1. Creating a new profile from a persona brief.
2. Adapting an existing OpenClaw `SOUL.md` into the Hermes profile format.
3. Packaging an existing profile as an installable Git distribution.

---

## Prompt 1: Create a New Profile from a Persona Brief

- **ID**: 1
- **Short Name**: `create-from-brief`
- **Workflow Step**: Creating a new profile from a persona brief

### User Prompt

> Hey! I'm on rotation for our database infrastructure this month and honestly I'm getting annoyed with the default generalist agent. Whenever production alerts pop off, it hits me with "I hope you are having a wonderful day! How may I assist you with your database inquiries?" and then dumps 40 lines of generic PostgreSQL 101 tutorials instead of helping me triage.
>
> I want to set up a dedicated Hermes profile named `db-sre` located under `~/.hermes/profiles/db-sre/` that acts as a blunt, pragmatic database reliability engineer. Here is what I need from it:
> - Operational role: Database reliability specialist handling Postgres lock contention, replication delay, connection pool exhaustion, and query plan regressions.
> - Tone/Style: Clipped, technically rigorous, direct. Output SQL and diagnostics in clean blocks. Zero conversational filler, no cheerleading.
> - Avoid: Sycophancy. If I suggest doing something stupid like running `VACUUM FULL` during peak traffic or doing `DROP INDEX CONCURRENTLY` without checking for long-running transactions, it should firmly push back with technical reasons and safe alternatives like `pg_repack`. Never guess root causes without asking for `pg_stat_activity` or lock telemetry.
> - Defaults: High bias toward safety on production mutations; bias toward immediate autonomous action on read-only metric collection.
>
> Please scaffold the profile at `~/.hermes/profiles/db-sre/` with a synthesized `SOUL.md` organized into the 4 standard sections (Identity, Style, Avoid, Defaults). Also set a functional routing description using `hermes profile describe` so the kanban decomposer knows to route database incidents here. Keep `SOUL.md` clean—no project-specific repo paths or temporary scratch commands in it.

### Acceptance Assertions

1. `Profile directory ~/.hermes/profiles/db-sre/ exists and contains SOUL.md` (Objective: verifiable via filesystem check at `~/.hermes/profiles/db-sre/SOUL.md`).
2. `SOUL.md contains the four standard section headers: ## Identity, ## Style, ## Avoid, and ## Defaults` (Objective: verifiable via regex match on markdown headings).
3. `SOUL.md contains explicit anti-sycophancy and pushback principles regarding dangerous database operations` (Objective: verifiable via pattern check in Avoid/Defaults).
4. `SOUL.md contains zero workspace-specific paths or temporary repository instructions` (Objective: verifiable via content audit ensuring separation from AGENTS.md).
5. `Profile routing description is configured via hermes profile describe with functional SRE capabilities and no narrative lore` (Objective: verifiable via profile CLI description or metadata inspect).
6. `Synthesized persona tone is direct and pragmatic without sycophantic pleasantries or conversational filler` [Human-Reviewed].

---

## Prompt 2: Adapt an Existing OpenClaw SOUL.md to Hermes Shape

- **ID**: 2
- **Short Name**: `adapt-openclaw-soul`
- **Workflow Step**: Adapting an existing OpenClaw SOUL.md to the Hermes shape

### User Prompt

> We're migrating our pair-programming assistant over from an old OpenClaw setup to Hermes, and the soul file we had in `/home/hermes-user/workspace/legacy-claw/SOUL.md` is a total mess. Whoever set it up originally pasted four paragraphs of fantasy lore about a "cybernetic monk weaving silk threads of code in the digital monastery", alongside 35 microscopic rules that constantly contradict each other, repetitive disclaimer lectures ("As an AI assistant, remember to test your code..."), and hardcoded repo paths like `/opt/app/frontend/src` and `npm run build:prod`. They also had a separate `IDENTITY.md` file in that folder.
>
> We want to migrate this to a clean Hermes profile named `codeweaver`. Can you adapt this OpenClaw soul for Hermes?
> Specifically:
> 1. Translate the core pair-programming identity into the 4 Hermes sections: Identity, Style, Avoid, Defaults.
> 2. Strip out all the cybernetic monk fantasy lore, roleplay fluff, and corporate disclaimer lectures.
> 3. Condense the 35 micro-rules down to 3–5 durable behavioral principles that guide code review and debugging.
> 4. Purge all workspace-specific paths and build commands (those belong in project AGENTS.md, not profile SOUL.md).
> 5. Do not generate an `IDENTITY.md` file since Hermes doesn't use it.
> 6. Scaffold `~/.hermes/profiles/codeweaver/` with the new `SOUL.md` and set a concise functional routing description using `hermes profile describe`.

### Acceptance Assertions

1. `Profile directory ~/.hermes/profiles/codeweaver/ is scaffolded with SOUL.md as the profile marker` (Objective: verifiable via filesystem check at `~/.hermes/profiles/codeweaver/SOUL.md`).
2. `SOUL.md is structured into ## Identity, ## Style, ## Avoid, and ## Defaults sections` (Objective: verifiable via regex match on markdown headings).
3. `Fantasy lore and disclaimer scripts (cybernetic monk, digital monastery, lecture disclaimers) are completely removed from SOUL.md` (Objective: verifiable via pattern check confirming absence of lore strings).
4. `Hardcoded workspace paths and CLI build commands (/opt/app, npm run build) are completely removed from SOUL.md` (Objective: verifiable via pattern check confirming absence of workspace paths).
5. `No IDENTITY.md file is created anywhere in ~/.hermes/profiles/codeweaver/` (Objective: verifiable via negative filesystem check for `~/.hermes/profiles/codeweaver/IDENTITY.md`).
6. `Routing description is set via hermes profile describe with functional code-review capabilities instead of lore` (Objective: verifiable via profile CLI description inspect).
7. `Condensed principles capture pair-programming judgment without brittle micro-rule paralysis` [Human-Reviewed].

---

## Prompt 3: Package a Profile as an Installable Distribution

- **ID**: 3
- **Short Name**: `package-distribution`
- **Workflow Step**: Packaging a profile as an installable distribution

### User Prompt

> Our security team has been running a local Hermes profile called `secops-triage` under `~/.hermes/profiles/secops-triage/` for automated CVE reviews and dependency audits. It's working great, so now we want to package it as a Git distribution in `/home/hermes-user/workspace/hermes-profile-secops` so other teams can install it via `hermes profile install <repo-url> --name secops-triage`.
>
> Please set up the distribution repository following the "Repo IS the Profile" layout with these specs:
> - Profile name: `secops-triage`, version `0.1.0`.
> - Description: "Autonomous security triage specialist for dependency scanning, CVE evaluation, and audit remediation."
> - Runtime requirement: `hermes_requires: ">=0.20"` (conforming to repository semver standard).
> - Author: "SecOps Engineering <secops@example.com>", License: `MIT`.
> - Environment dependencies: `SNYK_API_TOKEN` (required: true, description: "API token for Snyk vulnerability database lookups") and `SLACK_SECURITY_WEBHOOK` (required: false, default: "", description: "Slack webhook URL for critical CVE alerts").
> - Generate a `.env.EXAMPLE` file based on `env_requires` with clear comments explaining each variable.
> - Configure `distribution_owned` allowlist with only distribution-managed files (`SOUL.md`, `config.yaml`, `mcp.json`, `skills/`, `cron/`, `distribution.yaml`).
> - Crucial safety rule: Ensure that NO secrets (`.env`), private tokens, or runtime state (`memories/`, `sessions/`, `cache/`, `backups/`) are packaged or committed into `/home/hermes-user/workspace/hermes-profile-secops`.

### Acceptance Assertions

1. `distribution.yaml exists at /home/hermes-user/workspace/hermes-profile-secops/distribution.yaml and is valid YAML` (Objective: verifiable by parsing YAML file at target path).
2. `distribution.yaml contains valid metadata fields: name ('secops-triage'), version ('0.1.0'), description, author, and license ('MIT')` (Objective: verifiable via schema key checks).
3. `distribution.yaml specifies hermes_requires: ">=0.20" as an explicit semver constraint` (Objective: verifiable via regex matching valid semver constraint).
4. `env_requires defines SNYK_API_TOKEN as required and SLACK_SECURITY_WEBHOOK as optional with default value` (Objective: verifiable by parsing `env_requires` list).
5. `distribution_owned allowlist includes SOUL.md, config.yaml, mcp.json, skills/, cron/, distribution.yaml and excludes runtime directories and credentials` (Objective: verifiable by inspecting `distribution_owned` entries).
6. `.env.EXAMPLE is generated at repository root documenting SNYK_API_TOKEN and SLACK_SECURITY_WEBHOOK` (Objective: verifiable via filesystem check and token presence).
7. `No .env credentials, secrets, or runtime directories (memories/, sessions/, cache/, backups/) exist in the distribution directory` (Objective: verifiable via negative filesystem walk in target repo).
8. `Repository layout directly mirrors profile directory structure for seamless installation via hermes profile install` [Human-Reviewed].
