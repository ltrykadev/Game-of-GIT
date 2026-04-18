"""Smoke tests: verify the Textual app launches and quest flow works end-to-end."""

import pytest

from gameofgit.app import GameOfGitApp
from gameofgit.widgets.quest_pane import QuestPane


@pytest.mark.asyncio
async def test_app_launches_with_first_quest():
    """App starts up and the quest pane shows the first quest (about a repository)."""
    app = GameOfGitApp()
    async with app.run_test() as pilot:
        assert "repository" in app.query_one(QuestPane).title_text.lower()


@pytest.mark.asyncio
async def test_typing_git_init_completes_first_quest():
    """Typing 'git init' in the shell and pressing Enter passes the first quest."""
    app = GameOfGitApp()
    async with app.run_test() as pilot:
        # Type each character; space becomes the 'space' key name
        await pilot.press("g", "i", "t", "space", "i", "n", "i", "t")
        await pilot.press("enter")
        await pilot.pause()
        assert app._session._last_check.passed is True
