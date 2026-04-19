/**
 * Game of GIT — play screen logic
 *
 * ES module, no framework, no build step.
 * All DOM interaction is isolated to named helpers at the bottom.
 */

"use strict";

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------
let gameId = null;
let suggestTimer = null;
// Cached view of the latest quest state — used by the /exit summary, which
// needs progress numbers without making another round-trip.
let currentQuest = null;
// True while we're waiting for the user to confirm a `/exit`. Next Enter
// decides: "yes"/"y" leaves, anything else cancels.
let pendingExit = false;
let currentPlayer = null;
let previousTier = null;
let sessionXpStart = 0;

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function apiFetch(path, opts) {
    const defaults = { headers: { "Content-Type": "application/json" } };
    const res = await fetch(path, Object.assign(defaults, opts || {}));
    if (!res.ok && res.status !== 204) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error("HTTP " + res.status + ": " + text);
    }
    if (res.status === 204) return null;
    return res.json();
}

async function createGame() {
    var slug = localStorage.getItem("gog.playerSlug");
    if (!slug) {
        window.location.href = "/";
        return null;
    }
    return apiFetch("/api/game", {
        method: "POST",
        body: JSON.stringify({ player_slug: slug }),
    });
}

async function runCommand(cmdline) {
    return apiFetch("/api/game/" + gameId + "/run", {
        method: "POST",
        body: JSON.stringify({ cmdline: cmdline }),
    });
}

async function revealHint() {
    return apiFetch("/api/game/" + gameId + "/hint", { method: "POST" });
}

async function getSuggestion(cmdline) {
    return apiFetch("/api/game/" + gameId + "/suggest", {
        method: "POST",
        body: JSON.stringify({ cmdline: cmdline }),
    });
}

async function closeGame() {
    if (!gameId) return;
    fetch("/api/game/" + gameId, { method: "DELETE", keepalive: true }).catch(function() {});
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function getEl(id) {
    return document.getElementById(id);
}

/** Remove all child nodes from an element (safe alternative to innerHTML = ""). */
function clearChildren(el) {
    while (el.firstChild) {
        el.removeChild(el.firstChild);
    }
}

/**
 * Append a line (or multi-line block) to the shell log.
 * @param {string} text
 * @param {string} [className]
 */
function appendLog(text, className) {
    if (className === undefined) className = "log-stdout";
    var log = getEl("shell-log");
    var lines = text.split("\n");
    // Drop trailing empty string from a trailing newline
    if (lines.length > 1 && lines[lines.length - 1] === "") {
        lines.pop();
    }
    for (var i = 0; i < lines.length; i++) {
        var span = document.createElement("span");
        span.className = "log-entry " + className;
        span.textContent = lines[i];
        log.appendChild(span);
    }
    log.scrollTop = log.scrollHeight;
}

function clearLog() {
    clearChildren(getEl("shell-log"));
}

function renderQuest(quest) {
    currentQuest = quest;
    getEl("quest-title").textContent = quest.title;
    getEl("quest-brief").textContent = quest.brief;

    renderProgress(quest);

    var pillsEl = getEl("allowed-pills");
    clearChildren(pillsEl);
    for (var i = 0; i < quest.allowed.length; i++) {
        var pill = document.createElement("span");
        pill.className = "allowed-pill";
        pill.textContent = quest.allowed[i];
        pillsEl.appendChild(pill);
    }

    renderHints(quest);
    renderStatus(quest);
}

function renderPlayer(player) {
    currentPlayer = player;
    if (previousTier === null) previousTier = player.tier;

    getEl("tier-pill").textContent = player.tier;
    getEl("xp-value").textContent = player.xp;

    var fill = getEl("xp-bar-fill");
    var pct;
    if (player.xp_to_next_tier === null || player.xp_to_next_tier === 0) {
        pct = 100;
    } else {
        var denom = player.xp + player.xp_to_next_tier;
        pct = denom > 0 ? Math.round((player.xp / denom) * 100) : 0;
    }
    fill.style.width = pct + "%";
}

function renderProgress(quest) {
    getEl("progress").textContent =
        "Level " + quest.level + " · Quest " +
        (quest.quest_index + 1) + " of " + quest.total;
}

function showTierUpToast(newTier) {
    var toast = document.createElement("div");
    toast.className = "tier-toast";
    toast.textContent = "You have risen to " + newTier + ".";
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 2000);
}

