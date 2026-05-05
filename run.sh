#!/bin/bash
# ============================================================
# JobCopilot Étudiant ISE — Lanceur automatique
# Usage : ./run.sh [commande]
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   🎓 JobCopilot Étudiant ISE          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# Vérifie Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 non trouvé. Installe Python 3.10+ depuis python.org${NC}"
    exit 1
fi

PYTHON=$(command -v python3)
echo -e "${GREEN}✓${NC} Python : $($PYTHON --version)"

# Vérifie / installe les dépendances
if [ ! -f ".deps_installed" ]; then
    echo -e "${YELLOW}→ Installation des dépendances...${NC}"
    $PYTHON -m pip install -r requirements.txt -q
    if [ $? -eq 0 ]; then
        touch .deps_installed
        echo -e "${GREEN}✓ Dépendances installées${NC}"
    else
        echo -e "${RED}❌ Erreur installation. Lance : pip install -r requirements.txt${NC}"
        exit 1
    fi
fi

# Vérifie la clé API
if [ -z "$ANTHROPIC_API_KEY" ] && [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}⚠  Clé API Anthropic manquante${NC}"
    echo "   Le scoring IA nécessite une clé API Claude."
    echo "   1. Va sur https://console.anthropic.com"
    echo "   2. Crée une clé API"
    echo "   3. Crée un fichier .env dans ce dossier avec :"
    echo "      ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx"
    echo ""
    echo "   Tu peux quand même utiliser --scan-only sans clé API."
    echo ""
fi

# Dispatch commandes
case "${1:-run}" in
    run)
        echo -e "${CYAN}→ Lancement du pipeline complet (scan + scoring + CV/LM)...${NC}"
        $PYTHON main.py
        ;;
    dashboard|dash)
        echo -e "${CYAN}→ Ouverture du tableau de bord...${NC}"
        $PYTHON main.py --dashboard
        ;;
    daemon)
        echo -e "${CYAN}→ Mode daemon (scan quotidien automatique)...${NC}"
        $PYTHON main.py --daemon
        ;;
    scan)
        echo -e "${CYAN}→ Scan uniquement (sans IA)...${NC}"
        $PYTHON main.py --scan-only
        ;;
    score)
        echo -e "${CYAN}→ Scoring des offres en base...${NC}"
        $PYTHON main.py --score-only
        ;;
    help|*)
        echo "Usage : ./run.sh [commande]"
        echo ""
        echo "  run       → Pipeline complet (défaut)"
        echo "  dashboard → Tableau de bord interactif"
        echo "  daemon    → Scan automatique quotidien"
        echo "  scan      → Scan uniquement (sans clé API)"
        echo "  score     → Score les offres en base"
        echo ""
        ;;
esac
