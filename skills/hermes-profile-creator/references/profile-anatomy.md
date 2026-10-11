# Hermes Profile Anatomy

## Instance Isolation
A Hermes profile is an isolated agent instance maintaining its own:
- Identity (`SOUL.md`)
- Configuration (`config.yaml`)
- Environment and secrets (`.env`)
- Tools and MCP servers (`mcp.json`, `skills/`, `plugins/`)
- Persistent memory and session transcripts (`memories/`, `sessions/`, `cron/`)

## Filesystem Layout
- **Default Profile**: Resides at `~/.hermes/` (or `$HERMES_HOME`). The name `default` is reserved for this root slot.
- **Named Profiles**: Reside at `~/.hermes/profiles/<name>/`.

**Editing the default profile.** Nothing to create: write `$HERMES_HOME/SOUL.md` directly and set the routing description with `hermes profile describe default --text "…"`. `hermes profile create default` is rejected because `default` is the reserved root slot.

### Profile Home Directory Structure
```text
~/.hermes/profiles/<name>/
├── SOUL.md          # Primary persona; definitive profile marker
├── config.yaml      # Model selection, provider settings, parameter defaults
├── .env             # Private secrets, tokens, API credentials (never committed)
├── mcp.json         # Model Context Protocol server definitions
├── skills/          # Custom skills scoped to this profile
├── plugins/         # Profile-specific plugin scripts
├── cron/            # Scheduled autonomous jobs
├── memories/        # Scoped long-term memory store
└── sessions/        # Serialized conversation histories
```

### The Profile Marker
`SOUL.md` is the definitive profile marker. Hermes scans `~/.hermes/profiles/` and skips any directory that lacks `SOUL.md`.

## Profile Command Surface

Any Hermes command can target a specific profile using the `-p` flag:
```bash
hermes -p <name> <cmd>
```

### Profile Management Commands
- **`create <name>`**: Initialize a new profile.
  - `--clone`: Clone configuration and base files from the default profile.
  - `--clone-from SOURCE`: Clone configuration and state from a specified source profile.
  - `--clone-all`: Clone all settings, skills, and MCP configurations.
  - `--clone-channels`: Copy communication channel bindings.
  - `--sync-imports`: Synchronize imported tools and dependencies.
  - `--no-alias`: Skip creating a shell alias for the profile.
  - `--no-skills`: Do not copy default skills into the new profile.
  - `--description "<text>"`: Set routing summary during profile creation.
- **`describe <name>`**: Set or update routing description for task decomposition.
  - `--text "<summary>"`: Provide an explicit functional role summary.
  - `--auto`: Automatically generate a description from `SOUL.md` and tools.
  - `--overwrite`: Overwrite existing description text.
  - `--all`: Process all profiles in batch.
- **`list`**: Display all detected profiles, active status, and descriptions.
- **`use <name>`**: Set the active profile in the current shell environment.
- **`show <name>`**: Display profile configuration details and file locations.
- **`info <name>`**: Report profile statistics (active skills, memory entries, session counts).
- **`export <name>`**: Archive a profile into a distributable bundle.
- **`import <path>`**: Import and register a profile from an archive.
- **`install <url|dir>`**: Install a profile from a Git repository or local directory.
- **`update <name>`**: Pull upstream updates for an installed profile.
- **`alias <name> <alias>`**: Assign a short CLI alias to the profile.
- **`rename <old> <new>`**: Rename a profile directory and update associated references.

## Kanban Decomposer Routing
The text set via `hermes profile describe` provides the routing key for the kanban task decomposer.
- **Role Summary**: State clear capabilities and technical focus (e.g., "Specialist in database migrations, SQL optimization, and schema design").
- **Avoid Poetry**: Do not write narrative lore or backstories. The decomposer matches tasks to capabilities, not literary personas.

## Verification
Run `hermes doctor` to audit profile status:
- Reports whether `SOUL.md` exists or is empty.
- Validates profile structure and configuration integrity.
