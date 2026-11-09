# Max's Events v1.0 validation checklist

This file is a **release verification checklist**, not a claim that every item has been tested on every Raspberry Pi or TV. Earlier internal RC validation logs were removed because some described the separate Max's Menu application and did not validate Max's Events v1.0.

## Automated checks

On a development machine with project dependencies installed:

```bash
python -m pytest -q tests --ignore=tests/test_product.py --ignore=tests/test_rc3.py
python install_theme_fonts.py
python build_release.py
```

The release workflow runs these checks and builds the offline ZIP. The exclusion of the two legacy tests reflects the current release workflow, not evidence that those tests passed.

## Before making the repository public

- Verify the official release ZIP is produced outside the source tree, contains `maxs-events/`, required locally bundled fonts and licenses, and passes ZIP integrity verification.
- Verify `README.md`, `UPGRADING.md`, `RELEASE_V1.0.md` and the GitHub release workflow agree on the archive name and supported upgrade procedure.
- Confirm no actual credentials, account files, private configuration, backups or personal data are present in the working tree **or Git history**.
- Test a fresh installation on the target Pi OS, including application and network-controller systemd services, health endpoint, and reboot.
- Test an in-place upgrade on a backed-up existing Max's Events installation; verify user accounts, ICS sources, screen assignments, uploaded files, themes and network settings survive.
- Verify both List and Detail views, portrait/landscape rotation, screens 1 and 20, and 12/24-hour time formatting.
- Verify offline operation with already fetched calendars, and confirm bundled web fonts load without Internet.
- Test hotspot switching, confirm/rollback, Onn reconnection, and kiosk auto-launch on the intended hardware.
- Refresh kiosk browsers after deploying changed CSS/JS, and verify live event/configuration polling separately.

## Publishing scope

Removing files from the current branch does **not** remove them from prior Git commits. If the repository's private development history should not become publicly readable, publish using a reviewed clean-history approach before changing visibility. Do not publish until that separate review is complete.
