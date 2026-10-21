#!/usr/bin/env python3
"""Unit tests for validate.py — pure validation rules.

Run: python3 scripts/test_validate.py
"""

import os
import sys
import tempfile
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from validate import (
    _check_name,
    _check_description,
    _check_port_attribution,
    _check_hermes_requires,
    _check_references,
    _check_secrets,
    _check_root_docs,
    _is_secret_file,
    _find_secret_literals,
    _collect,
    parse_frontmatter,
    extract_hermes_requires,
)


def test_check_name():
    """_check_name: present, matches dir, valid pattern."""
    assert _check_name("", "foo") == "Frontmatter 'name' is missing or empty"
    assert _check_name("foo", "bar") == "Skill name 'foo' does not match directory 'bar'"
    # Name mismatch is checked first, before pattern
    assert _check_name("Foo", "foo") == "Skill name 'Foo' does not match directory 'foo'"
    assert _check_name("foo_bar", "foo_bar") == "Skill name 'foo_bar' must match pattern '^[a-z0-9][a-z0-9-]*$'"
    assert _check_name("foo-bar", "foo-bar") is None
    assert _check_name("foo123", "foo123") is None
    assert _check_name("  foo-bar  ", "foo-bar") is None  # strips whitespace

def test_check_description():
    """_check_description: present, <= 1024 chars."""
    assert _check_description("") == "Frontmatter 'description' is missing or empty"
    assert _check_description("x" * 1025) == "Description length (1025) exceeds 1024 characters"
    assert _check_description("x" * 1024) is None
    assert _check_description("  valid desc  ") is None  # strips whitespace


def test_check_port_attribution():
    """_check_port_attribution: port detection and attribution line."""
    fm_data = {}
    fm_text = ""
    lines_after_fm = ["", "<!-- adapted from foo/bar (MIT) -->", "# Title"]

    # Not a port -> ok
    assert _check_port_attribution(lines_after_fm, fm_data, fm_text) is None

    # Port via ported_from key
    fm_data = {"ported_from": "foo/bar"}
    assert _check_port_attribution(lines_after_fm, fm_data, fm_text) is None  # has attribution

    # Port via ported_from key, missing attribution
    lines_after_fm = ["", "# Title"]
    assert _check_port_attribution(lines_after_fm, fm_data, fm_text) is not None

    # Port via adapted_from in body (first line) - both HTML comment and plain work
    fm_data = {}
    fm_text = ""
    lines_after_fm = ["adapted from foo/bar (MIT)", "# Title"]
    assert _check_port_attribution(lines_after_fm, fm_data, fm_text) is None  # valid attribution

    # Port via adapted_from in HTML comment (first line)
    lines_after_fm = ["<!-- adapted from foo/bar (MIT) -->", "# Title"]
    assert _check_port_attribution(lines_after_fm, fm_data, fm_text) is None

def test_check_hermes_requires():
    """_check_hermes_requires: frontmatter or distribution.yaml."""
    import tempfile

    # In frontmatter
    fm_text = "hermes_requires: \">=0.21\"\n"
    assert _check_hermes_requires(fm_text, "/tmp") is None

    # In distribution.yaml
    with tempfile.TemporaryDirectory() as td:
        dist = os.path.join(td, "distribution.yaml")
        with open(dist, "w") as f:
            f.write("hermes_requires: \">=0.20\"\n")
        assert _check_hermes_requires("", td) is None

    # Missing entirely
    assert _check_hermes_requires("", "/nonexistent") == "Missing 'hermes_requires' declaration in frontmatter or distribution.yaml"

    # Commented out
    fm_text = "# hermes_requires: \">=0.21\"\n"
    assert _check_hermes_requires(fm_text, "/nonexistent") == "Missing 'hermes_requires' declaration in frontmatter or distribution.yaml"


def test_collect():
    """_collect: accumulates non-None errors."""
    assert _collect(None, None) == []
    assert _collect("err1", None) == ["err1"]
    assert _collect(None, "err2") == ["err2"]
    assert _collect("err1", "err2") == ["err1", "err2"]


