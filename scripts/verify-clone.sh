#!/usr/bin/env bash
#
# Fresh-clone proof (C5).
#
# Clones this repository into a temporary directory and runs the exact sequence a
# reviewer would, with nothing primed: setup, doctor, tests, then both servers, then
# checks that the API and the public form actually answer. Anything that needs a
# manual step is a README bug.
#
#   make verify-clone                  # canonical: clones HEAD
#   make verify-clone ARGS=--working-tree
#
# --working-tree copies the current working tree instead of cloning HEAD, so the proof
# can be run before the change that fixes setup has been committed. The canonical form
# is the one that matters; the flag exists so a fix can be validated first.
#
# It never touches the working copy: everything happens in the clone.

set -euo pipefail

SOURCE_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLONE_DIR="${VERIFY_CLONE_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/alma-fresh.XXXXXX")}"

USE_WORKING_TREE=false
for arg in "$@"; do
  case "$arg" in
    --working-tree) USE_WORKING_TREE=true ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

BOLD=$'\033[1m'; GREEN=$'\033[32m'; RED=$'\033[31m'; RESET=$'\033[0m'
step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RESET"; }
pass() { printf '%s  PASS%s %s\n' "$GREEN" "$RESET" "$1"; }
fail() { printf '%s  FAIL%s %s\n' "$RED" "$RESET" "$1"; FAILURES=$((FAILURES + 1)); }

FAILURES=0
API_PID=""
WEB_PID=""

cleanup() {
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  # Belt and braces: nothing from this clone may outlive the script.
  pkill -f "$CLONE_DIR" 2>/dev/null || true
  # Leave the clone behind when asked, so a failure can be inspected.
  if [ "${VERIFY_CLONE_KEEP:-0}" != "1" ] && [ -z "${VERIFY_CLONE_DIR:-}" ]; then
    rm -rf "$CLONE_DIR"
  fi
}
trap cleanup EXIT

STARTED=$(date +%s)

rm -rf "$CLONE_DIR"
if [ "$USE_WORKING_TREE" = true ]; then
  step "Copying the working tree into $CLONE_DIR (pre-commit mode)"
  mkdir -p "$CLONE_DIR"
  # Everything git would carry, plus not-yet-committed files; never build output.
  tar -C "$SOURCE_REPO" \
    --exclude=.git --exclude=node_modules --exclude=.venv --exclude=data \
    --exclude=uploads --exclude=.next --exclude=test-results \
    --exclude=playwright-report --exclude=__pycache__ --exclude=.env \
    -cf - . | tar -C "$CLONE_DIR" -xf -
  cd "$CLONE_DIR"
  pass "working tree copied (pre-commit proof, not a real clone)"
else
  step "Cloning into $CLONE_DIR"
  git clone --quiet "$SOURCE_REPO" "$CLONE_DIR"
  cd "$CLONE_DIR"
  pass "clone created ($(git rev-parse --short HEAD))"
fi

step "make setup"
SETUP_STARTED=$(date +%s)
if make setup; then
  pass "setup completed in $(( $(date +%s) - SETUP_STARTED ))s"
else
  fail "make setup"
  exit 1
fi

step "make doctor"
if make doctor; then pass "doctor reports healthy"; else fail "make doctor"; fi

step "make test"
if make test; then pass "test suite green"; else fail "make test"; fi

step "make dev (both servers)"
make dev > "$CLONE_DIR/dev.log" 2>&1 &
DEV_PID=$!

# Wait for readiness rather than sleeping a fixed amount: a slow machine should not
# turn into a false failure.
for _ in $(seq 1 60); do
  curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1 && break
  sleep 1
done
for _ in $(seq 1 60); do
  curl -sf -o /dev/null http://localhost:3000/apply 2>/dev/null && break
  sleep 1
done

HEALTH_BODY="$(curl -s http://localhost:8000/api/v1/health || true)"
APPLY_CODE="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/apply || true)"
STATUS_CODE="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/status || true)"

printf '  API   /api/v1/health -> %s\n' "${HEALTH_BODY:-<no response>}"
printf '  Web   /apply         -> %s\n' "$APPLY_CODE"
printf '  Web   /status        -> %s\n' "$STATUS_CODE"

case "$HEALTH_BODY" in *'"status":"ok"'*) pass "API healthy" ;; *) fail "API health" ;; esac
[ "$APPLY_CODE" = "200" ] && pass "/apply renders" || fail "/apply returned $APPLY_CODE"
[ "$STATUS_CODE" = "200" ] && pass "/status renders" || fail "/status returned $STATUS_CODE"

# uvicorn spawns a worker that does not die with `make dev`, and a survivor holds
# port 8000 and silently poisons the next run (Playwright reuses an existing server).
stop_tree() {
  local pid="$1"
  pkill -P "$pid" 2>/dev/null || true
  kill "$pid" 2>/dev/null || true
}
stop_tree "$DEV_PID"
# Anything still listening on our ports belongs to this run; take it down by path.
pkill -f "$CLONE_DIR/api/.venv" 2>/dev/null || true
pkill -f "$CLONE_DIR/web" 2>/dev/null || true

ELAPSED=$(( $(date +%s) - STARTED ))
step "Result"
printf '  wall clock: %dm %ds\n' $((ELAPSED / 60)) $((ELAPSED % 60))

if [ "$FAILURES" -eq 0 ]; then
  printf '\n%s  A fresh clone works hands-free.%s\n\n' "$GREEN" "$RESET"
  exit 0
fi
printf '\n%s  %d check(s) failed — the README or setup needs fixing.%s\n\n' "$RED" "$FAILURES" "$RESET"
exit 1
