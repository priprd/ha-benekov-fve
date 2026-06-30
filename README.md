# Benekov FVE Monitor Integration for Home Assistant

This is a custom component for Home Assistant that integrates the data from a Benekov FVE (Photovoltaic Power Plant) monitoring system, typically available via a local or external API endpoint that requires specific parameters (`c_monitor` and `t_monitor`).

It uses Home Assistant's configuration flow and standard sensor entities for seamless integration and real-time data updates.

## ✨ Features

The integration fetches data every 10 seconds (default, configurable) and creates sensors for:

* **Current Power Flows (W):**
    * Total Consumption (`total_consumption_w`)
    * PV Production (`fpv_power_total_w`)
    * Grid Interaction (`grid_power_w` - negative means importing from grid, positive means exporting to grid)
    * Battery Charge/Discharge (`battery_power_w` - positive means charging)
* **Battery Status:**
    * State of Charge (SOC) (`battery_soc_percent`)
    * Voltage (`battery_voltage_v`)
    * Current (`battery_current_a`)
* **Daily Energy Statistics (kWh):**
    * Daily Solar Production (`daily_solar_production_kwh`) - **Compatible with Energy Dashboard**
    * Daily Grid Purchase (`daily_purchase_kwh`)
    * Daily Grid Export (`daily_grid_export_kwh`) - **Compatible with Energy Dashboard**
    * Daily Battery Charge (`daily_charge_kwh`)
    * Daily Battery Discharge (`daily_discharge_kwh`)
* **System Status:**
    * Inverter Temperature (`inverter_temp_c`)
    * Charger 2 Status (as an attribute)
    * Last Update Timestamp (as an attribute)

## ⬇️ Installation (HACS Recommended)

### 1. Using HACS (Preferred)

1.  Open the HACS interface in Home Assistant.
2.  Go to **Integrations**.
3.  Click the three dots (`...`) in the upper right corner and select **Custom repositories**.
4.  Add the URL of this repository (or your fork) and select **Integration** as the category.
5.  Search for "Benekov FVE Monitor" and install it.
6.  Restart Home Assistant.

### 2. Manual Installation

1.  Navigate to your Home Assistant configuration directory (`config/`).
2.  Create a folder structure: `custom_components/benekov_fve/`.
3.  Copy the **entire contents** of `custom_components/benekov_fve/` from this
    repository into your `custom_components/benekov_fve/` directory. All files
    in that folder are required (`__init__.py`, `manifest.json`, `const.py`,
    `config_flow.py`, `sensor.py`, `diagnostics.py`).

    > 💡 The easiest way is to download the latest release zip
    > (`benekov_fve.zip`) from the [Releases page](https://github.com/priprd/ha-benekov-fve/releases)
    > and extract it into `custom_components/benekov_fve/`.
4.  Restart Home Assistant.

## ⚙️ Configuration

1.  In Home Assistant, go to **Settings** -> **Devices & Services**.
2.  Click **+ Add Integration**.
3.  Search for **Benekov FVE Monitor**.
4.  Enter the required details in the configuration form:

| Field Name | Corresponding API Parameter | Description |
| :--- | :--- | :--- |
| **Monitor API URL** | N/A | The full URL endpoint that provides the status JSON (e.g., `http://192.168.1.10/data`). |
| **Client ID (c_monitor)** | `c_monitor` | Your unique Client ID for the monitoring system. |
| **Token (t_monitor)** | `t_monitor` | Your unique Token for the monitoring system. |
| **Scan Interval (s)** | N/A | How often Home Assistant should refresh the data from the API (default is 10 seconds). |

After successful connection, a new Device named after your system (e.g., `Benekov FVE (David Příplata)`) will appear, containing all monitored sensors.

## 🛠️ Data Source Mapping

This integration expects the API to respond with a JSON structure similar to the Benekov monitoring output. Key mappings are:

| HA Sensor Key | Source JSON Path | Units | Description |
| :--- | :--- | :--- | :--- |
| `total_consumption_w` | `spotrebaCelkem` | W | Total current power consumption of the house. |
| `grid_power_w` | `vykonSit` | W | Grid interaction. Negative=Import from grid, Positive=Export to grid. |
| `fpv_power_total_w` | `vykonFV` | W | Current power production from PV panels (sum of all strings). |
| `battery_soc_percent` | `baterie.soc` | % | Battery State of Charge. |
| `daily_purchase_kwh` | `statistika.denni.NakupEnergie` | kWh | Total energy purchased from the grid today. |
| `daily_solar_production_kwh` | `statistika.denni.VykonPanelu` | kWh | Total solar energy produced today. |
| `daily_grid_export_kwh` | `statistika.denni.ProdejEnergie` | kWh | Total energy exported to the grid today. |
| `inverter_temp_c` | `teplotaStridace` | °C | Internal temperature of the inverter. |

## ⚡ Home Assistant Energy Dashboard Configuration

This integration provides energy sensors that are fully compatible with Home Assistant's Energy Dashboard. To configure:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Configure each section:

### Solar Panels
- Click **Add Solar Production**
- Select: `sensor.benekov_fve_system_daily_solar_production`

### Grid Consumption
- Click **Add Consumption**
- Select: `sensor.benekov_fve_system_daily_grid_purchase`

### Return to Grid
- Click **Add Return to Grid**
- Select: `sensor.benekov_fve_system_daily_grid_export`

### Battery Systems (Optional)
- **Energy going in to the battery**: `sensor.benekov_fve_system_daily_battery_charge`
- **Energy coming out of the battery**: `sensor.benekov_fve_system_daily_battery_discharge`

After configuration, the Energy Dashboard will display your solar production, grid consumption, and energy flows. Historical data will accumulate over time for long-term analysis.

## 🔧 Troubleshooting

### Solar Production Not Showing in Energy Dashboard

If the solar production sensor is not appearing in Home Assistant's Energy Dashboard:

1. **Check sensor state**: Go to **Developer Tools** → **States** and search for `sensor.benekov_fve_system_daily_solar_production`
2. **Verify sensor attributes**: Ensure it has:
   - `device_class: energy`
   - `state_class: total_increasing`
   - `unit_of_measurement: kWh`
3. **Check logs**: Enable debug logging by adding to `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.benekov_fve: debug
   ```
4. **Restart Home Assistant**: After enabling debug logging, restart and check the logs for messages about API response structure
5. **Verify API field name**: Check the debug logs for `statistika.denni keys:` to confirm the API provides `VykonPanelu` field

If the API uses a different field name for solar production, please open an issue on GitHub with the log output.

## 📦 Releases & Versioning

This project uses [semantic versioning](https://semver.org). Every version is
published as a [GitHub Release](https://github.com/priprd/ha-benekov-fve/releases),
which HACS picks up automatically and presents in the integration's update
dropdown. See [CHANGELOG.md](CHANGELOG.md) for the full history of changes.

### For maintainers — how to publish a new release

1. Add a new `## [X.Y.Z] - YYYY-MM-DD` section at the top of `CHANGELOG.md`.
2. Bump `version` in `custom_components/benekov_fve/manifest.json` to `X.Y.Z`.
3. Commit and push to `main`.
4. Create and push a tag matching the version (no `v` prefix):
   ```bash
   git tag -a X.Y.Z -m "Release X.Y.Z"
   git push origin X.Y.Z
   ```
5. The `release.yml` GitHub Actions workflow verifies the tag matches
   `manifest.json`, extracts the matching `CHANGELOG.md` section, and
   publishes a GitHub Release with the integration packaged as `benekov_fve.zip`.

The `validate.yml` workflow additionally runs HACS and `hassfest` validation
on every push and pull request.
