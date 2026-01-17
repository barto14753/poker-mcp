#!/bin/bash

# Skrypt do uruchomienia serwera poker-mcp

# Kolory do outputu
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Poker MCP Server ===${NC}"

# Sprawdź czy istnieje venv
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Tworzę środowisko wirtualne...${NC}"
    python3 -m venv venv
fi

# Aktywuj venv
echo -e "${GREEN}Aktywuję środowisko wirtualne...${NC}"
source venv/bin/activate

# Zainstaluj zależności
echo -e "${GREEN}Instaluję zależności...${NC}"
pip install -q -r requirements.txt

# Uruchom serwer
echo -e "${GREEN}Uruchamiam serwer...${NC}"
export FLASK_APP=app.py
export FLASK_ENV=development
python app.py
