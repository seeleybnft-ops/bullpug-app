#!/usr/bin/env bash
#
# restore-archived.sh — restore a parked feature from /archived/ back
# into the live codebase in one command.
#
# Usage:
#   bin/restore-archived.sh --list
#   bin/restore-archived.sh feature=<name>
#   bin/restore-archived.sh feature=<name> --dry-run
#
# Available features (see archived/README.md for full context):
#   pug-pit          — coin-flip P2P betting + jackpot
#   cosmic-runner    — 2D + 3D endless-runner game + skin store
#   showcase         — /showcase/<wallet> skin share page
#   nft-gallery      — /nft placeholder mint page
#   trading-journal  — journal + portfolio + reflections + exit-simulator
#
# After the script runs, follow the printed MANUAL STEPS to re-wire
# App.js routes and routers/__init__.py imports. The script never edits
# those files — restoring a feature is a product decision that should
# be committed explicitly, not auto-patched.
#
# Exit codes: 0 ok · 1 bad usage · 2 unknown feature · 3 nothing to move

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE_ROOT="${REPO_ROOT}/archived"

# ─────────────────────────────────────────── Feature manifests
# Each manifest is a newline-separated list of paths RELATIVE TO REPO ROOT.
# Every entry must currently live under archived/<same-path>. The script
# moves it to <same-path> (i.e. strips the "archived/" prefix).

manifest_pug_pit=$(cat <<'EOF'
frontend/src/pages/BettingArena.js
frontend/src/components/BigWinToast.js
frontend/src/components/JackpotTicker.js
frontend/src/components/JackpotDisplay.js
frontend/src/components/PugPitFaceOff.js
frontend/src/components/PackRingAvatar.js
frontend/src/components/RakeJackpotCard.js
backend/routers/betting.py
backend/routers/escrow.py
backend/routers/ledger.py
EOF
)

manifest_cosmic_runner=$(cat <<'EOF'
frontend/src/pages/SpeedRunGame.js
frontend/src/pages/Phase1Runner3D.js
frontend/src/components/GameAchievements.js
frontend/src/components/GameGuide.js
frontend/src/components/SkinStore.js
frontend/src/components/SkinPreview3D.js
frontend/src/components/LeaderboardPanel.js
frontend/src/game_lib/GameEngine.js
frontend/src/game_lib/GameGuide.js
frontend/src/game_lib/constants.js
frontend/src/game_lib/index.js
frontend/src/game_lib/useGameState.js
EOF
)

manifest_showcase=$(cat <<'EOF'
frontend/src/pages/Showcase.js
backend/routers/showcase.py
EOF
)

manifest_nft_gallery=$(cat <<'EOF'
frontend/src/pages/NFTGallery.js
EOF
)

manifest_trading_journal=$(cat <<'EOF'
frontend/src/pages/TradingJournal.js
frontend/src/pages/Portfolio.js
frontend/src/pages/ExitSimulator.js
frontend/src/pages/ReflectionsCalculator.js
frontend/src/components/journal_lib/ChatSection.js
frontend/src/components/journal_lib/CloudBackup.js
frontend/src/components/journal_lib/Dashboard.js
frontend/src/components/journal_lib/ExitSimulator.js
frontend/src/components/journal_lib/InsightsSection.js
frontend/src/components/journal_lib/PendingJournalEntries.js
frontend/src/components/journal_lib/TopPicksSection.js
frontend/src/components/journal_lib/TradeForm.js
frontend/src/components/journal_lib/TradesList.js
frontend/src/components/journal_lib/index.js
frontend/src/components/JournalAIAssistant.js
frontend/src/components/AchievementBadges.js
backend/routers/journal.py
backend/routers/portfolio.py
backend/routers/reflections.py
EOF
)

# ─────────────────────────────────────────── Post-restore manual steps

