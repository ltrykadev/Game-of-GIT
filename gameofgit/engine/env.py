"""Subprocess environment hardening for quest-driven git invocations.

Both the engine's executor (running the player's commands) and the quest
seed/predicate helpers (setting up / inspecting the sandbox) need the same
env scrubbing: kill inherited GIT_* keys so the player's ambient config
can't leak into the sandbox, and pin locale so git's output is stable
English regardless of the player's LANG.
"""

import os


def hardened_env() -> dict[str, str]:
    """Return os.environ with GIT_* scrubbed and locale pinned to C."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    env["LANGUAGE"] = "C"
    return env
