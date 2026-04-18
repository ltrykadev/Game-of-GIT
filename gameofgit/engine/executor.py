import subprocess
from dataclasses import dataclass
from pathlib import Path

from gameofgit.engine.env import hardened_env


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


def execute(argv: list[str], cwd: Path, timeout_s: float = 5.0) -> ExecResult:
    """Run a validated argv against `cwd`. No quest logic, no validation.

    Returns ExecResult. Translates TimeoutExpired into exit_code=124 (GNU
    timeout convention). Never raises for ordinary subprocess failures —
    those just show up as non-zero exit codes.
    """
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=hardened_env(),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return ExecResult(completed.stdout, completed.stderr, completed.returncode)
    except subprocess.TimeoutExpired:
        return ExecResult(
            stdout="",
            stderr=f"Command timed out after {timeout_s}s and was killed.",
            exit_code=124,
        )
