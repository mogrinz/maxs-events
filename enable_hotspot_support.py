"""Opt-in enablement of hotspot *capability*, without switching network mode.

Run as root only after making a full SD backup and connecting normal Ethernet/Wi-Fi.
Keeps the already-installed Max's Menu-derived network daemon names compatible
with Max's Events v0.7 deployments.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

if os.geteuid() != 0:
    sys.exit('Run with sudo.')
root = Path(__file__).resolve().parent
state_path = root/'data/menu-state.json'
config_path = Path('/etc/maxs-menu-network.json')
if not state_path.exists() or not config_path.exists():
    sys.exit('Existing application/network setup not found. Do not use this on a fresh Pi.')
state_stat=state_path.stat()
state=json.loads(state_path.read_text())
config=json.loads(config_path.read_text())
if not state['settings'].get('site_name') or not config.get('user'):
    sys.exit('Invalid current configuration.')
if config.get('enabled') and state['settings'].get('hotspot_enabled'):
    print('Hotspot support is already enabled. Switch modes through System.');sys.exit(0)
for binary in ('nmcli','hostapd','hostapd_cli','dnsmasq','ip'):
    if shutil.which(binary) is None:
        sys.exit('Missing '+binary+'. On your normal network, install hotspot dependencies as documented before retrying.')
from network_service import NM, network_config
nm=NM({**network_config(config),'enabled':True})
cap=nm.capabilities()
if not cap['hotspot_supported']:
    sys.exit('This Wi-Fi adapter cannot operate in hotspot mode: '+cap['hotspot_reason'])
# Do not attempt to change radio connectivity during this operation.
profiles=nm.profiles()
if not (nm.wired_info() or nm.active() in {p['uuid'] for p in profiles}):
    sys.exit('Connect to normal Ethernet or Wi-Fi before enabling support.')
answer=input('Enable hotspot support ONLY (no network switch)? Type ENABLE: ')
if answer!='ENABLE':sys.exit('No changes made.')
from network_service import write_json as atomic_json
backup_suffix=datetime.now(timezone.utc).strftime('.backup-%Y%m%d-%H%M%S')
for path in (state_path,config_path):
    shutil.copy2(path, str(path)+backup_suffix)
try:
    state['settings']['hotspot_enabled']=True
    config['enabled']=True
    atomic_json(state_path,state)
    os.chown(state_path,state_stat.st_uid,state_stat.st_gid)
    os.chmod(state_path,state_stat.st_mode & 0o777)
    atomic_json(config_path,config)
    subprocess.run(['systemctl','restart','maxs-menu-network.service'],check=True)
except Exception:
    shutil.copy2(str(state_path)+backup_suffix,state_path)
    os.chown(state_path,state_stat.st_uid,state_stat.st_gid)
    os.chmod(state_path,state_stat.st_mode & 0o777)
    shutil.copy2(str(config_path)+backup_suffix,config_path)
    subprocess.run(['systemctl','restart','maxs-menu-network.service'],check=False)
    raise
print('Hotspot capability enabled; network mode has NOT changed. Refresh System, set and save a hotspot password, then switch only when ready.')
