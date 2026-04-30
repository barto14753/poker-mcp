#!/bin/bash
set -euo pipefail

# =============================================================================
# run.sh — Poker MCP: setup środowiska i uruchomienie aplikacji
#
# Użycie:
#   ./run.sh              # uruchamia serwer Flask (tryb domyślny)
#   ./run.sh --mcp        # uruchamia serwer MCP (stdio)
#   ./run.sh --install    # tylko instaluje zależności, nie uruchamia
#   ./run.sh --force      # reinstaluje venv od zera
#   ./run.sh --help       # wyświetla tę pomoc
# =============================================================================

# --- Kolory ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# --- Flagi ---
MODE="flask"
FORCE=false
INSTALL_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --mcp)      MODE="mcp" ;;
        --install)  INSTALL_ONLY=true ;;
        --force)    FORCE=true ;;
        --help|-h)
            sed -n '/^# Użycie:/,/^# =====/p' "$0" | grep -v '^# =====' | sed 's/^# //'
            exit 0
            ;;
        *) error "Nieznana opcja: $arg. Użyj --help." ;;
    esac
done

# --- Katalog skryptu jako katalog roboczy ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Poker MCP — środowisko deweloperskie ${NC}"
echo -e "${BLUE}========================================${NC}"

# --- Sprawdź wymagania systemowe ---
info "Sprawdzam wymagania systemowe..."
command -v python3 >/dev/null 2>&1 || error "python3 nie jest zainstalowany. Zainstaluj go i spróbuj ponownie."

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    error "Wymagany Python >= 3.9. Znaleziono: $PYTHON_VERSION"
fi
success "Python $PYTHON_VERSION — OK"

# --- Wirtualne środowisko ---
if [ "$FORCE" = true ] && [ -d "venv" ]; then
    warn "Usuwam istniejące venv (--force)..."
    rm -rf venv
fi

if [ ! -d "venv" ]; then
    info "Tworzę wirtualne środowisko Python..."
    python3 -m venv venv
    success "venv utworzone"
else
    info "Wirtualne środowisko już istnieje — pomijam tworzenie"
fi

# --- Aktywacja venv ---
# shellcheck source=/dev/null
source venv/bin/activate
success "Środowisko wirtualne aktywowane"

# --- Instalacja zależności ---
info "Instaluję zależności z requirements.txt..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
success "Zależności zainstalowane"

if [ "$INSTALL_ONLY" = true ]; then
    success "Instalacja zakończona. Aplikacja nie została uruchomiona (--install)."
    exit 0
fi

# --- Inicjalizacja bazy danych ---
info "Inicjalizuję bazę danych (jeśli potrzeba)..."
python3 - <<'EOF'
from app import app, db
with app.app_context():
    db.create_all()
print("Baza danych gotowa.")
EOF
success "Baza danych gotowa"

# --- Uruchomienie ---
export FLASK_APP=app.py
export FLASK_ENV=development
export POKER_API_URL="${POKER_API_URL:-http://localhost:5001}"

if [ "$MODE" = "mcp" ]; then
    info "Uruchamiam serwer MCP (stdio)..."
    info "POKER_API_URL=${POKER_API_URL}"
    echo ""
    exec python3 mcp_server.py
else
    info "Uruchamiam serwer Flask na http://0.0.0.0:5001 ..."
    echo ""
    exec python3 app.py
fi
