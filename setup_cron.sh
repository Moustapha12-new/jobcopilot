#!/bin/bash
# ============================================================
# setup_cron.sh — Configure le scan quotidien automatique
# Lance une fois : ./setup_cron.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=$(command -v python3 || command -v python)
LOG="$SCRIPT_DIR/logs/cron.log"

# Crée le dossier logs si besoin
mkdir -p "$SCRIPT_DIR/logs"

# Ligne cron : tous les jours à 07:30
CRON_LINE="30 7 * * * cd $SCRIPT_DIR && $PYTHON main.py >> $LOG 2>&1"

echo ""
echo "Configuration du cron job quotidien..."
echo "Heure : 07:30 chaque matin"
echo "Log : $LOG"
echo ""

# Ajoute à crontab (évite les doublons)
(crontab -l 2>/dev/null | grep -v "jobcopilot"; echo "$CRON_LINE") | crontab -

echo "✓ Cron job configuré !"
echo ""
echo "Pour vérifier : crontab -l"
echo "Pour supprimer : crontab -e puis supprime la ligne jobcopilot"
echo ""
echo "Alternative sans cron : lance 'python main.py --daemon' dans un terminal"
