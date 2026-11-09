# Changelog

## 0.4.0 — 2026-11-08

- Add a Celsius/Fahrenheit selector for the physical display.
- Add sound detection threshold and motion silence duration number controls, using verified characteristic IDs and device-advertised bounds.
- Preserve pairing and all existing entity IDs; never write settings automatically during setup.
- Serialize polling and setting writes, verify values by reading them back, and handle rejected or unconfirmed writes.
- Keep optional control failures from disabling standard sensor readings.
- Include characteristic units and step sizes in diagnostics.
- Add setting-validation, entity, error-handling, concurrency, and encrypted simulator write tests.

## 0.3.0 — 2026-11-08

- Add a sound-detection binary sensor for clearly labelled custom HAP fields, including events and polling.
- Add automatic/manual/disabled sound-source options and active-state inversion without changing pairing credentials.
- Keep sound separate from occupancy and exclude sensitivity/threshold/enable controls from automatic detection.
- Fix full UUID matching so vendor UUID prefixes cannot impersonate standard HAP types.
- Add a diagnostic characteristic export that omits config credentials and string values.
- Add parser, binary-state, options, diagnostic-redaction, and encrypted sound-event tests.
- Automatic discovery remains dependent on firmware labels; the tests use synthetic vendor UUIDs, not a physical iSS50 capture.

## 0.2.0 — 2026-11-08

- Publish as a HACS custom repository with complete metadata, local brand assets, and installation documentation.
- Test against Home Assistant 2026.11.0; declare aiohomekit >=4.0.1 directly instead of depending on the built-in HomeKit Device integration.
- Add IP/port reconfiguration that authenticates with existing credentials before saving.
- Keep fallback polling scheduled during frequent sensor events and preserve events received during a poll.
- Attempt to unpair the HA controller when its integration entry is deleted.
- Show distinct connection, authentication, existing-pairing, and rate-limit errors.
- Add regression tests, Ruff, hassfest/HACS validation, issue templates, and release packaging.

## 0.1.0 — imported archive

- Direct-IP HAP pairing, automatic port search, standard sensor entities, events and fallback polling.
- Pairing-credential persistence and recovery after configuration UI cancellation.
