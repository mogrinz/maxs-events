#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$EUID" -eq 0 ]]; then
  echo "Run setup as your regular Pi user, without sudo."
  exit 1
fi
umask 077
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [[ ! -f .events.env ]]; then
  printf '%s\n' 'MENU_PORT=8080' > .events.env
fi
chmod 600 .events.env
# Verify bundled web fonts locally. The installer only downloads missing variants.
.venv/bin/python install_theme_fonts.py
.venv/bin/python configure.py
printf '%s\n' "Setup complete. Run: sudo python3 install_service.py"
