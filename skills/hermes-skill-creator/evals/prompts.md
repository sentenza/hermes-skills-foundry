# Evaluation Prompts: Hermes Skill Creator

This test suite defines evaluation scenarios for `hermes-skill-creator` covering the three primary workflows:

1. Turning a repeated manual workflow into a new skill.
2. Testing and iterating an existing draft `SKILL.md`.
3. Aligning a Hermes skill with an upstream from another agent ecosystem.

---

## Prompt 1: Create a New Skill from a Repeated Workflow

- **ID**: 1
- **Short Name**: `create-from-workflow`
- **Workflow Step**: Capture intent and draft a new skill

### User Prompt

> I keep doing the same tedious thing every sprint and I want to stop. When we cut a release, I manually: pull the merged PRs since the last tag, group them by conventional-commit type, check which ones touched the public API, draft the changelog section with breaking changes highlighted, bump the version, and tag. It takes me 40 minutes and I always forget the API-change check.
>
> Turn this into a Hermes skill so the agent does it next time. I care about: it should trigger when I say things like "cut the release", "draft the changelog", or "prepare the next version"; it must never push or tag without me seeing the drafted changelog first; and it should produce a markdown changelog block I can paste into the release notes. Give me a couple of realistic test cases too, and write the skill under a `release` category.

### Acceptance Assertions

1. `A skill directory is created under a 'release' category with a SKILL.md whose name matches its directory` (Objective: filesystem check + frontmatter name/dir equality).
2. `SKILL.md frontmatter contains name, a trigger-action description, and tags` (Objective: parse YAML frontmatter keys).
3. `The description encodes the trigger phrases ("cut the release", "draft the changelog", "prepare the next version")` (Objective: substring match on the description field).
4. `The skill body includes a safety rule requiring human review of the drafted changelog before any push or tag` (Objective: pattern match for the review-before-tag instruction).
5. `The skill declares the public-API-change check as an explicit workflow step` (Objective: pattern match for the API-check step).
6. `A test-case file is created with at least two realistic prompts` (Objective: parse the evals fixture and count prompts ≥ 2).
7. `The captured workflow genuinely removes the manual 40-minute routine rather than restating it` [Human-Reviewed].

---

## Prompt 2: Test and Improve a Draft Skill

- **ID**: 2
- **Short Name**: `evaluate-and-improve`
- **Workflow Step**: Run the evaluation loop and iterate

### User Prompt

> I drafted this skill for extracting tables out of PDFs into CSV and I think it's OK but I've never actually checked whether it works. Here's the SKILL.md at `/home/hermes-user/workspace/drafts/pdf-table-extract/SKILL.md`. Can you test it properly and improve it? I want to know whether the skill actually helps versus just asking the model cold, not a gut feeling. If it's bad, make it better and show me the before/after.

### Acceptance Assertions

1. `A workspace is created as a sibling of the skill directory, organised by iteration` (Objective: filesystem check for `<skill-name>-workspace/iteration-1/`).
2. `Each eval has a with-skill configuration and a without-skill (baseline) configuration, with more than one run each` (Objective: count `<config>/run-*` directories per eval, both configs present).
3. `A grading record is written per run using the field names text, passed, and evidence` (Objective: parse `run-*/grading.json` and check field names).
4. `An aggregated benchmark.json (and benchmark.md) exists with pass_rate per configuration and the delta` (Objective: parse `benchmark.json` for `configuration` and nested `result.pass_rate`).
5. `An HTML eval viewer is generated from the workspace and its path delivered to the user` (Objective: filesystem check for `eval_viewer.html` + delivery in the reply).
6. `At least one iteration of improvement is applied and rerun into a later iteration directory` (Objective: existence of `iteration-2/` after feedback).
7. `No evaluation record claims more than was measured (no all-green 'complete' status for an unrun suite)` (Objective: inspect recorded results for honest status).
8. `The improvement is general rather than overfit to the specific test prompts` [Human-Reviewed].

---

## Prompt 3: Align a Hermes Skill with an Upstream

- **ID**: 3
- **Short Name**: `port-align-upstream`
- **Workflow Step**: Selective port from another agent ecosystem

### User Prompt

> I've got a Hermes skill called `web-perf-audit` that I wrote from scratch, and I've since found that the `webapp-testing` skill in `anthropics/skills` does a much more thorough job of driving a browser for audits. I'd like to align mine with theirs — pull in what's genuinely better without wrecking the Hermes-specific bits (it uses the `delegate_task` runner and Hermes frontmatter keys). Be careful: theirs shells out to a Node/Playwright CLI I don't want to depend on. Show me what you'd change and why before doing it.

### Acceptance Assertions

1. `The upstream is inspected and its real capabilities verified before design (commands, files) rather than assumed` (Objective: evidence of upstream inspection in the transcript).
2. `Each upstream artefact is classified as engine-agnostic (portable) or engine-coupled (rewrite)` (Objective: presence of a per-file classification in the reply or notes).
3. `Engine-coupled pieces that shell out to a non-Hermes CLI are rewritten rather than copied verbatim` (Objective: pattern check that no Node/Playwright CLI dependency is introduced).
4. `The Hermes-specific choices already in the skill (delegate_task runner, Hermes frontmatter keys) are preserved` (Objective: diff check that those are unchanged).
5. `Divergences from upstream are recorded in an HTML comment at the end of SKILL.md` (Objective: pattern match for the upstream/divergences comment).
6. `The proposed changes are presented to the user before being applied` (Objective: reply contains a proposal preceding any edit).
7. `The result is a selective port, not a wholesale replacement, and stays coherent as a Hermes skill` [Human-Reviewed].
