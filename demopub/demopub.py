#!/usr/bin/env python3
"""
Demo OBD2 Data Publisher

This application publishes simulated OBD2 sensor data to a public MQTT broker.
The data includes RPM, Speed, Throttle, Engine Temperature, and Oil Temperature
with realistic oscillating patterns.
"""

import json
import time
import math
import os
import logging
from typing import Dict, Any
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OBD2DataSimulator:
    """Simulates OBD2 sensor data with realistic oscillating patterns."""
    
    def __init__(self):
        self.start_time = time.time()
        
        # Oscillation parameters for each sensor (frequency in Hz)
        self.rpm_freq = 1/60  # 1 oscillation per minute
        self.speed_freq = 2/60  # 2 oscillations per minute
        self.throttle_freq = 3/60  # 3 oscillations per minute
        self.engine_temp_freq = 1.5/60  # 1.5 oscillations per minute
        
        # Phase offsets to make them oscillate out of sync
        self.rpm_phase = 0
        self.speed_phase = math.pi / 3
        self.throttle_phase = 2 * math.pi / 3
        self.engine_temp_phase = math.pi
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Generate current sensor readings."""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Generate oscillating values using sine waves
        rpm_oscillation = math.sin(2 * math.pi * self.rpm_freq * elapsed + self.rpm_phase)
        rpm = 4500 + 2500 * rpm_oscillation  # 2000-7000 RPM
        
        speed_oscillation = math.sin(2 * math.pi * self.speed_freq * elapsed + self.speed_phase)
        speed = 70 + 50 * speed_oscillation  # 20-120 km/h
        
        throttle_oscillation = math.sin(2 * math.pi * self.throttle_freq * elapsed + self.throttle_phase)
        throttle = 50 + 50 * throttle_oscillation  # 0-100%
        
        engine_temp_oscillation = math.sin(2 * math.pi * self.engine_temp_freq * elapsed + self.engine_temp_phase)
        engine_temp = 95 + 25 * engine_temp_oscillation  # 70-120°C
        
        # Oil temperature stays steady at 130°C
        oil_temp = 130
        
        return {
            "timestamp": int(current_time),
            "rpm": int(round(rpm)),
            "speed_kmh": int(round(speed)),
            "throttle_percent": int(max(0, min(100, round(throttle)))),
            "engine_temp_c": int(round(engine_temp)),
            "oil_temp_c": int(oil_temp)
        }


class MQTTPublisher:
    """Handles MQTT connection and publishing."""
    
    def __init__(self, broker_host: str, broker_port: int, topic: str):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client = mqtt.Client()
        self.connected = False
        
        # Set up MQTT callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker {self.broker_host}:{self.broker_port}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker."""
        self.connected = False
        logger.info("Disconnected from MQTT broker")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published."""
        logger.debug(f"Message {mid} published successfully")
    
    def connect(self):
        """Connect to the MQTT broker."""
        try:
            logger.info(f"Connecting to MQTT broker {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise ConnectionError("Failed to connect to MQTT broker within timeout")
                
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            raise
    
    def publish(self, data: Dict[str, Any]):
        """Publish data to the MQTT topic."""
        if not self.connected:
            logger.warning("Not connected to MQTT broker. Attempting to reconnect...")
            self.connect()
        
        try:
            message = json.dumps(data, indent=2)
            result = self.client.publish(self.topic, message)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {self.topic}: {data}")
            else:
                logger.error(f"Failed to publish message. Return code: {result.rc}")
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
    
    def disconnect(self):
        """Disconnect from the MQTT broker."""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()


def main():
    """Main application entry point."""
    # Configuration
    BROKER_HOST = "broker.hivemq.com"
    BROKER_PORT = 1883
    DEFAULT_TOPIC = "bilprojekt72439/obd/data"
    PUBLISH_INTERVAL = 0.2  # seconds
    
    # Get topic from environment variable or use default
    topic = os.getenv("MQTT_TOPIC", DEFAULT_TOPIC)
    
    logger.info("Starting OBD2 Demo Publisher")
    logger.info(f"Broker: {BROKER_HOST}:{BROKER_PORT}")
    logger.info(f"Topic: {topic}")
    logger.info(f"Publish interval: {PUBLISH_INTERVAL}s")
    
    # Initialize components
    simulator = OBD2DataSimulator()
    publisher = MQTTPublisher(BROKER_HOST, BROKER_PORT, topic)
    
    try:
        # Connect to MQTT broker
        publisher.connect()
        
        logger.info("Starting data publication. Press Ctrl+C to stop.")
        
        # Main publishing loop
        while True:
            # Generate sensor data
            sensor_data = simulator.get_sensor_data()
            
            # Publish to MQTT
            publisher.publish(sensor_data)
            
            # Log current values
            logger.info(
                f"RPM: {sensor_data['rpm']}, "
                f"Speed: {sensor_data['speed_kmh']} km/h, "
                f"Throttle: {sensor_data['throttle_percent']}%, "
                f"Engine: {sensor_data['engine_temp_c']}°C, "
                f"Oil: {sensor_data['oil_temp_c']}°C"
            )
            
            # Wait for next publish interval
            time.sleep(PUBLISH_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Clean up
        publisher.disconnect()
        logger.info("Application stopped")


if __name__ == "__main__":
    main()
