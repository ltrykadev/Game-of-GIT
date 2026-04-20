from pathlib import Path
from typing import Callable

from gameofgit.engine.quest import Quest
from gameofgit.engine.session import QuestSession
from gameofgit.quests._helpers import run_git

Driver = Callable[[QuestSession], None]


def _stage_a_file(session: QuestSession) -> None:
    sandbox: Path = session._sandbox.path
    (sandbox / "README.md").write_text("hello\n")
    session.run("git add README.md")


def _meaningful_message(session: QuestSession) -> None:
    sandbox: Path = session._sandbox.path
    (sandbox / "new.txt").write_text("new content\n")
    session.run("git add new.txt")
    session.run('git commit -m "Add greeting to new file"')


def _inspect_a_commit(session: QuestSession) -> None:
    out = session.run("git log --pretty=%H -n 2")
    sha = out.stdout.splitlines()[-1]
    session.run(f"git show {sha}")


def _switch_and_return(session: QuestSession) -> None:
    session.run("git checkout dragonstone")
    session.run("git checkout main")


def _rebase_a_branch(session: QuestSession) -> None:
    session.run("git checkout feature")
    session.run("git rebase main")


def _cherry_pick_one(session: QuestSession) -> None:
    out = session.run("git log experiment --pretty=%H")
    middle_sha = out.stdout.splitlines()[1]
    session.run(f"git cherry-pick {middle_sha}")


def _resolve_the_conflict(session: QuestSession) -> None:
    # Merging rebellion into main collides on throne.txt — that's expected.
    # The UI would let the player edit the file; simulate that here.
    sandbox: Path = session._sandbox.path
    session.run("git merge rebellion")
    (sandbox / "throne.txt").write_text("The Iron Throne stands resolute.\n")
    session.run("git add throne.txt")
    session.run('git commit -m "resolve: throne"')


def _revert_a_public_commit(session: QuestSession) -> None:
    # Grab the middle (bad) SHA directly — not part of the quest flow we're testing.
    bad_sha = run_git(
        ["git", "log", "--pretty=%H"], cwd=session._sandbox.path, capture=True
    ).stdout.splitlines()[1]
    session.run(f"git revert --no-edit {bad_sha}")


def _remove_a_tracked_file(session: QuestSession) -> None:
    session.run("git rm scroll.txt")
    session.run('git commit -m "drop scroll"')


def _rename_a_file(session: QuestSession) -> None:
    session.run("git mv oldname.txt newname.txt")
    session.run('git commit -m "rename"')


def _find_the_bug(session: QuestSession) -> None:
    session.run("git bisect start")
    session.run("git bisect bad HEAD")
    first = run_git(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=session._sandbox.path,
        capture=True,
    ).stdout.strip()
    session.run(f"git bisect good {first}")
    session.run("git bisect run ./bisect_test.sh")


_DRIVERS: dict[str, Driver] = {
    "init-repo": lambda s: s.run("git init"),
    "stage-a-file": _stage_a_file,
    "first-commit": lambda s: s.run('git commit -m "initial commit"'),
    "meaningful-message": _meaningful_message,
    "read-the-log": lambda s: s.run("git log"),
    "spot-the-diff": lambda s: s.run("git diff"),
    "inspect-a-commit": _inspect_a_commit,
    "list-the-branches": lambda s: s.run("git branch"),
    "make-a-branch": lambda s: s.run("git branch kingsguard"),
    "switch-and-return": _switch_and_return,
    "fast-forward-merge": lambda s: s.run("git merge feature"),
    "rebase-a-branch": _rebase_a_branch,
    "cherry-pick-one": _cherry_pick_one,
    "resolve-the-conflict": _resolve_the_conflict,
    "inspect-remotes": lambda s: s.run("git remote -v"),
    "fetch-the-news": lambda s: s.run("git fetch origin"),
    "push-your-work": lambda s: s.run("git push origin main"),
    "unstage-a-file": lambda s: s.run("git restore --staged oath.txt"),
    "undo-a-commit-keep-work": lambda s: s.run("git reset --soft HEAD~1"),
    "revert-a-public-commit": _revert_a_public_commit,
    "stash-your-changes": lambda s: s.run("git stash"),
    "list-the-stashes": lambda s: s.run("git stash list"),
    "pop-a-stash": lambda s: s.run("git stash pop"),
    "remove-a-tracked-file": _remove_a_tracked_file,
    "rename-a-file": _rename_a_file,
    "amend-your-last-commit": lambda s: s.run(
        'git commit --amend -m "Properly describe the work"'
    ),
    "set-your-name": lambda s: s.run('git config user.name "Robb Stark"'),
    "set-your-email": lambda s: s.run(
        'git config user.email "robb@winterfell.north"'
    ),
    "list-the-config": lambda s: s.run("git config --list"),
    "read-the-reflog": lambda s: s.run("git reflog"),
    "blame-a-line": lambda s: s.run("git blame chronicle.txt"),
    "tag-a-release": lambda s: s.run('git tag -a v1.0 -m "first release"'),
    "find-the-bug": _find_the_bug,
}


def _play_through(session: QuestSession, slug: str) -> None:
    """Drive a quest to completion using only session.run() + filesystem writes.

    File writes (outside the whitelist) mirror what a real UI would allow
    the player to do via a text-editor pane.
    """
    driver = _DRIVERS.get(slug)
    if driver is None:
        raise AssertionError(f"no playthrough defined for slug: {slug}")
    driver(session)


def test_each_quest_starts_not_completed(quest: Quest):
    with QuestSession(quest) as s:
        assert s._last_check.passed is False


def test_each_quest_can_be_completed(quest: Quest):
    with QuestSession(quest) as s:
        _play_through(s, quest.slug)
        # Final "git status" is a cheap, state-preserving command that forces
        # one more re-check and gives the UI a clean "you're done" outcome.
        out = s.run("git status")
        assert out.exit_code == 0
        assert out.check.passed is True, out.check.detail


def test_quest_rejects_non_git_commands_without_breaking_state(quest: Quest):
    # Typing junk shouldn't affect whether the quest later succeeds.
    with QuestSession(quest) as s:
        out = s.run("rm -rf /")
        assert out.exit_code == 127
        # Now the quest should still be completable the normal way.
        _play_through(s, quest.slug)
        assert s.run("git status").check.passed is True
