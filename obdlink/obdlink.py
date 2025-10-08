#!/usr/bin/env python3
"""
OBDLink SX MQTT Publisher

Reads a few OBD-II PIDs via an OBDLink SX (ELM327-compatible) connected over USB
and publishes available datapoints to an MQTT broker. Designed to be resilient:
- Recovers from USB disconnects / car power cycles
- Continues running even if some PIDs return no data

Environment variables:
- MQTT_BROKER_HOST (default: broker.hivemq.com)
- MQTT_BROKER_PORT (default: 1883)
- MQTT_TOPIC       (default: bilprojekt72439/obd/data)
- OBD_PORT         (default: /dev/ttyUSB0)
- OBD_BAUD         (default: 115200)
- PUBLISH_INTERVAL (default: 1.0 seconds)
"""
import os
import time
import json
import logging
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt

# python-OBD handles ELM327/OBDLink devices
import obd
from obd import OBDStatus
from obd import commands as OBD

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("obdlink")

# Config
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.com")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "bilprojekt72439/obd/data")
OBD_PORT = os.getenv("OBD_PORT", "/dev/ttyUSB0")
OBD_BAUD = int(os.getenv("OBD_BAUD", "115200"))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "1.0"))

# PID candidate names per python-OBD variants (only the requested PIDs)
PID_CANDIDATES: Dict[str, list[str]] = {
    "SPEED": ["SPEED"],
    "THROTTLE": ["THROTTLE_POS"],
    "COOLANT_TEMP": ["COOLANT_TEMP", "ENGINE_COOLANT_TEMP"],
    "INTAKE_TEMP": ["INTAKE_TEMP", "INTAKE_AIR_TEMP", "AIR_TEMP", "AMBIENT_AIR_TEMP", "AMBIANT_AIR_TEMP"],
    "STFT": ["STFT_BANK_1", "SHORT_FUEL_TRIM_1", "SHORT_FUEL_TRIM_BANK_1"],
    "LTFT": ["LTFT_BANK_1", "LONG_FUEL_TRIM_1", "LONG_FUEL_TRIM_BANK_1"],
    "ADAPTER_VOLT": ["ELM_VOLTAGE", "ELM_VOLT"],
}

def _resolve_cmd(name: str):
    cands = PID_CANDIDATES.get(name, [])
    for n in cands:
        if hasattr(OBD, n):
            return getattr(OBD, n)
    return None


