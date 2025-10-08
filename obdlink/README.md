# obdlink

OBDLink SX MQTT Publisher for Raspberry Pi 4.

Reads a few OBD-II PIDs via an OBDLink SX (ELM327-compatible) over USB and publishes
to the same MQTT broker as `demopub`.

- Resilient to USB disconnects and car power cycles.
- Does not crash if data is unavailable; logs and retries.
- Publishes only when any value is available.

## Requirements

- Raspberry Pi OS (or Linux) with Python 3.9+
- OBDLink SX connected via USB (usually `/dev/ttyUSB0`)
- Internet access to reach the public broker (default) or your own broker

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Run

Default broker and settings are the same as `demopub`.

```bash
# Inside obdlink/
python obdlink.py
```

Environment variables you can override:

- `MQTT_BROKER_HOST` (default: `broker.hivemq.com`)
- `MQTT_BROKER_PORT` (default: `1883`)
- `MQTT_TOPIC` (default: `bilprojekt72439/obd/data`)
- `OBD_PORT` (default: `/dev/ttyUSB0`)
- `OBD_BAUD` (default: `115200`)
- `PUBLISH_INTERVAL` (default: `1.0` seconds)

Example with a custom serial port:

```bash
export OBD_PORT=/dev/ttyUSB1
python obdlink.py
```

## Notes for Raspberry Pi

- Serial permissions: ensure your user can access `/dev/ttyUSB*`.
  You can add your user to the `dialout` group and re-login:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
- Without a car connected, many PIDs may return no data. The script will keep
  reconnecting and publishing whenever values are available.
- If you use a different ELM327-compatible adapter, adjust `OBD_PORT` accordingly.

## MQTT message format

Same format as `demopub` (only fields that are available will be present):

```json
{
  "timestamp": 1695408378,
  "rpm": 1234,
  "speed_kmh": 45,
  "throttle_percent": 12,
  "engine_temp_c": 90
}
```
# Starting the service
sudo systemctl daemon-reload
sudo systemctl enable --now obdlink.service
systemctl status obdlink.service

# tail
journalctl -u obdlink.service -f
