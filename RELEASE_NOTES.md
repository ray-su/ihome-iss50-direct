Initial public HACS release of iHome iSS50 Direct.

- Install as a HACS custom repository: `https://github.com/ray-su/ihome-iss50-direct`, category **Integration**.
- Requires Home Assistant Core **2026.11.0+**. Restart HA after installation and add **iHome iSS50 Direct**.
- Direct-IP pairing uses the HomeKit protocol with HA as the controller. Apple Home is not required.
- Includes saved-key IP/port reconfiguration, polling fixes, best-effort unpairing on removal, and clearer setup errors.
- Includes automated protocol/coordinator tests and HACS/hassfest validation workflows.

**Experimental:** simulator-tested; successful physical iSS50 pairing and complete sensor readings are not yet verified. Proprietary sound detection is not implemented. Back up HA before setup and retain the config entry when troubleshooting.

The ZIP is for manual installation: copy `custom_components/ihome_iss50` into `/config/custom_components/`. HACS installs the integration directory directly from this release's tag.
