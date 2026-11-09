# iHome iSS50 Direct

[![Validate](https://github.com/ray-su/ihome-iss50-direct/actions/workflows/validate.yml/badge.svg)](https://github.com/ray-su/ihome-iss50-direct/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/ray-su/ihome-iss50-direct)](https://github.com/ray-su/ihome-iss50-direct/releases)
[![Marketplace custom repository](https://img.shields.io/badge/Marketplace-Custom-orange.svg)](https://www.home-assistant.io/integrations/marketplace#custom-repositories)

Connect an iHome **iSS50 SmartMonitor** directly to Home Assistant by IP address when HomeKit discovery does not find it.

Home Assistant pairs with the sensor using the **HomeKit Accessory Protocol (HAP)** and its printed code. Apple Home, an Apple hub, and an iHome cloud account are not required during use. This is not a non-HomeKit protocol driver: it bypasses multicast discovery, not authentication or an existing controller's pairing.

**Experimental:** temperature, humidity, light, and motion have been reported working on a physical iSS50 with version 0.2.0. After updating to 0.3.0, the user confirmed that the **Sound detection** entity appears in HA. Detected/clear transitions are simulator-tested but still await physical-device confirmation. See [validation](VALIDATION.md).

## Requirements

- Home Assistant Core **2026.11.0 or newer**. This is the initial tested baseline; future HA versions are not guaranteed compatible until tested.
- An iSS50 already connected to Wi-Fi and reachable from the HA host.
- The eight-digit HomeKit code printed on the sensor.
- The accessory must accept a new pairing. Wi-Fi connectivity and absence from Apple Home do not prove that it is unpaired.

If HA's built-in **HomeKit Device** integration discovers the sensor, prefer that supported integration. This custom integration is for manual-IP setup.

<!-- ha-marketplace:exclude-start -->

## Install with Marketplace

Home Assistant **2026.11** includes [Marketplace](https://www.home-assistant.io/integrations/marketplace), which replaces HACS. No separate HACS installation is needed. This project is a **custom repository**; add its link before installing.

[![Open iHome iSS50 Direct in Home Assistant Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=ray-su&repository=ihome-iss50-direct&category=integration)

Or add the repository manually:

1. As an administrator, open **Settings → Marketplace** and acknowledge the first-use notice.
2. Select **Add from link** and enter `https://github.com/ray-su/ihome-iss50-direct`.
3. Connect GitHub if prompted, then select **Add**. If asked for a type, choose **Integration**.
4. Open **iHome iSS50 Direct**, select **Install**, and confirm the version. Restart if prompted.
5. Complete the setup that opens, or go to **Settings → Devices & services → Add integration → iHome iSS50 Direct**. Enter the sensor's IPv4 address, TCP port, and printed HomeKit code.

### Manual installation

Download the release ZIP from [Releases](https://github.com/ray-su/ihome-iss50-direct/releases). Copy its `custom_components/ihome_iss50` directory into `/config/custom_components/`, then restart HA and add the integration. Do not nest the whole repository inside `custom_components`.

<!-- ha-marketplace:exclude-end -->

## Updates and existing installations

Marketplace [automatically migrates existing HACS repositories](https://www.home-assistant.io/integrations/marketplace#coming-from-hacs). Keep your **iHome iSS50 Direct** integration entry; migration does not require reinstalling or pairing the sensor again.

Install new releases through **Settings → Updates**, then restart Home Assistant to load the updated integration. Existing pairing credentials and entity IDs are preserved. Keep Marketplace's GitHub connection active for custom-repository update checks.

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
| Sound detection | A clearly labelled custom sound-detection field, or an explicitly selected field |

Only characteristics actually exposed by the accessory become entities. Display settings, Wi-Fi provisioning, and firmware updates are not implemented. Sound detection reports detected/clear; it is not an audio recording or a decibel meter.

The integration requests event notifications and reads each characteristic individually every 30 seconds as a fallback. Incoming events do not postpone fallback polling. Failed reads mark entities unavailable; successful later polls restore them.

## Sound detection

After upgrading from 0.2.0, restart Home Assistant. Existing pairing credentials and entity IDs are preserved; **do not delete the integration or pair the sensor again**.

The integration discovers custom readable sound-detection fields by their description (for example, `Sound Detected`) or an unambiguous sound service name. It adds a **Sound detection** binary sensor and subscribes to its events, with the same polling fallback as the other sensors.

If a firmware exposes an unnamed field, open **Settings → Devices & services → iHome iSS50 Direct → Configure** and select the sound-detection source. Automatic is the default; Disabled turns this feature off. The detected value defaults to `1 / true` and can be inverted for firmware using `0 / false`. This changes only integration options and reloads the saved connection.

No hardware-derived iSS50 sound UUID has been verified yet. Automatic detection therefore requires meaningful firmware labels; it does not assume that every unknown boolean means sound. Sensitivity, threshold, volume, and enable controls are excluded. Invalid values (including numbers other than 0 and 1) make the sound entity unavailable rather than reporting a false detection. Occupancy remains a separate entity.

For an ambiguous firmware, **Download diagnostics** provides characteristic descriptions, IDs, formats, and numeric states to help identify the field. It omits the config entry, pairing keys, host address, and string values such as serial numbers. Review device-supplied descriptions before sharing diagnostics.

## Connection changes and removal

- **IP address or port changed:** open the integration entry's menu and choose **Reconfigure**. Enter the new address and known port. HA verifies the existing credentials against that endpoint before saving. Reconfiguration does not start a new pairing.
- **Temporary connection failure:** reload the entry or wait for polling/setup retries. Keep the entry so its keys are preserved.
- **Delete the integration:** when the device is reachable, HA attempts to remove its controller pairing from the sensor. Keep the device powered and reachable during deletion. If unpairing fails, HA still deletes the entry; restoring a backup or resetting the sensor may then be necessary. Marketplace requires removal of the configured integration before uninstalling its files, or offers **Delete and uninstall** to do both. Manually deleting files does not unpair the device.
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

Marketplace still uses [`hacs.json` and the HACS validation action](https://contributors.home-assistant.io/marketplace/how-it-works/#before-home-assistant-202611). Their names are intentional; the repository layout and release process remain compatible.

## License and attribution

MIT. The initial implementation was imported from `ihome_iss50_direct_v0.1.0.zip`; the original license notice is retained. This is an independent community integration, not an official iHome or Apple product. The generic thermometer icon is from Pictogrammers Material Design Icons; see [NOTICE.md](NOTICE.md).