function renderHints(quest) {
    var list = getEl("hint-list");
    clearChildren(list);
    for (var i = 0; i < quest.hints_revealed.length; i++) {
        var li = document.createElement("li");
        li.className = "hint-item";
        li.textContent = quest.hints_revealed[i];
        list.appendChild(li);
    }
    var btn = getEl("hint-btn");
    btn.disabled = quest.hints_revealed.length >= quest.total_hints;
}

function renderStatus(quest) {
    var label = getEl("status-label");
    var detail = getEl("status-detail");

    if (quest.check_passed) {
        label.textContent = "\u2713 COMPLETED";
        label.className = "status-label completed";
    } else {
        label.textContent = "IN PROGRESS";
        label.className = "status-label in-progress";
    }

    detail.textContent = quest.check_detail || "";
}

function showSuggestion(text) {
    var bar = getEl("suggestion-bar");
    var textEl = getEl("suggestion-text");
    if (text) {
        textEl.textContent = text;
        bar.classList.remove("hidden");
    } else {
        bar.classList.add("hidden");
        textEl.textContent = "";
    }
}

function showLevelComplete() {
    var overlay = getEl("level-complete-overlay");
    var xpLine = getEl("level-complete-xp");
    if (currentPlayer) {
        var earned = currentPlayer.xp - sessionXpStart;
        xpLine.textContent =
            "+ " + earned + " XP earned this session  \u00b7  Tier: " + currentPlayer.tier;
    } else {
        xpLine.textContent = "";
    }
    overlay.classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// /exit flow — progress summary + farewell, then return to the Keep
// ---------------------------------------------------------------------------

function showExitSummary() {
    var completed = 0;
    var total = 0;
    var hintsUsed = 0;
    if (currentQuest) {
        completed = currentQuest.quest_index + (currentQuest.check_passed ? 1 : 0);
        total = currentQuest.total;
        hintsUsed = currentQuest.hints_revealed ? currentQuest.hints_revealed.length : 0;
    }

    var rule = "\u2500".repeat(49);
    appendLog("", "log-stdout");
    appendLog(rule, "log-info");
    appendLog("  Farewell, brave soul.", "log-info");
    appendLog(rule, "log-info");

    if (currentPlayer) {
        appendLog("  Tier             : " + currentPlayer.tier + " \u2694", "log-info");
        appendLog(
            "  Total XP         : " + currentPlayer.xp + " / " +
            (currentPlayer.xp + (currentPlayer.xp_to_next_tier || 0)) +
            (currentPlayer.tier === "Expert" ? " (Master of the Realm)" : ""),
            "log-info"
        );
    }
    appendLog("  Quests completed : " + completed + " of " + total, "log-info");
    if (currentPlayer && currentPlayer.xp_to_next_tier !== null && currentPlayer.tier !== "Expert") {
        var nextTier = currentPlayer.tier === "Junior" ? "Senior" : "Expert";
        appendLog("  " + currentPlayer.xp_to_next_tier + " XP from " + nextTier, "log-info");
    } else if (currentPlayer && currentPlayer.tier === "Expert") {
        appendLog("  The title of Expert is yours.", "log-info");
    }
    appendLog("  Hints revealed   : " + hintsUsed, "log-info");
    appendLog("", "log-stdout");

    var msg;
    if (total > 0 && completed >= total) {
        msg = "You have mastered this level. The realm sings your name.";
    } else if (total > 0 && completed >= Math.ceil(total / 2)) {
        msg = "A worthy showing. The sword grows lighter in your hand.";
    } else if (completed > 0) {
        msg = "Every maester began with a single scroll. Return when ready.";
    } else {
        msg = "The path awaits you still. Return when you are prepared.";
    }
    appendLog("  " + msg, "log-info");
    appendLog("", "log-stdout");
    appendLog("  Returning to the Keep\u2026", "log-info");

    var input = getEl("shell-input");
    input.disabled = true;
    input.placeholder = "game ended";

    closeGame();
    setTimeout(function() { window.location.href = "/"; }, 2500);
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

async function handleEnter(input) {
    var cmdline = input.value.trim();
    input.value = "";
    showSuggestion(null);

    if (!cmdline) return;

    // If we're waiting for an /exit confirmation, this Enter resolves it.
    // Any non-"yes" response cancels — the typed text is NOT executed as a
    // git command, to prevent accidental runs while user thought they were
    // still at the confirm prompt.
    if (pendingExit) {
        pendingExit = false;
        var lower = cmdline.toLowerCase();
        if (lower === "yes" || lower === "y") {
            showExitSummary();
        } else {
            appendLog("Exit cancelled. Continue your quest.", "log-info");
        }
        return;
    }

    // /exit shortcut: ask for confirmation, then show progress + farewell
    if (cmdline === "/exit") {
        pendingExit = true;
        appendLog(
            "Leave the realm? Type 'yes' to confirm, anything else to stay.",
            "log-info"
        );
        return;
    }

    // '?' shortcut: reveal hint without touching the engine
    if (cmdline === "?") {
        try {
            var quest = await revealHint();
            renderHints(quest);
        } catch (err) {
            appendLog("Error revealing hint: " + err.message, "log-error");
        }
        return;
    }

    // Echo the command
    appendLog("$ " + cmdline, "log-cmd");

    try {
        var body = await runCommand(cmdline);

        if (body.stdout) appendLog(body.stdout, "log-stdout");
        if (body.stderr) appendLog(body.stderr, "log-stderr");

        renderQuest(body.quest);

        if (body.player) {
            var oldTier = previousTier;
            renderPlayer(body.player);
            if (body.xp_awarded && body.xp_awarded > 0) {
                appendLog("+" + body.xp_awarded + " XP earned. Onward.", "log-info");
            }
            if (body.player.tier !== oldTier) {
                showTierUpToast(body.player.tier);
                previousTier = body.player.tier;
            }
        }

        if (body.advanced) {
            appendLog("Quest passed! The next quest awaits.", "log-info");
        }
        if (body.level_complete) {
            appendLog("Level 1 complete! The realm remembers.", "log-info");
            showLevelComplete();
        }
    } catch (err) {
        appendLog("Error: " + err.message, "log-error");
    }
}

function scheduleTypoCheck(input) {
    clearTimeout(suggestTimer);
    var cmdline = input.value;

    if (!cmdline.trim() || cmdline.trim() === "?") {
        showSuggestion(null);
        return;
    }

    suggestTimer = setTimeout(async function() {
        try {
            var res = await getSuggestion(cmdline);
            showSuggestion(res.suggestion || null);
        } catch (_) {
            // Suggestion is best-effort — ignore errors silently
        }
    }, 150);
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function init() {
    appendLog("Preparing your sandbox\u2026", "log-info");

    var gameData;
    try {
        gameData = await createGame();
    } catch (err) {
        appendLog("Failed to start game: " + err.message, "log-error");
        return;
    }

    gameId = gameData.game_id;
    clearLog();

    appendLog("The sandbox is ready. Type your first git command below.", "log-info");
    appendLog("Type ? for a hint, or click \u2018Show next hint\u2019 on the right.", "log-info");
    appendLog("Type /exit to leave the realm.", "log-info");
    appendLog("", "log-stdout");

    renderQuest(gameData.quest);
    if (gameData.player) {
        renderPlayer(gameData.player);
        sessionXpStart = gameData.player.xp;
    }

    var input = getEl("shell-input");
    input.focus();

    input.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
            handleEnter(input);
        }
    });

    input.addEventListener("input", function() {
        scheduleTypoCheck(input);
    });

    getEl("hint-btn").addEventListener("click", async function() {
        try {
            var quest = await revealHint();
            renderHints(quest);
        } catch (err) {
            appendLog("Error: " + err.message, "log-error");
        }
    });

    window.addEventListener("beforeunload", closeGame);
}

// Run on DOMContentLoaded (or immediately if already loaded)
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
