from flask import Flask
import psycopg
from psycopg.rows import dict_row
import paho.mqtt.client as mqtt
import json
import os
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'mydb'),
    'user': os.getenv('DB_USER', 'myuser'),
    'password': os.getenv('DB_PASSWORD', 'mypassword')
}

# MQTT configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'timescale-mqtt-server')

# MQTT Topics
TOPICS = {
    # Request topics (client publishes to these)
    'health_request': 'sensors/health/request',
    'get_all_request': 'sensors/get_all/request',
    'get_by_id_request': 'sensors/get_by_id/request',
    'create_request': 'sensors/create/request',
    'create_bulk_request': 'sensors/create_bulk/request',
    'update_request': 'sensors/update/request',
    'delete_request': 'sensors/delete/request',
    'delete_by_id_request': 'sensors/delete_by_id/request',
    'stats_request': 'sensors/stats/request',
    'time_bucket_request': 'sensors/time_bucket/request',
    
    # Response topics (server publishes to these)
    'health_response': 'sensors/health/response',
    'get_all_response': 'sensors/get_all/response',
    'get_by_id_response': 'sensors/get_by_id/response',
    'create_response': 'sensors/create/response',
    'create_bulk_response': 'sensors/create_bulk/response',
    'update_response': 'sensors/update/response',
    'delete_response': 'sensors/delete/response',
    'delete_by_id_response': 'sensors/delete_by_id/response',
    'stats_response': 'sensors/stats/response',
    'time_bucket_response': 'sensors/time_bucket/response',
}


def get_db_connection():
    """Create and return a database connection."""
    conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    return conn


def publish_response(client, topic, data, status_code=200):
    """Publish a response to an MQTT topic."""
    response = {
        'status_code': status_code,
        'data': data
    }
    client.publish(topic, json.dumps(response), qos=1)
    logger.info(f"Published to {topic}: {json.dumps(response)[:100]}...")


# ============== MQTT MESSAGE HANDLERS ==============

def handle_health_check(client, payload):
    """Health check handler."""
    try:
        conn = get_db_connection()
        conn.close()
        publish_response(client, TOPICS['health_response'], 
                        {'status': 'healthy', 'database': 'connected'}, 200)
    except Exception as e:
        publish_response(client, TOPICS['health_response'], 
                        {'status': 'unhealthy', 'error': str(e)}, 500)


def handle_get_all_sensors(client, payload):
    """Get all sensor data with optional filtering."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Parse optional parameters from payload
        data = json.loads(payload) if payload else {}
        sensor_id = data.get('sensor_id')
        hours = data.get('hours', 24)
        limit = data.get('limit', 100)
        
        if sensor_id:
            query = """
                SELECT time, sensor_id, temperature, humidity 
                FROM sensor_data 
                WHERE sensor_id = %s AND time > NOW() - INTERVAL '%s hours'
                ORDER BY time DESC 
                LIMIT %s
            """
            cursor.execute(query, (sensor_id, hours, limit))
        else:
            query = """
                SELECT time, sensor_id, temperature, humidity 
                FROM sensor_data 
                WHERE time > NOW() - INTERVAL '%s hours'
                ORDER BY time DESC 
                LIMIT %s
            """
            cursor.execute(query, (hours, limit))
        
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert datetime objects to ISO format strings
        result = []
        for row in data:
            row_dict = dict(row)
            row_dict['time'] = row_dict['time'].isoformat()
            result.append(row_dict)
        
        publish_response(client, TOPICS['get_all_response'], 
                        {'data': result, 'count': len(result)}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['get_all_response'], 
                        {'error': str(e)}, 500)


def handle_get_sensor_by_id(client, payload):
    """Get data for a specific sensor."""
    try:
        data = json.loads(payload) if payload else {}
        sensor_id = data.get('sensor_id')
        hours = data.get('hours', 24)
        
        if sensor_id is None:
            publish_response(client, TOPICS['get_by_id_response'], 
                            {'error': 'sensor_id is required'}, 400)
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT time, sensor_id, temperature, humidity 
            FROM sensor_data 
            WHERE sensor_id = %s AND time > NOW() - INTERVAL '%s hours'
            ORDER BY time DESC
        """
        cursor.execute(query, (sensor_id, hours))
        data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        result = []
        for row in data:
            row_dict = dict(row)
            row_dict['time'] = row_dict['time'].isoformat()
            result.append(row_dict)
        
        publish_response(client, TOPICS['get_by_id_response'], 
                        {'data': result, 'count': len(result)}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['get_by_id_response'], 
                        {'error': str(e)}, 500)


