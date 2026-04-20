from pathlib import Path

from gameofgit.engine.quest import Quest
from gameofgit.engine.session import QuestSession
from gameofgit.quests._helpers import run_git


def _play_through(session: QuestSession, slug: str) -> None:
    """Drive a quest to completion using only session.run() + filesystem writes.

    File writes (outside the whitelist) mirror what a real UI would allow
    the player to do via a text-editor pane.
    """
    sandbox: Path = session._sandbox.path
    if slug == "init-repo":
        session.run("git init")
    elif slug == "stage-a-file":
        (sandbox / "README.md").write_text("hello\n")
        session.run("git add README.md")
    elif slug == "first-commit":
        # Seed has already staged a file; all that's left is committing.
        session.run('git commit -m "initial commit"')
    elif slug == "meaningful-message":
        (sandbox / "new.txt").write_text("new content\n")
        session.run("git add new.txt")
        session.run('git commit -m "Add greeting to new file"')
    elif slug == "read-the-log":
        session.run("git log")
    elif slug == "spot-the-diff":
        session.run("git diff")
    elif slug == "inspect-a-commit":
        # Pick the parent of HEAD (an older commit) and `git show` it.
        out = session.run("git log --pretty=%H -n 2")
        sha = out.stdout.splitlines()[-1]
        session.run(f"git show {sha}")
    elif slug == "list-the-branches":
        session.run("git branch")
    elif slug == "make-a-branch":
        session.run("git branch kingsguard")
    elif slug == "switch-and-return":
        session.run("git checkout dragonstone")
        session.run("git checkout main")
    elif slug == "fast-forward-merge":
        # Seed leaves us on main; feature is ahead by 2 commits.
        session.run("git merge feature")
    elif slug == "rebase-a-branch":
        session.run("git checkout feature")
        session.run("git rebase main")
    elif slug == "cherry-pick-one":
        # Pick the middle of three commits on `experiment`.
        out = session.run("git log experiment --pretty=%H")
        middle_sha = out.stdout.splitlines()[1]
        session.run(f"git cherry-pick {middle_sha}")
    elif slug == "resolve-the-conflict":
        # Merging rebellion into main collides on throne.txt — that's expected.
        session.run("git merge rebellion")
        # The UI would let the player edit the file; simulate that here.
        (sandbox / "throne.txt").write_text("The Iron Throne stands resolute.\n")
        session.run("git add throne.txt")
        session.run('git commit -m "resolve: throne"')
    elif slug == "inspect-remotes":
        session.run("git remote -v")
    elif slug == "fetch-the-news":
        session.run("git fetch origin")
    elif slug == "push-your-work":
        session.run("git push origin main")
    elif slug == "unstage-a-file":
        session.run("git restore --staged oath.txt")
    elif slug == "undo-a-commit-keep-work":
        session.run("git reset --soft HEAD~1")
    elif slug == "revert-a-public-commit":
        # Grab the middle (bad) SHA directly — not part of the quest flow we're testing.
        bad_sha = run_git(
            ["git", "log", "--pretty=%H"], cwd=sandbox, capture=True
        ).stdout.splitlines()[1]
        session.run(f"git revert --no-edit {bad_sha}")
    elif slug == "stash-your-changes":
        session.run("git stash")
    elif slug == "list-the-stashes":
        session.run("git stash list")
    elif slug == "pop-a-stash":
        session.run("git stash pop")
    elif slug == "remove-a-tracked-file":
        session.run("git rm scroll.txt")
        session.run('git commit -m "drop scroll"')
    elif slug == "rename-a-file":
        session.run("git mv oldname.txt newname.txt")
        session.run('git commit -m "rename"')
    elif slug == "amend-your-last-commit":
        session.run('git commit --amend -m "Properly describe the work"')
    elif slug == "set-your-name":
        session.run('git config user.name "Robb Stark"')
    elif slug == "set-your-email":
        session.run('git config user.email "robb@winterfell.north"')
    elif slug == "list-the-config":
        session.run("git config --list")
    elif slug == "read-the-reflog":
        session.run("git reflog")
    elif slug == "blame-a-line":
        session.run("git blame chronicle.txt")
    elif slug == "tag-a-release":
        session.run('git tag -a v1.0 -m "first release"')
    elif slug == "find-the-bug":
        session.run("git bisect start")
        session.run("git bisect bad HEAD")
        first = run_git(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            cwd=sandbox, capture=True,
        ).stdout.strip()
        session.run(f"git bisect good {first}")
        session.run("git bisect run ./bisect_test.sh")
    else:
        raise AssertionError(f"no playthrough defined for slug: {slug}")


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
