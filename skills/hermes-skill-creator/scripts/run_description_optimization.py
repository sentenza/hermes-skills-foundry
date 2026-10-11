#!/usr/bin/env python3
"""
Description optimization loop for Hermes skills (engine-agnostic).

Tests trigger accuracy by running queries through a configured engine CLI (agy,
opencode, claude, or custom) and measuring whether the skill's description would
trigger the model to use the skill. Splits the eval set into train/test, iterates
on the engine-proposed description, keeps the best by *test* score (avoiding
overfitting), and emits both a JSON report and an HTML report.

This is the Hermes engine-agnostic counterpart of upstream skill-creator's
run_eval.py + run_loop.py + improve_description.py (which were hardwired to
`claude -p`). The output JSON is shaped so `generate_report.py` can render it.

Usage:
  python run_description_optimization.py \
    --eval-set trigger_eval_set.json \
    --skill-path /path/to/skill \
    --engine auto \
    --max-iterations 5 \
    --runs-per-query 3
"""
import argparse
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Make the sibling generate_report importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_report import generate_html  # noqa: E402

DEFAULT_TEMPLATES = {
    "agy": ["agy", "--model", "{model}", "--print", "{prompt}"],
    "opencode": ["opencode", "run", "{prompt}"],
    "claude": ["claude", "-p", "{prompt}"],
}


def load_engine_config() -> Dict[str, List[str]]:
    """Read optional JSON config mapping engine name -> argv template."""
    templates = {k: list(v) for k, v in DEFAULT_TEMPLATES.items()}
    config_env = os.environ.get("HERMES_SKILL_ENGINE_CONFIG")
    if config_env:
        config_path = Path(config_env).expanduser()
    else:
        config_path = Path("~/.hermes/skill-creator-engines.json").expanduser()

    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_templates = json.load(f)
                if isinstance(user_templates, dict):
                    for k, v in user_templates.items():
                        if isinstance(v, list):
                            templates[k] = [str(arg) for arg in v]
                        elif isinstance(v, str):
                            templates[k] = shlex.split(v)
        except Exception as e:
            print(f"[warn] Failed to read engine config from {config_path}: {e}", file=sys.stderr)
    return templates


