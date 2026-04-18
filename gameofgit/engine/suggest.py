"""Typo-correction suggestions for shell input.

Pure function — no UI coupling, no external dependencies.
Uses difflib.get_close_matches (cutoff=0.6) to detect likely typos in the
entered git command and return a corrected command line.

Future refinement: Tab-to-accept (auto-complete the suggestion on Tab press)
is intentionally NOT implemented here. The player reads the suggestion and
types the corrected form themselves.
"""

import difflib
import shlex


def suggest(cmdline: str, allowed: frozenset[str]) -> str | None:
    """Return a corrected cmdline if the input looks like a typo of a valid command.

    Returns None when:
    - Input is empty or whitespace
    - shlex can't tokenize it (unclosed quotes, etc.)
    - Input is already valid (``git <allowed-sub> ...``)
    - No close match found for the likely-wrong token

    Uses difflib.get_close_matches with cutoff=0.6.

    Cases handled:
    1. argv[0] is a typo of "git" — fix it; also fix argv[1] if it's a typo
       of an allowed subcommand.
    2. argv[0] is missing "git" but IS in allowed — prepend "git".
    3. argv[0] == "git" but argv[1] is a typo of an allowed subcommand —
       suggest the corrected subcommand with the rest of argv unchanged.
    4. No close match — return None.
    5. Valid command (git <allowed-sub> ...) — return None.
    6. Empty input — return None.
    7. Unclosed quotes / shlex error — return None.
    """
    if not cmdline or not cmdline.strip():
        return None

    try:
        tokens = shlex.split(cmdline)
    except ValueError:
        # Unclosed quotes or other shlex parse errors — nothing to suggest.
        return None

    if not tokens:
        return None

    argv0 = tokens[0]

    # --- Case 5 / guard: already valid ---
    if argv0 == "git":
        if len(tokens) == 1:
            # Just "git" with no subcommand yet — nothing to correct.
            return None
        if tokens[1] in allowed:
            # Fully valid command, no suggestion needed.
            return None

        # --- Case 3: git <typo-of-subcommand> [rest...] ---
        sub_match = difflib.get_close_matches(tokens[1], allowed, n=1, cutoff=0.6)
        if sub_match:
            corrected = ["git", sub_match[0]] + tokens[2:]
            return shlex.join(corrected)
        return None

    # --- Case 2: argv[0] is directly in allowed (user forgot "git") ---
    if argv0 in allowed:
        corrected = ["git"] + tokens
        return shlex.join(corrected)

    # --- Case 1 / Case 4: argv[0] might be a typo of "git" ---
    git_match = difflib.get_close_matches(argv0, ["git"], n=1, cutoff=0.6)
    if not git_match:
        # argv[0] doesn't look like "git" at all — no suggestion.
        return None

    # argv[0] is a typo of "git".  Try to also fix argv[1] if present.
    if len(tokens) == 1:
        # Only the mangled "git" token — suggest "git" alone? Not very useful,
        # but return it so the caller has something to show.
        return "git"

    sub_token = tokens[1]
    if sub_token in allowed:
        # argv[1] is fine, just fix the "git" typo.
        corrected = ["git", sub_token] + tokens[2:]
    else:
        sub_match = difflib.get_close_matches(sub_token, allowed, n=1, cutoff=0.6)
        if sub_match:
            corrected = ["git", sub_match[0]] + tokens[2:]
        else:
            # Can fix "git" but sub is unrecognisable — still suggest with the
            # original sub token so the player at least sees "git <whatever>".
            corrected = ["git"] + tokens[1:]

    return shlex.join(corrected)
