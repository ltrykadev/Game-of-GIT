# Game of GIT

Game of GIT is an interactive learning experience that turns mastering version control into an engaging adventure. Players step into the role of a developer progressing through levels — from basic commit actions to advanced operations like rebase, merge, and conflict resolution.

Each stage presents challenges inspired by real-world teamwork scenarios: fixing a broken repository, syncing remote branches, or recovering lost changes. The gameplay focuses on exploration, logical thinking, and experimentation — mistakes aren't punished, they're part of the learning process.

As the game progresses, it introduces increasingly complex concepts while providing clear feedback and visualizations of repository history, making even advanced workflows intuitive. It's a blend of education and gameplay that helps players truly understand Git in practice — without the boredom of traditional tutorials.

**Language:** Python. **Visualization:** Game of Thrones style. **Sound:** none.

The window is split in two: the left pane simulates a shell where the player types `git` commands; the right pane shows the current task with an explanation and hidden tips that can be revealed on demand. Gameplay is task-oriented — the player types any `git` command to solve the task — and the game watches input as it's typed, offering suggestions when it detects typos or likely-wrong commands. The goal is to teach Git through a friendly interface.

## Status

Playable: **Level 1 (INIT NOOB)** — four quests covering `git init`, `git add`, and `git commit`. Levels 2–10 are specified below and are the implementation roadmap.

## Quick start

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m gameofgit
```

Once the venv is populated you can also just run `./run_me.sh` — a three-line
launcher that calls `./venv/bin/python -m gameofgit` without asking you to
activate the venv first.

On startup the server prints the LAN URL(s) it's reachable on — something like:

```
  Game of GIT: The Tears of DevSecOps
  ─────────────────────────────────────
  Play at:
    http://192.168.1.42:8000
```

Open that URL in a browser (on the same machine or on any phone / laptop on the same network) and click **PLAY** to start. The server binds to every interface, so there's no private-only loopback URL — use the address it prints.

### How to play

- Type any `git` command in the left pane and press **Enter**. Success is checked against the repo state, not the exact command.
- Type `?` and press Enter to reveal a hint (one at a time).
- Type `/exit` and confirm with `yes` to leave the realm — the shell prints a progress summary (quests completed, hints revealed) and a farewell, then returns you to the home page.
- The shell suggests corrections as you type — typos and likely-wrong commands surface inline.
- Mistakes are not punished. When a quest passes, the game auto-advances to the next one.

## Development

```bash
pip install -r requirements-dev.txt
pytest -q
```

The codebase is split into a UI-agnostic engine and a FastAPI web layer:

- `gameofgit/engine/` — sandboxed quest runner. `quest.py` (quest + check dataclasses), `parser.py` (argv validation), `executor.py` (subprocess), `sandbox.py` (tmpdir per game), `session.py` (orchestration), `suggest.py` (typo correction), `env.py` (hardened subprocess env).
- `gameofgit/quests/` — quest definitions. Each quest specifies a predicate over the sandbox repo state, so any command(s) that achieve the outcome pass.
- `gameofgit/web/` — FastAPI server (`server.py`), in-memory game registry (`games.py`), Pydantic schemas (`schemas.py`), and vanilla-JS frontend in `static/` (no build step).

Every quest runs against a throwaway repo under `/tmp`; the player's working tree is never touched.

### Repo utility: `.claude/scripts/file_cmd.py`

A tiny CLI for three file operations, committed alongside the codebase:

```bash
python3 .claude/scripts/file_cmd.py add    <path> [content...]
python3 .claude/scripts/file_cmd.py edit   <path> [note...]
python3 .claude/scripts/file_cmd.py delete <path>
```

`edit` appends a visually unique **stamp** — an ISO-8601 UTC timestamp, an optional note, and a 50-character random ID — using the correct comment leader for the file's extension (`#`, `//`, or a wrapping `<!-- … -->` block). It's useful for leaving audit markers on files during long-running manual work.

If you drive this repo with [Claude Code](https://claude.com/claude-code), the same three verbs are also reachable as the `/file` slash command (`.claude/commands/file.md`), which adds a confirmation step before `delete` and a guard against stamping credential-shaped paths.

## Levels

### LEVEL 1: INIT NOOB (Survival basics)

Learn what a repository actually is.

```
git init
git clone <url>
git status
git add <file>
git add .
git commit -m "msg"
```

Quest: Create a repo and save your first changes.

### LEVEL 2: TIME TRAVELER (History)

Start making sense of the project's past.

```
git log
git log --oneline
git show
git diff
git diff --staged
```

Quest: Find out what broke the code.

### LEVEL 3: BRANCH MASTER (Multiverse)

Step into parallel realities.

```
git branch
git branch <name>
git checkout <branch>
git checkout -b <branch>
git switch <branch>
git switch -c <branch>
```

Quest: Create a feature branch and come back safely.

### LEVEL 4: MERGE WARRIOR (Joining worlds)

First conflicts and chaos.

```
git merge <branch>
git merge --no-ff
git rebase <branch>
git cherry-pick <commit>
```

Boss fight: Resolve a merge conflict.

### LEVEL 5: REMOTE HACKER (The online world)

Sync with other players.

```
git remote -v
git remote add origin <url>
git fetch
git pull
git pull --rebase
git push
git push -u origin <branch>
```

Quest: Push your code and sync with the team.

### LEVEL 6: DAMAGE CONTROL (Undoing mistakes)

Fix your own — and other people's — mistakes.

```
git reset --soft
git reset --mixed
git reset --hard
git revert <commit>
git restore <file>
git restore --staged <file>
```

Quest: Undo a commit without wrecking history.

### LEVEL 7: STEALTH MODE (Temporary work)

Disappear and come back without a trace.

```
git stash
git stash pop
git stash list
git stash apply
```

Quest: Hide your changes and return to them later.

### LEVEL 8: CLEANUP CREW (Housekeeping)

Tidy up the repo like a pro.

```
git clean -fd
git rm <file>
git mv <file>
git commit --amend
```

Quest: Fix your last commit.

### LEVEL 9: CONFIG GOD (Personalization)

Become the demiurge of Git.

```
git config --global user.name
git config --global user.email
git config --list
```

Quest: Configure your environment.

### LEVEL 10: GIT NINJA (Advanced techniques)

Start thinking like Git.

```
git reflog
git blame <file>
git tag
git tag -a v1.0 -m "msg"
git bisect
```

Final Boss: Find the commit that introduced the bug.
