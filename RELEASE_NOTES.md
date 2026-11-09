Sound detection support for existing iHome iSS50 Direct installations.

**Update through HACS and restart Home Assistant. Keep the existing integration entry; no re-pairing or Apple Home setup is required.**

- Creates a Sound detection binary sensor when the accessory clearly labels its custom sound field.
- Receives live detection/clear events and uses polling as a fallback.
- Adds Configure options for unnamed fields, inverted active states, and disabling sound support.
- Preserves existing pairing credentials and entity IDs.
- Adds a credential-free characteristic diagnostic export and correct full-UUID matching.

**Compatibility:** no hardware-derived sound UUID is hard-coded. If the firmware does not label the field, select the sound source under the integration’s Configure options. Tested with synthetic custom HAP fields and encrypted simulator events; physical iSS50 sound behavior remains unverified. Sound detection is separate from occupancy and does not measure decibels.

Requires Home Assistant Core 2026.11.0 or newer. The attached ZIP is for manual installation; HACS installs directly from the release tag.