manual_pug_pit=$(cat <<'EOF'
  • frontend/src/App.js       — un-comment the /betting Route block
                                (search for "Archived routes")
  • backend/routers/__init__.py — re-add:
        from routers.betting import router as betting_router
        from routers.escrow  import router as escrow_router
        from routers.ledger  import router as ledger_router
    then add betting_router, escrow_router, ledger_router to ALL_ROUTERS
  • backend/routers/admin.py  — restore the 8 admin endpoints trimmed
    on 18 Sep 2026 (challenges, challenge/cancel, pot/draw, bets,
    escrow, escrow-alert-test, escrow-status, rake-summary). Grab them
    from history:  git log --diff-filter=D -p -- backend/routers/admin.py
  • backend/server.py         — restore /ws/pot to broadcast real pot
    data (currently a no-op stub)
EOF
)

manual_cosmic_runner=$(cat <<'EOF'
  • frontend/src/App.js       — un-comment /game and /game/3d Route
                                blocks (search for "Archived routes")
  • frontend/src/game_lib/    — the directory is expected to live at
                                src/game/ per the original convention;
                                the moves above leave it at src/game_lib/.
                                If you want the original name back run:
        git mv frontend/src/game_lib frontend/src/game
  • No backend re-wiring needed — leaderboard router stayed live.
EOF
)

manual_showcase=$(cat <<'EOF'
  • frontend/src/App.js       — re-add /showcase and /showcase/:walletAddress
                                Routes
  • backend/routers/__init__.py — re-add:
        from routers.showcase import router as showcase_router
    then add showcase_router to ALL_ROUTERS
EOF
)

manual_nft_gallery=$(cat <<'EOF'
  • frontend/src/App.js       — re-add the /nft Route
  • No backend re-wiring needed.
EOF
)

manual_trading_journal=$(cat <<'EOF'
  • backend/routers/__init__.py — re-add:
        from routers.journal      import router as journal_router
        from routers.portfolio    import router as portfolio_router
        from routers.reflections  import router as reflections_router
    Add each to ALL_ROUTERS if you want the endpoints reachable, or
    keep them as F401-noqa orphans if the routes should stay 404.
  • frontend/src/App.js       — add /journal, /portfolio, /reflections,
                                /exit-simulator Routes if you want the
                                pages mounted. All were previously
                                unmounted (May 2026).
EOF
)

# ─────────────────────────────────────────── Feature registry

FEATURES=(pug-pit cosmic-runner showcase nft-gallery trading-journal)

get_manifest() {
    case "$1" in
        pug-pit)         echo "$manifest_pug_pit" ;;
        cosmic-runner)   echo "$manifest_cosmic_runner" ;;
        showcase)        echo "$manifest_showcase" ;;
        nft-gallery)     echo "$manifest_nft_gallery" ;;
        trading-journal) echo "$manifest_trading_journal" ;;
        *) return 1 ;;
    esac
}

get_manual() {
    case "$1" in
        pug-pit)         echo "$manual_pug_pit" ;;
        cosmic-runner)   echo "$manual_cosmic_runner" ;;
        showcase)        echo "$manual_showcase" ;;
        nft-gallery)     echo "$manual_nft_gallery" ;;
        trading-journal) echo "$manual_trading_journal" ;;
        *) return 1 ;;
    esac
}

# ─────────────────────────────────────────── Helpers

usage() {
    cat <<EOF
Usage:
  $(basename "$0") --list
  $(basename "$0") feature=<name> [--dry-run]

Available features: ${FEATURES[*]}
See archived/README.md for the full archival policy and each feature's
scope, restore intent, and expected side-effects.
EOF
}

list_features() {
    echo "Restorable features (from archived/):"
    for f in "${FEATURES[@]}"; do
        manifest=$(get_manifest "$f")
        n=$(echo "$manifest" | sed '/^\s*$/d' | wc -l | tr -d ' ')
        printf "  • %-16s (%s files)\n" "$f" "$n"
    done
    echo ""
    echo "Run:  $(basename "$0") feature=<name> [--dry-run]"
}

# ─────────────────────────────────────────── Argument parsing

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

FEATURE=""
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --list|-l)
            list_features
            exit 0
            ;;
        --dry-run|-n)
            DRY_RUN=1
            ;;
        feature=*)
            FEATURE="${arg#feature=}"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$FEATURE" ]]; then
    echo "Missing feature=<name>." >&2
    usage
    exit 1
fi

