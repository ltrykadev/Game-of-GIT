"""Unit tests for gameofgit.engine.suggest."""

import pytest

from gameofgit.engine.suggest import suggest

ALLOWED = frozenset({"init", "status", "add", "commit"})


# ---------------------------------------------------------------------------
# Empty / whitespace
# ---------------------------------------------------------------------------


def test_suggest_empty_input():
    assert suggest("", ALLOWED) is None
    assert suggest("   ", ALLOWED) is None


# ---------------------------------------------------------------------------
# Valid commands — should always return None
# ---------------------------------------------------------------------------


def test_suggest_valid_command_returns_none():
    assert suggest("git init", ALLOWED) is None
    assert suggest("git commit -m 'msg'", ALLOWED) is None
    assert suggest("git add .", ALLOWED) is None
    assert suggest("git status", ALLOWED) is None


# ---------------------------------------------------------------------------
# Case 1: argv[0] is a typo of "git"
# ---------------------------------------------------------------------------


def test_suggest_typo_of_git_itself():
    assert suggest("gti init", ALLOWED) == "git init"
    assert suggest("gi status", ALLOWED) == "git status"


# ---------------------------------------------------------------------------
# Case 2: argv[0] is missing "git" but IS in allowed
# ---------------------------------------------------------------------------


def test_suggest_git_missing_for_known_sub():
    assert suggest("init", ALLOWED) == "git init"
    assert suggest("commit -m 'x'", ALLOWED) == "git commit -m x"


# ---------------------------------------------------------------------------
# Case 3: argv[0] == "git" but argv[1] is a typo of an allowed subcommand
# ---------------------------------------------------------------------------


def test_suggest_typo_of_subcommand():
    assert suggest("git statsu", ALLOWED) == "git status"
    assert suggest("git cmmit", ALLOWED) == "git commit"


# ---------------------------------------------------------------------------
# Case 1+3 combined: both tokens are typos
# ---------------------------------------------------------------------------


def test_suggest_typo_in_both_tokens():
    # User mangled "git" AND the subcommand
    assert suggest("gti statsu", ALLOWED) == "git status"


# ---------------------------------------------------------------------------
# Case 4: no close match — return None
# ---------------------------------------------------------------------------


def test_suggest_no_close_match_returns_none():
    assert suggest("foobar baz", ALLOWED) is None
    assert suggest("git xyzzy", ALLOWED) is None


# ---------------------------------------------------------------------------
# Just "git" with no subcommand yet
# ---------------------------------------------------------------------------


def test_suggest_git_alone_returns_none():
    # Just "git" with no subcommand yet — nothing to correct
    assert suggest("git", ALLOWED) is None


# ---------------------------------------------------------------------------
# shlex error handling
# ---------------------------------------------------------------------------


def test_suggest_handles_shlex_error():
    # Unclosed quote — should not raise, returns None
    assert suggest('git commit -m "unterminated', ALLOWED) is None


# ---------------------------------------------------------------------------
# Trailing args are preserved after a subcommand fix
# ---------------------------------------------------------------------------


def test_suggest_preserves_trailing_args_after_fix():
    # shlex.join(["git", "commit", "-m", "hi"]) == "git commit -m hi"
    result = suggest("git cmmit -m 'hi'", ALLOWED)
    assert result == "git commit -m hi"
