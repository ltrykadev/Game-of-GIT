"""Left-pane shell widget: scrollback log + command input."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, RichLog


class CommandSubmitted(Message):
    """Emitted when the player presses Enter in the shell input."""

    def __init__(self, cmdline: str) -> None:
        super().__init__()
        self.cmdline = cmdline


class ShellPane(Widget):
    """Left pane: shows command output history and accepts player input."""

    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield RichLog(id="shell-log", wrap=True, markup=True, auto_scroll=True)
        yield Input(placeholder="git <command>...", id="shell-input")

    def on_mount(self) -> None:
        self.query_one("#shell-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmdline = event.value.strip()
        event.input.clear()
        if cmdline:
            self.post_message(CommandSubmitted(cmdline))

    # ------------------------------------------------------------------
    # Public helpers called by app.py
    # ------------------------------------------------------------------

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
