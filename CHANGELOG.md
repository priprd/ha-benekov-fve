# Changelog

All notable changes to the Benekov FVE Monitor integration are documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.4] - 2026-06-30

### Fixed
- **"Solar Power" sensor was always `null`** because the underlying data key
  (`solar_power_w`) was never populated by the API parser. The broken
  duplicate entity has been removed. Use **Total Solar Panels Power**
  (`sensor.benekov_fve_*_total_solar_panels_power`, key `fpv_power_total_w`)
  instead — it exposes the same `vykonFV` value and was already working.
- **"Daily Solar Production" was stuck at `0.0 kWh`**, breaking the Energy
  Dashboard solar graph. The integration was reading `statistika.denni.VyrobaFV`
  but the actual API field is `statistika.denni.VykonPanelu`.
- **Device class constants were silently broken.** `DEVICE_CLASS_POWER`,
  `DEVICE_CLASS_ENERGY`, `DEVICE_CLASS_TEMPERATURE`, `DEVICE_CLASS_VOLTAGE`,
  `DEVICE_CLASS_CURRENT` and `DEVICE_CLASS_BATTERY` were assigned to plain
  fallback strings because `getattr(ha_const, "SensorDeviceClass.POWER", ...)`
  does not resolve dotted attribute paths. They are now properly imported from
  the `SensorDeviceClass` enum in `homeassistant.components.sensor`.
- Replaced deprecated `hass.config_entries.async_forward_entry_unload(entry, "sensor")`
  with the current `async_unload_platforms(entry, ["sensor"])` API.

### Changed
- Default scan interval aligned to **10 s** across `sensor.py` and
  `config_flow.py` (previously inconsistent: 5 s default in code, 10 s default
  in the config flow form).
- Removed a bogus `state_attr_key="measurement"` argument on the Grid Power
  sensor that referenced a non-existent data key.
- **README — grid power sign convention corrected:** `grid_power_w` is
  **negative when importing from the grid** and **positive when exporting to
  the grid**. The previous README description had the sign inverted.
- README mapping table updated to reference the actual sensor keys produced
  by the integration (`fpv_power_total_w`, `VykonPanelu`).

### Removed
- Stale `config_flow_impl.py` backup file (unused duplicate).
- Broken duplicate `solar_power_w` sensor entity (see Fixed above).

### Added
- `iot_class: cloud_polling` in `manifest.json` (required by Home Assistant
  Core; accurately describes the integration which polls the deye.cz cloud
  API).
- GitHub Actions CI workflow (`validate.yml`) that runs HACS validation and
  `home-assistant/actions/hassfest` on every push and pull request.
- GitHub Actions release workflow (`release.yml`) that automatically publishes
  a GitHub Release when a semver tag (`X.Y.Z`) is pushed. The workflow:
  - Verifies the tag matches `manifest.json` `version` before releasing.
  - Extracts the matching section from `CHANGELOG.md` and uses it as the
    release body.
  - Attaches a zip of the integration directory as a release asset.
- This `CHANGELOG.md` file.

### Breaking
- The `sensor.benekov_fve_*_solar_power` entity is **removed**. Replace any
  dashboard cards, automations or template sensors that reference it with
  `sensor.benekov_fve_*_total_solar_panels_power` — same source value, same
  unit (W), correct functionality.

## [0.0.1] - 2025-11-23

Initial tagged version. Released only as a git tag (no GitHub Release), so
HACS users downloaded it via commit hash rather than as a versioned release.

[0.0.4]: https://github.com/priprd/ha-benekov-fve/releases/tag/0.0.4
[0.0.1]: https://github.com/priprd/ha-benekov-fve/releases/tag/0.0.1
