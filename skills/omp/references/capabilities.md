# omp capabilities deep-dive

Summarized from https://omp.sh/docs (fetched 2026-09-14). Page list = sidebar index at /docs. Skill authoring: /docs/skills. Subagents: /docs/subagents.

## Sessions (docs/sessions)
- Auto-saved per working directory (JSONL, `~/.omp/agent/sessions/`).
- `omp -c` continue latest; `omp -r` picker (search by title/ID/text; Tab = all projects); `omp -r <id-prefix>` specific.
- `/new` new session · `/rename` · `/pin` · `/move <dir>` · `/drop` (delete+new) · `/session delete|info`.
- `/branch` rewind to an earlier user message IN the same session (tree via `/tree`); `/fork` copy current state into a NEW session.
- `--no-session` ephemeral. Profiles (`--profile`) isolate everything.
- Crash recovery: `omp -c`, look for 'interrupted' sessions in `/r`; omp never invents missing tool results — verify external side effects before retry.

## Plan mode (docs/plan)
- Interactive `/plan` → read-only planning turn → Plan Review surface → approve+execute / approve+compact / approve+keep-context / refine / save.
- Config: `plan.enabled` (default true), `plan.defaultOnStartup`, `modelRoles.plan`.
- Headless equivalent: `--plan-yolo` (+ `--plan-yolo-into`).
- Mutually exclusive with goal mode and vibe mode.

## Subagents (docs/subagents)
- Bundled: scout, designer, reviewer, security-reviewer, librarian, task, sonic. `/agents` = control center; Alt+A = Agent Hub (live roster, steering, kill with x, revive parked with r).
- Prompt-level control: name the specialist, require file-disjoint ownership.
- Isolation: `/settings → Tasks → Isolation: Auto` (git repo required; workspaces under ~/.omp/wt; successful patches auto-applied).
- Limits: task.maxConcurrency 32, maxRecursionDepth 2, softRequestBudget 200, agentIdleTtlMs 420000, isolation.mode none|auto, isolation.apply true, isolation.merge patch.
- Subagents run headless WITHOUT interactive approvals — scope their authority.

## Code intelligence / LSP (docs/code-intelligence)
- Enabled by default; auto-selects server by project marker (package.json, Cargo.toml, go.mod, pyproject.toml — in the LAUNCH dir only, no parent walk) + executable in project-local bin (node_modules/.bin, venv bin, binstubs) or PATH. Lazy start; shared across sessions via daemon broker.
- Ask in natural language: definitions, implementations, references, inferred types, diagnostics, server fixes, semantic rename, file move with import updates. For non-symbol edits use structural edits (docs/editing).

## Debugging (docs/debugging)
- DAP over the `debug` tool (gated by debug.enabled, default on).
- Adapters auto-discovered on PATH: lldb-dap (C/C++/Rust/Swift/Zig/ObjC, ships with macOS Xcode CLT), dlv (Go), debugpy (Python), vscode-js-debug (Node), + .NET/Kotlin/Ruby/PHP/Bash/Dart/Elixir.
- Ops: launch/attach/terminate/sessions, set_breakpoint (file+line|function, condition/hit), data & instruction breakpoints, continue/step_over/in/out/pause, threads, stack_trace, evaluate in frame, scopes/locals.

## Web & browser (docs/web)
- Web search (answer + source URLs; provider chain in settings), URL reading, managed Puppeteer browser (headless by default), browser relay driving your REAL Chrome tabs (visible state). For GitHub issues/PRs prefer the GitHub integration over scraping.

## GitHub (docs/github)
- Structured GitHub context (issues, PRs) inside omp; cached and more reliable than scraping.

## Approvals (docs/approvals)
- tools.approvalMode: always-ask (prompt on writes/exec) | write (prompt on exec: bash/eval/browser/task) | yolo (default — no prompts).
- Per-tool policy: `tools.approval.<tool>: prompt|deny|...`. Headless: prefer deny (prompt would hang). One-run: `--approval-mode`, `--auto-approve`.

