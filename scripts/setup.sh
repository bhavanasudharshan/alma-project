#!/usr/bin/env bash
#
# One-command bootstrap for a fresh clone.
#
# Idempotent: safe to run repeatedly. Never overwrites an existing .env, and never
# prints a secret value -- it only says where the credentials live.
#
#   ./scripts/setup.sh              # api + web dependencies, .env, database
#   ./scripts/setup.sh --with-e2e   # also install the Playwright browser

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WITH_E2E=false
for arg in "$@"; do
  case "$arg" in
    --with-e2e) WITH_E2E=true ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

# --- output helpers ---------------------------------------------------------------
if [ -t 1 ]; then
  BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

step() { printf '\n%s==>%s %s\n' "$BOLD" "$RESET" "$1"; }
ok()   { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
warn() { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$1"; }
die()  { printf '  %s✗%s %s\n' "$RED" "$RESET" "$1" >&2; exit 1; }

# --- prerequisites ----------------------------------------------------------------
MISSING=0

require() {
  local tool="$1" hint_mac="$2" hint_linux="$3" hint_wsl="$4"
  if command -v "$tool" >/dev/null 2>&1; then
    return 0
  fi
  printf '  %s✗%s %s is not installed\n' "$RED" "$RESET" "$tool"
  printf '      macOS:       %s\n' "$hint_mac"
  printf '      Linux:       %s\n' "$hint_linux"
  printf '      Windows/WSL: %s\n' "$hint_wsl"
  MISSING=1
}

step "Checking prerequisites"

require uv \
  "brew install uv  (or: curl -LsSf https://astral.sh/uv/install.sh | sh)" \
  "curl -LsSf https://astral.sh/uv/install.sh | sh" \
  "curl -LsSf https://astral.sh/uv/install.sh | sh"

require node \
  "brew install node@22" \
  "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs" \
  "same as Linux, inside your WSL distribution"

if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$NODE_MAJOR" -lt 20 ]; then
    die "node 20 or newer is required (found $(node --version))"
  fi
  ok "node $(node --version)"
fi

if ! command -v pnpm >/dev/null 2>&1; then
  if command -v corepack >/dev/null 2>&1; then
    warn "pnpm not found; enabling it through corepack"
    corepack enable >/dev/null 2>&1 || true
    corepack prepare pnpm@9 --activate >/dev/null 2>&1 || true
  fi
fi
require pnpm \
  "corepack enable && corepack prepare pnpm@9 --activate" \
  "corepack enable && corepack prepare pnpm@9 --activate" \
  "corepack enable && corepack prepare pnpm@9 --activate"

[ "$MISSING" -eq 0 ] || die "Install the tools above, then run this script again."

command -v uv   >/dev/null 2>&1 && ok "uv $(uv --version | awk '{print $2}')"
command -v pnpm >/dev/null 2>&1 && ok "pnpm $(pnpm --version)"

# --- configuration ----------------------------------------------------------------
step "Configuring"

if [ -f .env ]; then
  ok ".env already exists (left untouched)"
else
  cp .env.example .env
  ok ".env created from .env.example"
fi

# --- dependencies -----------------------------------------------------------------
step "Installing API dependencies"
(cd api && uv sync)
ok "api dependencies installed"

step "Installing web dependencies"
(cd web && pnpm install --frozen-lockfile)
ok "web dependencies installed"

if [ "$WITH_E2E" = true ]; then
  step "Installing the Playwright browser"
  (cd web && pnpm exec playwright install chromium)
  ok "chromium installed"
fi

# --- database ---------------------------------------------------------------------
step "Preparing the database"
mkdir -p data
(cd api && uv run alembic upgrade head)
ok "migrations applied"

# --- done -------------------------------------------------------------------------
cat <<EOF

$BOLD Setup complete.$RESET Start everything with:

    make dev

  Web app       http://localhost:3000
  Public form   http://localhost:3000/apply
  Status portal http://localhost:3000/status
  API docs      http://localhost:8000/docs
  Health        http://localhost:8000/api/v1/health

  The attorney sign-in email and password are ATTORNEY_EMAIL and ATTORNEY_PASSWORD
  in your .env file. They are placeholders for local use; change them before
  deploying anywhere (the app refuses to start outside ENVIRONMENT=local if you do not).

  Populate the queue with demo data:  make seed
  Something not working?              make doctor

EOF
