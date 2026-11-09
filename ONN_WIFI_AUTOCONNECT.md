# Onn stick: optional offline Wi-Fi auto-connect workaround

**[Companion video: Connecting the Onn stick to an offline Pi hotspot](https://youtu.be/kLXIXsSObfs)**

Some Google TV / Onn firmware will manually connect to a Wi-Fi hotspot without Internet but fail to reconnect after reboot. The following workaround helped on the tested device with the Pi's 2.4 GHz hotspot. Other firmware and device models may behave differently. It is not necessary if your stick reconnects normally.

## 1. Start on a working Internet-connected Wi-Fi network

Connect both your **computer and Onn stick to the same normal Wi-Fi network**. Do not forget this network until after ADB configuration. Networks with client isolation can prevent ADB connections.

## 2. Install Android Platform Tools

Download the official [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) and extract them. Open a terminal or PowerShell in that folder. The ADB commands below run **on your computer**, not the Pi.

## 3. Enable ADB debugging on the stick

On the Onn device, go to **Settings → System → About**. Highlight **Android TV OS Build** and select it seven times to enable Developer options. Return to **Developer options** and enable **ADB debugging** or **Wireless debugging**, depending on firmware. Menu names may differ.

## 4. Connect and authorize ADB

Get the stick's IP address from Network & Internet and substitute it below:

```bash
adb connect 192.168.1.125
adb devices
```

Accept the authorization prompt on the stick. You should see the device with status `device`, not `unauthorized`. Newer Android versions may require wireless pairing, with separate pairing and debugging ports:

```bash
adb pair <ONN_IP>:<PAIRING_PORT>
adb connect <ONN_IP>:<DEBUG_PORT>
adb devices
```

## 5. Disable the captive-portal validation check

This changes an Android **system-wide** setting:

```bash
adb shell settings put global captive_portal_mode 0
adb shell settings get global captive_portal_mode
```

The second command should return `0`. This verifies the setting was applied, not that auto-reconnection is guaranteed on your firmware.

## 6. Enable and confirm the Pi hotspot

In **Max's Events → System**, select **Switch to Events Hotspot**. Rejoin its new Wi-Fi network from your computer/phone, then visit `http://192.168.50.1:8080/system` and select **Keep this mode** within three minutes. Otherwise the Pi is designed to restore its previous normal Wi-Fi connection. The hotspot has **no Internet access**.

## 7. Connect the Onn and forget other networks

On the stick, join the Pi hotspot SSID and enter its password. If prompted, choose to remain connected despite the lack of Internet. In Google TV's saved Wi-Fi networks, **Forget all other networks**, including the original Internet-connected Wi-Fi used for ADB setup. Keep only the Pi hotspot. This will terminate the earlier ADB connection and is expected.

Set Fully Kiosk's Start URL to:

```text
http://192.168.50.1:8080/display/screen1
```

Change the screen number for other displays. Test a reboot and a complete power cycle of both the stick and Pi, including simultaneous startup and stick-first startup.

## Reversal and precautions

To restore Android's normal captive-portal behavior from ADB on a reachable network:

```bash
adb shell settings put global captive_portal_mode 1
```

Alternatively, remove the override to return to device defaults:

```bash
adb shell settings delete global captive_portal_mode
```

Disabling captive-portal checks may prevent Android from noticing public Wi-Fi login portals or other connectivity problems. Disable ADB/Wireless debugging after setup unless still needed. This workaround is device and firmware dependent, not a universal fix.
