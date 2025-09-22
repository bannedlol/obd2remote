import os

# MQTT
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.com")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "bilprojekt72439/obd/#")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "viewer-ingestor")

# InfluxDB 2.0
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "influx-dev-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "obd")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "obd")

# Retention and query defaults
RETENTION_HOURS = int(os.getenv("RETENTION_HOURS", "24"))
DEFAULT_QUERY_HOURS = int(os.getenv("DEFAULT_QUERY_HOURS", "24"))

# App
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