manifest="$(get_manifest "$FEATURE" || true)"
if [[ -z "$manifest" ]]; then
    echo "Unknown feature: '$FEATURE'." >&2
    echo "Try:  $(basename "$0") --list" >&2
    exit 2
fi

# ─────────────────────────────────────────── Preflight

cd "$REPO_ROOT"

if [[ ! -d "$ARCHIVE_ROOT" ]]; then
    echo "archived/ directory not found at $ARCHIVE_ROOT" >&2
    exit 3
fi

# Split manifest into an array and drop blank lines.
mapfile -t PATHS < <(echo "$manifest" | sed '/^\s*$/d')

# Categorize each path.
MOVES=()      # src:dst pairs that will actually be moved
ALREADY=()    # already live (target exists, source doesn't)
MISSING=()    # not in archive AND not live — genuinely missing
CONFLICT=()   # both source (archived) AND target (live) exist

for rel in "${PATHS[@]}"; do
    src="${ARCHIVE_ROOT}/${rel}"
    dst="${REPO_ROOT}/${rel}"
    if [[ -e "$src" && -e "$dst" ]]; then
        CONFLICT+=("$rel")
    elif [[ -e "$src" && ! -e "$dst" ]]; then
        MOVES+=("$rel")
    elif [[ ! -e "$src" && -e "$dst" ]]; then
        ALREADY+=("$rel")
    else
        MISSING+=("$rel")
    fi
done

# ─────────────────────────────────────────── Report

echo "Feature: $FEATURE"
echo "Archive root: $ARCHIVE_ROOT"
if [[ $DRY_RUN -eq 1 ]]; then
    echo "Mode: DRY RUN — no files will be moved"
fi
echo ""
echo "Would move (${#MOVES[@]}):"
for p in "${MOVES[@]}"; do echo "  archived/$p -> $p"; done
[[ ${#MOVES[@]} -eq 0 ]] && echo "  (none — feature already fully live or already missing)"
echo ""

if [[ ${#ALREADY[@]} -gt 0 ]]; then
    echo "Already live (${#ALREADY[@]}) — skipped:"
    for p in "${ALREADY[@]}"; do echo "  $p"; done
    echo ""
fi

if [[ ${#CONFLICT[@]} -gt 0 ]]; then
    echo "CONFLICT (${#CONFLICT[@]}) — both archived and live exist:" >&2
    for p in "${CONFLICT[@]}"; do echo "  archived/$p  vs  $p" >&2; done
    echo "Resolve manually before re-running." >&2
    exit 3
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "MISSING (${#MISSING[@]}) — not in archive or repo:" >&2
    for p in "${MISSING[@]}"; do echo "  $p" >&2; done
    echo "The manifest is stale or the file was deleted; skipping and continuing." >&2
    echo ""
fi

if [[ ${#MOVES[@]} -eq 0 ]]; then
    echo "Nothing to move. Exiting."
    exit 0
fi

# ─────────────────────────────────────────── Execute

if [[ $DRY_RUN -eq 1 ]]; then
    echo "Dry run — no changes made."
else
    IN_GIT_REPO=0
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then IN_GIT_REPO=1; fi

    for rel in "${MOVES[@]}"; do
        src="archived/$rel"
        dst="$rel"
        mkdir -p "$(dirname "$dst")"
        if [[ $IN_GIT_REPO -eq 1 && -n "$(git ls-files -- "$src" 2>/dev/null || true)" ]]; then
            git mv "$src" "$dst"
        else
            mv "$src" "$dst"
        fi
        echo "  ✓ $src -> $dst"
    done
    echo ""
    echo "Restored ${#MOVES[@]} files for '$FEATURE'."
fi

# ─────────────────────────────────────────── Manual steps footer

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "MANUAL STEPS still required to make '$FEATURE' reachable:"
echo "─────────────────────────────────────────────────────────────"
get_manual "$FEATURE"
echo ""
echo "After you wire routes/imports, restart the affected service:"
echo "  sudo supervisorctl restart backend   # if backend routers changed"
echo "  # frontend hot-reloads automatically"
echo "─────────────────────────────────────────────────────────────"
