# All Quests + Gamification — Design Spec

**Date:** 2026-04-19
**Scope:** Implement the remaining 29 quests (Levels 2–10) and add a gamification layer: named player profiles, XP per quest, and a three-tier progression bar (Junior → Senior → Expert).

---

## 1. Architecture + data model

### 1.1 New files / packages

- `gameofgit/quests/level2.py` through `gameofgit/quests/level10.py` — one file per level, same shape as the existing `level1.py` (module-level `Quest` constants + seed/check functions).
- `gameofgit/quests/_helpers.py` — shared authoring primitives:
  - `run_git(args, cwd, capture=False)` — hardened subprocess runner; raises on non-zero.
  - `set_identity(cwd)` — configures `user.name` / `user.email` for the sandbox.
  - `commit_file(cwd, path, content, msg)` — write → `git add` → `git commit`.
  - `head_exists(cwd)`, `commit_count(cwd)`, `branch_exists(cwd, name)`, `working_tree_clean(cwd)`, `head_message(cwd)`.
- `gameofgit/player/__init__.py`
- `gameofgit/player/model.py` — `Player` dataclass + tier computation.
- `gameofgit/player/store.py` — JSON-per-player persistence at `~/.gameofgit/players/<slug>.json`. Atomic writes via tmp + rename. Creates the directory on first use. Honors a `GAMEOFGIT_PROFILES_DIR` env var for test injection. Exports an `InvalidName` exception raised when the supplied name slugifies to an empty string; callers (web layer) translate it to HTTP 400.
- `gameofgit/player/tiers.py` — tier constants and boundary logic.

### 1.2 Changes to existing files

- `gameofgit/engine/quest.py`:
  - `Quest` dataclass gains two required fields: `xp: int` and `level: int`. Every existing and new quest must be tagged.
  - A new `SessionState` dataclass is defined: `last_argv: tuple[str, ...] | None`, `all_argv: list[tuple[str, ...]]`. It captures what the player has run so far in the current quest.
  - `Quest.check` signature changes from `Callable[[Path], CheckResult]` to `Callable[[Path, SessionState], CheckResult]`. Existing Level 1 checks are updated to accept the second argument and ignore it.
- `gameofgit/engine/session.py` — `QuestSession` tracks `_last_argv` and `_all_argv`, exposes them as a `SessionState` when evaluating the check, and resets both on each quest advance.
- `gameofgit/quests/__init__.py` — imports from all `level*.py` files and concatenates level tuples into a single ordered `all_quests()` output. Existing call sites do not change.
- `gameofgit/web/games.py` — `Game` gains `player: Player` (the loaded profile). `new_game()` takes a required `player_slug: str` and loads/creates the profile via `store`. `Game.advance()` is unchanged.
- `gameofgit/web/schemas.py` — adds `PlayerView`; `RunResponse` gets `xp_awarded: int` and `player: PlayerView`; `GameCreatedResponse` gets `player: PlayerView`; `QuestView` gets `xp: int` and `level: int`.

### 1.3 Name → slug rule

```
slug = re.sub(r'[^a-z0-9_]+', '_', name.strip().lower()).strip('_')
```

If the slug is empty after that, reject the name with 400. Two different inputs that produce the same slug share a profile (no authentication on a LAN training tool — treated as feature, not bug).

### 1.4 Invariants

- **XP is awarded once per `(player_slug, quest_slug)` pair.** Replays after a profile reset re-earn XP. Re-passing the same quest in the same profile awards 0.
- **`completed_quests` is the source of truth.** `xp` is denormalized for display but recomputable by summing `quest.xp` over every slug in `completed_quests`. On `store.load()`, `xp` is always recomputed against the current catalog; stored value is ignored if they disagree. This makes profiles self-healing when quest XP values are retuned.
- **A level is "completed" only when every quest slug in it appears in `completed_quests`.** Partial levels don't count toward tier progression.

---

## 2. Quest content plan

All 10 levels, 33 quests total (4 existing on Level 1 + 29 new). Each quest gets a `slug`, `title`, `brief`, two `hints`, a level-wide `allowed` command set, a `seed` function (may be `None`), a `check` predicate, an `xp` value, and a `level` number.

### Level 1 — INIT NOOB (4 existing quests; XP backfilled)

| slug | xp |
|------|----|
| `init-repo` | 50 |
| `stage-a-file` | 50 |
| `first-commit` | 75 |
| `meaningful-message` | 75 |
| **Level total** | **250** |

