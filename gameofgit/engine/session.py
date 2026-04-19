import shlex
from dataclasses import dataclass
from pathlib import Path

from .executor import execute
from .parser import (
    EmptyCommand,
    EngineError,
    parse,
)
from .quest import CheckResult, Quest, SessionState
from .sandbox import Sandbox


@dataclass(frozen=True)
class Outcome:
    stdout: str
    stderr: str
    exit_code: int
    check: CheckResult


class QuestSession:
    """One session per quest. Owns a sandbox; the UI talks only to this class."""

    def __init__(self, quest: Quest) -> None:
        self._quest = quest
        self._sandbox = Sandbox()
        self._last_argv: tuple[str, ...] | None = None
        self._all_argv: list[tuple[str, ...]] = []
        try:
            if quest.seed is not None:
                quest.seed(self._sandbox.path)
            self._last_check: CheckResult = self._run_check()
        except Exception:
            self._sandbox.close()
            raise

    def _state(self) -> SessionState:
        return SessionState(last_argv=self._last_argv, all_argv=list(self._all_argv))

    def _run_check(self) -> CheckResult:
        return self._quest.check(self._sandbox.path, self._state())

    def run(self, cmdline: str) -> Outcome:
        try:
            argv = parse(cmdline, self._quest.allowed)
        except EmptyCommand:
            return Outcome("", "", 0, self._last_check)
        except EngineError as e:
            return Outcome(
                stdout="",
                stderr=str(e),
                exit_code=127,
                check=self._last_check,
            )

        result = execute(argv, cwd=self._sandbox.path)
        # Only record successful runs — failed commands don't count as "done this".
        if result.exit_code == 0:
            recorded = tuple(argv)
            self._last_argv = recorded
            self._all_argv.append(recorded)
        self._last_check = self._run_check()
        return Outcome(result.stdout, result.stderr, result.exit_code, self._last_check)

    def close(self) -> None:
        self._sandbox.close()

    def __enter__(self) -> "QuestSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
