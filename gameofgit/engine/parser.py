import shlex


class EngineError(Exception):
    """Base class for engine-level command rejections."""


class EmptyCommand(EngineError):
    """The command line parsed to an empty argv (empty string or whitespace)."""


class NotAGitCommand(EngineError):
    """argv[0] is not 'git'."""

    def __init__(self, argv0: str) -> None:
        super().__init__(argv0)
        self.argv0 = argv0


class DisallowedSubcommand(EngineError):
    """argv[1] is missing or not in the quest's allowed set."""

    def __init__(self, sub: str, allowed: frozenset[str]) -> None:
        super().__init__(sub)
        self.sub = sub
        self.allowed = allowed


def parse(cmdline: str, allowed: frozenset[str]) -> list[str]:
    argv = shlex.split(cmdline)
    if not argv:
        raise EmptyCommand()
    if argv[0] != "git":
        raise NotAGitCommand(argv[0])
    sub = argv[1] if len(argv) >= 2 else ""
    if sub not in allowed:
        raise DisallowedSubcommand(sub, allowed)
    return argv
