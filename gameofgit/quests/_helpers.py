"""Shared primitives for quest authoring.

These wrap the hardened subprocess runner and common repo-state queries so
individual quest files stay focused on *what* they test, not *how* to run git.
"""
import subprocess
from pathlib import Path

from gameofgit.engine.env import hardened_env


def run_git(
    args: list[str],
    cwd: Path,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git (or any) command under the hardened env, from `cwd`.

    Raises CalledProcessError on non-zero exit by default (check=True). Pass
    check=False when the failure is an expected outcome you want to inspect.
    """
    return subprocess.run(
        args,
        cwd=cwd,
        env=hardened_env(),
        capture_output=capture,
        text=True,
        check=check,
    )


def set_identity(cwd: Path) -> None:
    """Configure a local git identity so commits can succeed regardless of
    the player's global ~/.gitconfig."""
    run_git(["git", "config", "user.email", "player@gameofgit.local"], cwd=cwd)
    run_git(["git", "config", "user.name", "Player"], cwd=cwd)


def commit_file(cwd: Path, path: str, content: str, msg: str) -> None:
    """Write `content` to `path` (relative to cwd), stage, and commit with `msg`.

    Assumes `cwd` is already an initialized repo with an identity set.
    """
    file = cwd / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    run_git(["git", "add", path], cwd=cwd)
    run_git(["git", "commit", "-q", "-m", msg], cwd=cwd)


def head_exists(cwd: Path) -> bool:
    result = run_git(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=cwd,
        capture=True,
        check=False,
    )
    return result.returncode == 0


def commit_count(cwd: Path) -> int:
    if not head_exists(cwd):
        return 0
    result = run_git(["git", "rev-list", "--count", "HEAD"], cwd=cwd, capture=True)
    return int(result.stdout.strip() or 0)


def branch_exists(cwd: Path, name: str) -> bool:
    result = run_git(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"],
        cwd=cwd,
        check=False,
    )
    return result.returncode == 0


def working_tree_clean(cwd: Path) -> bool:
    result = run_git(["git", "status", "--porcelain"], cwd=cwd, capture=True)
    return result.stdout.strip() == ""


def head_message(cwd: Path) -> str:
    result = run_git(["git", "log", "-1", "--pretty=%s", "HEAD"], cwd=cwd, capture=True)
    return result.stdout.strip()
