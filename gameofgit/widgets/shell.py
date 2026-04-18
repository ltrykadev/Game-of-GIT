"""Left-pane shell widget: scrollback log + command input."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, RichLog


class CommandSubmitted(Message):
    """Emitted when the player presses Enter in the shell input."""

    def __init__(self, cmdline: str) -> None:
        super().__init__()
        self.cmdline = cmdline


class CommandChanged(Message):
    """Emitted on every keystroke in the shell input (before Enter)."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class ShellPane(Widget):
    """Left pane: shows command output history and accepts player input."""

    DEFAULT_CSS = ""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Suggestion text exposed for testing (mirrors QuestPane.title_text).
        self.suggestion_text: str = ""

    def compose(self) -> ComposeResult:
        yield RichLog(id="shell-log", wrap=True, markup=True, auto_scroll=True)
        yield Label("", id="shell-suggestion")
        yield Input(placeholder="git <command>...", id="shell-input")

    def on_mount(self) -> None:
        self.query_one("#shell-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmdline = event.value.strip()
        event.input.clear()
        # Clear the suggestion on submit.
        self.set_suggestion("")
        if cmdline:
            self.post_message(CommandSubmitted(cmdline))

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(CommandChanged(event.value))

    # ------------------------------------------------------------------
    # Public helpers called by app.py
    # ------------------------------------------------------------------

    def set_suggestion(self, text: str) -> None:
        """Update the suggestion label.  Empty string hides it visually."""
        self.suggestion_text = text
        self.query_one("#shell-suggestion", Label).update(text)

    def echo(self, text: str) -> None:
        """Echo the player's input line in dim style."""
        log = self.query_one("#shell-log", RichLog)
        log.write(f"[dim]$ {text}[/dim]")

    def write_stdout(self, text: str) -> None:
        """Write normal git stdout output."""
        log = self.query_one("#shell-log", RichLog)
        if text:
            log.write(text.rstrip())

    def write_stderr(self, text: str) -> None:
        """Write stderr / rejection output in red."""
        log = self.query_one("#shell-log", RichLog)
        if text:
            log.write(f"[red]{text.rstrip()}[/red]")

    def write_info(self, text: str) -> None:
        """Write an informational message (green success marker etc.)."""
        log = self.query_one("#shell-log", RichLog)
        log.write(f"[bold green]{text}[/bold green]")
