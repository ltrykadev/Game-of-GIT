# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Greenfield. The repo currently contains `README.md` (product spec with 10 levels), `LICENSE`, `.gitignore`, and a pre-created Python virtual environment. There is no application code, test suite, or build configuration yet. When adding the first real code, expect to also pick surrounding tooling (dependency manager, test runner, entry point) — confirm the choice with the user rather than defaulting silently.

## Product spec (authoritative source: `README.md`)

Game of GIT teaches Git through a leveled, task-oriented game. Key design constraints that should drive technical choices:

- **Language:** Python (3.12, venv already set up).
- **Visualization:** "Game of Thrones" style — i.e. a fantasy/medieval aesthetic for repository history and UI framing. No graphical assets are defined yet; assume terminal/TUI rendering unless the user specifies otherwise.
- **No sound.** Do not add audio dependencies.
- **Two-pane window:**
  - **Left pane** — simulated shell where the player types `git` commands.
  - **Right pane** — current task with explanation and *hidden tips that reveal on demand*.
- **Task-oriented:** each level is a set of quests; the player completes a quest by typing any `git` command(s) that achieve the described outcome. There is no single "correct" command string.
- **Mistakes aren't punished** — they're a learning surface. Error feedback should teach, not score-penalize.

## Level structure (summary; full text in `README.md`)

Ten levels, each scoped to a conceptual cluster of Git commands. When implementing a level, treat the command list in the README as the *vocabulary the player is expected to discover*, not a rigid checklist — the quest's success criterion is the repository state, not which exact command was typed.

| # | Theme | Focus |
|---|-------|-------|
| 1 | INIT NOOB | init, clone, status, add, commit |
| 2 | TIME TRAVELER | log, show, diff |
| 3 | BRANCH MASTER | branch, checkout, switch |
| 4 | MERGE WARRIOR | merge, rebase, cherry-pick, conflict resolution |
| 5 | REMOTE HACKER | remote, fetch, pull, push |
| 6 | DAMAGE CONTROL | reset, revert, restore |
| 7 | STEALTH MODE | stash |
| 8 | CLEANUP CREW | clean, rm, mv, commit --amend |
| 9 | CONFIG GOD | config |
| 10 | GIT NINJA | reflog, blame, tag, bisect |

Level 4 is labeled a "boss fight" (conflict resolution) and Level 10 is the "final boss" (find the bug-introducing commit) — these are intentional difficulty spikes and deserve more elaborate quest design than neighboring levels.

## Implementation notes for future sessions

- **Quest success = repo state, not command string.** Each quest needs a predicate that inspects the sandbox repo (e.g. "HEAD has ≥1 commit", "branch `feature/x` exists and is merged into `main`"). Design quests around these predicates from the start; don't hardcode expected commands.
- **Sandbox isolation.** The player runs real `git` against a throwaway repo per session/level. Never run quest commands against the user's working tree. A per-level temp directory (e.g. under `/tmp` or `tempfile.mkdtemp`) is the natural shape.
- **README is bilingual** (English framing, Polish quest text). Keep in-game text Polish unless the user changes direction; keep code/comments/docs English.
- **TUI library choice is open.** `textual`, `urwid`, `prompt_toolkit`, and `rich` are all viable for the two-pane UX. Ask the user before picking — this choice shapes the whole architecture.

## Environment

- Python virtual environment at `./venv/` (Python 3.12, `include-system-site-packages = false`). Only `pip` is installed.
- Activate: `source venv/bin/activate`, or call `./venv/bin/python` directly.
- `.gitignore` is the standard Python GitHub template; `venv/` is already ignored.

## Conventions

- No dependency manifest yet (no `requirements.txt`, `pyproject.toml`, `uv.lock`). Confirm the tool with the user before creating lock files.
- No test framework wired up. Before writing tests, confirm pytest vs unittest with the user.
- No formatter/linter configured. Don't introduce `ruff`/`black`/`mypy` config unprompted.
