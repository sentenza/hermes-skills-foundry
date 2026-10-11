#!/usr/bin/env python3
"""Hermes Skills Foundry validation gate.

Validates skills against repository standards:
1. Structure: SKILL.md presence, valid YAML frontmatter, naming and length constraints.
2. Provenance: Attribution header for ported skills.
3. Compatibility: Declared hermes_requires version range.
4. Reference integrity: Referenced files in references/ and assets/ exist on disk.
"""

import argparse
import os
import re
import sys

# Pattern for skill identifier: lowercase alphanumeric characters and hyphens
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Attribution line pattern: adapted from <repo> (<LICENSE>)
ATTRIBUTION_PATTERN = re.compile(r"adapted from\s+\S+\s*\([^)]+\)", re.IGNORECASE)
# Reference link pattern under references/ or assets/
REFERENCE_PATTERN = re.compile(
    r"(?:(?:\./)?(?:references|assets)/[a-zA-Z0-9_.-]+[^\s)\]`\"'>]*)"
)


def parse_frontmatter(content):
    """Parse YAML frontmatter delimited by --- from SKILL.md content.

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

    fm_text = "\n".join(lines[1:closing_idx])
    body_text = "\n".join(lines[closing_idx + 1:])
    lines_after_fm = lines[closing_idx + 1:]

    data = {}
    current_key = None
    current_val_lines = []

    for line in lines[1:closing_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if m:
            if current_key:
                data[current_key] = " ".join(current_val_lines).strip()
                current_val_lines = []
            current_key = m.group(1)
            val_part = m.group(2).strip()
            if val_part not in (">", "|", ">-", "|-") and val_part:
                if (val_part.startswith('"') and val_part.endswith('"')) or (
                    val_part.startswith("'") and val_part.endswith("'")
                ):
                    val_part = val_part[1:-1]
                current_val_lines = [val_part]
            else:
                current_val_lines = []
        elif current_key and (line.startswith("  ") or line.startswith("\t")):
            val_line = stripped
            if val_line.startswith("- "):
                val_line = val_line[2:].strip()
            current_val_lines.append(val_line)

    if current_key:
        data[current_key] = " ".join(current_val_lines).strip()

    return data, fm_text, body_text, lines_after_fm


def validate_skill(skill_dir, verbose=False):
    """Validate a single skill directory against repository rules.

    Returns:
        list: List of failure error messages (empty if passed).
    """
    errors = []
    skill_name = os.path.basename(skill_dir)
    skill_file = os.path.join(skill_dir, "SKILL.md")

    # Gate 1: Structure - File presence
    if not os.path.isfile(skill_file):
        return [f"SKILL.md does not exist in {skill_name}"]

    try:
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        return [f"Could not read SKILL.md: {exc}"]

    # Gate 1: Structure - Frontmatter syntax and fields
    fm_data, fm_text, body, lines_after_fm = parse_frontmatter(content)
    if fm_data is None:
        errors.append("Missing or malformed YAML frontmatter delimited by '---'")
        return errors

    name = fm_data.get("name", "").strip()
    if not name:
        errors.append("Frontmatter 'name' is missing or empty")
    else:
        if name != skill_name:
            errors.append(f"Skill name '{name}' does not match directory '{skill_name}'")
        if not NAME_PATTERN.match(name):
            errors.append(f"Skill name '{name}' must match pattern '^[a-z0-9][a-z0-9-]*$'")

    description = fm_data.get("description", "").strip()
    if not description:
        errors.append("Frontmatter 'description' is missing or empty")
    elif len(description) > 1024:
        errors.append(f"Description length ({len(description)}) exceeds 1024 characters")

    # Gate 3: Provenance - Port check
    has_ported_key = "ported_from" in fm_data or bool(
        re.search(r"^\s*ported_from\s*:", fm_text, re.MULTILINE)
    )
    has_adapted_in_body = bool(re.search(r"\badapted from\b", body, re.IGNORECASE))

    if has_ported_key or has_adapted_in_body:
        # Check for attribution line immediately under frontmatter
        first_line = ""
        for line in lines_after_fm:
            s = line.strip()
            if s:
                first_line = s
                break
        if not (first_line and ATTRIBUTION_PATTERN.search(first_line)):
            errors.append(
                "Ported skill requires an attribution line of the form "
                "'adapted from <repo> (<LICENSE>)' immediately under frontmatter"
            )

    # Gate 4: Compatibility - Hermes version requirement
    has_compat = False
    fm_compat = re.search(r"^\s*hermes_requires:\s*(.+)$", fm_text, re.MULTILINE)
    if fm_compat and fm_compat.group(1).strip() and not fm_compat.group(1).strip().startswith("#"):
        has_compat = True
    else:
        dist_file = os.path.join(skill_dir, "distribution.yaml")
        if os.path.isfile(dist_file):
            try:
                with open(dist_file, "r", encoding="utf-8") as df:
                    dist_text = df.read()
                dist_compat = re.search(
                    r"^\s*hermes_requires:\s*(.+)$", dist_text, re.MULTILINE
                )
                if (
                    dist_compat
                    and dist_compat.group(1).strip()
                    and not dist_compat.group(1).strip().startswith("#")
                ):
                    has_compat = True
            except Exception:
                pass

    if not has_compat:
        errors.append(
            "Missing 'hermes_requires' declaration in frontmatter or distribution.yaml"
        )

    # Gate 1: Reference integrity - Path verification
    raw_refs = REFERENCE_PATTERN.findall(body)
    checked_refs = set()
    for raw_ref in raw_refs:
        clean_ref = re.sub(r"^\./", "", raw_ref).split("#")[0].split("?")[0]
        clean_ref = clean_ref.rstrip(".,;:)'\"]")
        if not clean_ref or clean_ref in checked_refs:
            continue
        checked_refs.add(clean_ref)

        ref_target = os.path.join(skill_dir, clean_ref)
        if not os.path.exists(ref_target):
            errors.append(f"Referenced path '{clean_ref}' does not exist on disk")

    return errors


def main():
    """Main gate entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Hermes skills against repository standards."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed validation messages."
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    skills_dir = os.path.join(repo_root, "skills")

    if not os.path.isdir(skills_dir):
        print("nothing to validate yet")
        return 0

    skill_subdirs = [
        d
        for d in sorted(os.listdir(skills_dir))
        if os.path.isdir(os.path.join(skills_dir, d)) and not d.startswith(".")
    ]

    if not skill_subdirs:
        print("nothing to validate yet")
        return 0

    passed_count = 0
    failed_count = 0

    for name in skill_subdirs:
        skill_path = os.path.join(skills_dir, name)
        errors = validate_skill(skill_path, verbose=args.verbose)

        if not errors:
            passed_count += 1
            print(f"PASS: {name}")
        else:
            failed_count += 1
            print(f"FAIL: {name}")
            for err in errors:
                print(f"  - {err}")

    print(f"\nOverall: {passed_count} passed, {failed_count} failed")
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
