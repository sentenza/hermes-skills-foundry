#!/usr/bin/env python3
"""Hermes Skills Foundry validation gate.

Validates skills against repository standards:
1. Structure: SKILL.md presence, valid YAML frontmatter, naming and length constraints.
2. Provenance: Attribution header for ported skills.
3. Compatibility: Declared hermes_requires version range.
4. Reference integrity: Referenced files in references/, assets/, and supporting
   dirs (scripts/, agents/, eval-viewer/) exist on disk — in SKILL.md for all
   dirs, and in references/*.md and agents/*.md for references/ and assets/.
5. Secret hygiene: No credential files (.env, *.pem, *.p12, *.pfx) and no
   credential literals inside a skill directory.
6. Root docs: AGENTS.md exists at the repository root and stays within its
   200-line budget, so the standard every agent reads stays scannable.
"""

import argparse
import concurrent.futures
import os
import re
import sys
from typing import Optional

# Pattern for skill identifier: lowercase alphanumeric characters and hyphens
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Attribution line pattern: adapted from <repo> (<LICENSE>)
ATTRIBUTION_PATTERN = re.compile(r"adapted from\s+\S+\s*\([^)]+\)", re.IGNORECASE)
# Reference link pattern under references/, assets/, or supporting dirs
REFERENCE_PATTERN = re.compile(
    r"(?:(?:\./|(?<=[\s(\[{<]))(?:references|assets|scripts|agents|eval-viewer)/[a-zA-Z0-9_.-/]+[^\s)\]`\"'>]*)"
)
# Documentation cross-links (references/ and assets/) may be named from any skill
# markdown file, not only SKILL.md, and MUST always resolve. scripts/, agents/ and
# eval-viewer/ are checked in SKILL.md only: reference docs legitimately name
# upstream script paths that do not exist in this skill.
DOC_REFERENCE_PATTERN = re.compile(
    r"(?:(?:\./|(?<=[\s(\[{<]))(?:references|assets|agents)/[a-zA-Z0-9_.-/]+[^\s)\]`\"'>]*)"
)


def extract_hermes_requires(text):
    """Extract hermes_requires value from text, or None if not found/invalid."""
    m = re.search(r"^\s*hermes_requires:\s*(.+)$", text, re.MULTILINE)
    if m:
        val = m.group(1).strip()
        if val and not val.startswith("#"):
            return val
    return None