def test_parse_frontmatter():
    """parse_frontmatter: basic parsing."""
    content = textwrap.dedent("""\
        ---
        name: test-skill
        description: "A test skill"
        tags:
          - tag1
          - tag2
        hermes_requires: ">=0.21"
        ---
        Body content
    """)
    data, fm_text, body, lines_after = parse_frontmatter(content)
    assert data["name"] == "test-skill"
    assert data["description"] == "A test skill"
    assert data["tags"] == ["tag1", "tag2"]
    assert data["hermes_requires"] == ">=0.21"
    assert "Body content" in body


def test_parse_frontmatter_nested():
    """parse_frontmatter: nested mapping."""
    content = textwrap.dedent("""\
        ---
        compatibility:
          engine: hermes
          optional_engines:
            - agy
            - opencode
        ---
    """)
    data, _, _, _ = parse_frontmatter(content)
    assert data["compatibility"]["engine"] == "hermes"
    assert data["compatibility"]["optional_engines"] == ["agy", "opencode"]


def test_parse_frontmatter_inline_comment():
    """parse_frontmatter: strips inline comments."""
    content = textwrap.dedent("""\
        ---
        name: test # this is a comment
        description: "desc # not a comment"
        ---
    """)
    data, _, _, _ = parse_frontmatter(content)
    assert data["name"] == "test"
    assert data["description"] == "desc # not a comment"


def test_parse_frontmatter_multiline_rejected():
    """parse_frontmatter: rejects multiline scalars."""
    content = textwrap.dedent("""\
        ---
        desc: |
          multiline
        ---
    """)
    try:
        parse_frontmatter(content)
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "Multiline scalars" in str(e)


def test_extract_hermes_requires():
    """extract_hermes_requires: extracts valid semver (with quotes preserved, no comment stripping)."""
    assert extract_hermes_requires('hermes_requires: \">=0.21\"\n') == '">=0.21"'
    assert extract_hermes_requires("hermes_requires: '^0.20.1'\n") == "'^0.20.1'"
    # Inline comments are NOT stripped - returns raw value
    assert extract_hermes_requires('hermes_requires: \">=0.21\" # comment\n') == '">=0.21" # comment'
    assert extract_hermes_requires("# hermes_requires: \">=0.21\"\n") is None
    assert extract_hermes_requires("") is None
    assert extract_hermes_requires("hermes_requires: \n") is None

