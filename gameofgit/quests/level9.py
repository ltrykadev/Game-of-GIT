"""Level 9 — CONFIG GOD. user.name, user.email, --list."""
from pathlib import Path

from gameofgit.engine.quest import CheckResult, Quest, SessionState
from gameofgit.quests._helpers import run_git

_ALLOWED = frozenset({"config", "status"})

_SEED_NAME = "Anon"
_SEED_EMAIL = "seed@gameofgit.local"


def _seed_with_default_identity(sandbox: Path) -> None:
    run_git(["git", "init", "-q", "-b", "main"], cwd=sandbox)
    run_git(["git", "config", "user.name", _SEED_NAME], cwd=sandbox)
    run_git(["git", "config", "user.email", _SEED_EMAIL], cwd=sandbox)


def _config_value(sandbox: Path, key: str) -> str:
    return run_git(
        ["git", "config", key], cwd=sandbox, capture=True, check=False
    ).stdout.strip()


def _check_set_your_name(sandbox: Path, _state: SessionState) -> CheckResult:
    name = _config_value(sandbox, "user.name")
    if not name:
        return CheckResult(False, "user.name is empty.")
    if name == _SEED_NAME:
        return CheckResult(False, "Still the default — change user.name.")
    return CheckResult(True)


SET_YOUR_NAME = Quest(
    slug="set-your-name",
    title="Claim your true name.",
    brief=(
        "The repo's current `user.name` is `Anon`. Replace it with your real "
        "name (or whatever name you wish to sign commits with)."
    ),
    hints=(
        "`git config user.name \"Your Name\"`",
        "Add `--global` to set it for all your repositories — but the quest only needs the local config.",
    ),
    allowed=_ALLOWED,
    check=_check_set_your_name,
    xp=50,
    level=9,
    seed=_seed_with_default_identity,
)


def _check_set_your_email(sandbox: Path, _state: SessionState) -> CheckResult:
    email = _config_value(sandbox, "user.email")
    if not email:
        return CheckResult(False, "user.email is empty.")
    if email == _SEED_EMAIL:
        return CheckResult(False, "Still the seeded email — change user.email.")
    if "@" not in email:
        return CheckResult(False, "That doesn't look like an email (no @).")
    return CheckResult(True)


SET_YOUR_EMAIL = Quest(
    slug="set-your-email",
    title="Seal your correspondence.",
    brief=(
        "Set `user.email` to a real email address. Anything with `@` in it "
        "will do — this is a sandbox."
    ),
    hints=(
        "`git config user.email \"you@example.com\"`",
        "Git doesn't verify the address — any `@`-containing string works.",
    ),
    allowed=_ALLOWED,
    check=_check_set_your_email,
    xp=50,
    level=9,
    seed=_seed_with_default_identity,
)


def _check_list_the_config(sandbox: Path, state: SessionState) -> CheckResult:
    for argv in state.all_argv:
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "config" and argv[2] in ("--list", "-l"):
            return CheckResult(True)
    return CheckResult(False, "Try `git config --list`.")


LIST_THE_CONFIG = Quest(
    slug="list-the-config",
    title="Read the laws of your realm.",
    brief="Ask git to print every configured setting it can see, from every level.",
    hints=(
        "`git config --list` prints everything.",
        "Add `--show-origin` to see which file each setting came from.",
    ),
    allowed=_ALLOWED,
    check=_check_list_the_config,
    xp=100,
    level=9,
    seed=_seed_with_default_identity,
)
