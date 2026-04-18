"""Main Textual application for Game of GIT."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from gameofgit.engine import QuestSession
from gameofgit.quests import all_quests
from gameofgit.widgets.quest_pane import QuestPane
from gameofgit.widgets.shell import CommandSubmitted, ShellPane

_INSTRUCTIONS = (
    "Bindings: Enter submits, h reveals next hint, "
    "n advances after a quest passes, Ctrl+Q quits."
)

_CSS_PATH = Path(__file__).parent / "ui.tcss"
_QUESTS = list(all_quests())


class GameOfGitApp(App):
    """Two-pane Game of GIT application."""

    CSS_PATH = str(_CSS_PATH)

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("h", "hint", "Hint", show=True),
        Binding("n", "next_quest", "Next", show=True),
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

    def on_command_submitted(self, event: CommandSubmitted) -> None:
        shell = self.query_one(ShellPane)
        quest_pane = self.query_one(QuestPane)

        cmdline = event.cmdline
        shell.echo(cmdline)

        prev_passed = self._quest_passed
        outcome = self._session.run(cmdline)

        if outcome.stdout:
            shell.write_stdout(outcome.stdout)
        if outcome.stderr:
            shell.write_stderr(outcome.stderr)

        current_check = outcome.check
        quest_pane.set_check(current_check)
        self._quest_passed = current_check.passed

        # Show success marker the first time the quest passes
        if current_check.passed and not prev_passed:
            shell.write_info("Quest passed!")
            if self._quest_index < len(_QUESTS) - 1:
                quest_pane.show_advance_prompt()
            else:
                quest_pane.show_level_complete()

    # ------------------------------------------------------------------
    # Key binding actions
    # ------------------------------------------------------------------

    def action_hint(self) -> None:
        self.query_one(QuestPane).reveal_next_hint()

    def action_next_quest(self) -> None:
        if not self._quest_passed:
            return
        if self._quest_index >= len(_QUESTS) - 1:
            return

        # Tear down old session
        self._session.close()

        self._quest_index += 1
        quest = _QUESTS[self._quest_index]
        self._session = QuestSession(quest)
        self._quest_passed = self._session._last_check.passed

        # Replace quest pane
        old_pane = self.query_one(QuestPane)
        new_pane = QuestPane(
            quest,
            self._quest_index,
            len(_QUESTS),
            id="quest-pane",
        )
        old_pane.remove()
        self.query_one("#panes", Horizontal).mount(new_pane)
