#!/bin/bash

# -- CONFIGURATION --
PROJET_PATH="/home/clients/88825ac5e5f79e7ac027b682eb1b2848/sites/thegreenpadel.fr"
PYTHON_PATH="$(which python3)"
SCRIPT_PATH="$PROJET_PATH/scraper/scraper_full_year.py"
LOG_PATH="$PROJET_PATH/logs/scraper.log"

# -- 1. Créer le dossier logs si besoin --
mkdir -p "$PROJET_PATH/logs"

# -- 2. Supprimer d’anciennes entrées cron similaires (évite doublons) --
TMP_CRON=$(mktemp)
crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" > "$TMP_CRON"

# -- 3. Ajouter la nouvelle tâche cron --
echo "0 1 * * * $PYTHON_PATH $SCRIPT_PATH >> $LOG_PATH 2>&1" >> "$TMP_CRON"

# -- 4. Installer la nouvelle crontab --
crontab "$TMP_CRON"
rm "$TMP_CRON"

echo "✅ Cron installé : $PYTHON_PATH $SCRIPT_PATH (tous les jours à 1h, log dans $LOG_PATH)"
