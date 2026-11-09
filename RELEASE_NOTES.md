Three device controls for iHome iSS50 Direct:

- **Display temperature units:** select Celsius (°C) or Fahrenheit (°F) for the physical LCD.
- **Sound detection threshold:** adjust the raw device threshold (3–200 on the inspected iSS50).
- **Motion silence duration:** adjust motion silence timing (1–120 on the inspected iSS50). This is not motion sensitivity; the duration unit has not yet been verified.

**Update through Marketplace, restart Home Assistant, then open the iSS50 device’s Configuration section. Keep your existing integration entry; no re-pairing or Apple Home setup is required.** Select Celsius in the display control to change the LCD. Installation does not change settings automatically.

Controls use recognized writable fields, honor advertised limits, and read back values after each write. Rejected or unconfirmed writes report an error. Existing sensors and pairing credentials are preserved.

The control identifiers, permissions, and ranges were verified from physical-device diagnostics. Encrypted writes/read-back were tested with a local HAP simulator; physical display and sensitivity/timing effects still need confirmation. Sound threshold values are not labelled as decibels, and motion duration values are not assigned an unverified time unit.

Requires Home Assistant Core 2026.11.0 or newer. The attached ZIP is for manual installation; Marketplace installs from the release tag. See the [installation and device settings documentation](https://github.com/ray-su/ihome-iss50-direct#device-settings).
