'''
Subscriber Script: mqtt_subscriber.py

Purpose:
- Subscribes to the MQTT broker to receive messages on 'sensors/sensegrid'.
- Prints received sensor data to the console.
- Can optionally forward data to a REST API or save to a database (future extension).

Usage:
1. Ensure MQTT broker is running on localhost:1883.
2. Run the script:
    python mqtt_subscriber.py
3. The subscriber will print messages like:
    Received message: {'machine_id': 1, 'production_count': 1027, 'oee': 91.43, 'downtime_reason': 'Electrical', 'timestamp': '2025-12-09T15:42:32Z'}

Dependencies:
- paho-mqtt
- python-dotenv (if using environment variables)
'''

import os
import json
import requests
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Load environment variables
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/sensegrid")
API_URL = os.getenv("API_URL", "http://localhost:5000/api/sensors")  # Optional: forward to Flask

# Callback when a message is received
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    print(f"Received message: {payload}")

    # Optional: forward to Flask API
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print("Data sent to API successfully")
        else:
            print(f"API response error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send to API: {e}")

# Connect to MQTT Broker
client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.subscribe(MQTT_TOPIC)

print(f"Subscribed to topic {MQTT_TOPIC} at {MQTT_BROKER}:{MQTT_PORT} ...")

# Blocking loop to keep script running
client.loop_forever()
