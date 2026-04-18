"""Right-pane quest widget: title, brief, status, hints, progress."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static

from gameofgit.engine import CheckResult, Quest


class QuestPane(Widget):
    """Right pane: displays current quest info, status and hints."""

    def __init__(self, quest: Quest, quest_index: int, total: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._quest = quest
        self._quest_index = quest_index
        self._total = total
        self._hints_revealed = 0
        # Title text exposed for testing
        self.title_text = quest.title

    def compose(self) -> ComposeResult:
        yield Label(self._quest.title, id="quest-title")
        yield Static(self._quest.brief, id="quest-brief")
        yield Label("", id="quest-status")
        yield Label("", id="quest-hints")
        yield Label("", id="quest-advance")
        yield Label(
            f"Quest {self._quest_index + 1} of {self._total}",
            id="quest-progress",
        )

    def on_mount(self) -> None:
        self._refresh_status(passed=False)

    # ------------------------------------------------------------------
    # Public API called by app.py
    # ------------------------------------------------------------------

    def set_check(self, check: CheckResult) -> None:
        """Update the status line based on the latest CheckResult."""
        self._refresh_status(check.passed)

    def reveal_next_hint(self) -> None:
        """Reveal the next hidden hint, if any remain."""
        hints = self._quest.hints
        if self._hints_revealed >= len(hints):
            return
        self._hints_revealed += 1
        revealed = hints[: self._hints_revealed]
        text = "\n".join(f"Hint {i + 1}: {h}" for i, h in enumerate(revealed))
        self.query_one("#quest-hints", Label).update(text)

    def show_advance_prompt(self) -> None:
        """Show the 'press n for next quest' prompt."""
        self.query_one("#quest-advance", Label).update(
            "[bold yellow]Quest complete! Press [n] for the next quest.[/bold yellow]"
        )

    def hide_advance_prompt(self) -> None:
        """Hide the advance prompt (e.g. when advancing)."""
        self.query_one("#quest-advance", Label).update("")

    def show_level_complete(self) -> None:
        """Replace advance prompt with level-complete message."""
        self.query_one("#quest-advance", Label).update(
            "[bold green]Level 1 complete! Well done.[/bold green]"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _refresh_status(self, passed: bool) -> None:
        status_label = self.query_one("#quest-status", Label)
        if passed:
            status_label.update("[bold green]Status: completed[/bold green]")
        else:
            status_label.update("Status: not yet")
