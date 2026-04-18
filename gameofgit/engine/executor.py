import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


def _build_env() -> dict[str, str]:
    """Inherit the caller's env, but scrub anything that would disturb git's
    idea of where the repo is, and pin the locale so git's error strings are
    stable English (our predicates and tests match on them)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    env["LANGUAGE"] = "C"
    return env


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
            env=_build_env(),
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
