# Profile Distribution and Publishing

## The distribution.yaml Manifest
A distributable profile defines a `distribution.yaml` manifest at the repository root.

```yaml
name: backend-architect
version: 0.1.0
description: Autonomous system architect and Go/Rust service specialist.
hermes_requires: ">=0.20"
author: Dev Team <dev@example.com>
license: MIT
env_requires:
  - name: GITHUB_TOKEN
    description: Personal access token with repo scope for PR management.
    required: true
    default: ""
  - name: SENTRY_AUTH_TOKEN
    description: Read-only auth token for error tracing.
    required: false
    default: ""
distribution_owned:
  - SOUL.md
  - config.yaml
  - mcp.json
  - skills/
  - cron/
  - distribution.yaml
```

### Manifest Fields
- **`name`**: Profile identifier conforming to `^[a-z0-9][a-z0-9-]*$`.
- **`version`**: Semantic version string (e.g., `0.1.0`, `1.2.3`).
- **`description`**: Summary of profile capabilities and intended use.
- **`hermes_requires`**: Semver constraint for Hermes agent runtime (e.g., `>=0.20`, `^0.20.1`). Prohibited values: `latest`, `*`.
- **`author`**: Name and contact details of maintainer.
- **`license`**: SPDX license identifier (e.g., `MIT`, `Apache-2.0`).
- **`env_requires`**: List of environment variable requirements. Each entry defines:
  - `name`: Variable name.
  - `description`: Purpose of the variable.
  - `required`: Boolean flag indicating if variable is mandatory.
  - `default`: Default fallback value if unset.
- **`distribution_owned`**: Allowlist of files and directories managed by the distribution. Only paths listed here are updated or overwritten during distribution updates.

## Distribution Payload Boundaries

### Allowed Payload (`distribution_owned`)
Default distribution-owned files:
- `SOUL.md`: Persona and system prompt instructions.
- `config.yaml`: Provider-neutral configuration.
- `mcp.json`: Declared tool integrations and server commands.
- `skills/`: Custom skills directory.
- `cron/`: Scheduled autonomous jobs.
- `distribution.yaml`: Package manifest.

### Never Distribution-Owned
Never package, commit, or distribute runtime state or secrets:
- `.env` or credentials, API keys, tokens.
- `memories/`: Persistent user and agent memories.
- `sessions/`: Conversation transcripts and history.
- `cache/`: Model caching and temporary scratch files.
- `backups/`: Historical backups or snapshots.
- `workspace/`: Local working trees and scratch workspaces.

## Configuration Best Practices
- **Provider-Neutral `config.yaml`**: Ship configurations without hardcoded API keys, private endpoints, or vendor-locked model overrides. Allow downstream users to bind their own providers.
- **Environment Templates**: Generate `.env.template` or `.env.EXAMPLE` files from `env_requires`:
  ```bash
  # .env.EXAMPLE
  # Generated from distribution.yaml env_requires

  # Required: Personal access token with repo scope for PR management.
  GITHUB_TOKEN=

  # Optional: Read-only auth token for error tracing.
  SENTRY_AUTH_TOKEN=
  ```

## Publishing Patterns and Installation

### The "Repo IS the Profile" Pattern
Structure the Git repository so its root directly mirrors a profile directory:
```text
repo/
├── SOUL.md
├── distribution.yaml
├── config.yaml
├── mcp.json
├── .env.EXAMPLE
└── skills/
```
Users can clone directly to `~/.hermes/profiles/<name>/` or use the CLI commands.

### Distribution CLI Commands
- **Install**:
  ```bash
  hermes profile install <git-url|dir> --name <name>
  ```
- **Update**:
  ```bash
  hermes profile update <name>
  ```
  Applies upstream updates strictly to files in `distribution_owned`, preserving local `.env`, memories, and sessions.
- **Info**:
  ```bash
  hermes profile info <git-url|name>
  ```
  Inspects manifest metadata before or after installation.
