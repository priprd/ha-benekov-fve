import logging
import json
from datetime import timedelta
import requests

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import (
    CONF_URL, 
    CONF_USERNAME, 
    CONF_PASSWORD,
    PERCENTAGE,
    # Use stable constants for common items and fall back to literal
    # unit strings for measurement units to maximize compatibility
    PERCENTAGE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_BATTERY
)

_LOGGER = logging.getLogger(__name__)

# Default to 5 seconds as requested
DEFAULT_SCAN_INTERVAL = timedelta(seconds=5)

class BenekovFVEAPI:
    """Handles communication with the external Benekov FVE API."""

    def __init__(self, hass: HomeAssistant, url: str, c_monitor: str, t_monitor: str):
        """Initialize the API handler."""
        self.hass = hass
        self.url = url
        self.payload = {
            'c_monitor': c_monitor,
            't_monitor': t_monitor
        }
        self.system_id = None # Will store a unique ID for device info
        self.system_name = "Benekov FVE System"

    def get_data(self):
        """Fetch and parse data synchronously (runs in HA executor)."""
        try:
            # 1. Fetch data via POST request
            response = requests.post(
                self.url, 
                data=self.payload, 
                timeout=10, 
                verify=True # Enable SSL verification
            )
            response.raise_for_status()
            json_str = response.text
            
            # 2. Parse the JSON string
            return self._parse_energy_status(json_str)
            
        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to fetch data from API: %s", e)
            raise UpdateFailed(f"API communication failed: {e}") from e
        except Exception as e:
            _LOGGER.error("An unexpected error occurred during API call: %s", e)
            raise UpdateFailed(f"Unexpected error: {e}") from e
            
    def _safe_get(self, d, keys, default=None):
        """Accesses nested dictionary keys safely."""
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d

    def _parse_energy_status(self, json_str):
        """Parses the JSON string into a flat dictionary."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode JSON from API: %s", json_str)
            return {"error": "JSON_DECODE_FAILED"}

        # Store unique ID (uid) for the device
        # Use the UID from the data, or a fallback.
        self.system_id = data.get("uid", "unknown_benekov_system") 
        self.system_name = data.get("jmeno", "Benekov FVE System").strip()

        # Create the flat output dictionary
        output = {
            "user_name": data.get("jmeno", "Unknown User").strip(),
            "last_update": data.get("posledniZaznam", "N/A"),
            "time_of_day": data.get("castDne", "N/A"),
            "inverter_temp_c": self._safe_get(data, ["teplotaStridace"], 0.0),
            "wifi_percent": data.get("wifiProc", 0),
            
            # Power Flows (W)
            "inverter_output_w": data.get("Inverter output total power", 0),
            "total_consumption_w": data.get("spotrebaCelkem", 0),
            "grid_power_w": data.get("vykonSit", 0), 
            "battery_power_w": data.get("vykonBat", 0), 
            "pv_power_w": data.get("vykonFV", 0),
            
            # Battery Status
            "battery_soc_percent": self._safe_get(data, ["baterie", "soc"], 0),
            "battery_voltage_v": self._safe_get(data, ["baterie", "napeti"], 0.0),
            "battery_current_a": self._safe_get(data, ["baterie", "proud"], 0.0),

            # Daily Statistics (kWh)
            "daily_purchase_kwh": self._safe_get(data, ["statistika", "denni", "NakupEnergie"], 0.0),
            "daily_charge_kwh": self._safe_get(data, ["statistika", "denni", "NabitiBaterie"], 0.0),
            "daily_discharge_kwh": self._safe_get(data, ["statistika", "denni", "VybitiBaterie"], 0.0),
            
            # Charger Status
            "charger_2_status": self._safe_get(data, ["nabijecka", "nabijecka2", "stavKonektoru"], "N/A")
        }
        return output

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform from a config entry."""
    
    url = config_entry.data[CONF_URL]
    c_monitor = config_entry.data[CONF_USERNAME]
    t_monitor = config_entry.data[CONF_PASSWORD]
    scan_interval_s = config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL.seconds)
    
    # Renamed API class
    api = BenekovFVEAPI(hass, url, c_monitor, t_monitor)
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Benekov FVE Monitor", # Coordinator name update
        update_method=api.get_data,
        update_interval=timedelta(seconds=scan_interval_s),
    )

    # Fetch initial data and then start the coordinator
    await coordinator.async_config_entry_first_refresh()

    # Create sensors for each metric
    entities = [
        # Renamed Sensor class
        BenekovFVESensor(coordinator, api, "total_consumption_w", "Total Consumption", "W", DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "pv_power_w", "PV Power", "W", DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "grid_power_w", "Grid Power", "W", DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "battery_power_w", "Battery Power", "W", DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "battery_soc_percent", "Battery SOC", PERCENTAGE, DEVICE_CLASS_BATTERY),
        BenekovFVESensor(coordinator, api, "battery_voltage_v", "Battery Voltage", "V", DEVICE_CLASS_VOLTAGE),
        BenekovFVESensor(coordinator, api, "battery_current_a", "Battery Current", "A", DEVICE_CLASS_CURRENT),
        BenekovFVESensor(coordinator, api, "daily_purchase_kwh", "Daily Grid Purchase", "kWh", DEVICE_CLASS_ENERGY, state_attr_key="last_update"),
        BenekovFVESensor(coordinator, api, "inverter_temp_c", "Inverter Temperature", "°C", DEVICE_CLASS_TEMPERATURE),
    ]

    async_add_entities(entities)


class BenekovFVESensor(SensorEntity):
    """Representation of a sensor from the Benekov FVE system."""

    def __init__(self, coordinator, api: BenekovFVEAPI, key: str, name: str, unit: str, device_class: str = None, state_attr_key: str = None):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._api = api
        self._key = key
        self._name = name
        self._unit = unit
        self._device_class = device_class
        self._state_attr_key = state_attr_key

    @property
    def name(self):
        """Return the name of the sensor."""
        # Use the system name + the metric name
        return f"{self._api.system_name} {self._name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this sensor."""
        # Unique ID based on the system ID and the metric key
        return f"benekov_fve_{self._api.system_id}_{self._key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        # Get the value from the coordinator's data
        return self.coordinator.data.get(self._key)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the system."""
        return DeviceInfo(
            identifiers={(self._api.system_id, "BenekovFVE")},
            name=self._api.system_name,
            manufacturer="Benekov",
            model="FVE Monitoring Inverter",
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # For the daily purchase sensor, also show the last update time as an attribute
        if self._state_attr_key and self.coordinator.data.get(self._state_attr_key):
            return {
                "Last Update Time": self.coordinator.data.get(self._state_attr_key),
                "Charger 2 Status": self.coordinator.data.get("charger_2_status"),
                "Time of Day": self.coordinator.data.get("time_of_day"),
            }
        return {
            "Charger 2 Status": self.coordinator.data.get("charger_2_status"),
            "Time of Day": self.coordinator.data.get("time_of_day"),
        }

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        # Register the update listener for the coordinator
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        """Update the entity. Only used by the coordinator."""
        # The coordinator handles the actual data refresh
        pass
