#!/usr/bin/env bash
# In-place application upgrade after extracting the official release ZIP.
# Never rerun setup.sh or replace the existing data directory.
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$EUID" -eq 0 ]]; then
  echo 'Run as the normal Pi user, not root.' >&2
  exit 1
fi
if [[ ! -d data || ! -f .events.env ]]; then
  echo 'This is not an existing Maxs Events installation. For a new installation, follow README.md.' >&2
  exit 1
fi
if [[ ! -f static/fonts/events-google-fonts.css ]] || [[ ! -s static/fonts/events-google-fonts.css ]]; then
  echo 'Bundled offline font stylesheet missing. Extract the official v1.0 offline ZIP before upgrading.' >&2
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  echo 'Existing Python virtual environment missing. Inspect the installation before proceeding.' >&2
  exit 1
fi
if ! systemctl list-unit-files maxs-events.service --no-legend 2>/dev/null | grep -q '^maxs-events.service'; then
  echo 'maxs-events.service not found. Check the installation before proceeding.' >&2
  exit 1
fi
sudo systemctl restart maxs-events.service
sudo systemctl --no-pager status maxs-events.service
echo 'Maxs Events application upgrade complete. Reload kiosk browsers to load updated CSS and JavaScript.'
