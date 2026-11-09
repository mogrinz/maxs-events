# Upgrade an existing Max's Events installation to v1.0

**Do not use the fresh-install `setup.sh` procedure to upgrade an existing working system.** Make an off-Pi backup of `~/maxs-events/data/`, and preferably an image of the Pi's SD card, before proceeding.

Download the official `maxs-events.zip` release asset, **not** GitHub's source archive. Transfer it to the Pi's home directory. The release ZIP contains the `maxs-events/` directory, bundled fonts and the current `upgrade.sh`.

On the Pi, as your normal user:

```bash
cd ~
test -d maxs-events/data || { echo 'Not an existing installation; use README.md'; exit 1; }
cp -a maxs-events maxs-events-backup-before-v1.0
unzip -o maxs-events.zip
cd ~/maxs-events
bash upgrade.sh
```

`upgrade.sh` verifies that existing configuration, the Python environment, the service, and the bundled font stylesheet are present, then restarts `maxs-events.service`. It does **not** rerun setup, replace `data/`, or modify the Pi's network configuration. Existing users, calendars, screen assignments, custom themes and settings remain in `data/`, provided the release ZIP is extracted *over* the existing directory and not into a fresh location.

**Important:** This is an application-code upgrade, not a universal operating-system or network-controller migration. Very old private prototypes may use a different service or layout and are not covered by this procedure. The special legacy RC8 network-controller migration is retained separately as `legacy_network_controller_migration.py`; it is **not** invoked by `upgrade.sh`. Only use it when repairing a verified older network-controller installation, after checking for a pending network switch and with physical or alternative network access available. Similarly, a legacy root-owned `data/menu-state.json` may need a deliberate ownership repair; the general upgrade script does not silently change permissions.

After upgrading, reload each Onn/TV kiosk browser once to load changed CSS and JavaScript (data polling does not reload program assets). Verify administrator login, calendar assignments, `/display/screen1` and `/display/screen20`, and both portrait and landscape displays. Keep SSH or console access while testing.

If the service fails, inspect:

```bash
sudo journalctl -u maxs-events.service -n 80 --no-pager
```

Keep the pre-upgrade directory backup until the new installation has been verified. Never commit local configuration or backups to the public repository.
