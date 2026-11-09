"""Enable Max's Events startup using the dedicated maxs-events service."""
import os
from pathlib import Path
import pwd
import subprocess
import json
import time
import urllib.request

root=Path(__file__).resolve().parent
if os.geteuid()!=0:
    raise SystemExit('Run: sudo python3 install_service.py')
owner=pwd.getpwuid(root.stat().st_uid)
if owner.pw_uid==0:
    raise SystemExit('Install as your regular Pi user, not root.')
if not (root/'.events.env').exists() or not (root/'.venv/bin/python').exists():
    raise SystemExit('Run bash setup.sh first.')
if any(c in str(root) for c in '\n\r"\\%'):
    raise SystemExit('Use a simple path such as /home/your-user/maxs-events.')
from install_network_service import install
install(root)

service=f'''[Unit]
Description=Max's Events server
After=network.target

[Service]
Type=simple
User={owner.pw_name}
WorkingDirectory={root}
EnvironmentFile={root/'.events.env'}
ExecStart="{root/'.venv/bin/python'}" "{root/'app.py'}"
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
'''
path=Path('/etc/systemd/system/maxs-events.service')
if path.exists():
    old=path.read_text()
    expected=(f'WorkingDirectory="{root}"',f'WorkingDirectory={root}')
    if not any(line in old for line in expected) or str(root/'.venv/bin/python') not in old or f'User={owner.pw_name}\n' not in old:
        raise SystemExit('An unrelated maxs-events.service exists. Review it before replacing it.')
path.write_text(service)
subprocess.run(['systemd-analyze','verify',str(path)],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','maxs-events.service'],check=True)
subprocess.run(['systemctl','restart','maxs-events.service'],check=True)
port='8080'
for line in (root/'.events.env').read_text().splitlines():
    if line.startswith('MENU_PORT='):
        port=line.split('=',1)[1].strip()
for _ in range(40):
    try:
        with urllib.request.urlopen('http://127.0.0.1:'+str(int(port))+'/health',timeout=1) as response:
            health=json.load(response)
        if health.get('status')=='ok':
            break
    except (OSError,ValueError):
        pass
    time.sleep(.25)
else:
    raise SystemExit('The new server did not become healthy. Check: journalctl -u maxs-events.service -n 50 --no-pager')
print('Max’s Events is running. Check: systemctl status maxs-events.service')