def handle_create_sensor(client, payload):
    """Create new sensor data entry."""
    try:
        data = json.loads(payload) if payload else {}
        
        if not data:
            publish_response(client, TOPICS['create_response'], 
                            {'error': 'No data provided'}, 400)
            return
        
        sensor_id = data.get('sensor_id')
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        time = data.get('time')
        
        if sensor_id is None:
            publish_response(client, TOPICS['create_response'], 
                            {'error': 'sensor_id is required'}, 400)
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if time:
            query = """
                INSERT INTO sensor_data (time, sensor_id, temperature, humidity)
                VALUES (%s, %s, %s, %s)
                RETURNING time, sensor_id, temperature, humidity
            """
            cursor.execute(query, (time, sensor_id, temperature, humidity))
        else:
            query = """
                INSERT INTO sensor_data (time, sensor_id, temperature, humidity)
                VALUES (NOW(), %s, %s, %s)
                RETURNING time, sensor_id, temperature, humidity
            """
            cursor.execute(query, (sensor_id, temperature, humidity))
        
        new_record = cursor.fetchone()
        conn.commit()
        
        cursor.close()
        conn.close()
        
        result = dict(new_record)
        result['time'] = result['time'].isoformat()
        
        publish_response(client, TOPICS['create_response'], 
                        {'message': 'Sensor data created successfully', 'data': result}, 201)
    
    except psycopg.IntegrityError as e:
        publish_response(client, TOPICS['create_response'], 
                        {'error': 'Duplicate entry for this time and sensor_id'}, 409)
    except Exception as e:
        publish_response(client, TOPICS['create_response'], 
                        {'error': str(e)}, 500)


def handle_create_bulk_sensors(client, payload):
    """Create multiple sensor data entries at once."""
    try:
        data = json.loads(payload) if payload else []
        
        if not data or not isinstance(data, list):
            publish_response(client, TOPICS['create_bulk_response'], 
                            {'error': 'Expected a list of sensor data'}, 400)
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        inserted_count = 0
        for entry in data:
            sensor_id = entry.get('sensor_id')
            temperature = entry.get('temperature')
            humidity = entry.get('humidity')
            time = entry.get('time')
            
            if sensor_id is None:
                continue
            
            if time:
                query = """
                    INSERT INTO sensor_data (time, sensor_id, temperature, humidity)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (time, sensor_id, temperature, humidity))
            else:
                query = """
                    INSERT INTO sensor_data (time, sensor_id, temperature, humidity)
                    VALUES (NOW(), %s, %s, %s)
                """
                cursor.execute(query, (sensor_id, temperature, humidity))
            
            inserted_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        publish_response(client, TOPICS['create_bulk_response'], 
                        {'message': f'{inserted_count} records inserted successfully'}, 201)
    
    except Exception as e:
        publish_response(client, TOPICS['create_bulk_response'], 
                        {'error': str(e)}, 500)


def handle_update_sensor(client, payload):
    """Update sensor data by time and sensor_id."""
    try:
        data = json.loads(payload) if payload else {}
        
        if not data:
            publish_response(client, TOPICS['update_response'], 
                            {'error': 'No data provided'}, 400)
            return
        
        time = data.get('time')
        sensor_id = data.get('sensor_id')
        
        if not time or sensor_id is None:
            publish_response(client, TOPICS['update_response'], 
                            {'error': 'time and sensor_id are required to identify the record'}, 400)
            return
        
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE sensor_data 
            SET temperature = COALESCE(%s, temperature),
                humidity = COALESCE(%s, humidity)
            WHERE time = %s AND sensor_id = %s
            RETURNING time, sensor_id, temperature, humidity
        """
        cursor.execute(query, (temperature, humidity, time, sensor_id))
        updated_record = cursor.fetchone()
        
        if not updated_record:
            cursor.close()
            conn.close()
            publish_response(client, TOPICS['update_response'], 
                            {'error': 'Record not found'}, 404)
            return
        
        conn.commit()
        cursor.close()
        conn.close()
        
        result = dict(updated_record)
        result['time'] = result['time'].isoformat()
        
        publish_response(client, TOPICS['update_response'], 
                        {'message': 'Sensor data updated successfully', 'data': result}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['update_response'], 
                        {'error': str(e)}, 500)


