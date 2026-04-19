"""Tests for gameofgit.quests._helpers — shared quest-authoring primitives."""
from pathlib import Path

from gameofgit.quests._helpers import (
    branch_exists,
    commit_count,
    commit_file,
    head_exists,
    head_message,
    run_git,
    set_identity,
    working_tree_clean,
)


def test_run_git_returns_completed_process(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    result = run_git(["git", "status", "--porcelain"], cwd=tmp_path, capture=True)
    assert result.returncode == 0
    assert result.stdout == ""


def test_set_identity_configures_user(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    email = run_git(["git", "config", "user.email"], cwd=tmp_path, capture=True).stdout.strip()
    name = run_git(["git", "config", "user.name"], cwd=tmp_path, capture=True).stdout.strip()
    assert email and name


def test_commit_file_creates_a_commit(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    commit_file(tmp_path, "hello.txt", "world\n", "first")
    assert head_exists(tmp_path)
    assert commit_count(tmp_path) == 1
    assert head_message(tmp_path) == "first"


def test_head_exists_false_on_fresh_repo(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    assert head_exists(tmp_path) is False


def test_branch_exists_detects_named_branches(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    commit_file(tmp_path, "a.txt", "a\n", "a")
    run_git(["git", "branch", "feature"], cwd=tmp_path)
    assert branch_exists(tmp_path, "feature")
    assert not branch_exists(tmp_path, "ghost")


def test_working_tree_clean_detects_modifications(tmp_path):
    run_git(["git", "init", "-q"], cwd=tmp_path)
    set_identity(tmp_path)
    commit_file(tmp_path, "a.txt", "a\n", "a")
    assert working_tree_clean(tmp_path)
    (tmp_path / "a.txt").write_text("changed\n")
    assert not working_tree_clean(tmp_path)