class EngineRunner:
    """Executes queries and improvement prompts against the selected engine CLI."""

    def __init__(self, cmd_template: List[str], engine_name: str, timeout: int = 120):
        self.cmd_template = cmd_template
        self.engine_name = engine_name
        self.timeout = timeout
        self.successful_calls = 0
        self.total_calls = 0

    def run(self, prompt: str, query_context: str = "") -> Optional[str]:
        """Run engine substituting prompt as a single argv element."""
        self.total_calls += 1
        if any("{prompt}" in arg for arg in self.cmd_template):
            cmd = [arg.replace("{prompt}", prompt) if "{prompt}" in arg else arg for arg in self.cmd_template]
        else:
            cmd = list(self.cmd_template) + [prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if result.returncode != 0:
                print(
                    f"  [warn] Engine returned non-zero exit code {result.returncode}: {result.stderr.strip()[:120]}",
                    file=sys.stderr,
                )
                return None
            self.successful_calls += 1
            return result.stdout
        except (FileNotFoundError, OSError) as e:
            print(f"Fatal error running engine '{self.engine_name}' ({cmd[0]}): {e}", file=sys.stderr)
            sys.exit(2)
        except subprocess.TimeoutExpired:
            ctx = f" (Query: {query_context[:60]}...)" if query_context else ""
            print(f"  [timeout] Engine timed out after {self.timeout}s.{ctx}", file=sys.stderr)
            return None


def load_skill_description(skill_path: Path) -> str:
    """Extract description from SKILL.md frontmatter."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        print(f"Error: SKILL.md not found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    content = skill_file.read_text()
    match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        print("Error: No YAML frontmatter found in SKILL.md", file=sys.stderr)
        sys.exit(1)

    frontmatter = match.group(1)
    desc_match = re.search(r'description:\s*["\']?(.*?)["\']?\s*$', frontmatter, re.MULTILINE | re.DOTALL)
    if not desc_match:
        print("Error: No description found in frontmatter", file=sys.stderr)
        sys.exit(1)

    desc = desc_match.group(1).strip()
    if desc.startswith('"') and desc.endswith('"'):
        desc = desc[1:-1]
    elif desc.startswith("'") and desc.endswith("'"):
        desc = desc[1:-1]
    desc = re.sub(r'\s+', ' ', desc)
    return desc


def update_skill_description(skill_path: Path, new_description: str) -> None:
    """Update the description field in SKILL.md frontmatter."""
    skill_file = skill_path / "SKILL.md"
    content = skill_file.read_text()

    pattern = r'(description:\s*)(["\'].*?["\']|\S.*?)(\n(?=\w)|$)'
    escaped = new_description.replace('\\', '\\\\').replace('"', '\\"')
    replacement = r'\1"' + escaped + r'"\3'

    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    if new_content == content:
        pattern = r'(description:\s*\|?\s*\n?)(.*?)(?=\n\w|\n---)'
        new_content = re.sub(pattern, f'\\1"{escaped}"', content, count=1, flags=re.DOTALL)

    skill_file.write_text(new_content)
    print(f"Description updated in {skill_file}")


def test_trigger_once(query: str, description: str, skill_name: str, engine: EngineRunner) -> Optional[bool]:
    """Ask engine to classify whether this query should trigger the skill.

    Returns:
        True: query should trigger the skill
        False: query should NOT trigger the skill
        None: engine call timed out or failed (failure marker)
    """
    prompt = f"""You are a skill-triggering classifier. Given a skill named "{skill_name}" with this description:

"{description}"

Determine if the following user query SHOULD trigger this skill (i.e., the skill would be useful for handling this request).

Query: "{query}"

Reply with ONLY "YES" or "NO". No explanation."""

    stdout = engine.run(prompt, query_context=query)
    if stdout is None:
        return None
    response = stdout.strip().upper()
    return "YES" in response[:10]


def evaluate_description(eval_set: list, description: str, skill_name: str,
                         engine: EngineRunner, runs_per_query: int = 1) -> dict:
    """Evaluate a description against an eval set.

    Returns history-shaped results: accuracy for scoring, plus per-query
    {pass, triggers, runs} so generate_report.py can render trigger rates.
    """
    results = []
    correct = 0
    total = len(eval_set)
    calls_before = engine.successful_calls

    print(f"  Evaluating description ({total} queries x {runs_per_query} runs)...")
    for i, item in enumerate(eval_set):
        query = item["query"]
        expected = item["should_trigger"]

        run_results = [
            test_trigger_once(query, description, skill_name, engine)
            for _ in range(runs_per_query)
        ]
        triggers = sum(1 for r in run_results if r is True)
        runs = runs_per_query

        # A query counts as correctly handled only if all runs succeeded without error
        # and the trigger behavior is consistent with expectation across all runs.
        all_succeeded = all(r is not None for r in run_results)
        if all_succeeded:
            if expected:
                passed = (triggers == runs)
            else:
                passed = (triggers == 0)
        else:
            passed = False

        results.append({
            "query": query,
            "should_trigger": expected,
            "expected_trigger": expected,
            "triggers": triggers,
            "runs": runs,
            "pass": passed,
            "passed": passed,
        })

        if passed:
            correct += 1

        status = "OK " if passed else "ERR"
        print(f"    [{i+1}/{total}] {status} trigger={triggers}/{runs} "
              f"(expected: {'trigger' if expected else 'no-trigger'}): {query[:80]}")

    calls_made = engine.successful_calls - calls_before
    if total > 0 and calls_made == 0:
        print(
            "\nError: Evaluation completed with 0 successful engine calls (all timed out or errored). Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    accuracy = correct / total if total > 0 else 0
    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "results": results,
    }


def propose_improvement(current_description: str, eval_results: dict, skill_name: str, engine: EngineRunner) -> str:
    """Ask engine to propose an improved description based on eval results."""
    failures = [r for r in eval_results["results"] if not r["passed"]]

    failure_details = "\n".join([
        f"- Query: \"{r['query']}\" | Expected: {'trigger' if r['expected_trigger'] else 'no-trigger'} | "
        f"Got: {r['triggers']}/{r['runs']} triggers"
        for r in failures
    ])

    prompt = f"""I have a skill named "{skill_name}" with this description:

"{current_description}"

When tested against a set of eval queries, the following failures occurred:

{failure_details}

Accuracy: {eval_results['correct']}/{eval_results['total']} ({eval_results['accuracy']:.0%})

Please propose an improved description that:
1. Makes the skill trigger correctly for queries that SHOULD use it
2. Avoids triggering for queries that should NOT use it
3. Is still concise (under 150 words)
4. Uses specific keywords and context cues

Reply with ONLY the new description text, nothing else."""

    stdout = engine.run(prompt, query_context="propose_improvement")
    if stdout is None:
        print("  [warn] Engine call failed while proposing improvement.", file=sys.stderr)
        return current_description
    new_desc = stdout.strip().strip('"\'')
    return new_desc if new_desc else current_description


def main():
    templates = load_engine_config()
    default_engine = os.environ.get("HERMES_SKILL_ENGINE", "auto")
    engine_choices = ["auto"] + [k for k in templates.keys() if k != "auto"]
    if default_engine not in engine_choices:
        engine_choices.append(default_engine)

    parser = argparse.ArgumentParser(description="Run description optimization loop (engine-agnostic)")
    parser.add_argument("--eval-set", required=True, help="Path to trigger eval set JSON")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--skill-name", default="", help="Skill name (from frontmatter if not provided)")
    parser.add_argument("--engine", choices=engine_choices, default=default_engine,
                        help="Engine to use: auto, agy, opencode, claude, or configured engine (default: HERMES_SKILL_ENGINE or auto)")
    parser.add_argument("--engine-cmd", default=None,
                        help="Free-form command template using {prompt} placeholder (parsed with shlex.split)")
    parser.add_argument("--model", default="Gemini 3.8 Flash (Medium)",
                        help="Model to use for agy (ignored by other engines)")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max optimization iterations")
    parser.add_argument("--train-split", type=float, default=0.6, help="Train/test split ratio")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Runs per query for a reliable trigger rate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for the train/test split")
    parser.add_argument("--timeout", type=int, default=120, help="Per-query engine timeout in seconds")
    parser.add_argument("--out-dir", default=".", help="Directory for the report files (default: current directory)")
    args = parser.parse_args()

    # Preflight: resolve the engine before any query
    if args.engine_cmd:
        cmd_template = shlex.split(args.engine_cmd)
        if not cmd_template:
            print("Error: --engine-cmd cannot be empty", file=sys.stderr)
            sys.exit(2)
        binary = cmd_template[0]
        if not shutil.which(binary):
            print(
                f"Error: Engine binary '{binary}' from --engine-cmd not found on PATH.\n"
                "No external engine is required: Phase 8 description optimization can be done in-session by the Hermes agent.\n"
                f"To use an external engine, install '{binary}' or specify an installed command via --engine-cmd '<command> {{prompt}}'.",
                file=sys.stderr,
            )
            sys.exit(2)
        resolved_engine_name = "custom"
        if any("{model}" in arg for arg in cmd_template):
            cmd_template = [arg.replace("{model}", args.model) for arg in cmd_template]
    else:
        if args.engine == "auto":
            auto_order = ["agy", "opencode", "claude"]
            selected = None
            resolved_template = None
            for candidate in auto_order:
                tmpl = templates.get(candidate, DEFAULT_TEMPLATES.get(candidate, []))
                bin_candidate = tmpl[0] if tmpl else candidate
                if shutil.which(bin_candidate):
                    selected = candidate
                    resolved_template = list(tmpl)
                    break

            if not selected:
                print(
                    "Error: No engine found on PATH under 'auto' (checked: agy, opencode, claude).\n"
                    "No external engine is required: Phase 8 description optimization can be done in-session by the Hermes agent.\n"
                    "To use an external engine, install one or specify a command via --engine-cmd '<command> {prompt}'.",
                    file=sys.stderr,
                )
                sys.exit(2)
            resolved_engine_name = selected
            cmd_template = resolved_template
        else:
            resolved_engine_name = args.engine
            if resolved_engine_name not in templates:
                print(
                    f"Error: Engine '{resolved_engine_name}' not configured.\n"
                    "No external engine is required: Phase 8 description optimization can be done in-session by the Hermes agent.\n"
                    "Configure the engine in ~/.hermes/skill-creator-engines.json or use --engine-cmd '<command> {prompt}'.",
                    file=sys.stderr,
                )
                sys.exit(2)
            cmd_template = list(templates[resolved_engine_name])
            binary = cmd_template[0] if cmd_template else resolved_engine_name
            if not shutil.which(binary):
                print(
                    f"Error: Engine '{resolved_engine_name}' binary '{binary}' not found on PATH.\n"
                    "No external engine is required: Phase 8 description optimization can be done in-session by the Hermes agent.\n"
                    f"To use an external engine, install '{binary}' or specify a command via --engine-cmd '<command> {{prompt}}'.",
                    file=sys.stderr,
                )
                sys.exit(2)

        # Substitute {model} if agy or if {model} is in template
        if resolved_engine_name == "agy" or any("{model}" in arg for arg in cmd_template):
            cmd_template = [arg.replace("{model}", args.model) for arg in cmd_template]

    engine = EngineRunner(cmd_template=cmd_template, engine_name=resolved_engine_name, timeout=args.timeout)

    skill_path = Path(args.skill_path)
    if not skill_path.exists():
        print(f"Error: skill path {skill_path} not found", file=sys.stderr)
        sys.exit(1)

    skill_name = args.skill_name
    if not skill_name:
        skill_file = skill_path / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text()
            match = re.search(r'^---\s*\n.*?name:\s*(.*?)\s*\n', content, re.DOTALL)
            if match:
                skill_name = match.group(1).strip()

    eval_set_path = Path(args.eval_set)
    if not eval_set_path.exists():
        print(f"Error: eval set {eval_set_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(eval_set_path) as f:
        eval_set = json.load(f)

    if not eval_set:
        print(f"Error: eval set {eval_set_path} is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Skill: {skill_name}")
    print(f"Engine: {resolved_engine_name} ({cmd_template[0]})")
    print(f"Eval set: {len(eval_set)} queries")
    print(f"Runs per query: {args.runs_per_query}")
    print(f"Max iterations: {args.max_iterations}")
    print()

    if args.seed is not None:
        random.seed(args.seed)
    random.shuffle(eval_set)
    split_idx = int(len(eval_set) * args.train_split)
    train_set = eval_set[:split_idx]
    test_set = eval_set[split_idx:]
    if not train_set:
        train_set = eval_set
        test_set = eval_set
    print(f"Train: {len(train_set)} queries, Test: {len(test_set)} queries")
    print()

    original_description = load_skill_description(skill_path)
    current_description = original_description
    print(f"Starting description: \"{current_description[:100]}...\"")
    print()

    best_description = current_description
    best_test_score = -1.0
    best_train_score = -1.0
    history = []
    iteration = 0

    for iteration in range(1, args.max_iterations + 1):
        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"{'='*60}")

        print("\n--- Train Set Evaluation ---")
        train_result = evaluate_description(train_set, current_description, skill_name, engine, args.runs_per_query)

        print("\n--- Test Set Evaluation ---")
        test_result = evaluate_description(test_set, current_description, skill_name, engine, args.runs_per_query)

        print(f"\n  Train accuracy: {train_result['accuracy']:.1%}")
        print(f"  Test accuracy:  {test_result['accuracy']:.1%}")

        history.append({
            "iteration": iteration,
            "description": current_description,
            "train_passed": train_result["correct"],
            "train_total": train_result["total"],
            "test_passed": test_result["correct"],
            "test_total": test_result["total"],
            "train_results": train_result["results"],
            "test_results": test_result["results"],
        })

        if test_result["accuracy"] > best_test_score:
            best_test_score = test_result["accuracy"]
            best_train_score = train_result["accuracy"]
            best_description = current_description
            print("  New best (by test score)!")

        if test_result["accuracy"] >= 1.0 and test_result["total"] > 0:
            print("\n  Perfect test score! Stopping early.")
            break

        if iteration < args.max_iterations:
            print("\n--- Proposing Improvement ---")
            new_description = propose_improvement(current_description, train_result, skill_name, engine)
            if new_description and new_description != current_description:
                print(f"  New description: \"{new_description[:120]}...\"")
                current_description = new_description
                update_skill_description(skill_path, current_description)
            else:
                print("  No improvement proposed. Stopping.")
                break

    if engine.successful_calls == 0:
        print("\nError: Evaluation completed with 0 successful engine calls. Aborting.", file=sys.stderr)
        sys.exit(1)

    if best_test_score < 0:
        best_test_score = 0.0
    if best_train_score < 0:
        best_train_score = 0.0

    print(f"\n{'='*60}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*60}")
    print(f"Best test accuracy: {best_test_score:.1%}")
    print(f"Best description: \"{best_description[:150]}...\"")

    update_skill_description(skill_path, best_description)

    report = {
        "skill_name": skill_name,
        "original_description": original_description,
        "best_description": best_description,
        "best_score": f"{best_test_score:.0%} (test)",
        "best_test_score": best_test_score,
        "best_train_score": best_train_score,
        "iterations_run": iteration,
        "train_size": len(train_set),
        "test_size": len(test_set),
        "runs_per_query": args.runs_per_query,
        "holdout": len(test_set),
        "history": history,
    }

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "description_optimization_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report written to {json_path}")

    try:
        html_path = out_dir / "description_optimization_report.html"
        html_path.write_text(generate_html(report, skill_name=skill_name))
        print(f"HTML report written to {html_path}")
    except Exception as e:
        print(f"[warn] could not generate HTML report: {e}")


if __name__ == "__main__":
    main()
