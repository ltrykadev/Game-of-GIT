---
description: Add a file, append a visually unique stamp, or delete a file
argument-hint: add|edit|delete <path> [note...]
allowed-tools: Bash, Read
---

Perform this file operation: **$ARGUMENTS**

The three verbs (`add`, `edit`, `delete`) are implemented deterministically by a helper script at `.claude/scripts/file_cmd.py`. Your job is to validate, confirm, and then delegate — not to re-implement.

## How to handle each verb

Parse the first word of `$ARGUMENTS` as the verb, the second as `<path>`, and everything else as `<tail>`.

### add

Run directly (no confirmation needed):

```bash
python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/scripts/file_cmd.py" add <path> <tail>
```

If the script exits with `error: ... already exists`, relay the message and ask the user whether to delete first.

### edit

Run directly:

```bash
python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/scripts/file_cmd.py" edit <path> <tail>
```

If `<tail>` is empty, pass no trailing argument — the script defaults to `no note`.

### delete

**Destructive.** Before running, print a one-line confirmation request:

> `About to delete <absolute-path>. Confirm? (yes/no)`

Only after the user answers `yes` (or `y`), run:

```bash
python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/scripts/file_cmd.py" delete <path>
```

If `$ARGUMENTS` already contains the literal word `confirmed` after the path (e.g. `delete foo.txt confirmed`), skip the confirmation step and run immediately.

## Rules

1. **Unknown verbs** — if the first word isn't `add`, `edit`, or `delete`, ask a single clarifying question. Do not silently map to a similar verb.
2. **Secrets** — if the path's basename matches `.env*`, `*.pem`, `*.key`, or contains `credentials`, refuse and explain. Override requires the user to say "intentional" or similar.
3. **Report the script's stdout line as-is** — it's already in the right shape (`added <path>` / `stamped <path> with id <prefix>…` / `deleted <path>`). Don't paraphrase.
4. **No arguments** — print this menu and wait:

   ```
   What would you like to do?
     add    <path> [content]   — new file
     edit   <path> [note]      — append a unique timestamped stamp
     delete <path>             — remove a file (confirmed)
   ```
