import pytest

from gameofgit.engine.parser import (
    DisallowedSubcommand,
    EmptyCommand,
    EngineError,
    MalformedCommand,
    NotAGitCommand,
    parse,
)

ALLOWED = frozenset({"init", "status", "add", "commit"})


def test_parse_simple_valid():
    assert parse("git init", ALLOWED) == ["git", "init"]


def test_parse_valid_with_arg():
    assert parse("git add README.md", ALLOWED) == ["git", "add", "README.md"]


def test_parse_valid_with_quoted_message():
    assert parse('git commit -m "hello world"', ALLOWED) == [
        "git",
        "commit",
        "-m",
        "hello world",
    ]


@pytest.mark.parametrize("cmdline", ["", "   ", "\t", "\n"])
def test_parse_empty_or_whitespace_raises(cmdline):
    with pytest.raises(EmptyCommand):
        parse(cmdline, ALLOWED)


def test_parse_non_git_raises():
    with pytest.raises(NotAGitCommand) as exc:
        parse("rm -rf /", ALLOWED)
    assert exc.value.argv0 == "rm"


def test_parse_disallowed_subcommand_raises():
    with pytest.raises(DisallowedSubcommand) as exc:
        parse("git rebase main", ALLOWED)
    assert exc.value.sub == "rebase"
    assert exc.value.allowed == ALLOWED


def test_parse_bare_git_raises_disallowed():
    with pytest.raises(DisallowedSubcommand) as exc:
        parse("git", ALLOWED)
    assert exc.value.sub == ""


def test_all_engine_errors_share_base():
    # Useful when the Session wants a single except EngineError: clause.
    assert issubclass(EmptyCommand, EngineError)
    assert issubclass(NotAGitCommand, EngineError)
    assert issubclass(DisallowedSubcommand, EngineError)
    assert issubclass(MalformedCommand, EngineError)


def test_parse_rejects_unclosed_quote():
    with pytest.raises(MalformedCommand):
        parse('git commit -m "unterminated', frozenset({"commit"}))
