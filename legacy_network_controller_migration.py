"""Legacy Max's Events RC8 network-controller migration.

This optional tool updates an already installed root-owned controller in place,
without switching networks. It is NOT part of the normal v1.0 application upgrade.
Run only after reviewing the original RC8 preconditions in UPGRADING.md.
"""
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CONFIG = Path('/etc/maxs-menu-network.json')
INSTALLED = Path('/usr/local/lib/maxs-menu-network/network_service.py')
STATE = Path('/var/lib/maxs-menu-network/state.json')
SERVICE = 'maxs-menu-network.service'


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run the network-controller upgrade with sudo.')
    if not CONFIG.is_file() or not INSTALLED.is_file():
        print('Network controller not installed; no controller update needed.')
        return
    config = json.loads(CONFIG.read_text())
    owner = pwd.getpwuid(ROOT.stat().st_uid).pw_name
    if config.get('user') != owner:
        raise SystemExit('Network controller belongs to a different OS user. No changes made.')
    if INSTALLED.is_symlink() or INSTALLED.parent.is_symlink() or INSTALLED.stat().st_uid != 0:
        raise SystemExit('Unexpected installed network-controller ownership. No changes made.')
    if STATE.exists() and json.loads(STATE.read_text()).get('pending'):
        raise SystemExit('A network switch trial is pending. Confirm/cancel it before upgrading RC8.')
    unit = subprocess.run(['systemctl', 'show', SERVICE, '-p', 'ExecStart', '--value'],
                          capture_output=True, text=True, check=True).stdout
    if '/usr/local/lib/maxs-menu-network/network_service.py' not in unit:
        raise SystemExit('Installed network-controller service differs from expected. No changes made.')
    original = INSTALLED.read_bytes()
    replacement = (ROOT / 'network_service.py').read_bytes()
    if original == replacement:
        print('Network controller already at RC8.')
        return
    fd, name = tempfile.mkstemp(dir=INSTALLED.parent, prefix='.network-service-rc8-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(replacement)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o644)
        os.replace(name, INSTALLED)
    finally:
        Path(name).unlink(missing_ok=True)
    print('Updated installed network controller. Restarting controller service...')
    result = subprocess.run(['systemctl', 'restart', SERVICE])
    if result.returncode:
        # Restore the previous code if restart fails, then attempt to restart it.
        fd, name = tempfile.mkstemp(dir=INSTALLED.parent, prefix='.network-service-restore-')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(original)
            os.chmod(name, 0o644)
            os.replace(name, INSTALLED)
        finally:
            Path(name).unlink(missing_ok=True)
        subprocess.run(['systemctl', 'restart', SERVICE], check=False)
        raise SystemExit('RC8 network controller could not start. Previous controller code restored.')
    print('Network controller updated. No Wi-Fi switch was requested.')


if __name__ == '__main__':
    main()
