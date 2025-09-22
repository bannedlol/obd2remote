import json
import threading
import time
from typing import Dict, Any, List

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WriteOptions

import config

class MQTTInfluxIngestor:
    def __init__(self):
        self._stop = threading.Event()
        self.client = mqtt.Client(client_id=config.MQTT_CLIENT_ID)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # InfluxDB client with batching for resilience and throughput
        self.influx = InfluxDBClient(
            url=config.INFLUX_URL,
            token=config.INFLUX_TOKEN,
            org=config.INFLUX_ORG,
            timeout=30_000,
        )
        self.write_api = self.influx.write_api(
            write_options=WriteOptions(batch_size=5_000, flush_interval=2_000, retry_interval=5_000, max_retries=5)
        )

    # MQTT callbacks
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(config.MQTT_TOPIC)
        else:
            # Will retry via client.loop_forever internal backoff
            pass

    def _on_disconnect(self, client, userdata, rc):
        # Let paho handle reconnects automatically
        pass

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
            data = json.loads(payload)
            # Expect key/value pairs; timestamp optional
            ts_sec = int(data.get("timestamp", int(time.time())))
            ts_ns = ts_sec * 1_000_000_000

            points: List[Point] = []
            for k, v in data.items():
                if k == "timestamp":
                    continue
                try:
                    iv = int(v)
                except Exception:
                    # Skip non-integer values silently for resilience
                    continue
                p = Point("obd").tag("key", k).field("v", iv).time(ts_ns)
                points.append(p)

            if points:
                self.write_api.write(bucket=config.INFLUX_BUCKET, org=config.INFLUX_ORG, record=points)
        except Exception:
            # Swallow errors to be resilient to malformed messages
            pass

    def start(self):
        # Enable automatic reconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT, keepalive=60)
        t = threading.Thread(target=self.client.loop_forever, daemon=True)
        t.start()

    def stop(self):
        self._stop.set()
        try:
            self.write_api.flush()
        except Exception:
            pass
        self.client.disconnect()
        self.influx.close()
