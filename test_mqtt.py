"""
MQTT API Test Client
Run this script to test the MQTT sensor API endpoints.
"""
import paho.mqtt.client as mqtt
import json
import time

MQTT_BROKER = 'localhost'
MQTT_PORT = 1883

responses = {}

def on_connect(client, userdata, flags, rc, properties=None):
    print("✅ Connected to MQTT Broker!")
    # Subscribe to all response topics
    response_topics = [
        'sensors/health/response',
        'sensors/get_all/response',
        'sensors/get_by_id/response',
        'sensors/create/response',
        'sensors/create_bulk/response',
        'sensors/update/response',
        'sensors/delete/response',
        'sensors/delete_by_id/response',
        'sensors/stats/response',
        'sensors/time_bucket/response',
    ]
    for topic in response_topics:
        client.subscribe(topic, qos=1)
    print("✅ Subscribed to response topics\n")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = json.loads(msg.payload.decode())
    responses[topic] = payload
    print(f"📥 Response from {topic}:")
    print(json.dumps(payload, indent=2))
    print("-" * 50)

def send_request(client, topic, payload=None):
    """Send a request and wait for response."""
    print(f"\n📤 Sending to {topic}:")
    print(json.dumps(payload, indent=2) if payload else "{}")
    
    message = json.dumps(payload) if payload else "{}"
    client.publish(topic, message, qos=1)
    time.sleep(1)  # Wait for response

def main():
    client = mqtt.Client(
        client_id="mqtt-test-client",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT Broker...")
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    time.sleep(1)  # Wait for connection

    print("\n" + "=" * 50)
    print("MQTT API TEST SUITE")
    print("=" * 50)

    # Test 1: Health Check
    print("\n🧪 TEST 1: Health Check")
    send_request(client, 'sensors/health/request', {})

    # Test 2: Create Sensor Data
    print("\n🧪 TEST 2: Create Sensor Data")
    send_request(client, 'sensors/create/request', {
        'sensor_id': 1,
        'temperature': 25.5,
        'humidity': 45.0
    })

    # Test 3: Bulk Create
    print("\n🧪 TEST 3: Bulk Create Sensor Data")
    send_request(client, 'sensors/create_bulk/request', [
        {'sensor_id': 2, 'temperature': 23.5, 'humidity': 40.0},
        {'sensor_id': 3, 'temperature': 24.0, 'humidity': 42.0}
    ])

    # Test 4: Get All Sensors
    print("\n🧪 TEST 4: Get All Sensors")
    send_request(client, 'sensors/get_all/request', {
        'limit': 10
    })

    # Test 5: Get Sensor by ID
    print("\n🧪 TEST 5: Get Sensor by ID")
    send_request(client, 'sensors/get_by_id/request', {
        'sensor_id': 1,
        'hours': 24
    })

    # Test 6: Get Stats
    print("\n🧪 TEST 6: Get Sensor Stats")
    send_request(client, 'sensors/stats/request', {
        'hours': 24
    })

    # Test 7: Time Bucket
    print("\n🧪 TEST 7: Time Bucket Aggregation")
    send_request(client, 'sensors/time_bucket/request', {
        'bucket': '1 hour',
        'hours': 24
    })

    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)

    client.loop_stop()
    client.disconnect()

if __name__ == '__main__':
    main()
