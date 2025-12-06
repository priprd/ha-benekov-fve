import logging
import json
from datetime import timedelta
import socket
import ssl
from urllib.parse import urlparse, urlencode

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant import const as ha_const
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD

# Compatibility: use Home Assistant constants when available, otherwise
# fall back to literal strings so the integration works across HA versions.
PERCENTAGE = getattr(ha_const, "PERCENTAGE", "%")
UNIT_VOLT = getattr(ha_const, "ELECTRIC_POTENTIAL_VOLT", "V")
UNIT_AMPERE = getattr(ha_const, "ELECTRIC_CURRENT_AMPERE", "A")
UNIT_WATT = getattr(ha_const, "POWER_WATT", "W")
UNIT_KWH = getattr(ha_const, "ENERGY_KILO_WATT_HOUR", "kWh")
UNIT_TEMP_C = getattr(ha_const, "TEMP_CELSIUS", "°C")

DEVICE_CLASS_POWER = getattr(ha_const, "DEVICE_CLASS_POWER", "power")
DEVICE_CLASS_ENERGY = getattr(ha_const, "DEVICE_CLASS_ENERGY", "energy")
DEVICE_CLASS_TEMPERATURE = getattr(ha_const, "DEVICE_CLASS_TEMPERATURE", "temperature")
DEVICE_CLASS_VOLTAGE = getattr(ha_const, "DEVICE_CLASS_VOLTAGE", "voltage")
DEVICE_CLASS_CURRENT = getattr(ha_const, "DEVICE_CLASS_CURRENT", "current")
DEVICE_CLASS_BATTERY = getattr(ha_const, "DEVICE_CLASS_BATTERY", "battery")