## Providers (docs/providers, docs/custom-models)
- Provider = account/backend; model = provider/model-id. Subscription vs API IDs differ (openai-codex vs openai; google-gemini-cli vs google; xai-oauth vs xai). /login /logout /model inside TUI.
- Local engines auto-discovered: ollama (11434), llama.cpp (8080), lm-studio (1234) + base-URL env overrides; vllm route exists.
- Custom endpoints in ~/.omp/agent/models.yml: providers.<name>.baseUrl/api (openai-completions|anthropic|…)/apiKey (env-var NAME first, literal otherwise)/auth: none/models[]. (id,name,contextWindow,maxTokens).
- `omp models refresh` after login changes; `omp config get disabledProviders` when a provider is missing.

## Settings (docs/settings)
- `omp config list [--json] | get <k> | set <k> <v> | reset <k> | path`. Arrays/records as JSON in `set`.
- Scopes: global ~/.omp/agent/config.yml · profile ~/.omp/profiles/<n>/agent/config.yml · project <cwd>/.omp/config.yml (exact dir, no parent walk) · `--config` overlays · runtime flags. A project array REPLACES the global one.
- Useful families: tools, task (subagents), plan, modelRoles, providers, web_search, mcp, skills, memory/autolearn, edit/read/lsp, shell/python, worktree, commit, security, computer, browser, async.

## Skills (docs/skills)
- ~/.omp/agent/skills/<name>/SKILL.md (user) · .omp/skills/<name>/SKILL.md (project) · plugins/marketplaces (`omp plugin discover|install`).
- Frontmatter: description (REQUIRED — the match trigger; concrete verbs, objects, boundary), name, hide. globs/alwaysApply NOT used by omp.
- Discovery one level deep. Compatible dirs also read: ~/.agent/skills, ~/.agents/skills, ~/.claude/skills, ~/.codex/skills, ~/.config/opencode/skills (+ project equivalents, walked to repo root). Same-name skills don't merge — highest-priority provider wins.
- Explicit: /skill:<name> prompt. Manage/inspect: /extensions → Skills, then /reload-plugins. Filters: --skills 'git-*,pg', config skills.include/ignoredSkills/customDirectories.

## MCP (docs/mcp)
- Config: .omp/mcp.json (project) · ~/.omp/agent/mcp.json (user) · mcp.json / .mcp.json at root (portable fallback). Auto-imports from Claude Code, Codex, Gemini CLI, OpenCode, Cursor, Windsurf, VS Code — check /mcp list first.
- Transports: stdio (command/args/env/cwd; default) · http (type:"http", url, headers) · sse (legacy; explicit type). Never both command and url.
- Secrets: ${VAR}/${VAR:-default} expansion; `!cmd` runs a shell command (trusted only); OAuth via /mcp reauth (stored in profile auth storage, NOT mcp.json). auth.type apikey does NOT inject keys — use env/headers.
- Commands: /mcp add|list|test|reload|reconnect|enable|disable|reauth|unauth|resources|prompts|notifications|remove. Tools appear as mcp__<server>_<tool>.

## Programmatic (docs/sdk, docs/rpc, docs/acp)
- RPC: `omp --mode rpc [--no-session]` — JSON lines on stdio: host sends {"id","type":"prompt","message"}, omp streams events, turn ends at agent_end (isTerminal). Protocol negotiation v1/v2 via first ready frame. rpc-ui = same protocol + UI bridge frames (extension_ui_request).
- SDK: TypeScript, runs omp in-process with typed APIs (see docs/sdk).
- ACP: Agent Client Protocol over stdio for editor integration.

## Misc pages worth knowing
- Memory/autolearn, compaction (context summarization), goal mode (persistent objective with budget), vibe mode, advisor (passive turn review), handoff (structured wrap-up), collab (shared live sessions, `omp join`), computer control (native desktop I/O, disabled by default), TTSR, themes, prompt templates, magic keywords, hooks, custom tools, session tree/format, tools index — see the /docs sidebar.