def test_validate_integration():
    """Integration: validate_skill on a minimal valid skill."""
    from validate import validate_skill

    with tempfile.TemporaryDirectory() as td:
        skill_dir = os.path.join(td, "test-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(textwrap.dedent("""\
                ---
                name: test-skill
                description: "A test skill for validation"
                tags:
                  - test
                hermes_requires: ">=0.21"
                ---
                # Test Skill
            """))
        errors = validate_skill(skill_dir)
        assert errors == [], f"unexpected errors: {errors}"


def test_validate_name_mismatch():
    """validate_skill: early exit on name mismatch."""
    from validate import validate_skill

    with tempfile.TemporaryDirectory() as td:
        skill_dir = os.path.join(td, "correct-name")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(textwrap.dedent("""\
                ---
                name: wrong-name
                description: "Test"
                hermes_requires: ">=0.21"
                ---
            """))
        errors = validate_skill(skill_dir)
        assert len(errors) == 1
        assert "does not match directory" in errors[0]


def test_is_secret_file():
    """_is_secret_file: credential files flagged, templates allowed."""
    assert _is_secret_file(".env") is True
    assert _is_secret_file(".env.local") is True
    assert _is_secret_file("server.pem") is True
    assert _is_secret_file("cert.p12") is True
    assert _is_secret_file(".env.example") is False
    assert _is_secret_file(".env.template") is False
    assert _is_secret_file("SKILL.md") is False
    assert _is_secret_file("environment.md") is False


def test_find_secret_literals():
    """_find_secret_literals: credential shapes flagged, placeholders ignored."""
    assert _find_secret_literals("key = sk-" + "a" * 32) == ["provider key"]
    assert _find_secret_literals("token ghp_" + "b" * 36) == ["github token"]
    assert _find_secret_literals("id AKIA" + "C" * 16) == ["aws access key id"]
    assert "private key block" in _find_secret_literals(
        "-----BEGIN RSA PRIVATE KEY-----"
    )
    # placeholders and env references are not credentials
    assert _find_secret_literals("sk-EXAMPLEKEYEXAMPLEKEYEXAMPLEKEY12") == []
    assert _find_secret_literals("Bearer $DEEPSEEK_API_KEY") == []
    assert _find_secret_literals("export DEEPSEEK_API_KEY=$(cat key)") == []


def test_check_secrets():
    """_check_secrets: reports credential files and literals, values never echoed."""
    with tempfile.TemporaryDirectory() as tmp:
        skill = os.path.join(tmp, "my-skill")
        os.makedirs(os.path.join(skill, "scripts"))
        with open(os.path.join(skill, "SKILL.md"), "w") as f:
            f.write("---\nname: my-skill\n---\n")
        with open(os.path.join(skill, ".env"), "w") as f:
            f.write("DEEPSEEK_API_KEY=sk-realsecretvalue1234567890ab\n")
        with open(os.path.join(skill, "scripts", "run.py"), "w") as f:
            f.write('KEY = "sk-' + "z" * 32 + '"\n')

        errors = _check_secrets(skill)
        assert any(".env" in e for e in errors), errors
        assert any("provider key" in e for e in errors), errors
        # the credential value must not appear in the error text
        assert not any("z" * 32 in e for e in errors), errors

        os.remove(os.path.join(skill, ".env"))
        os.remove(os.path.join(skill, "scripts", "run.py"))
        with open(os.path.join(skill, ".env.example"), "w") as f:
            f.write("DEEPSEEK_API_KEY=\n")
        assert _check_secrets(skill) == []


def test_check_root_docs():
    """_check_root_docs: AGENTS.md must exist and stay within the line budget."""
    from validate import MAX_AGENTS_MD_LINES

    with tempfile.TemporaryDirectory() as tmp:
        assert _check_root_docs(tmp) == ["AGENTS.md is missing from the repository root"]

        with open(os.path.join(tmp, "AGENTS.md"), "w") as f:
            f.write("\n".join(["line"] * (MAX_AGENTS_MD_LINES + 1)))
        errors = _check_root_docs(tmp)
        assert errors and "line budget" in errors[0], errors

        with open(os.path.join(tmp, "AGENTS.md"), "w") as f:
            f.write("\n".join(["line"] * 10))
        assert _check_root_docs(tmp) == []


def test_validate_cli_single_skill():
    """CLI: validate a single skill by name and by path; unknown name fails."""
    import subprocess

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script = os.path.join(repo, "scripts", "validate.py")
    for target in ("deepseek-search", os.path.join("skills", "deepseek-search")):
        proc = subprocess.run(
            [sys.executable, script, target], capture_output=True, text=True, cwd=repo
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "PASS: deepseek-search" in proc.stdout
    proc = subprocess.run(
        [sys.executable, script, "no-such-skill"], capture_output=True, text=True, cwd=repo
    )
    assert proc.returncode == 1
    assert "skill not found" in proc.stderr


if __name__ == "__main__":
    import traceback

    tests = [
        test_check_name,
        test_check_description,
        test_check_port_attribution,
        test_check_hermes_requires,
        test_collect,
        test_parse_frontmatter,
        test_parse_frontmatter_nested,
        test_parse_frontmatter_inline_comment,
        test_parse_frontmatter_multiline_rejected,
        test_extract_hermes_requires,
        test_validate_integration,
        test_validate_name_mismatch,
        test_is_secret_file,
        test_find_secret_literals,
        test_check_secrets,
        test_check_root_docs,
        test_validate_cli_single_skill,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)