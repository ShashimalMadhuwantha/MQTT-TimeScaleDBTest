'''
Publisher Script: mqtt_publisher.py

Purpose:
- Publishes simulated or real sensor data to the MQTT broker.
- Sends messages to the topic 'sensors/sensegrid'.
- Designed to be run independently of existing test clients.

Usage:
1. Ensure MQTT broker is running on localhost:1883 (Mosquitto).
2. Run the script:
    python mqtt_publisher.py
3. The script will continuously (or periodically) publish JSON messages containing:
    - machine_id
    - production_count
    - oee
    - downtime_reason
    - timestamp

Dependencies:
- paho-mqtt
- python-dotenv (if using environment variables)
'''

import os
import json
import time
import random
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Load environment variables from .env
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/sensegrid")

# Connect to MQTT Broker
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

def generate_sensegrid_data():
    """Simulate real PLC/machine data for SenseGrid"""
    return {
        "machine_id": random.randint(1, 5),            # 5 machines
        "production_count": random.randint(1000, 5000),
        "oee": round(random.uniform(70, 95), 2),      # OEE %
        "downtime_reason": random.choice([
            "Mechanical", "Electrical", "Setup", "Quality", "Other"
        ]),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

print(f"Publishing to MQTT broker {MQTT_BROKER}:{MQTT_PORT} on topic {MQTT_TOPIC} ...")

try:
    while True:
        data = generate_sensegrid_data()
        payload = json.dumps(data)
        client.publish(MQTT_TOPIC, payload)
        print(f"Published: {payload}")
        time.sleep(2)  # publish every 2 seconds
except KeyboardInterrupt:
    print("Publisher stopped")
    client.disconnect()
