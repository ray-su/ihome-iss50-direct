# Contributing

Use the Python version and commands in the README. Keep the runtime dependency in `manifest.json` aligned with the tested Home Assistant version and `requirements-dev.txt`. Do not upgrade aiohomekit independently without checking the HA version's own dependency and rerunning protocol tests.

For protocol or lifecycle changes, add a test that demonstrates the affected behavior. Prefer the loopback HAP simulator for pairing, encrypted transport, and removal. Never point automated tests at a real device. State explicitly whether a result came from a simulator or physical hardware.

Run Ruff, pytest, and the GitHub validation workflow before merging. Do not commit pairing data, backups, personal network details, or captured credentials.

## Releases

1. Update `custom_components/ihome_iss50/manifest.json`, `CHANGELOG.md`, and `RELEASE_NOTES.md`. Update `hacs.json` if the minimum HA version changes.
2. Commit the changes and wait for all **Validate** jobs to pass on that commit.
3. Create and push a matching version tag, for example `v0.2.0`.
4. The **Release** workflow reruns tests/lint, verifies the tag matches the manifest, builds an archive from tracked files, and publishes GitHub release notes and the ZIP.
5. Verify the release and Actions results. Hardware testing is still required before claiming physical-device compatibility.

For a local archive, run `python scripts/build_release.py` from a Git checkout. The archive appears in `dist/` and contains only integration files, metadata, notices, and user documentation.