### Level 2 — TIME TRAVELER (3 quests)

Allowed: `log`, `show`, `diff`, `status`.

- **`read-the-log` (75 XP)** — Seed: repo with 5 committed files.
  - Check: the session has executed a `git log` command (any arguments) with exit 0. Implementation: `QuestSession` records the last successful `argv`; check inspects it.
- **`spot-the-diff` (100 XP)** — Seed: 5 commits + one tracked file modified but unstaged.
  - Check: a `git diff` command was executed with exit 0.
- **`inspect-a-commit` (100 XP)** — Seed: 5 commits; record the middle commit's hash in a seed-side state file.
  - Check: a `git show <sha>` was executed where `<sha>` resolves (in that repo) to any commit other than HEAD.

**Implementation note — "command-was-run" checks:** some Level 2, 3, 7, 9, 10 checks need to know the player ran a specific command (not just that the repo state changed). Extend `QuestSession` with a `_last_run: tuple[str, ...] | None` field that stores the most recent successful `argv`. Pass `session_state` into `check` — upgrade `check` signature from `Callable[[Path], CheckResult]` to `Callable[[Path, SessionState], CheckResult]`, where `SessionState` is a small dataclass with `last_argv: tuple[str, ...] | None` and `all_argv: list[tuple[str, ...]]`. Existing Level 1 checks ignore the second argument.

### Level 3 — BRANCH MASTER (3 quests)

Allowed: `branch`, `checkout`, `switch`, `log`, `status`.

- **`list-the-branches` (75 XP)** — Seed: repo with 3 branches (`main`, `dragonstone`, `winterfell`).
  - Check: `git branch` was executed (last_argv begins with `branch` with no subcommand that would mutate).
- **`make-a-branch` (100 XP)** — Seed: same as above.
  - Check: `git branch` output lists ≥ 4 branches (one more than seeded).
- **`switch-and-return` (125 XP)** — Seed: `main` + `dragonstone`; HEAD on `main`.
  - Check: HEAD is on `main` AND `git reflog` contains a checkout/switch record referencing `dragonstone`.

### Level 4 — MERGE WARRIOR (4 quests, boss fight)

Allowed: `merge`, `rebase`, `cherry-pick`, `branch`, `checkout`, `switch`, `status`, `log`, `add`, `commit`, `diff`.

- **`fast-forward-merge` (150 XP)** — Seed: `main` at commit A; `feature` branches off A with two additional commits; HEAD on `main` at A.
  - Check: HEAD (on `main`) is equal to or a descendant of `feature`'s tip AND a merge happened (feature's tip is reachable from main).
- **`rebase-a-branch` (175 XP)** — Seed: `main` has advanced past branch point; `feature` has its own commits from the older point.
  - Check: `feature` is linearly descended from current `main` (i.e., `main` is ancestor of `feature`, and no merge commits on `feature`).
- **`cherry-pick-one` (175 XP)** — Seed: `experiment` branch with 3 distinct commits; HEAD on `main`.
  - Check: `main` contains a commit whose tree matches the middle `experiment` commit's tree, and `main` does **not** contain the first or third `experiment` commits.
- **`resolve-the-conflict` (250 XP, boss)** — Seed: `main` and `rebellion` both modify line 1 of `throne.txt` differently; HEAD on `main`.
  - Check: HEAD on `main` is a merge commit with two parents; `throne.txt` contains no `<<<<<<<`/`=======`/`>>>>>>>` markers; working tree clean.

### Level 5 — REMOTE HACKER (3 quests)

Allowed: `remote`, `fetch`, `pull`, `push`, `log`, `branch`, `status`.

Seed helper: `seed_with_bare_remote(sandbox)` creates `sandbox.parent / "<sandbox_name>.origin.git"` as a bare repo, clones it or adds it as `origin`, and seeds a commit. Each Level 5 quest reuses this helper.

- **`inspect-remotes` (75 XP)** — Seed: `origin` added.
  - Check: `git remote -v` was executed with exit 0.
- **`fetch-the-news` (125 XP)** — Seed: bare remote has a commit on `main` that the local clone lacks.
  - Check: `refs/remotes/origin/main` SHA matches bare remote's `refs/heads/main`.
- **`push-your-work` (150 XP)** — Seed: local is one commit ahead of bare remote.
  - Check: bare remote's `refs/heads/main` SHA equals local `refs/heads/main` SHA.

### Level 6 — DAMAGE CONTROL (3 quests)

