# obd2remote

OBD2 Remote Monitoring System

## Applications

### demopub.py - Demo OBD2 Data Publisher

A Python application that publishes simulated OBD2 sensor data to a public MQTT broker for testing and demonstration purposes.

#### Features

- Publishes realistic OBD2 sensor data every 0.2 seconds
- Simulates multiple sensors with oscillating values:
  - **RPM**: 2000-7000 RPM (1 oscillation/minute)
  - **Speed**: 20-120 km/h (2 oscillations/minute)
  - **Throttle**: 0-100% (3 oscillations/minute)
  - **Engine Temperature**: 70-120°C (1.5 oscillations/minute)
  - **Oil Temperature**: Steady at 130°C
- All sensors oscillate out of sync for realistic simulation
- Configurable MQTT topic via environment variable
- JSON message format with timestamps

#### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Usage

1. Run with default settings:
   ```bash
   python demopub/demopub.py
   ```

2. Run with custom MQTT topic:
   ```bash
   set MQTT_TOPIC=your/custom/topic
   python demopub/demopub.py
   ```

#### Configuration

- **MQTT Broker**: broker.hivemq.com:1883 (no authentication)
- **Default Topic**: bilprojekt72439/obd/data
- **Custom Topic**: Set `MQTT_TOPIC` environment variable
- **Publish Rate**: 0.2 seconds (5 messages per second)

#### Message Format

```json
{
  "timestamp": 1695408378,
  "rpm": 4568,
  "speed_kmh": 85,
  "throttle_percent": 67,
  "engine_temp_c": 99,
  "oil_temp_c": 130
}
```

#### Monitoring

The application logs all published values to the console. Press `Ctrl+C` to stop the publisher gracefully.

### subscriber.py - Simple MQTT Subscriber

A minimal subscriber that connects to the same public broker and prints all received messages to the terminal. Useful for testing alongside the publisher.

#### Usage

1. Run with default topic (wildcard):
   ```bash
   python demopub/subscriber.py
   ```

2. Run with a custom topic:
   ```bash
   set MQTT_TOPIC=bilprojekt72439/obd/data
   python demopub/subscriber.py
   ```

#### Defaults

- **Broker**: broker.hivemq.com:1883
- **Default Topic**: `bilprojekt72439/obd/#` (subscribes to all `obd` messages)