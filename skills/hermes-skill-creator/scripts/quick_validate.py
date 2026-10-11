#!/usr/bin/env python3
# Copyright 2026 Alfredo Torre (sentenza).
# Derived from anthropics/skills skill-creator (Apache-2.0); modified for the Hermes Agent. See NOTICE.
"""
Quick validation script for skills - minimal, self-contained version.

Uses PyYAML when available; otherwise falls back to a small frontmatter
parser so the script works on hosts without PyYAML installed.
"""

import sys
import re
from pathlib import Path

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except ImportError:  # pragma: no cover - exercised on minimal hosts
    _HAVE_YAML = False


def _parse_frontmatter_minimal(text: str) -> dict:
    """Parse a flat-ish YAML frontmatter block without PyYAML.

    Handles top-level `key: value` scalars and `key:` followed by an indented
    block (list or nested map, collected as a list of strings). Enough for
    skill frontmatter validation, not a general YAML parser.
    """
    data: dict = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if raw[:1].isspace():  # indented line outside a block we already consumed
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", raw)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            block = []
            i += 1
            while i < len(lines) and (lines[i][:1].isspace() or lines[i].strip() == ""):
                if lines[i].strip():
                    block.append(lines[i].strip())
                i += 1
            data[key] = block
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key] = value
        i += 1
    return data


def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter (PyYAML preferred, minimal parser fallback)
    if _HAVE_YAML:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            return False, f"Invalid YAML in frontmatter: {e}"
    else:
        frontmatter = _parse_frontmatter_minimal(frontmatter_text)

    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    # Allowed frontmatter properties.
    # Hermes Agent skills additionally use `tags`, `related_skills` and
    # `hermes_requires` (see the Hermes skill conventions, the Hermes Skills
    # Foundry standard, and the hermes-skill-creator skill).
    ALLOWED_PROPERTIES = {
        'name', 'description', 'license', 'allowed-tools', 'metadata',
        'compatibility', 'tags', 'related_skills', 'version', 'author',
        'hermes_requires',
    }

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        # Check naming convention (kebab-case: lowercase with hyphens)
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        # Check name length (max 64 characters per spec)
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        # Check for angle brackets
        if '<' in description or '>' in description:
            return False, "Description cannot contain angle brackets (< or >)"
        # Check description length (max 1024 characters per spec)
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate compatibility field if present (optional).
    # It may be a plain string, or a mapping (e.g. requires_agy: true) — both fine.
    compatibility = frontmatter.get('compatibility', '')
    if compatibility:
        if isinstance(compatibility, str):
            if len(compatibility) > 500:
                return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."
        elif not isinstance(compatibility, (dict, list)):
            return False, f"Compatibility must be a string or a mapping, got {type(compatibility).__name__}"

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