Allowed: `reset`, `revert`, `restore`, `log`, `status`, `add`, `commit`, `diff`.

- **`unstage-a-file` (100 XP)** — Seed: file `oath.txt` is staged on top of an existing commit.
  - Check: `git diff --cached --name-only` returns empty.
- **`undo-a-commit-keep-work` (125 XP)** — Seed: repo has 3 commits; HEAD's commit is the "bad" one, and its changes should remain in the working tree after reset.
  - Check: HEAD has moved back exactly one commit AND the files modified in the bad commit still show as modified in working tree.
- **`revert-a-public-commit` (150 XP)** — Seed: 3 commits; the second commit introduced a file `bug.txt` with bad content.
  - Check: HEAD has 4 commits; tree at HEAD lacks `bug.txt` (or has the pre-bad content); no commits were removed (count is 4, not 2).

### Level 7 — STEALTH MODE (3 quests)

Allowed: `stash`, `status`, `log`, `diff`.

- **`stash-your-changes` (100 XP)** — Seed: clean commit history, working tree has 1 modified tracked file.
  - Check: `git stash list` has ≥1 entry AND working tree is clean.
- **`list-the-stashes` (75 XP)** — Seed: 1 stash entry pre-made.
  - Check: `git stash list` was executed.
- **`pop-a-stash` (150 XP)** — Seed: clean working tree, 1 stash entry pre-made.
  - Check: `git stash list` has 0 entries AND working tree has modifications.

### Level 8 — CLEANUP CREW (3 quests)

Allowed: `clean`, `rm`, `mv`, `commit`, `add`, `status`, `log`.

- **`remove-a-tracked-file` (100 XP)** — Seed: `scroll.txt` tracked and committed.
  - Check: HEAD's tree does not contain `scroll.txt`; working tree clean.
- **`rename-a-file` (100 XP)** — Seed: `oldname.txt` tracked and committed.
  - Check: HEAD's tree contains `newname.txt`, does not contain `oldname.txt`; working tree clean.
- **`amend-your-last-commit` (150 XP)** — Seed: HEAD commit has message `"wip"` (too short).
  - Check: HEAD's message is ≥ 10 characters AND differs from `"wip"`.

### Level 9 — CONFIG GOD (3 quests)

Allowed: `config`, `status`.

Seed helper: `Quest`-level seed configures `user.email` to a known sentinel (`seed@gameofgit.local`) so the check can detect change.

- **`set-your-name` (50 XP)** — Seed: `user.name` set to `"Anon"`.
  - Check: `git config user.name` returns a non-empty string different from `"Anon"`.
- **`set-your-email` (50 XP)** — Seed: `user.email` set to sentinel.
  - Check: `git config user.email` returns a non-empty string different from sentinel AND contains `@`.
- **`list-the-config` (100 XP)** — Seed: any valid repo.
  - Check: `git config --list` was executed.

### Level 10 — GIT NINJA (4 quests, final boss)

Allowed: `reflog`, `blame`, `tag`, `bisect`, `log`, `show`, `status`, `checkout`.

- **`read-the-reflog` (125 XP)** — Seed: 5 commits + one branch switch in reflog.
  - Check: `git reflog` was executed.
- **`blame-a-line` (175 XP)** — Seed: `chronicle.txt` with 5 lines, each committed in a separate commit.
  - Check: `git blame <file>` was executed (last_argv starts with `blame`).
- **`tag-a-release` (200 XP)** — Seed: at least one commit.
  - Check: at least one annotated tag exists (`git tag -l --format=%(objecttype)` returns `tag` for ≥1 entry) AND its message is non-empty.
- **`find-the-bug` (500 XP, final boss)** — Seed: 15 commits. Commit #9 introduces a file `bisect_test.sh` (executable, checks a condition that fails from commit #9 onward). Commit #9's message contains the marker `[PLANTED_BUG]`.
  - Check: `.git/refs/bisect/bad` exists AND the commit it points at has `[PLANTED_BUG]` in its message. (After a successful `git bisect run`, `bisect/bad` is set to the first bad commit.)

### Total XP

| Level | Quests | XP |
|-------|--------|----|
| 1 | 4 | 250 |
| 2 | 3 | 275 |
| 3 | 3 | 300 |
| 4 | 4 | 750 |
| 5 | 3 | 350 |
| 6 | 3 | 375 |
| 7 | 3 | 325 |
| 8 | 3 | 350 |
| 9 | 3 | 200 |
| 10 | 4 | 1000 |
| **Total** | **33** | **4,175** |