def handle_delete_sensor(client, payload):
    """Delete sensor data by time and sensor_id."""
    try:
        data = json.loads(payload) if payload else {}
        
        time = data.get('time')
        sensor_id = data.get('sensor_id')
        
        if not time or sensor_id is None:
            publish_response(client, TOPICS['delete_response'], 
                            {'error': 'time and sensor_id are required'}, 400)
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            DELETE FROM sensor_data 
            WHERE time = %s AND sensor_id = %s
        """
        cursor.execute(query, (time, sensor_id))
        deleted_count = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count == 0:
            publish_response(client, TOPICS['delete_response'], 
                            {'error': 'Record not found'}, 404)
            return
        
        publish_response(client, TOPICS['delete_response'], 
                        {'message': 'Sensor data deleted successfully', 'deleted_count': deleted_count}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['delete_response'], 
                        {'error': str(e)}, 500)


def handle_delete_sensor_by_id(client, payload):
    """Delete all data for a specific sensor."""
    try:
        data = json.loads(payload) if payload else {}
        sensor_id = data.get('sensor_id')
        
        if sensor_id is None:
            publish_response(client, TOPICS['delete_by_id_response'], 
                            {'error': 'sensor_id is required'}, 400)
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM sensor_data WHERE sensor_id = %s"
        cursor.execute(query, (sensor_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        publish_response(client, TOPICS['delete_by_id_response'], 
                        {'message': f'Deleted {deleted_count} records for sensor {sensor_id}'}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['delete_by_id_response'], 
                        {'error': str(e)}, 500)


def handle_get_stats(client, payload):
    """Get aggregated statistics for sensors."""
    try:
        data = json.loads(payload) if payload else {}
        hours = data.get('hours', 24)
        sensor_id = data.get('sensor_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if sensor_id:
            query = """
                SELECT 
                    sensor_id,
                    COUNT(*) as total_readings,
                    AVG(temperature) as avg_temperature,
                    MIN(temperature) as min_temperature,
                    MAX(temperature) as max_temperature,
                    AVG(humidity) as avg_humidity,
                    MIN(humidity) as min_humidity,
                    MAX(humidity) as max_humidity,
                    MIN(time) as first_reading,
                    MAX(time) as last_reading
                FROM sensor_data 
                WHERE sensor_id = %s AND time > NOW() - INTERVAL '%s hours'
                GROUP BY sensor_id
            """
            cursor.execute(query, (sensor_id, hours))
        else:
            query = """
                SELECT 
                    sensor_id,
                    COUNT(*) as total_readings,
                    AVG(temperature) as avg_temperature,
                    MIN(temperature) as min_temperature,
                    MAX(temperature) as max_temperature,
                    AVG(humidity) as avg_humidity,
                    MIN(humidity) as min_humidity,
                    MAX(humidity) as max_humidity,
                    MIN(time) as first_reading,
                    MAX(time) as last_reading
                FROM sensor_data 
                WHERE time > NOW() - INTERVAL '%s hours'
                GROUP BY sensor_id
                ORDER BY sensor_id
            """
            cursor.execute(query, (hours,))
        
        stats = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for row in stats:
            row_dict = dict(row)
            if row_dict['first_reading']:
                row_dict['first_reading'] = row_dict['first_reading'].isoformat()
            if row_dict['last_reading']:
                row_dict['last_reading'] = row_dict['last_reading'].isoformat()
            # Convert Decimal to float for JSON serialization
            for key in ['avg_temperature', 'min_temperature', 'max_temperature', 
                        'avg_humidity', 'min_humidity', 'max_humidity']:
                if row_dict[key] is not None:
                    row_dict[key] = float(row_dict[key])
            result.append(row_dict)
        
        publish_response(client, TOPICS['stats_response'], 
                        {'data': result}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['stats_response'], 
                        {'error': str(e)}, 500)


def handle_time_bucket(client, payload):
    """Get time-bucketed aggregations (TimescaleDB feature)."""
    try:
        data = json.loads(payload) if payload else {}
        hours = data.get('hours', 24)
        bucket = data.get('bucket', '1 hour')
        sensor_id = data.get('sensor_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if sensor_id:
            query = f"""
                SELECT 
                    time_bucket('{bucket}', time) AS bucket,
                    sensor_id,
                    AVG(temperature) as avg_temperature,
                    AVG(humidity) as avg_humidity,
                    COUNT(*) as readings
                FROM sensor_data 
                WHERE sensor_id = %s AND time > NOW() - INTERVAL '%s hours'
                GROUP BY bucket, sensor_id
                ORDER BY bucket DESC
            """
            cursor.execute(query, (sensor_id, hours))
        else:
            query = f"""
                SELECT 
                    time_bucket('{bucket}', time) AS bucket,
                    sensor_id,
                    AVG(temperature) as avg_temperature,
                    AVG(humidity) as avg_humidity,
                    COUNT(*) as readings
                FROM sensor_data 
                WHERE time > NOW() - INTERVAL '%s hours'
                GROUP BY bucket, sensor_id
                ORDER BY bucket DESC, sensor_id
            """
            cursor.execute(query, (hours,))
        
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for row in data:
            row_dict = dict(row)
            row_dict['bucket'] = row_dict['bucket'].isoformat()
            if row_dict['avg_temperature'] is not None:
                row_dict['avg_temperature'] = float(row_dict['avg_temperature'])
            if row_dict['avg_humidity'] is not None:
                row_dict['avg_humidity'] = float(row_dict['avg_humidity'])
            result.append(row_dict)
        
        publish_response(client, TOPICS['time_bucket_response'], 
                        {'data': result, 'bucket_size': bucket}, 200)
    
    except Exception as e:
        publish_response(client, TOPICS['time_bucket_response'], 
                        {'error': str(e)}, 500)


# ============== MQTT CLIENT SETUP ==============

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        # Subscribe to all request topics
        for topic_name, topic in TOPICS.items():
            if 'request' in topic_name:
                client.subscribe(topic, qos=1)
                logger.info(f"Subscribed to {topic}")
    else:
        logger.error(f"Failed to connect, return code {rc}")


def on_disconnect(client, userdata, rc, properties=None):
    """Callback when disconnected from MQTT broker."""
    logger.warning(f"Disconnected from MQTT Broker with code {rc}")


def on_message(client, userdata, msg):
    """Callback when a message is received."""
    topic = msg.topic
    payload = msg.payload.decode('utf-8') if msg.payload else ''
    logger.info(f"Received message on {topic}: {payload[:100]}...")
    
    # Route to appropriate handler
    handlers = {
        TOPICS['health_request']: handle_health_check,
        TOPICS['get_all_request']: handle_get_all_sensors,
        TOPICS['get_by_id_request']: handle_get_sensor_by_id,
        TOPICS['create_request']: handle_create_sensor,
        TOPICS['create_bulk_request']: handle_create_bulk_sensors,
        TOPICS['update_request']: handle_update_sensor,
        TOPICS['delete_request']: handle_delete_sensor,
        TOPICS['delete_by_id_request']: handle_delete_sensor_by_id,
        TOPICS['stats_request']: handle_get_stats,
        TOPICS['time_bucket_request']: handle_time_bucket,
    }
    
    handler = handlers.get(topic)
    if handler:
        handler(client, payload)
    else:
        logger.warning(f"No handler for topic: {topic}")


def create_mqtt_client():
    """Create and configure MQTT client."""
    client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    return client


def start_mqtt_client():
    """Start the MQTT client in a separate thread."""
    client = create_mqtt_client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")


# Flask route for status check
@app.route('/status', methods=['GET'])
def status():
    """Status endpoint for the MQTT server."""
    return {'status': 'MQTT server running', 'broker': MQTT_BROKER, 'port': MQTT_PORT}


if __name__ == '__main__':
    # Start MQTT client in a separate thread
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    logger.info("MQTT client thread started")
    
    # Run Flask app for status endpoint
    app.run(host='0.0.0.0', port=5001, debug=False)
