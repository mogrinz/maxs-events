# Max's Events

**Free, self-hosted digital event boards, powered by a Raspberry Pi.**

Max's Events turns a Raspberry Pi into a central event-schedule server for TVs, monitors, or tablets. Upload iCalendar (`.ics`) files or subscribe to iCalendar URLs, assign calendars to screens, and show live schedules using an inexpensive streaming stick or any compatible web browser. There is no hosted service or subscription for the Pi software.

The server can use an existing network or create an optional offline Wi-Fi hotspot. Fonts needed for the included themes are bundled locally. Kiosk displays poll for new events and configuration changes approximately every **15 seconds** while the Pi is reachable. If connectivity is interrupted, an already-open display retains its previous schedule.

## Features

- **20 screen addresses** (`/display/screen1` through `/display/screen20`); any number of physical displays can use one address.
- Two layout modes: **List** and **Detail**, with portrait and landscape screen orientations.
- Multiple ICS file uploads and iCalendar URL subscriptions, source colors, and per-screen calendar selection.
- Screen titles, optional detail headers and subtitles, Today or a chosen date, 12/24-hour time, all-day events, visibility and description controls, and continuous scrolling.
- Global themes, per-screen overrides, and uploadable custom CSS themes; built-in fonts work without Internet access.
- **19 included example ICS calendars**: four repeating demo rooms and 15 theme examples.
- Administrator accounts, backups, network configuration and an optional Pi-hosted Wi-Fi hotspot.
- Local screens run on Android/Google TV, a tablet, or a computer browser. On some Android/Google TVs, Fully Kiosk can run directly without an extra streaming stick.

**How it works:** the Pi serves web pages over Wi-Fi or Ethernet; it does *not* drive the TVs via HDMI cables. Each display loads its assigned URL and refreshes its event data from the Pi.

## What you'll need

| Item | Notes |
| --- | --- |
| Raspberry Pi and suitable power supply | A Pi Zero 2 W is a tested project platform; choose hardware with sufficient network connectivity. |
| **32 GB microSD card recommended** | Use a quality card. Keep an image backup and ideally a spare Pi/card for quick recovery. |
| Wired or Wi-Fi network | Existing network is simplest. Optional offline hotspot needs compatible Wi-Fi AP hardware. |
| TV, monitor, or tablet | A web browser capable of showing the kiosk URL. |
| Optional onn. Full HD Google TV streaming stick | One per TV if a compatible browser is not built into the television. |
| Computer with microSD reader | For preparing Raspberry Pi OS and transferring the release ZIP. |

