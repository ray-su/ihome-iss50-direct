# iHome iSS50 Direct

[![Validate](https://github.com/ray-su/ihome-iss50-direct/actions/workflows/validate.yml/badge.svg)](https://github.com/ray-su/ihome-iss50-direct/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ray-su/ihome-iss50-direct)](https://github.com/ray-su/ihome-iss50-direct/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

Connect an iHome **iSS50 SmartMonitor** directly to Home Assistant by IP address when HomeKit discovery does not find it.

Home Assistant pairs with the sensor using the **HomeKit Accessory Protocol (HAP)** and its printed code. Apple Home, an Apple hub, and an iHome cloud account are not required during use. This is not a non-HomeKit protocol driver: it bypasses multicast discovery, not authentication or an existing controller's pairing.

**Experimental:** automated tests cover a simulated HAP accessory and Home Assistant APIs. Successful pairing and all readings on a physical iSS50 remain unverified. See [validation](VALIDATION.md).

## Requirements

- Home Assistant Core **2026.11.0 or newer**. This is the initial tested baseline; future HA versions are not guaranteed compatible until tested.
- An iSS50 already connected to Wi-Fi and reachable from the HA host.
- The eight-digit HomeKit code printed on the sensor.
- The accessory must accept a new pairing. Wi-Fi connectivity and absence from Apple Home do not prove that it is unpaired.

If HA's built-in **HomeKit Device** integration discovers the sensor, prefer that supported integration. This custom integration is for manual-IP setup.

## Install with HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ray-su&repository=ihome-iss50-direct&category=integration)

Or add the repository manually:

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/ray-su/ihome-iss50-direct` with category **Integration**.
3. Find **iHome iSS50 Direct**, select it, and download the latest release.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration → iHome iSS50 Direct**.
6. Enter the sensor's IPv4 address, TCP port, and printed HomeKit code.

This is a HACS **custom repository**, not a listing in HACS's default catalog.

### Manual installation

Download the release ZIP from [Releases](https://github.com/ray-su/ihome-iss50-direct/releases). Copy its `custom_components/ihome_iss50` directory into `/config/custom_components/`, then restart HA and add the integration. Do not nest the whole repository inside `custom_components`.

## Configuration

| Field | Meaning |
| --- | --- |
| Sensor IP address | The device's IPv4 address, shown by your router. Reserve it in DHCP. |
| Port | Use the known HAP port; `80` is a useful first candidate. `0` searches only this device's TCP ports and may take several minutes. |
| Pairing code | The eight-digit HomeKit code, with or without dashes. |

The integration stores authenticated controller credentials in HA's config entry, not the printed code. No Apple Home pairing is performed. Do not share HA backups or `.storage` contents: they contain credentials.

## Sensors

| Entity | Requirement |
| --- | --- |
| Temperature | Standard readable HAP current-temperature characteristic |
| Humidity | Standard readable relative-humidity characteristic |
| Illuminance | Standard readable light-level characteristic |
| Motion | Standard readable motion characteristic |
| Occupancy | Standard readable occupancy characteristic |

Only characteristics actually exposed by the accessory become entities. Proprietary sound detection, display settings, Wi-Fi provisioning, and firmware updates are not implemented.

The integration requests event notifications and reads each characteristic individually every 30 seconds as a fallback. Incoming events do not postpone fallback polling. Failed reads mark entities unavailable; successful later polls restore them.

## Connection changes and removal

- **IP address or port changed:** open the integration entry's menu and choose **Reconfigure**. Enter the new address and known port. HA verifies the existing credentials against that endpoint before saving. Reconfiguration does not start a new pairing.
- **Temporary connection failure:** reload the entry or wait for polling/setup retries. Keep the entry so its keys are preserved.
- **Delete the integration:** when the device is reachable, HA attempts to remove its controller pairing from the sensor. Keep the device powered and reachable during deletion. If unpairing fails, HA still deletes the entry; restoring a backup or resetting the sensor may then be necessary. Deleting files through HACS without first deleting the integration entry does not unpair the device.
- **Cancel setup:** an in-progress pairing is allowed to finish and the flow attempts to retain successful credentials. A process crash, HA shutdown, or lost final pairing response can still prevent recovery. Do not intentionally interrupt pairing.

## Troubleshooting

- **Not discovered:** manual IP setup does not require mDNS. HA must still be able to reach the configured TCP port. Guest Wi-Fi, client isolation, VLAN firewalls, and VPN routing can interfere.
- **Cannot connect:** verify the device address and port from the HA network. A router showing a Wi-Fi association does not establish that the HAP service is reachable.
- **Authentication failed:** check the printed code during first pairing. During reconfiguration, verify that this is the original sensor and that it has not been reset.
- **Already paired or no pairing slots:** retain any existing HA entry. If another controller owns the device, remove that pairing from the owning controller. A factory reset may erase Wi-Fi configuration; do not reset merely because discovery is missing.
- **Busy or rate limited:** stop concurrent setup attempts and wait before retrying.

When reporting a bug, include the exact HA Core and integration versions, model/firmware if known, configured port, network layout, and relevant redacted logs. Never post pairing codes, controller keys, access tokens, or backups.

## Development

Use Python **3.14.2 or newer** in the 3.14 series:

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
python -m pytest -q
```

Tests use a loopback-only HAP simulator; they do not contact real sensors. CI runs tests, Ruff, Home Assistant's hassfest, and the HACS repository validator. See [contributing](CONTRIBUTING.md) for release steps and [changelog](CHANGELOG.md) for changes.

## License and attribution

MIT. The initial implementation was imported from `ihome_iss50_direct_v0.1.0.zip`; the original license notice is retained. This is an independent community integration, not an official iHome or Apple product. The generic thermometer icon is from Pictogrammers Material Design Icons; see [NOTICE.md](NOTICE.md).
