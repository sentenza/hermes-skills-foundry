# Evaluation Prompts: omp Terminal Agent Adapter

This test suite defines evaluation scenarios for `omp` covering the primary workflows:
1. One-shot code delegation with session management
2. Multi-turn sessions with memory (continue/resume)
3. Plan-then-execute for risky changes
4. Structured JSON output parsing
5. Subagent delegation within omp
6. Model selection and configuration
7. Safety/approval modes and read-only limits

---

## Prompt 1: One-Shot Code Delegation (Default Pattern)

- **ID**: 1
- **Short Name**: `one-shot-delegation`
- **Workflow Step**: Delegating a focused coding task to omp headless

### User Prompt

> Use omp to fix the failing test in `src/parser.test.ts`. Run the test, explain the root cause in 3 lines. Use `--max-time 600` and `--no-session` since this is a throwaway task.

### Acceptance Assertions

1. `The omp command uses -p (print mode) for non-interactive execution` (Objective: verifiable via terminal invocation arguments in transcript).
2. `The omp command includes --max-time with a finite value (e.g., 600)` (Objective: verifiable via terminal argument inspection).
3. `The omp command includes --no-session for throwaway scratch tasks` (Objective: verifiable via terminal argument inspection).
4. `The omp command specifies workdir=<project root> explicitly` (Objective: verifiable via terminal workdir parameter).
5. `Hermes verifies the test passes by reading the test output rather than trusting omp's claim` (Objective: verifiable via filesystem read or terminal output inspection).

---

## Prompt 2: Long-Running Background Task

- **ID**: 2
- **Short Name**: `background-long-task`
- **Workflow Step**: Delegating a long-running task to omp in background mode

### User Prompt

> Use omp to migrate the job queue to Postgres; keep the public API; run the full test suite after. This will take a while, so run it in the background with a 1-hour timeout.

### Acceptance Assertions

1. `The omp command uses -p (print mode) with --max-time 3600 (or 1h)` (Objective: verifiable via terminal arguments).
2. `The terminal call uses background=true and notify=true` (Objective: verifiable via terminal tool parameters).
3. `Hermes explains how to poll the background process or read its log` (Objective: verifiable via response text pattern match).

---

## Prompt 3: Multi-Turn Session with Memory (Continue)

- **ID**: 3
- **Short Name**: `session-continue`
- **Workflow Step**: Continuing an existing omp session to reuse accumulated context

### User Prompt

> The project at `~/proj` already has omp sessions from earlier work. Continue the latest session for that directory and implement fix #2 from the previous investigation report. Use a 15-minute timeout.

### Acceptance Assertions

1. `The omp command uses -c (continue) flag to resume the latest session for the directory` (Objective: verifiable via terminal arguments).
2. `The omp command includes -p (print mode) and --max-time 900` (Objective: verifiable via terminal arguments).
3. `Hermes checks for prior sessions before starting fresh (ls ~/.omp/agent/sessions/)` (Objective: verifiable via prior terminal call or explanation).
4. `The prompt references the previous investigation's fix #2, demonstrating session memory reuse` (Objective: verifiable via prompt text in omp command).

---

## Prompt 4: Plan-Then-Execute (Risky Changes)

- **ID**: 4
- **Short Name**: `plan-yolo`
- **Workflow Step**: Using omp's headless plan-yolo for read-only planning then implementation

### User Prompt

> Draft a plan for refactoring the authentication module to use JWT instead of session cookies. Investigate the codebase, do NOT edit anything. Output the full plan as markdown. Then, after I review it, implement exactly that plan.

### Acceptance Assertions

1. `First omp call uses --plan-yolo (or explicit plan prompt) with --no-session and read-only investigation` (Objective: verifiable via terminal arguments and prompt text).
2. `Hermes presents the plan to the user for review before the second call` (Objective: verifiable via conversation flow).
3. `Second omp call implements the reviewed plan with explicit "Implement exactly this plan:" prompt` (Objective: verifiable via prompt text).
4. `The plan includes investigation steps, file changes, and test verification` (Objective: verifiable via plan content review).

---

## Prompt 5: Structured JSON Output Parsing

- **ID**: 5
- **Short Name**: `json-mode-parse`
- **Workflow Step**: Running omp in JSON mode and extracting the final assistant response

### User Prompt

> Run omp in JSON mode (--mode json) with --no-session and --max-time 300 to create a simple Python hello world script. Parse the JSONL output and extract only the final assistant message text.

### Acceptance Assertions

1. `The omp command includes --mode json` (Objective: verifiable via terminal arguments).
2. `Hermes provides Python code to parse newline-delimited JSON events` (Objective: verifiable via code snippet in response).
3. `The parsing logic takes the LAST turn_end with role=assistant` (Objective: verifiable via code logic inspection).
4. `The extracted answer contains the generated script content` (Objective: verifiable via output inspection).

---

## Prompt 6: Subagent Delegation Within OMP

- **ID**: 6
- **Short Name**: `subagent-delegation`
- **Workflow Step**: Using omp's bundled subagents for parallel audits

### User Prompt

> Use omp to audit the src/auth directory for security issues. Use the security-reviewer subagent (read-only) to do the audit, do not edit anything. Report all findings.

### Acceptance Assertions

1. `The omp prompt explicitly names the security-reviewer subagent` (Objective: verifiable via prompt text in omp command).
2. `The prompt specifies read-only / do not edit constraint` (Objective: verifiable via prompt text).
3. `Hermes acknowledges that subagents multiply cost and should be file-disjoint` (Objective: verifiable via response text or subsequent guidance).

---

## Prompt 7: Model Selection and Role Overrides

- **ID**: 7
- **Short Name**: `model-selection`
- **Workflow Step**: Selecting specific models and roles for omp runs

### User Prompt

> List available models in omp, then run a task using the 'slow' (deep reasoning) role with the Opus model. Also show how to configure a custom OpenAI-compatible endpoint.

### Acceptance Assertions

1. `Hermes runs omp models first to list available providers/models` (Objective: verifiable via terminal call).
2. `The task run uses --slow or --model with Opus identifier` (Objective: verifiable via terminal arguments).
3. `Response explains ~/.omp/agent/models.yml structure for custom endpoints` (Objective: verifiable via response text pattern match).

---

## Prompt 8: Read-Only Hard Limit and Approval Modes

- **ID**: 8
- **Short Name**: `readonly-approval`
- **Workflow Step**: Enforcing read-only execution and understanding approval modes

### User Prompt

> Run omp in read-only mode (only read, grep, glob tools) to investigate the codebase without any edits. Also explain the difference between yolo, write, and always-ask approval modes for headless runs.

### Acceptance Assertions

1. `The omp command includes --tools read,grep,glob (or --no-tools with explicit allows)` (Objective: verifiable via terminal arguments).
2. `Response explains yolo = no prompts (default), write = prompt on exec, always-ask = prompt on writes/exec` (Objective: verifiable via response text).
3. `Response warns that headless -p with prompt/always-ask hangs silently` (Objective: verifiable via response text).
4. `Response recommends --auto-approve or --approval-mode yolo for headless runs` (Objective: verifiable via response text).