def parse_frontmatter(content):
    """Parse YAML frontmatter delimited by --- from SKILL.md content.

    Supports a practical subset: simple scalars, quoted strings, lists,
    and one level of nested mappings. Rejects multiline scalars (|, >),
    anchors, and complex structures with a clear error.

    Returns:
        tuple: (data_dict, raw_fm_text, body_text, lines_after_fm)
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "", content, []

    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return None, "", content, []

    fm_lines = lines[1:closing_idx]
    fm_text = "\n".join(fm_lines)
    body_text = "\n".join(lines[closing_idx + 1:])
    lines_after_fm = lines[closing_idx + 1:]

    # Parse using a simple state machine
    data = {}
    stack = [(data, -1)]  # (current_dict, indent_level)
    i = 0

    while i < len(fm_lines):
        line = fm_lines[i]
        # Strip inline comments (but not inside quotes)
        in_single = in_double = False
        comment_pos = -1
        for idx, ch in enumerate(line):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                comment_pos = idx
                break
        if comment_pos >= 0:
            line = line[:comment_pos].rstrip()

        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Calculate indent
        indent = len(line) - len(line.lstrip())

        # Pop stack to current indent level
        while stack and indent <= stack[-1][1]:
            stack.pop()

        if not stack:
            return None, fm_text, body_text, lines_after_fm

        current_dict, _ = stack[-1]

        # Check for list item
        if stripped.startswith("- "):
            # List item: find the most recently created list in current_dict
            # (Python 3.7+ preserves insertion order)
            parent_key = None
            for k, v in current_dict.items():
                if isinstance(v, list):
                    parent_key = k
            if parent_key is None:
                raise ValueError(
                    f"List item at line {i+2} has no parent list key "
                    f"(in frontmatter, lists must follow a key:)"
                )
            item = stripped[2:].strip()
            # Strip quotes
            if (item.startswith('"') and item.endswith('"')) or (
                item.startswith("'") and item.endswith("'")
            ):
                item = item[1:-1]
            current_dict[parent_key].append(item)
            i += 1
            continue

        # Key: value pair
        m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", stripped)
        if not m:
            raise ValueError(
                f"Invalid frontmatter line {i+2}: '{line.strip()}' "
                f"(expected 'key: value' or '  - item')"
            )

        key = m.group(1)
        val_part = m.group(2).strip()

        # Detect multiline scalar indicators (not supported)
        if val_part in ("|", ">", "|-", ">-", "|+", ">+"):
            raise ValueError(
                f"Multiline scalars (|, >) not supported at line {i+2} "
                f"for key '{key}'. Use a single-line string."
            )

        # Check for nested mapping or list (value is empty, next lines indented more)
        if not val_part:
            # Peek ahead to find next non-empty, non-comment line
            j = i + 1
            while j < len(fm_lines) and (not fm_lines[j].strip() or fm_lines[j].strip().startswith("#")):
                j += 1
            if j < len(fm_lines):
                next_line = fm_lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())
                next_stripped = next_line.strip()
                if next_indent > indent:
                    if next_stripped.startswith("- "):
                        # List follows
                        current_dict[key] = []
                        i += 1
                        continue
                    else:
                        # Nested mapping
                        current_dict[key] = {}
                        stack.append((current_dict[key], indent))
                        i += 1
                        continue

        # Simple scalar value
        val = val_part
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        elif val_part == "":
            val = ""
        # Check if this key should start a list (next line is list item)
        elif i + 1 < len(fm_lines):
            next_stripped = fm_lines[i + 1].strip()
            if next_stripped.startswith("- "):
                current_dict[key] = []
                # Don't consume the list item here; let next iteration handle it
                i += 1
                continue

        current_dict[key] = val
        i += 1

    return data, fm_text, body_text, lines_after_fm


def check_reference_paths(skill_dir, text, pattern, source, checked):
    """Verify every path matched by `pattern` exists under `skill_dir`.

    Returns:
        list: Failure messages for paths that do not resolve.
    """
    errors = []
    for raw_ref in pattern.findall(text):
        clean_ref = re.sub(r"^\./", "", raw_ref).split("#")[0].split("?")[0]
        clean_ref = clean_ref.rstrip(".)]\">'")
        if not clean_ref or clean_ref in checked:
            continue
        checked.add(clean_ref)
        if not os.path.exists(os.path.join(skill_dir, clean_ref)):
            errors.append(
                f"Referenced path '{clean_ref}' does not exist on disk (from {source})"
            )
    return errors


# =============================================================================
# Pure validation rules — each returns error message (str) or None (ok).
# These have NO side effects: no I/O, no printing, no mutation.
# Easy to unit test in isolation.
# =============================================================================

def _check_name(name: str, dir_name: str) -> Optional[str]:
    """Validate skill name: present, matches directory, valid pattern."""
    name = name.strip()
    if not name:
        return "Frontmatter 'name' is missing or empty"
    if name != dir_name:
        return f"Skill name '{name}' does not match directory '{dir_name}'"
    if not NAME_PATTERN.match(name):
        return f"Skill name '{name}' must match pattern '^[a-z0-9][a-z0-9-]*$'"
    return None


def _check_description(description: str) -> Optional[str]:
    """Validate description: present, <= 1024 chars."""
    description = description.strip()
    if not description:
        return "Frontmatter 'description' is missing or empty"
    if len(description) > 1024:
        return f"Description length ({len(description)}) exceeds 1024 characters"
    return None


def _check_port_attribution(lines_after_fm: list[str], fm_data: dict, fm_text: str) -> Optional[str]:
    """
    Validate port attribution: if skill is ported (has ported_from key or
    'adapted from' in first non-empty line after frontmatter), it must have
    an attribution line of the form '<!-- adapted from <repo> (LICENSE) -->'
    immediately under the frontmatter.
    """
    has_ported_key = "ported_from" in fm_data or bool(
        re.search(r"^\s*ported_from\s*:", fm_text, re.MULTILINE)
    )
    # First non-empty line after frontmatter
    first_line = next((line.strip() for line in lines_after_fm if line.strip()), "")
    has_adapted = bool(ATTRIBUTION_PATTERN.search(first_line))

    if not (has_ported_key or has_adapted):
        return None  # not a port, no check needed

    if not (first_line and ATTRIBUTION_PATTERN.search(first_line)):
        return (
            "Ported skill requires an attribution line of the form "
            "'adapted from <repo> (<LICENSE>)' immediately under frontmatter"
        )
    return None


def _check_hermes_requires(fm_text: str, skill_dir: str) -> Optional[str]:
    """Validate hermes_requires: declared in frontmatter or distribution.yaml."""
    if extract_hermes_requires(fm_text):
        return None
    dist_file = os.path.join(skill_dir, "distribution.yaml")
    if os.path.isfile(dist_file):
        try:
            with open(dist_file, "r", encoding="utf-8") as df:
                if extract_hermes_requires(df.read()):
                    return None
        except Exception:
            pass
    return "Missing 'hermes_requires' declaration in frontmatter or distribution.yaml"


def _check_references(
    skill_dir: str,
    body: str,
    lines_after_fm: list[str],  # unused but kept for signature consistency
    verbose: bool = False,
) -> list[str]:
    """
    Validate all references in SKILL.md and documentation files.
    Returns list of errors (empty if all ok).
    """
    errors = []
    checked_refs = set()

    def v(msg):
        if verbose:
            print(f"  [verbose] {msg}")

    v("Checking references in SKILL.md")
    errors.extend(
        check_reference_paths(skill_dir, body, REFERENCE_PATTERN, "SKILL.md", checked_refs)
    )

    for rel_dir in ("references", "agents"):
        doc_dir = os.path.join(skill_dir, rel_dir)
        if not os.path.isdir(doc_dir):
            v(f"No {rel_dir}/ directory")
            continue
        v(f"Checking references in {rel_dir}/")
        for name in sorted(os.listdir(doc_dir)):
            if not name.endswith(".md"):
                continue
            try:
                with open(os.path.join(doc_dir, name), "r", encoding="utf-8") as dfh:
                    doc_text = dfh.read()
            except Exception:
                continue
            errors.extend(
                check_reference_paths(
                    skill_dir, doc_text, DOC_REFERENCE_PATTERN, f"{rel_dir}/{name}", checked_refs
                )
            )
    return errors


# Small combinator: collect all non-None results
def _collect(*checks: Optional[str]) -> list[str]:
    """Collect all error messages from validation checks."""
    return [c for c in checks if c is not None]


# The root AGENTS.md is the standard every agent reads. It has to stay
# scannable, so it carries a hard line budget.
MAX_AGENTS_MD_LINES = 200


def _check_root_docs(repo_root: str) -> list[str]:
    """Check the repository-root agent docs: AGENTS.md within its line budget."""
    errors = []
    path = os.path.join(repo_root, "AGENTS.md")
    if not os.path.isfile(path):
        return ["AGENTS.md is missing from the repository root"]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            line_count = len(fh.read().splitlines())
    except OSError as exc:
        return [f"Could not read AGENTS.md: {exc}"]
    if line_count > MAX_AGENTS_MD_LINES:
        errors.append(
            f"AGENTS.md is {line_count} lines, over the {MAX_AGENTS_MD_LINES}-line budget"
        )
    return errors


# =============================================================================
# Secret hygiene — a published skill must not carry credentials.
# =============================================================================

# Files that hold credentials by convention. Templates are allowed.
SECRET_FILE_PATTERN = re.compile(r"^\.env(\..*)?$", re.IGNORECASE)
SECRET_FILE_ALLOWLIST = {".env.example", ".env.sample", ".env.template"}
SECRET_FILE_SUFFIXES = (".pem", ".p12", ".pfx")

# Literal credential shapes worth refusing in a published skill.
SECRET_LITERAL_PATTERNS = (
    ("provider key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("aws access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

# Substrings that mark a token as documentation, not a live credential.
PLACEHOLDER_MARKERS = (
    "YOUR",
    "EXAMPLE",
    "PLACEHOLDER",
    "REPLACE",
    "XXXX",
    "FAKE",
    "DUMMY",
    "SAMPLE",
    "REDACTED",
    "CHANGEME",
)

# File types scanned for credential literals.
SCANNABLE_SUFFIXES = (
    ".md",
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".toml",
    ".cfg",
    ".ini",
    ".js",
    ".ts",
)


def _is_secret_file(name: str) -> bool:
    """True when a file name is a credential file (templates excluded)."""
    lowered = name.lower()
    if lowered in SECRET_FILE_ALLOWLIST:
        return False
    if SECRET_FILE_PATTERN.match(lowered):
        return True
    return lowered.endswith(SECRET_FILE_SUFFIXES)


def _find_secret_literals(text: str) -> list[str]:
    """Return labels of credential-shaped literals found in text.

    Values are never echoed back — only the kind of credential is reported.
    """
    found = []
    for label, pattern in SECRET_LITERAL_PATTERNS:
        for match in pattern.finditer(text):
            token = match.group(0).upper()
            if any(marker in token for marker in PLACEHOLDER_MARKERS):
                continue
            if label not in found:
                found.append(label)
    return found


def _check_secrets(skill_dir: str) -> list[str]:
    """Reject credential files and credential literals inside a skill directory."""
    errors = []
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules"}]
        for name in sorted(files):
            path = os.path.join(root, name)
            rel = os.path.relpath(path, skill_dir)
            if _is_secret_file(name):
                errors.append(f"Secret file '{rel}' must not be committed in a skill directory")
                continue
            if not name.lower().endswith(SCANNABLE_SUFFIXES):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            for label in _find_secret_literals(text):
                errors.append(f"Possible {label} literal in '{rel}' — remove it or use a placeholder")
    return errors



# =============================================================================
# Main validation orchestration — impure (I/O, logging), calls pure rules.
# =============================================================================

def validate_skill(skill_dir, verbose=False):
    """Validate a single skill directory against repository rules.

    Returns:
        list: List of failure error messages (empty if passed).
    """
    def v(msg):
        if verbose:
            print(f"  [verbose] {msg}")

    errors = []
    skill_name = os.path.basename(skill_dir)
    skill_file = os.path.join(skill_dir, "SKILL.md")

    v(f"Validating {skill_name}")

    # Gate 1: Structure - File presence (early return, no recovery)
    if not os.path.isfile(skill_file):
        return [f"SKILL.md does not exist in {skill_name}"]
    v("SKILL.md found")

    try:
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        return [f"Could not read SKILL.md: {exc}"]

    # Gate 1: Frontmatter syntax (early return)
    fm_data, fm_text, body, lines_after_fm = parse_frontmatter(content)
    if fm_data is None:
        return ["Missing or malformed YAML frontmatter delimited by '---'"]
    v("Frontmatter parsed successfully")

    # --- Pure validation rules (all run, all errors collected) ---
    errors.extend(_collect(
        _check_name(fm_data.get("name", ""), skill_name),
        _check_description(fm_data.get("description", "")),
        _check_port_attribution(lines_after_fm, fm_data, fm_text),
        _check_hermes_requires(fm_text, skill_dir),
    ))

    # Early exit on name mismatch (avoids cascading confusing errors)
    # Note: _check_name already returns the mismatch error, but we need
    # to stop before reference checks which depend on correct skill identity.
    name_err = _check_name(fm_data.get("name", ""), skill_name)
    if name_err and "does not match directory" in name_err:
        return [name_err]

    # Gate 1 (cont'd): Reference integrity (runs even if other gates fail)
    errors.extend(_check_references(skill_dir, body, lines_after_fm, verbose))

    # Gate 5: Secret hygiene — no credential files or literals in a skill
    errors.extend(_check_secrets(skill_dir))

    if verbose:
        if errors:
            v(f"FAIL: {len(errors)} error(s)")
        else:
            v("PASS")

    return errors


def main():
    """Main gate entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Hermes skills against repository standards."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed validation messages."
    )
    parser.add_argument(
        "-j", "--jobs", type=int, default=0, help="Number of parallel jobs (0 = CPU count)."
    )
    parser.add_argument(
        "skill",
        nargs="?",
        help="Validate only this skill (directory name or path), e.g. deepseek-search",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    skills_dir = os.path.join(repo_root, "skills")

    if not os.path.isdir(skills_dir):
        print("ERROR: skills directory not found", file=sys.stderr)
        return 1

    if args.skill:
        skill_path = (
            os.path.abspath(args.skill)
            if os.path.isdir(args.skill)
            else os.path.join(skills_dir, args.skill)
        )
        if not os.path.isdir(skill_path):
            print(f"ERROR: skill not found: {args.skill}", file=sys.stderr)
            return 1
        name = os.path.basename(skill_path)
        errors = validate_skill(skill_path, verbose=args.verbose)
        if errors:
            print(f"FAIL: {name}")
            for err in errors:
                print(f"  - {err}")
            print("\nOverall: 0 passed, 1 failed")
            return 1
        print(f"PASS: {name}")
        print("\nOverall: 1 passed, 0 failed")
        return 0

    skill_subdirs = [
        d
        for d in sorted(os.listdir(skills_dir))
        if os.path.isdir(os.path.join(skills_dir, d)) and not d.startswith(".")
    ]

    if not skill_subdirs:
        print("WARNING: no skills to validate", file=sys.stderr)
        return 1

    max_workers = args.jobs or min(32, (os.cpu_count() or 1) + 4)

    def validate_one(name):
        skill_path = os.path.join(skills_dir, name)
        return name, validate_skill(skill_path, verbose=args.verbose)

    passed_count = 0
    failed_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {executor.submit(validate_one, name): name for name in skill_subdirs}
        for future in concurrent.futures.as_completed(future_to_name):
            name, errors = future.result()
            if not errors:
                passed_count += 1
                print(f"PASS: {name}")
            else:
                failed_count += 1
                print(f"FAIL: {name}")
                for err in errors:
                    print(f"  - {err}")

    root_errors = _check_root_docs(repo_root)
    if root_errors:
        failed_count += 1
        print("FAIL: AGENTS.md")
        for err in root_errors:
            print(f"  - {err}")

    print(f"\nOverall: {passed_count} passed, {failed_count} failed")
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())