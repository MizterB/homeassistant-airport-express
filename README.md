# AirPort Express for Home Assistant

A Home Assistant custom integration for Apple AirPort Express devices. Communicates via the ACP protocol (TCP 5009) and AirPlay HTTP API (port 7000).

## Features

- **Automatic discovery** — devices are detected via Zeroconf/mDNS (`_airport._tcp`)
- **AirPlay** binary sensor — detects active AirPlay sessions (2-second polling)
- **Firmware** diagnostic sensor — current firmware version
- **Uptime** diagnostic sensor — device uptime
- **IP Address** diagnostic sensor — WAN IP address
- **Reboot** button — restart the device remotely
- **Device info** — name, manufacturer, model, serial number, and MAC address

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/MizterB/homeassistant-airport-express` as an **Integration**
4. Search for "AirPort Express" and install
5. Restart Home Assistant
6. Your AirPort Express devices should be auto-discovered. If not, go to **Settings → Devices & Services → Add Integration → AirPort Express** and enter the host manually.

### Manual

Copy `custom_components/airport_express/` to your Home Assistant `custom_components/` directory and restart.

## Configuration

Discovered devices will prompt for just the admin password. For manual setup, enter the IP address or hostname and password.
