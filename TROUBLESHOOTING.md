# Max's Events troubleshooting

## The browser cannot reach the Pi

Confirm both devices are on the same network. Try the Pi IP address if its `.local` hostname doesn't resolve. Check the service on the Pi:

```bash
hostname -I
systemctl is-active maxs-events.service
curl http://localhost:8080/health
sudo journalctl -u maxs-events.service -n 80 --no-pager
```

If localhost works but other devices cannot connect, check router client isolation and firewall settings.

## Calendar or configuration changes do not appear

Connected kiosk pages poll the Pi approximately every 15 seconds for changes. A kiosk with no network connection retains its last displayed events; it cannot update until the Pi is reachable again. Changes to the application CSS or JavaScript require a full kiosk reload, rather than ordinary calendar polling. Calendar subscriptions may also be subject to caching by their provider (notably Google Calendar).

To check source content, open **Calendar Sources** and try a manual refresh; uploaded ICS calendars with the same filename can be replaced while preserving screen assignments. The events displayed depend on the screen's assigned sources, Today/Custom Date setting, and visibility filters.

## Clock and date are wrong in offline hotspot mode

The Pi's local clock and configured timezone govern the events. A Pi without Internet or a battery-backed real-time clock may lose accurate time after extended power loss. Confirm with:

```bash
date
timedatectl status
```

Set the system timezone correctly (`sudo raspi-config` or `timedatectl`) and ensure it has a reliable time source. When operating completely offline, consider a battery-backed RTC. The display can use 12/24-hour time as configured in System.

## Hotspot controls are missing or switching fails

Hotspot requires a Wi-Fi adapter supporting Linux access-point mode and the necessary networking packages. Check:

```bash
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
nmcli -f WIFI-PROPERTIES.AP device show wlan0
systemctl status maxs-menu-network.service --no-pager
systemctl status maxs-menu-hotspot.service --no-pager
```

The shared internal service names contain `maxs-menu` for historical compatibility, even though the application service is `maxs-events.service`. Do not rename installed network services by hand. Network mode switching has a three-minute rollback window; confirm the mode in System before it expires. If you lose network access, use a local console and check the service logs. Avoid switching modes while a trial is pending.

## Onn stick will not reconnect to the offline hotspot

[Watch the companion video](https://youtu.be/kLXIXsSObfs) or follow [ONN_WIFI_AUTOCONNECT.md](ONN_WIFI_AUTOCONNECT.md). First configure ADB with the computer and stick on the same Internet-connected Wi-Fi. The optional tested workaround changes `captive_portal_mode` to `0`. Then connect to the Pi hotspot and **forget all other saved networks** on the stick. Confirm the kiosk's Start URL uses `http://192.168.50.1:8080/display/screen1`, changing the screen number as needed. Test a full power cycle.

## Display colors or portrait spacing differ from the browser preview

The kiosk includes `color-scheme: only light` to discourage Android's automatic darkening. Some firmware can still override colors. The Onn runs portrait mode by rotating content on the stick's landscape video output, while the desktop editor shows an upright preview. Reload the kiosk once after installing a software upgrade, since CSS/JS are not replaced by the 15-second event polling.

## Recovering an administrator password

The Pi OS SSH login and the Max's Events web administrator are separate credentials. Stop the service, run the local reset script as the installation owner, and restart:

```bash
sudo systemctl stop maxs-events.service
cd ~/maxs-events
.venv/bin/python reset_admin.py
sudo systemctl start maxs-events.service
```

## Maintenance and recovery

Keep a copy of the system backup **off** the Pi, and periodically clone the microSD card. A system backup does not replace an SD-card image. An inexpensive spare Pi with a cloned card helps recover quickly from card or hardware failure. Protect backups as they contain application configuration and sensitive account data.
