#!/usr/bin/env bash
# Sets up a daily cron job that runs generate_digest.py at 11:00 local time.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
GENERATE="$SCRIPT_DIR/generate_digest.py"
LOG="$SCRIPT_DIR/logs/digest.log"
CRON_MARKER="generate_digest.py"

mkdir -p "$SCRIPT_DIR/logs"
chmod +x "$GENERATE"

CRON_LINE="0 11 * * * cd $SCRIPT_DIR && $PYTHON $GENERATE >> $LOG 2>&1"

if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
  echo "✓ Cron job already registered."
else
  ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
  echo "✓ Cron job added — runs every day at 11:00."
fi

echo ""
echo "Active crontab:"
crontab -l

echo ""
echo "─────────────────────────────────────────────────────────────────────────"
echo "Setup complete. Before the first run:"
echo "  1. Copy .env.example to .env and fill in ANTHROPIC_API_KEY"
echo "  2. (Optional) Set NTFY_TOPIC and subscribe at https://ntfy.sh/<topic>"
echo "  3. (Optional) Set OBSIDIAN_VAULT_PATH"
echo "  4. Install Python deps:  pip3 install -r requirements.txt"
echo "  5. Test immediately:     python3 generate_digest.py"
echo "  6. Serve the web app:    python3 -m http.server 8000"
echo "─────────────────────────────────────────────────────────────────────────"
