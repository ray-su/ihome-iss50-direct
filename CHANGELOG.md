# Changelog

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
