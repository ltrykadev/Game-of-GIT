from pathlib import Path

from gameofgit.engine.quest import Quest
from gameofgit.engine.session import QuestSession


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