The optional Onn approach uses [Fully Kiosk Browser & Lockdown](https://play.google.com/store/apps/details?id=de.ozerov.fully), a third-party app with free and paid features. Check the features required by your device before purchasing a license.

## 1. Set up the Raspberry Pi

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your Windows, macOS, or Linux computer:

1. Choose your Pi model and a compatible **Raspberry Pi OS Lite** image (Raspberry Pi OS 13 / Trixie is recommended for this networking setup). Choose the appropriate 32-bit/64-bit image for your hardware.
2. Select the microSD card, preferably **32 GB or larger**.
3. Configure a hostname, such as `maxsevents`, and a **Pi OS username and password**. Enable SSH and select the correct Wi-Fi country. If you plan to use existing Wi-Fi, enter its credentials; if using Ethernet, connect the cable.
4. Write the card and boot the Pi. Keep it on a normal Internet-connected network during initial package installation.

**Pi OS login and Max's Events login are different.** The Pi OS account is used for SSH and setup. The web administrator account is created by the installation script. No default administrator password is supplied.

To find the Pi, try its `.local` hostname, inspect your router, or run `hostname -I` on the Pi's console. On Windows PowerShell:

```powershell
ssh YOUR_PI_USER@maxsevents.local
```

If `.local` name resolution fails, use the actual numeric Pi IP address.

## 2. Transfer the installer ZIP

Download **`maxs-events-v1.0-offline.zip`** from this repository's [GitHub Releases](https://github.com/mogrinz/maxs-events/releases). Use the release ZIP, **not** GitHub's auto-generated Source code ZIP. The packaged archive contains a `maxs-events/` directory and bundled web fonts.

For example, from Windows PowerShell on your **computer**:

```powershell
$piUser = 'YOUR_PI_USER'
$piAddress = 'maxsevents.local'  # Or the Pi's actual IP
$release = Join-Path $HOME 'Downloads\maxs-events-v1.0-offline.zip'
scp "$release" "${piUser}@${piAddress}:~/"
ssh "${piUser}@${piAddress}"
```

The `scp` command transfers the archive. The `ssh` command opens a terminal on the Pi. Neither command requires entering a password in the command itself.

## 3. Install Max's Events on the Pi

The following commands run on the **Pi**, after SSH login. For a fresh install only:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip unzip network-manager \
    hostapd dnsmasq-base
cd ~
test ! -e "$HOME/maxs-events" || { echo 'STOP: Existing installation. See UPGRADING.md'; exit 1; }
unzip maxs-events-v1.0-offline.zip
cd ~/maxs-events
bash setup.sh
```

`setup.sh` installs Python dependencies (Internet access is useful for the first installation) and creates the application administrator. **All built-in theme web-font binaries are already included in the ZIP**; these do not need a Google Fonts download. The installer asks for site name, IANA timezone such as `America/New_York`, administrator username/password, and optional hotspot configuration. If you select a hotspot, you will also set its SSID, password, interface and country. It will *not* switch networks during setup.

Start the service:

```bash
sudo python3 install_service.py
curl http://localhost:8080/health
```

The health endpoint should report `"status":"ok"` and version `1.0.0`. The `maxs-events.service` starts automatically after subsequent reboots. If the installer reports a network issue, remain on normal Wi-Fi and inspect [Troubleshooting](TROUBLESHOOTING.md) before switching modes.

**First-install caution:** the network controller uses some historical internal service names starting with `maxs-menu-`; those names are retained for compatibility. Do not manually rename those Linux services or install Max's Menu and Max's Events hotspot controllers on the same Pi without reviewing their shared networking state.

## 4. Configure calendars and screens

On a computer or phone on the same network, open:

```text
http://maxsevents.local:8080/login
```

Or use `http://YOUR_PI_IP:8080/login`. Sign in using the **Max's Events administrator credentials** created in setup.

In **Calendar Sources**, upload an `.ics` file or add an iCalendar subscription URL. Source names and colors can be edited. Uploading the *same filename* again replaces that calendar's contents while retaining its identity and screen assignments. A remote calendar subscription may lag behind edits because of caching by the upstream provider, particularly Google Calendar.

Open **Edit Screens**, select one of the 20 logical screens, assign the calendars to show, then choose List or Detail view, title, orientation, scrolling, date, visibility, and theme settings. Screens can inherit the global theme or override it. A screen's URL never changes when you edit its settings.

Sample calendars are included in `examples/`; import them through Calendar Sources to explore the themes immediately. Use `static/examples/maxs-events-custom-theme.css` as a starting point for a custom theme.

## 5. Set up the onn. streaming stick and TV

Repeat this for each TV needing its own player.

1. Plug the **onn. Full HD Streaming Device with Google TV** into the TV's HDMI input, connect its power adapter, and complete initial Google TV setup on an **Internet-connected Wi-Fi network**.
2. Find and install [**Fully Kiosk Browser & Lockdown**](https://play.google.com/store/apps/details?id=de.ozerov.fully) if available for your device.
3. Open Fully Kiosk and set its **Start URL** to the desired screen:

   ```text
   http://YOUR_PI_ADDRESS:8080/display/screen1
   ```

   Replace `YOUR_PI_ADDRESS` with the Pi's IP or working hostname. In offline hotspot mode, use `http://192.168.50.1:8080/display/screen1`.
4. Enable full-screen display and hide browser navigation controls where supported.
5. Look for **Launch on Boot / Start on Boot** and **Keep Screen On** in Fully Kiosk. Enable the available options and grant the Android permissions needed for your installation.
6. **Fully restart** the TV/stick and verify that it reconnects to Wi-Fi, starts the browser, and loads the correct schedule without intervention. Firmware may restrict automatic startup.

Use `/display/screen2`, `/display/screen3` and so on up to `/display/screen20` for other logical screens. Multiple TVs can point to the same screen URL. For portrait displays connected to an Onn with landscape video output, select Portrait in Edit Screens; the kiosk rotates the rendered page for that display.

A compatible Android/Google TV with Fully Kiosk may not need an Onn stick at all. We tested browser startup on a Sony Google TV, but **check your specific television's firmware**. The page can also run in a tablet browser; on an iPad, **Guided Access** can restrict use to the chosen app.

## 6. Optional: use the Pi's offline hotspot

Hotspot mode allows the Pi and displays to operate on a self-contained local network. Your Wi-Fi hardware must support access-point mode. The application uses a **2.4 GHz hotspot on channel 6**. During initial Pi setup, retain a normal Internet-connected network for Python package installation and for configuring the stick.

1. In Max's Events **System**, select **Switch to Events Hotspot**.
2. Reconnect your phone/computer to the new Pi hotspot SSID.
3. Visit `http://192.168.50.1:8080/system` and select **Keep this mode** within the **three-minute** confirmation window. Otherwise the switch is designed to roll back.
4. On the Onn stick, connect to that SSID and use `http://192.168.50.1:8080/display/screen1` as the Start URL. If the stick refuses to reconnect to Wi-Fi with no Internet, use [the Onn hotspot auto-connect instructions](ONN_WIFI_AUTOCONNECT.md) and the [companion video](https://youtu.be/kLXIXsSObfs).
5. Once hotspot networking is working, **forget all other saved Wi-Fi networks on the Onn** to reduce accidental reconnection to a different network. Test Pi and stick power cycles, including both devices starting together.

The hotspot intentionally provides **no Internet connection**. Locally uploaded calendars and already downloaded event data can be shown offline, but external calendar subscriptions cannot receive new events while the Pi is offline. A correct Pi clock is important for displaying today's events; consider a battery-backed RTC for a permanently disconnected Pi.

**Important:** switch/rollback requires a working saved normal Wi-Fi profile. The network switch can temporarily drop your SSH connection. Use a local console or another recovery option if experimenting with network modes. An Ethernet-only Pi does not need to enable a hotspot.

Some Onn firmware treats Internet-free Wi-Fi as unusable. The [ADB workaround guide](ONN_WIFI_AUTOCONNECT.md) explains the optional `adb shell settings put global captive_portal_mode 0` command, its verification and reversal, and the security implications. It also explains why your computer and stick must start on the same normal Wi-Fi for ADB configuration.

## 7. Backups, upgrades, and troubleshooting

Under **System**, download the application backup and store it **off the Pi**. A backup may contain sensitive account and networking information; keep it private. Also make a **clone of the microSD card** and consider keeping a spare Raspberry Pi for hardware failure recovery. The application backup alone cannot recreate the operating system or SSH setup.

To upgrade an existing installation, use [UPGRADING.md](UPGRADING.md). Do not run the fresh-install commands over an existing configured system. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for clocks, connections, kiosk refresh, hotspot switching and password recovery.

## License

The Max's Events application is released under the **MIT License** ([LICENSE](LICENSE)). Bundled fonts use their own open-source licenses, documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and `static/fonts/licenses/`. Fully Kiosk is third-party software with its own terms and is not included in this repository.

## Publishing and reproducible releases

Run `python install_theme_fonts.py` to confirm all required font variants are available locally, then `python build_release.py` to produce an offline installation archive in the parent directory. The GitHub Actions **Publish v1.0 release** workflow runs the tests, validates the fonts, builds the ZIP, and creates the `v1.0.0` release when manually started by the maintainer. It refuses to overwrite an existing release.
