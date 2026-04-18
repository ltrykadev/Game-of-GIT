# Game-of-GIT

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

Then open <http://127.0.0.1:8000>. Click **PLAY** to start.

### How to play

- Type any `git` command in the left pane and press **Enter**. Success is checked against the repo state, not the exact command.
- Type `?` and press Enter to reveal a hint (one at a time).
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

## Levels

### 🟢 LEVEL 1: INIT NOOB (Podstawy przetrwania)

Uczysz się, czym w ogóle jest repozytorium.

```
git init
git clone <url>
git status
git add <file>
git add .
git commit -m "msg"
```

🎯 Quest: Stwórz repo i zapisz pierwsze zmiany

### 🔵 LEVEL 2: TIME TRAVELER (Historia)

Zaczynasz ogarniać przeszłość projektu.

```
git log
git log --oneline
git show
git diff
git diff --staged
```

🎯 Quest: Znajdź, co zepsuło kod

### 🟡 LEVEL 3: BRANCH MASTER (Multiświaty)

Wchodzisz w równoległe rzeczywistości.

```
git branch
git branch <name>
git checkout <branch>
git checkout -b <branch>
git switch <branch>
git switch -c <branch>
```

🎯 Quest: Stwórz feature branch i wróć bezpiecznie

### 🟠 LEVEL 4: MERGE WARRIOR (Łączenie światów)

Pierwsze konflikty i chaos.

```
git merge <branch>
git merge --no-ff
git rebase <branch>
git cherry-pick <commit>
```

🎯 Boss fight: Rozwiąż konflikt merge

### 🔴 LEVEL 5: REMOTE HACKER (Świat online)

Synchronizacja z innymi graczami.

```
git remote -v
git remote add origin <url>
git fetch
git pull
git pull --rebase
git push
git push -u origin <branch>
```

🎯 Quest: Wypchnij kod i zsynchronizuj team

### 🟣 LEVEL 6: DAMAGE CONTROL (Cofanie błędów)

Naprawiasz własne (i cudze) błędy.

```
git reset --soft
git reset --mixed
git reset --hard
git revert <commit>
git restore <file>
git restore --staged <file>
```

🎯 Quest: Cofnij commit bez rozwalenia historii

### ⚫ LEVEL 7: STEALTH MODE (Praca tymczasowa)

Znikasz i wracasz bez śladu.

```
git stash
git stash pop
git stash list
git stash apply
```

🎯 Quest: Ukryj zmiany i wróć do nich później

### 🟤 LEVEL 8: CLEANUP CREW (Porządki)

Sprzątanie repo jak pro.

```
git clean -fd
git rm <file>
git mv <file>
git commit --amend
```

🎯 Quest: Popraw ostatni commit

### ⚙️ LEVEL 9: CONFIG GOD (Personalizacja)

Stajesz się GIT-owym demiurgiem.

```
git config --global user.name
git config --global user.email
git config --list
```

🎯 Quest: Skonfiguruj swoje środowisko

### 🧠 LEVEL 10: GIT NINJA (Zaawansowane techniki)

Zaczynasz myśleć jak Git.

```
git reflog
git blame <file>
git tag
git tag -a v1.0 -m "msg"
git bisect
```

🎯 Final Boss: Znajdź commit, który wprowadził bug
