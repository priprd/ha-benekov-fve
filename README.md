# Benekov FVE Monitor Integration for Home Assistant

This is a custom component for Home Assistant that integrates the data from a Benekov FVE (Photovoltaic Power Plant) monitoring system, typically available via a local or external API endpoint that requires specific parameters (`c_monitor` and `t_monitor`).

It uses Home Assistant's configuration flow and standard sensor entities for seamless integration and real-time data updates.

## ✨ Features

The integration fetches data every 5 seconds (default, configurable) and creates sensors for:

* **Current Power Flows (W):**
    * Total Consumption (`total_consumption_w`)
    * PV Production (`pv_power_w`)
    * Grid Interaction (`grid_power_w` - negative means exporting, positive means importing)
    * Battery Charge/Discharge (`battery_power_w` - positive means charging)
* **Battery Status:**
    * State of Charge (SOC) (`battery_soc_percent`)
    * Voltage (`battery_voltage_v`)
    * Current (`battery_current_a`)
* **Daily Energy Statistics (kWh):**
    * Daily Grid Purchase (`daily_purchase_kwh`)
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
3.  Place the following four files inside the `benekov_fve` directory:
    * `__init__.py`
    * `manifest.json`
    * `config_flow.py`
    * `sensor.py`
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
| **Scan Interval (s)** | N/A | How often Home Assistant should refresh the data from the API (default is 5 seconds). |

After successful connection, a new Device named after your system (e.g., `Benekov FVE (David Příplata)`) will appear, containing all monitored sensors.

## 🛠️ Data Source Mapping

This integration expects the API to respond with a JSON structure similar to the Benekov monitoring output. Key mappings are:

| HA Sensor Key | Source JSON Path | Units | Description |
| :--- | :--- | :--- | :--- |
| `total_consumption_w` | `spotrebaCelkem` | W | Total current power consumption of the house. |
| `grid_power_w` | `vykonSit` | W | Grid interaction. Positive=Import, Negative=Export. |
| `pv_power_w` | `vykonFV` | W | Current power production from PV panels. |
| `battery_soc_percent` | `baterie.soc` | % | Battery State of Charge. |
| `daily_purchase_kwh` | `statistika.denni.NakupEnergie` | kWh | Total energy purchased from the grid today. |
| `inverter_temp_c` | `teplotaStridace` | °C | Internal temperature of the inverter. |
