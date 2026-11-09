# Validation

## Version 0.3.0

Development baseline: Home Assistant **2026.11.0**, aiohomekit **4.0.1**, HAP-python **5.2.0**, Python **3.14**. Dependencies are pinned in `requirements-dev.txt`.

Local result on 2026-11-08: **47 tests passed**. Ruff lint and formatting checks passed.

Sound tests use explicitly synthetic vendor UUIDs. They verify label-based discovery and explicit field selection, not a reverse-engineered iSS50 UUID. The user confirmed that the Sound detection entity appears in HA after updating to 0.3.0. Physical detected/clear transitions remain unverified.

The automated suite checks:

- Sound discovery by characteristic/service descriptions; settings and ambiguous fields are excluded.
- Binary sound-state validation, polarity, credential-preserving options, and diagnostic redaction.
- Encrypted sound detected/clear events after restoring saved pairing keys.
- Real TCP HAP detection and rejection of ordinary web servers.
- Standard sensor-characteristic parsing and read permissions.
- Port-search success/failure and worker cleanup.
- Real SRP pairing with a loopback HAP simulator, encrypted reads, saved-key restoration, and event delivery.
- Authentication of a replacement endpoint using saved keys.
- Simulator unpairing followed by a fresh pairing.
- Configuration input validation, credential persistence without the PIN, retry handling, and recovery after UI cancellation.
- Home Assistant coordinator scheduling: events do not postpone polling, and events arriving during a poll are not overwritten by its older snapshot.
- Reconfiguration retains credentials and leaves the old endpoint unchanged on failure.

Home Assistant's real flow and coordinator classes are used. Services and config-entry objects are mocked where appropriate; this is not a complete HA frontend/end-to-end test.

GitHub Actions runs the suite, Ruff checks, hassfest, and HACS validation. Check the exact commit's Actions results for current status.

## Hardware limits

A user reported working temperature, humidity, light, and motion readings on a physical iSS50 using version 0.2.0, and confirmed that the Sound detection entity appears after updating to 0.3.0. This confirms entity availability on that installation; the report does not establish whether automatic discovery or manual field selection was used, or whether sound causes detected/clear transitions. Simulator success does not establish the actual vendor UUID, firmware labels, Wi-Fi provisioning behavior, or compatibility with every firmware version. No replacement firmware support is claimed.

## Original archive

The supplied v0.1.0 archive reported nine tests against HA 2025.1.4 and aiohomekit 3.2.20. Its original nine tests were independently rerun successfully against HA 2026.11.0 and aiohomekit 4.0.1 before this repository's changes. The old environment claim was not independently reproduced.
