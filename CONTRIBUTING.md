# Contributing

Use the Python version and commands in the README. The manifest uses an aiohomekit minimum version, as required by hassfest for dependencies shared with Home Assistant. Keep its minimum aligned with the tested HA baseline. `requirements-dev.txt` pins the versions actually tested; update those together and rerun protocol tests when changing the baseline.

For protocol or lifecycle changes, add a test that demonstrates the affected behavior. Prefer the loopback HAP simulator for pairing, encrypted transport, and removal. Never point automated tests at a real device. State explicitly whether a result came from a simulator or physical hardware.

Run Ruff, pytest, and the GitHub validation workflow before merging. Do not commit pairing data, backups, personal network details, or captured credentials.

## Releases

Marketplace uses the existing `custom_components/ihome_iss50/` layout, root `hacs.json`, GitHub release tags, and HACS validation action. Keep these in place; do not rename `hacs.json` to `marketplace.json`. See the [Marketplace publisher documentation](https://contributors.home-assistant.io/marketplace/how-it-works/). Documentation-only changes do not require a new integration version or release tag.

1. Update `custom_components/ihome_iss50/manifest.json`, `CHANGELOG.md`, and `RELEASE_NOTES.md`. Update `hacs.json` if the minimum HA version changes.
2. Commit the changes and wait for all **Validate** jobs to pass on that commit.
3. Create and push a matching version tag, for example `v0.2.0`.
4. The **Release** workflow reruns tests/lint, verifies the tag matches the manifest, builds an archive from tracked files, and publishes GitHub release notes and the ZIP.
5. Verify the release and Actions results. Hardware testing is still required before claiming physical-device compatibility.

For a local archive, run `python scripts/build_release.py` from a Git checkout. The archive appears in `dist/` and contains only integration files, metadata, notices, and user documentation.
