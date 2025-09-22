#!/usr/bin/env python3
"""
Simple MQTT Subscriber

Subscribes to a topic on the public HiveMQ broker and prints incoming
messages to the terminal.

- Broker: broker.hivemq.com:1883 (no auth)
- Topic: defaults to 'bilprojekt72439/obd/#' (override with MQTT_TOPIC env var)
"""

import os
import sys
import json
import logging
import time
import paho.mqtt.client as mqtt

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
DEFAULT_TOPIC = "bilprojekt72439/obd/#"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        topic = userdata.get("topic", DEFAULT_TOPIC)
        client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")
    else:
        logger.error(f"Failed to connect to MQTT broker. rc={rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    # Try pretty-print JSON if possible, otherwise print raw
    try:
        obj = json.loads(payload)
        pretty = json.dumps(obj, indent=2)
        print(f"\nTopic: {msg.topic}\n{pretty}")
    except Exception:
        print(f"\nTopic: {msg.topic}\n{payload}")


def main():
    topic = os.getenv("MQTT_TOPIC", DEFAULT_TOPIC)
    logger.info("Starting simple MQTT subscriber")
    logger.info(f"Broker: {BROKER_HOST}:{BROKER_PORT}")
    logger.info(f"Topic: {topic}")

    client = mqtt.Client(userdata={"topic": topic})
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        # This will block and handle reconnects internally
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Subscriber error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