# Logger
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
            't_session': t_monitor
        }
        self.system_id = None # Will store a unique ID for device info
        self.system_name = "Benekov FVE System"

    def _http_post(self, url: str, data: dict, timeout: int = 10, verify: bool = True) -> str:
        """Perform a minimal HTTP POST using sockets (supports HTTP and HTTPS).

        Returns the response body as a string. Raises OSError/ssl.SSLError on network errors
        or ValueError for unexpected HTTP responses.
        """
        parsed = urlparse(url)
        scheme = parsed.scheme or "http"
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        body = urlencode(data or {}).encode("utf-8")

        # Build request
        request_lines = [f"POST {path} HTTP/1.1",
                         f"Host: {host}",
                         "User-Agent: benekov_fve/1.0",
                         "Content-Type: application/x-www-form-urlencoded",
                         f"Content-Length: {len(body)}",
                         "Connection: close",
                         "",
                         ""]
        request_header = "\r\n".join(request_lines).encode("utf-8")
        req = request_header + body

        # Open socket
        sock = socket.create_connection((host, port), timeout)
        try:
            if scheme == "https":
                if verify:
                    ctx = ssl.create_default_context()
                else:
                    ctx = ssl._create_unverified_context()
                sock = ctx.wrap_socket(sock, server_hostname=host)

            # Send request
            sock.sendall(req)

            # Read response until EOF
            response_chunks = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_chunks.append(chunk)

            raw = b"".join(response_chunks)
        finally:
            try:
                sock.close()
            except Exception:
                pass

        # Split headers and body
        sep = b"\r\n\r\n"
        if sep not in raw:
            raise ValueError("Invalid HTTP response")

        header_raw, body = raw.split(sep, 1)
        header_lines = header_raw.split(b"\r\n")
        status_line = header_lines[0].decode(errors="ignore")
        # Example: HTTP/1.1 200 OK
        parts = status_line.split()
        if len(parts) < 2:
            raise ValueError(f"Invalid status line: {status_line}")
        try:
            status = int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid status code in status line: {status_line}")

        # Check for chunked transfer encoding
        headers = {}
        for h in header_lines[1:]:
            if b":" in h:
                k, v = h.split(b":", 1)
                headers[k.decode().strip().lower()] = v.decode().strip()

        if headers.get("transfer-encoding") == "chunked":
            # Decode chunked body
            body = self._decode_chunked(body)

        # If status is not OK, raise
        if status < 200 or status >= 300:
            raise ValueError(f"HTTP {status}: {status_line}")

        return body.decode("utf-8", errors="replace")

    def _decode_chunked(self, raw: bytes) -> bytes:
        """Decode an HTTP chunked transfer-encoded body."""
        i = 0
        out = bytearray()
        length = len(raw)
        while i < length:
            # read chunk-size line
            nl = raw.find(b"\r\n", i)
            if nl == -1:
                break
            line = raw[i:nl].decode("ascii", errors="ignore").strip()
            try:
                chunk_size = int(line.split(";", 1)[0], 16)
            except ValueError:
                break
            i = nl + 2
            if chunk_size == 0:
                # consume trailing CRLF after last chunk
                break
            out += raw[i:i+chunk_size]
            i += chunk_size + 2
        return bytes(out)

    def get_data(self):
        """Fetch and parse data synchronously (runs in HA executor)."""
        try:
            # 1. Fetch data via a socket-based POST to avoid relying on requests/urllib3
            json_str = self._http_post(self.url, self.payload, timeout=10, verify=True)

            # 2. Parse the JSON string
            return self._parse_energy_status(json_str)

        except (OSError, ssl.SSLError, ValueError) as e:
            _LOGGER.error("Failed to fetch data from API (socket): %s", e)
            raise UpdateFailed(f"API communication failed: {e}") from e
        except Exception as e:
            _LOGGER.exception("An unexpected error occurred during API call: %s", e)
            raise UpdateFailed(f"Unexpected error: {e}") from e
            
    def _safe_get(self, d, keys, default=None):
        """Accesses nested dictionary keys safely."""
        # Be defensive: allow `keys` to be a single key (str) or iterable.
        if keys is None:
            return default

        # If a string was passed, treat it as a single key
        if isinstance(keys, str):
            keys = [keys]

        try:
            iterator = iter(keys)
        except TypeError:
            # keys is not iterable
            return default

        for key in iterator:
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

        # Ensure we received a mapping/dictionary. If not, bail out early.
        if not isinstance(data, dict):
            _LOGGER.error("API returned non-dict JSON payload: %s", repr(data))
            return {"error": "INVALID_PAYLOAD", "payload": data}

        try:
            # Store unique ID (uid) for the device
            # Use the UID from the data, or a fallback.
            self.system_id = data.get("uid", "unknown_benekov_system")
            self.system_name = str(data.get("jmeno", "Benekov FVE System")).strip()

            # Create the flat output dictionary
            output = {
                "user_name": str(data.get("jmeno", "Unknown User")).strip(),
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
                "battery_temp_c": self._safe_get(data, ["baterie", "teplota"], 0),

                # Daily Statistics (kWh)
                "daily_purchase_kwh": self._safe_get(data, ["statistika", "denni", "NakupEnergie"], 0.0),
                "daily_charge_kwh": self._safe_get(data, ["statistika", "denni", "NabitiBaterie"], 0.0),
                "daily_discharge_kwh": self._safe_get(data, ["statistika", "denni", "VybitiBaterie"], 0.0),

                # Charger Status
                "charger_2_status": self._safe_get(data, ["nabijecka", "nabijecka2", "stavKonektoru"], "N/A"),
            }

            return output
        except Exception as e:
            _LOGGER.exception("Unexpected error while parsing API response: %s", e)
            return {"error": "PARSE_FAILED", "exception": str(e)}

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform from a config entry."""
    
    url = config_entry.data[CONF_URL]
    c_monitor = config_entry.data[CONF_USERNAME]
    t_monitor = config_entry.data[CONF_PASSWORD]
    scan_interval_s = config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL.seconds)
    
    # Renamed API class
    api = BenekovFVEAPI(hass, url, c_monitor, t_monitor)
    
    async def _async_update_data():
        """Wrapper to run the blocking `api.get_data` in the executor."""
        result = await hass.async_add_executor_job(api.get_data)
        _LOGGER.debug("BenekovFVE: _async_update_data result type=%s", type(result))
        return result

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Benekov FVE Monitor",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=scan_interval_s),
    )

    # Do NOT perform an initial blocking refresh here. The integration's
    # `async_setup_entry` in `__init__.py` already validated connectivity.
    # Performing `async_config_entry_first_refresh` here can raise
    # `ConfigEntryNotReady` from the platform which we prefer to avoid.
    # Let the coordinator handle its first update on its own schedule.

    # Store coordinator for later access/unload
    try:
        from .const import DOMAIN
    except Exception:
        DOMAIN = "benekov_fve"

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})
    # store coordinator in the mutable container for this entry
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = coordinator

    # Create sensors for each metric
    entities = [
        # Renamed Sensor class
        BenekovFVESensor(coordinator, api, "total_consumption_w", "Total Consumption", UNIT_WATT, DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "pv_power_w", "PV Power", UNIT_WATT, DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "grid_power_w", "Grid Power", UNIT_WATT, DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "battery_power_w", "Battery Power", UNIT_WATT, DEVICE_CLASS_POWER),
        BenekovFVESensor(coordinator, api, "battery_soc_percent", "Battery SOC", PERCENTAGE, DEVICE_CLASS_BATTERY),
        BenekovFVESensor(coordinator, api, "battery_voltage_v", "Battery Voltage", UNIT_VOLT, DEVICE_CLASS_VOLTAGE),
        BenekovFVESensor(coordinator, api, "battery_current_a", "Battery Current", UNIT_AMPERE, DEVICE_CLASS_CURRENT),
        BenekovFVESensor(coordinator, api, "battery_temp_c", "Battery Temperature", UNIT_TEMP_C, DEVICE_CLASS_TEMPERATURE),
        BenekovFVESensorBattery(coordinator, api, "battery_temp_c", "Battery Temperature", UNIT_TEMP_C, DEVICE_CLASS_TEMPERATURE),
        BenekovFVESensor(coordinator, api, "daily_purchase_kwh", "Daily Grid Purchase", UNIT_KWH, DEVICE_CLASS_ENERGY, state_attr_key="last_update"),
        BenekovFVESensor(coordinator, api, "inverter_temp_c", "Inverter Temperature", UNIT_TEMP_C, DEVICE_CLASS_TEMPERATURE),
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

class BenekovFVESensorBattery(SensorEntity):
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
        return f"{self._api.system_name} {self._name} Battery"

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