class MQTTPublisher:
    def __init__(self, host: str, port: int, topic: str):
        self.host = host
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self.connected = False

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        # Backoff for reconnect handled by paho
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = (rc == 0)
        if self.connected:
            logger.info("Connected to MQTT broker %s:%s", self.host, self.port)
        else:
            logger.warning("MQTT connect failed rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning("Disconnected from MQTT broker rc=%s", rc)

    def _on_publish(self, client, userdata, mid):
        logger.debug("Published mid=%s", mid)

    def ensure_connected(self):
        if self.connected:
            return
        try:
            logger.info("Connecting MQTT %s:%s...", self.host, self.port)
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error("MQTT connect error: %s", e)

    def publish_json(self, payload: Dict[str, Any]):
        try:
            self.ensure_connected()
            msg = json.dumps(payload, separators=(",", ":"))
            self.client.publish(self.topic, msg)
        except Exception as e:
            logger.error("MQTT publish error: %s", e)


class OBDReader:
    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self.conn: Optional[obd.OBD] = None
        self.last_try = 0.0
        self.retry_delay = 3.0

    def _connect(self):
        try:
            logger.info("Connecting to OBD adapter on %s @ %s baud...", self.port, self.baud)
            # fast=False tends to be more reliable; specify port and baud
            self.conn = obd.OBD(portstr=self.port, baudrate=self.baud, fast=False, timeout=5.0)
            if self.conn.status() == OBDStatus.CAR_CONNECTED or self.conn.is_connected():
                logger.info("OBD connected: status=%s", self.conn.status())
            else:
                logger.warning("OBD not connected to ECU yet: status=%s", self.conn.status())
        except Exception as e:
            logger.error("OBD connect error: %s", e)
            self.conn = None

    def ensure_connected(self):
        now = time.time()
        # If we appear connected but the adapter dropped, force a reconnect
        if self.conn is not None:
            try:
                if self.conn.is_connected():
                    return
            except Exception:
                # Any error checking connection means we should rebuild it
                self.conn = None
        if now - self.last_try < self.retry_delay:
            return
        self.last_try = now
        self._connect()

    def query_int(self, cmd) -> Optional[int]:
        if self.conn is None or not self.conn.is_connected():
            return None
        try:
            r = self.conn.query(cmd)
            if r.is_null():
                return None
            v = r.value
            # Convert based on expected units
            if cmd == OBD.SPEED:
                # v is in kph as a Unit object
                return int(round(getattr(v, "magnitude", v.to("kph").magnitude)))
            elif cmd == OBD.THROTTLE_POS:
                return int(round(getattr(v, "magnitude", float(v))))
            elif cmd == OBD.COOLANT_TEMP:
                return int(round(getattr(v, "magnitude", v.to("degC").magnitude)))
            # Additional PIDs handled generically below
            else:
                # Try common units
                try:
                    return int(round(v.to("degC").magnitude))
                except Exception:
                    pass
                try:
                    return int(round(v.to("kph").magnitude))
                except Exception:
                    pass
                try:
                    return int(round(v.to("L/h").magnitude))
                except Exception:
                    pass
                try:
                    # Return millivolts for voltage so it's an integer
                    return int(round(v.to("V").magnitude * 1000))
                except Exception:
                    pass
                # Fallback: try magnitude/float
                return int(round(getattr(v, "magnitude", float(v))))
        except Exception as e:
            # Mark connection broken so next loop attempts a reconnect
            logger.warning("OBD query error (%s); will reconnect", getattr(cmd, 'name', cmd))
            try:
                if self.conn is not None:
                    self.conn.close()
            except Exception:
                pass
            self.conn = None
            return None

    def query_int_retry(self, cmd, retries: int = 2, delay: float = 0.1) -> Optional[int]:
        """Query a PID and retry a few times if it returns no data."""
        for i in range(max(1, retries + 1)):
            val = self.query_int(cmd)
            if val is not None:
                return val
            if i < retries:
                time.sleep(delay)
        return None


 


 


def collect_datapoint(reader: OBDReader) -> Dict[str, Any]:
    ts = int(time.time())
    data: Dict[str, Any] = {"timestamp": ts}

    # Query only the requested PIDs; if not available (no car), values may be None
    speed = reader.query_int(OBD.SPEED)
    throttle = reader.query_int(OBD.THROTTLE_POS)
    ect = reader.query_int(OBD.COOLANT_TEMP)
    air_cmd = _resolve_cmd("INTAKE_TEMP")
    stft_cmd = _resolve_cmd("STFT")
    ltft_cmd = _resolve_cmd("LTFT")
    adapter_volt_cmd = _resolve_cmd("ADAPTER_VOLT")

    air_temp = reader.query_int(air_cmd) if air_cmd else None
    stft = reader.query_int(stft_cmd) if stft_cmd else None
    ltft = reader.query_int(ltft_cmd) if ltft_cmd else None
    adapter_mv = reader.query_int(adapter_volt_cmd) if adapter_volt_cmd else None
    adapter_v = (round(adapter_mv / 1000.0, 1) if adapter_mv is not None else None)

    if speed is not None:
        data["speed_kmh"] = speed
    if throttle is not None:
        data["throttle_percent"] = max(0, min(100, throttle))
    if ect is not None:
        data["engine_temp_c"] = ect
    if air_temp is not None:
        data["air_temp_c"] = air_temp
    if stft is not None:
        # fuel trims are percentages and can be negative; clamp to [-100, 100]
        data["short_term_fuel_trim_percent"] = max(-100, min(100, stft))
    if ltft is not None:
        data["long_term_fuel_trim_percent"] = max(-100, min(100, ltft))
    if adapter_v is not None:
        data["adapter_voltage_v"] = max(0.0, adapter_v)

    return data


def main():
    mqtt_pub = MQTTPublisher(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC)
    reader = OBDReader(OBD_PORT, OBD_BAUD)

    logger.info("Starting OBDLink publisher. Broker=%s:%s Topic=%s Port=%s Baud=%s Interval=%.1fs",
                MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC, OBD_PORT, OBD_BAUD, PUBLISH_INTERVAL)

    # Log once which PIDs are being queried
    logger.info("Querying PIDs: SPEED, THROTTLE, COOLANT_TEMP, INTAKE_TEMP, STFT, LTFT, ADAPTER_VOLT")

    while True:
        try:
            # Ensure MQTT and OBD connections
            mqtt_pub.ensure_connected()
            reader.ensure_connected()

            data = collect_datapoint(reader)

            # Only publish if we have at least one measurement besides timestamp
            if len(data) > 1:
                mqtt_pub.publish_json(data)
                logger.info("Published: %s", data)
            else:
                logger.info("No OBD data available yet; will retry")

            time.sleep(PUBLISH_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Interrupted, exiting...")
            break
        except Exception as e:
            logger.error("Main loop error: %s", e)
            # brief delay to avoid tight error loops
            time.sleep(1.0)


if __name__ == "__main__":
    main()
