# agy Quick Reference Card

## Default model

**Use `Gemini 3.8 Flash (Medium)` (newest Flash, Medium effort) for every agy call. Never switch model or tier on your own.**

## Core syntax
```
agy --model "Gemini 3.8 Flash (Medium)" --print "prompt"   # Non-interactive (preferred)
agy --model "Gemini 3.8 Flash (Medium)" -p "prompt"        # Shorthand
agy --model "Gemini 3.8 Flash (Low)" --print "prompt"      # Fastest variant
agy --model "Gemini 3.8 Flash (High)" --print "prompt"     # Highest quality
agy --print-timeout 0 --print "prompt"                    # Default: wait for the turn — never set a finite value
agy --model "Gemini 3.8 Flash (High)" -i                     # Interactive (needs pty=true)
agy -c                                                      # Continue last conversation
agy --mode accept-edits                                     # Auto-apply edits
agy --mode plan                                             # Plan-only mode
```

## Model list

**Available models** (live `agy models` on v1.4.0):

| Model | Variants | Status |
|-------|----------|--------|
| Gemini 3.8 Flash | Low, Medium, High | **Default (Medium)** |

> Run `agy models` for the live list — the CLI adds and removes models between releases.

## Subcommands
```
agy models                     # List available models
agy plugin list                # List plugins
agy plugin import <source>     # Import plugins from gemini or claude
agy plugin install <target>    # Install plugin@marketplace
agy plugin uninstall <name>    # Remove plugin
agy update                     # Update CLI
agy changelog                  # Show release notes
```

## Hermes patterns
```
terminal("agy --model 'Gemini 3.8 Flash (Medium)' --print-timeout 0 --print='prompt'", timeout=900)
```
- Always use --print from Hermes (non-interactive)
- Never add a finite --print-timeout: it cuts the turn mid-run, still exits 0, and leaves no artefacts
- Bound the job (one deliverable per run), not the clock; give terminal() a generous timeout
- Any run that must write a file or run a command also needs --dangerously-skip-permissions
- Non-interactive subprocess: pass stdin=DEVNULL, or the run hangs on a stdin that never arrives
- Verify file creation: read_file(path)
- Models are case-sensitive — include tier suffix

## Skill evaluation (hermes-skill-creator)
- Baseline runs: `agy --model "Gemini 3.8 Flash (Medium)" --print-timeout 0 --dangerously-skip-permissions --print="<eval prompt>"`
- Description optimization: called via `run_description_optimization.py` (subprocess)
- Automated grading: pipe output to assertion checker script

## Usage/quota (local language server)
```
# Start agy interactively, then query in another terminal:
ss -tlnp | grep agy
curl -sk -X POST "https://127.0.0.1:<PORT>/exa.language_server_pb.LanguageServerService/GetUserStatus" \
  -H 'Content-Type: application/json' -H 'Connect-Protocol-Version: 1' \
  -d '{"metadata":{"ideName":"antigravity","extensionName":"antigravity","locale":"en"}}'
```