---

## 3. Player, XP, tier mechanics

### 3.1 `Player` dataclass

```python
@dataclass
class Player:
    name: str                     # as entered ("Robb Stark")
    slug: str                     # filesystem-safe ("robb_stark")
    xp: int                       # recomputable from completed_quests
    completed_quests: set[str]    # quest slugs

    @property
    def levels_completed(self) -> int: ...
    @property
    def tier(self) -> Literal["Junior", "Senior", "Expert"]: ...
```

### 3.2 Tier rule

```
Junior   = 0–4 levels completed
Senior   = 5–9 levels completed
Expert   = 10 levels completed (every quest in the catalog)
```

### 3.3 `PlayerView` (API payload)

```python
class PlayerView(BaseModel):
    name: str
    tier: Literal["Junior", "Senior", "Expert"]
    xp: int
    xp_to_next_tier: int | None    # None when already Expert
    levels_completed: int
    total_levels: int              # always 10
```

`xp_to_next_tier` is a UI aid: `(total XP of all quests in the next 5-level milestone) − current_xp`, floor-clamped at 0. When Expert, returns `None`.

### 3.4 XP accrual rule

Triggered server-side in `POST /api/game/{gid}/run` at the exact `False → True` edge of the current quest's check (same edge that fires `advanced` / `level_complete`):

1. If the passed quest's slug is **not** already in `player.completed_quests`:
   1. Add slug to the set.
   2. `player.xp += quest.xp`.
   3. `store.save(player)`.
   4. `xp_awarded = quest.xp`.
2. Otherwise (replay / re-pass): `xp_awarded = 0`, no persistence write.

No hint penalties, no streak bonuses. This matches the "mistakes aren't punished" principle.

### 3.5 Name prompt flow

- Home page adds an input field labeled "Enter your name, ser:" below the logo, before the PLAY button.
- PLAY is disabled until the field has a non-empty (after strip) value.
- On PLAY: `POST /api/player` with `{"name": "<raw>"}`. Server slugifies, loads-or-creates profile, returns `PlayerView`.
  - If `xp > 0`: brief "Welcome back, <name> — Tier: <tier>, <xp> XP" greeting for 1.5 s, then navigate to `/play?player=<slug>`.
  - If `xp == 0`: navigate immediately.
- Browser stores the raw name in `localStorage['gog.playerName']` for auto-fill on return.
- Server is authoritative for profile state; localStorage is a UX convenience only.

### 3.6 `/exit` summary additions

The existing farewell block gains:

```
Tier            : Senior ⚔
Total XP        : 1,425 / 4,175
Quests completed: 18 of 33
{N} XP from Expert              (or "The title of Expert is yours.")
Hints revealed  : 2
```

Numbers come from the cached `currentPlayer` + `currentQuest` in the frontend — no extra round-trip.

---

## 4. API and schema changes

### 4.1 New routes

```
POST /api/player                      body: {"name": "<raw>"}
                                      → 200 PlayerView  (loads-or-creates)
                                      → 400 if name slugifies to empty

GET  /api/player/{slug}               → 200 PlayerView
                                      → 404 if unknown
```

### 4.2 Modified routes (additive only)

```
POST /api/game                        body: {"player_slug": "robb_stark"}
                                      → GameCreatedResponse
                                        { game_id, quest: QuestView,
                                          player: PlayerView }
                                      → 400 if player_slug unknown

POST /api/game/{gid}/run              → RunResponse (existing fields +)
                                        xp_awarded: int
                                        player: PlayerView
```

Hint and suggest routes are unchanged. Delete-game is unchanged.

### 4.3 `QuestView` additions

```python
class QuestView(BaseModel):
    # ... existing fields ...
    xp: int       # this quest's XP reward
    level: int    # 1..10
```

### 4.4 Data flow — one command to XP accrual

```
1. Client → POST /api/game/{gid}/run {"cmdline": "..."}
2. Server handler:
   a. game = get_game(gid)        # has game.player already loaded
   b. prev_passed = session._last_check.passed
   c. outcome = session.run(cmdline)
   d. if outcome.check.passed and not prev_passed:
         slug = game.quest.slug
         if slug not in game.player.completed_quests:
             game.player.completed_quests.add(slug)
             game.player.xp += game.quest.xp
             store.save(game.player)
             xp_awarded = game.quest.xp
         else:
             xp_awarded = 0
         if game.is_last_quest:
             level_complete = True
         else:
             game.advance()
             advanced = True
     else:
         xp_awarded = 0
3. Return RunResponse with xp_awarded + PlayerView(game.player)
```

