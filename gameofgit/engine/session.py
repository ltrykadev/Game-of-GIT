from dataclasses import dataclass
from pathlib import Path

from .executor import execute
from .parser import (
    DisallowedSubcommand,
    EmptyCommand,
    NotAGitCommand,
    parse,
)
from .quest import CheckResult, Quest
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
        try:
            if quest.seed is not None:
                quest.seed(self._sandbox.path)
            self._last_check: CheckResult = quest.check(self._sandbox.path)
        except Exception:
            self._sandbox.close()
            raise

    def run(self, cmdline: str) -> Outcome:
        try:
            argv = parse(cmdline, self._quest.allowed)
        except EmptyCommand:
            return Outcome("", "", 0, self._last_check)
        except NotAGitCommand as e:
            return Outcome(
                stdout="",
                stderr=f"{e.argv0}: command not available in this quest",
                exit_code=127,
                check=self._last_check,
            )
        except DisallowedSubcommand as e:
            return Outcome(
                stdout="",
                stderr=f"git: '{e.sub}' is not available in this level yet",
                exit_code=127,
                check=self._last_check,
            )

        result = execute(argv, cwd=self._sandbox.path)
        # Re-evaluate the predicate after every real subprocess invocation,
        # whether git succeeded or failed.
        self._last_check = self._quest.check(self._sandbox.path)
        return Outcome(result.stdout, result.stderr, result.exit_code, self._last_check)

    def close(self) -> None:
        self._sandbox.close()

    def __enter__(self) -> "QuestSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
