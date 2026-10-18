# omp CLI reference (v18.1.18, from `omp --help`)

Usage:
```
omp [options] [@files...] [messages...]
omp <command> [args] [flags]
```
Bare `omp` = interactive TUI in current dir. `-p` = one-shot print mode.
`@file` inlines file contents into the prompt.

Precedence: CLI flag > env var > `~/.omp/agent/config.yml` > built-in default.
`--api-key` overrides everything for one run, never persisted.

## Modes
`--mode text|json|rpc|rpc-ui|acp` (default text). `--export <jsonl> [out]` renders a session as HTML and exits. `--allow-home` permits launching from $HOME (otherwise omp auto-chdirs to a temp dir).

## Key flags
| Flag | Meaning |
|---|---|
| `--model <m>` | active model, fuzzy match |
| `--smol/--slow/--plan <m>` | role overrides (env: PI_SMOL_MODEL/PI_SLOW_MODEL/PI_PLAN_MODEL) |
| `--models <p1,p2>` | models for Ctrl+P cycling |
| `--thinking <lvl>` | off/minimal/low/medium/high/xhigh/max/auto |
| `--prewalk` / `--prewalk-into <m>` | switch to cheap model at first edit after plan todo exists |
| `--plan-yolo` / `--plan-yolo-into <m>` | read-only plan, auto-approve, implement |
| `-p/--print` | one-shot, no TUI |
| `-c/--continue` | continue latest session for this dir |
| `-r/--resume [<id>]` | resume by ID prefix/path, or picker |
| `--session-dir <dir>` | custom session storage for this run |
| `--no-session` | ephemeral, not saved |
| `--cwd <dir>` | override launch dir |
| `--add-dir <dir>` | extra workspace dir (repeatable) |
| `--mode <m>` | text/json/rpc/rpc-ui/acp |
| `--config <file>` | extra config overlay (repeatable) |
| `--tools <list>` | enable only these tools |
| `--no-tools` / `--no-lsp` / `--no-pty` | disable all tools / LSP / PTY bash |
| `--system-prompt <str>` / `--append-system-prompt <str>` | replace/append system prompt |
| `--max-time <t>` | kill session after duration (600, 10m, 1h) |
| `--auto-approve` | skip approval prompts (= yolo for this run) |
| `--approval-mode <m>` | always-ask/write/yolo |
| `--no-skills` / `--skills 'git-*,pg'` | disable/filter skills |
| `--no-rules` | disable rules/context files |
| `--no-extensions` / `-e <file>` / `--hook <file>` | extension control |
| `--profile <name>` / `--alias <cmd>` | isolated profile / shell shortcut for it |
| `--export <jsonl>` | export session to HTML |
| `--no-title` | disable auto title |
| `--print-thoughts` | include thinking blocks in -p output |
| `--from-claude` / `--from-codex` | import session from Claude Code / Codex |

## Subcommands
`acp` ACP server over stdio · `agents` manage subagents (unpack → export defs) · `auth-broker` credential vault · `auth-gateway` forward proxy · `bench` model benchmark · `browser-relay` CDP relay for own Chrome · `cleanse` fix diagnostics with parallel subagents · `commit` commit msg + changelog · `completions` shell completions · `compress` text → dense prompt register · `config` settings · `gc` storage GC · `git` fullscreen git UI · `grep` test grep tool · `join` shared collab session · `models` list/search/refresh models · `plugin` install/uninstall/list · `ps` daemon background processes · `read` preview read tool output · `render` render session · `say` TTS · `search` test web-search providers · `setup` onboarding/deps · `share` encrypted session link · `shell` interactive console · `ssh` SSH hosts · `stats` usage stats · `token` provider API key/token · `update` self-update · `usage` provider limits · `worktree` git worktrees.

## Built-in tools (default-enabled)
read, bash, edit, write, grep, glob, lsp, python (needs `omp setup python`), notebook, browser (Puppeteer), task (subagents), todo, web_search, ask (interactive only). `computer` disabled by default.

## Key env vars
ANTHROPIC_API_KEY / ANTHROPIC_OAUTH_TOKEN, OPENAI_API_KEY, GEMINI_API_KEY, COPILOT_GITHUB_TOKEN, ZAI_API_KEY, OPENROUTER_API_KEY, XAI_API_KEY, GROQ_API_KEY, AZURE_OPENAI_API_KEY, AWS_PROFILE (Bedrock), GOOGLE_CLOUD_PROJECT/GOOGLE_APPLICATION_CREDENTIALS (Vertex). Search: EXA_API_KEY, BRAVE_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY, PERPLEXITY_API_KEY/COOKIES. Config: OMP_PROFILE, PI_CODING_AGENT_DIR, PI_SMOL/PI_SLOW/PI_PLAN_MODEL. omp also loads `.env`: `./.env` → `~/.omp/agent/.env` → `~/.omp/.env` → `~/.env` (already-exported process vars win).