### 4.5 Persistence file format

Location: `~/.gameofgit/players/<slug>.json`. Created on first save; directory auto-created.

```json
{
    "name": "Robb Stark",
    "slug": "robb_stark",
    "completed_quests": ["init-repo", "stage-a-file", "first-commit"],
    "xp": 175,
    "created_at": "2026-04-19T12:00:00Z",
    "updated_at": "2026-04-19T14:32:11Z"
}
```

`xp` is denormalized. `store.load()` recomputes it from `completed_quests` against the current catalog; if stored `xp` disagrees, recomputed wins. This keeps profiles self-healing across XP rebalances.

Writes are atomic: write to `<slug>.json.tmp`, fsync, rename. No OS-level file locking (single-process server, last-write-wins is acceptable for a local training tool).

### 4.6 Error handling

- `POST /api/player` with empty/whitespace/unsluggable name → 400 `{"detail": "That name can't be written in the book — try another."}`
- `POST /api/game` with unknown `player_slug` → 400 (client must create the profile first).
- Disk I/O failures on save → log the traceback, return 500 with generic "The scribes dropped their quill. Try again." (don't expose paths).

### 4.7 Concurrency

- Single-process FastAPI, no threading in handlers.
- Two tabs for the same player → last `save()` wins. Acceptable; documented, not tested.
- No inter-process file locking.

---

## 5. UI changes

### 5.1 Home page (`index.html`)

Below the existing three-tier logo, add a named input + PLAY row:

```
Enter your name, ser:
[____________________________]

[ PLAY ]   (disabled until filled)
```

- Input is stripped and validated non-empty before PLAY enables.
- On PLAY: `POST /api/player` → on success, if returned `xp > 0` show a brief greeting for 1.5 s, then `window.location.href = "/play?player=<slug>"`.
- Raw name persisted to `localStorage['gog.playerName']`; pre-fills on return.

### 5.2 Play page (`play.html`) — header bar

Existing header becomes three-column:

```
┌────────────────────────────────────────────────────────────────────┐
│ GAME OF GIT   │  Tier: Junior · 175 XP  ▰▰▰▱▱▱   │  Level 2 · Quest 2 of 3 │
└────────────────────────────────────────────────────────────────────┘
```

- **Left:** existing mini-logo link to `/`.
- **Center (new):** status bar — tier pill (bronze→gold gradient matching logo), current XP number, progress bar (filled fraction = `xp / (xp + xp_to_next_tier)`). Expert shows "Master of the Realm" with a full bar; no numeric "next" label.
- **Right:** quest progress indicator, updated to include the level number (`Level 2 · Quest 2 of 3`).

### 5.3 Quest pane

Above the quest title, a thin level + XP row:

```
Level 2 · TIME TRAVELER                       + 100 XP
```

### 5.4 On quest pass

When `RunResponse.xp_awarded > 0`:

- Append a log-info line to the shell: `"+N XP earned. Onward."`
- Animate the status bar: XP count-up transition, progress bar width CSS transition (~400 ms).
- If `player.tier` changed from the previous render's tier, show a centered parchment toast for 2 s: `"You have risen to Senior."` / `"You have risen to Expert."` The toast dismisses itself; gameplay beneath is not blocked.

### 5.5 Level-complete overlay

Existing overlay body gains two lines:

```
+ 750 XP earned this level
Tier: Senior ⚔
```

### 5.6 `/exit` summary

Extend existing farewell block with the additions in § 3.6. All numbers read from `currentPlayer` + `currentQuest` (cached client-side), no extra API call.

### 5.7 Frontend state additions (`app.js`)

- `let currentPlayer = null;` — cache of latest `PlayerView`.
- `renderPlayer(player)` — paints the status bar; called after init and after every run response.
- `showTierUpToast(newTier)` — centered 2 s parchment toast.
- `flashXpDelta(amount)` — shell-log line + count-up animation on the XP number.
- `handleEnter` branch for `level_complete` is updated to include XP earned this level (computed from the cached player diff).

### 5.8 Styling (`style.css`)

- Reuse `--font-display` (Cinzel) for tier names, `--font-body` for XP numbers.
- Tier pill: bronze→gold gradient (same three-stop logic as the logo's `embossGrad`), ~22 px tall.
- Progress bar: bronze outline, gold fill, 1 px amber glow during transition.
- No new fonts, no new images, no audio.

---

## 6. Testing plan

`pytest` remains the runner (`pytest -q`, already in `requirements-dev.txt`).

### 6.1 New test files

**`tests/player/test_model.py`** — `Player` + tier logic:
- Empty player → `tier == "Junior"`, `levels_completed == 0`, `xp_to_next_tier > 0`.
- Player with all slugs for Levels 1–5 → `levels_completed == 5`, `tier == "Senior"`.
- Player with every slug in the catalog → `tier == "Expert"`, `xp_to_next_tier is None`.
- A level only counts as complete when **every** slug in it is present.

**`tests/player/test_tiers.py`** — boundary logic:
- 4 levels complete → Junior; 5 → Senior; 9 → Senior; 10 → Expert.

**`tests/player/test_store.py`** — JSON persistence (uses `tmp_path` + `monkeypatch.setenv("GAMEOFGIT_PROFILES_DIR", str(tmp_path))`):
- Round-trip: save → load returns equal Player.
- Slug collision: `"Robb Stark"` and `"robb stark"` → shared profile.
- Invalid name (`""`, `"   "`, `"!!!"`) → `slugify` returns empty → `store.load_or_create` raises `InvalidName`.
- Corrupt JSON → `store.load_or_create` logs + creates fresh profile (no crash on torn write).
- XP recomputation: saved file has stale `xp: 9999`; after load, `player.xp` equals the recomputed sum.

**`tests/web/test_player_routes.py`** — FastAPI routes:
- `POST /api/player {"name": "Robb"}` → 200, `PlayerView.xp == 0`, `tier == "Junior"`.
- `POST /api/player {"name": ""}` → 400.
- `POST /api/player` twice with same name → second call returns the already-saved state (idempotent create).
- `GET /api/player/unknown_slug` → 404.

**`tests/web/test_game_xp_flow.py`** — XP accrual end-to-end through the game API:
- Create player → create game → pass Level 1 quest 1 → response has `xp_awarded == 50`, `player.xp == 50`.
- Restart game for same player → `xp == 50` is preserved.
- Pass same quest twice across two separate games → total `xp == 50`, not 100.
- Pass all 4 Level 1 quests → `levels_completed == 1`, `xp == 250`.

**Per-level content tests** (`tests/quests/test_level2.py` through `test_level10.py`):
- For each quest in the level:
  - `seed` runs to completion on a fresh `tmp_path` sandbox without raising.
  - Immediately after `seed`, `check()` returns `False`.
  - A **happy-path command sequence** (hard-coded in the test) causes `check()` to return `True`.
- Level 4 `resolve-the-conflict`: the test writes a fixed resolution to `throne.txt`, stages, commits, and asserts the check passes.
- Level 5 tests use `tmp_path / "remote.git"` as the bare repo and verify `push`/`fetch` change bare-repo refs correctly.
- Level 10 `find-the-bug`: test invokes `git bisect start` + marks endpoints + `git bisect run ./bisect_test.sh` non-interactively.

### 6.2 Regression

Existing tests stay green. Level 1 quest constants gain `xp` and `level`; any test that builds a `Quest` by hand is updated.

### 6.3 Manual smoke test (documented, not automated)

After implementation:

1. `./run_me.sh`, open the printed LAN URL.
2. Enter a name → PLAY → verify Tier: Junior, 0 XP.
3. Pass Level 1 quest 1 → verify `+50 XP` log line, status-bar count-up.
4. Complete Level 1 entirely → verify level-complete overlay shows "+ 250 XP earned this level".
5. Play through one quest of each of Levels 2–5 to confirm per-level seeds work and XP accrues.
6. Close the tab; open the home page; enter the same name; verify XP is preserved and the "Welcome back" greeting appears.
7. `/exit` mid-quest → verify summary shows Tier, Total XP, quests-completed, XP-to-Expert.

### 6.4 What is **not** tested

- Visual tier-up toast animation (manual only).
- Name-casing UX (covered via store tests; no separate UI test).
- Two-tab concurrency (single-process app, last-write-wins documented).

---

## 7. Open items / out of scope

- **No scoreboard, no leaderboard.** Multiple players on the same LAN each see only their own profile.
- **No per-player deletion UI.** Profiles can be deleted manually from `~/.gameofgit/players/`.
- **No migration from an existing unnamed game.** Brand-new feature — existing in-memory games don't carry over.
- **No audio, no new images.** Enforced by the project's no-sound / terminal-aesthetic constraint.
