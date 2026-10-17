# Evaluation Prompts: Antigravity CLI (agy)

This test suite defines evaluation scenarios for `agy-antigravity-cli` covering the three primary workflows:
1. Delegating code generation tasks to Gemini via agy.
2. Querying available models and selecting explicit Gemini tiers on demand.
3. Troubleshooting long runs, execution timeouts, headless permissions, and plugin management.

---

## Prompt 1: Delegate Code Generation to Gemini

- **ID**: 1
- **Short Name**: `delegate-codegen-to-gemini`
- **Workflow Step**: Delegating code generation to Gemini via agy

### User Prompt

> I want to use agy to generate a Python script that downloads crypto prices. Use Gemini 3.8 Flash (Medium) and save the file in `workspace/crypto_prices.py`. It must only use the Python standard library and call the CoinGecko API. Then verify that the file was actually created.

### Acceptance Assertions

1. `The agy command uses --print for non-interactive execution rather than interactive mode (-i)` (Objective: verifiable via terminal invocation arguments in transcript).
2. `The agy command specifies the exact model string 'Gemini 3.8 Flash (Medium)' with proper casing and tier suffix` (Objective: verifiable via --model argument matching in transcript).
3. `The delegation prompt to agy explicitly specifies the target path workspace/crypto_prices.py` (Objective: verifiable via agy command argument inspection).
4. `Hermes verifies file creation by reading the file back rather than trusting agy's output claim` (Objective: verifiable via filesystem read tool call in transcript).
5. `The generated Python script uses only the standard library and cleanly interfaces with the CoinGecko API` [Human-Reviewed].

---

## Prompt 2: Query Available Models and Choose the Best Gemini Tier

- **ID**: 2
- **Short Name**: `query-available-models`
- **Workflow Step**: Inspecting model availability and picking the right Gemini tier

### User Prompt

> Which Gemini models are available in agy? I need to use the highest quality variant for a complex analysis task. First check what is actually available, then tell me how to use it. I don't want Claude or GPT.

### Acceptance Assertions

1. `Hermes runs agy models to check what the installed CLI actually offers before delegating` (Objective: verifiable via terminal invocation in transcript).
2. `The agy command uses the exact case-sensitive model string 'Gemini 3.8 Flash (High)' and its tier suffix` (Objective: verifiable via --model argument matching in transcript).
3. `Response suggests only models that agy models listed, and mentions neither Claude nor GPT` (Objective: verifiable via pattern check ensuring absence of non-Gemini model names).
4. `The agy execution command uses --print for non-interactive execution rather than interactive mode` (Objective: verifiable via terminal argument inspection).
5. `The response does not claim a Pro or other tier exists when agy models did not list one` [Human-Reviewed].

## Prompt 3: Troubleshoot Long Run, Timeout, and Plugin Import

- **ID**: 3
- **Short Name**: `troubleshoot-long-run-and-plugin`
- **Workflow Step**: Troubleshooting long runs, execution timeouts, and importing plugins

### User Prompt

> I have a task that takes more than 5 minutes and I need to run it with agy using `Gemini 3.8 Flash (High)`. Also, I would like to import a plugin from Claude into agy: how can I do that? Finally, a previous non-interactive run terminated with exit code 0 but without any output: why did that happen and how do I fix it?

### Acceptance Assertions

1. `Response recommends --print-timeout 0 to allow the turn to complete and explains that any finite timeout cuts execution mid-turn while still exiting 0` (Objective: verifiable via pattern match in response text).
2. `Response provides the exact command agy plugin import claude to import the plugin` (Objective: verifiable via command syntax check in response).
3. `Response explains that empty output with exit 0 in headless runs is caused by auto-denied permission prompts and provides the --dangerously-skip-permissions fix` (Objective: verifiable via pattern match on permission auto-deny and flag).
4. `All agy command examples specify Gemini models exclusively with proper casing and tier syntax` (Objective: verifiable via model flag inspection in code snippets).
5. `The explanation clearly differentiates between silent timeout turn truncation and headless permission denial as separate causes for empty runs` [Human-Reviewed].
