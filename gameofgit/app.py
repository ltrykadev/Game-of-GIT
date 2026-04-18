"""Main Textual application for Game of GIT."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from gameofgit.engine import QuestSession, suggest
from gameofgit.quests import all_quests
from gameofgit.widgets.quest_pane import QuestPane
from gameofgit.widgets.shell import CommandChanged, CommandSubmitted, ShellPane

_INSTRUCTIONS = (
    "Type a git command and press Enter. "
    "Type ? for a hint. Quests advance automatically. Ctrl+Q quits."
)

_CSS_PATH = Path(__file__).parent / "ui.tcss"
_QUESTS = list(all_quests())


class GameOfGitApp(App):
    """Two-pane Game of GIT application."""

    CSS_PATH = str(_CSS_PATH)

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._quest_index: int = 0
        self._session: QuestSession = QuestSession(_QUESTS[0])
        self._quest_passed: bool = self._session._last_check.passed

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(_INSTRUCTIONS, id="instructions")
        with Horizontal(id="panes"):
            yield ShellPane(id="shell-pane")
            yield QuestPane(
                _QUESTS[self._quest_index],
                self._quest_index,
                len(_QUESTS),
                id="quest-pane",
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_command_changed(self, event: CommandChanged) -> None:
        shell = self.query_one(ShellPane)
        allowed = self._session._quest.allowed
        correction = suggest(event.text, allowed)
        if correction is not None:
            shell.set_suggestion(f"Did you mean: {correction}?")
        else:
            shell.set_suggestion("")

    async def on_command_submitted(self, event: CommandSubmitted) -> None:
        shell = self.query_one(ShellPane)
        quest_pane = self.query_one(QuestPane)

        cmdline = event.cmdline
        shell.echo(cmdline)

        # '?' is a typed help command — reveal the next hint, skip the engine.
        if cmdline.strip() == "?":
            quest_pane.reveal_next_hint()
            return

        prev_passed = self._quest_passed
        outcome = self._session.run(cmdline)

        if outcome.stdout:
            shell.write_stdout(outcome.stdout)
        if outcome.stderr:
            shell.write_stderr(outcome.stderr)

        current_check = outcome.check
        quest_pane.set_check(current_check)
        self._quest_passed = current_check.passed

        if current_check.passed and not prev_passed:
            shell.write_info("Quest passed!")
            if self._quest_index < len(_QUESTS) - 1:
                await self._advance_to_next_quest()
            else:
                quest_pane.show_level_complete()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _advance_to_next_quest(self) -> None:
        self._session.close()
        self._quest_index += 1
        quest = _QUESTS[self._quest_index]
        self._session = QuestSession(quest)
        self._quest_passed = self._session._last_check.passed

        old_pane = self.query_one(QuestPane)
        await old_pane.remove()
        new_pane = QuestPane(
            quest,
            self._quest_index,
            len(_QUESTS),
            id="quest-pane",
        )
        self.query_one("#panes", Horizontal).mount(new_pane)
