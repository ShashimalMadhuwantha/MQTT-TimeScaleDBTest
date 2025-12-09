from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'mydb'),
    'user': os.getenv('DB_USER', 'myuser'),
    'password': os.getenv('DB_PASSWORD', 'mypassword')
}


def get_db_connection():
    """Create and return a database connection."""
    conn = psycopg.connect(**DB_CONFIG, row_factory=dict_row)
    return conn


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


# ============== SENSOR DATA ENDPOINTS ==============

@app.route('/api/sensors', methods=['GET'])
def get_all_sensor_data():
    """Get all sensor data with optional filtering."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Optional query parameters
        sensor_id = request.args.get('sensor_id', type=int)
        hours = request.args.get('hours', type=int, default=24)
        limit = request.args.get('limit', type=int, default=100)
        
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
        
        return jsonify({'data': result, 'count': len(result)}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<int:sensor_id>', methods=['GET'])
def get_sensor_by_id(sensor_id):
    """Get data for a specific sensor."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = request.args.get('hours', type=int, default=24)
        
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
        
        return jsonify({'data': result, 'count': len(result)}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors', methods=['POST'])
def create_sensor_data():
    """Create new sensor data entry."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        sensor_id = data.get('sensor_id')
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        time = data.get('time')  # Optional, defaults to NOW()
        
        if sensor_id is None:
            return jsonify({'error': 'sensor_id is required'}), 400
        
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
        
        return jsonify({'message': 'Sensor data created successfully', 'data': result}), 201
    
    except psycopg.IntegrityError as e:
        return jsonify({'error': 'Duplicate entry for this time and sensor_id'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/bulk', methods=['POST'])
def create_bulk_sensor_data():
    """Create multiple sensor data entries at once."""
    try:
        data = request.get_json()
        
        if not data or not isinstance(data, list):
            return jsonify({'error': 'Expected a list of sensor data'}), 400
        
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
        
        return jsonify({'message': f'{inserted_count} records inserted successfully'}), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors', methods=['PUT'])
def update_sensor_data():
    """Update sensor data by time and sensor_id."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields to identify the record
        time = data.get('time')
        sensor_id = data.get('sensor_id')
        
        if not time or sensor_id is None:
            return jsonify({'error': 'time and sensor_id are required to identify the record'}), 400
        
        # Fields to update
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
            return jsonify({'error': 'Record not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        result = dict(updated_record)
        result['time'] = result['time'].isoformat()
        
        return jsonify({'message': 'Sensor data updated successfully', 'data': result}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors', methods=['DELETE'])
def delete_sensor_data():
    """Delete sensor data by time and sensor_id."""
    try:
        time = request.args.get('time')
        sensor_id = request.args.get('sensor_id', type=int)
        
        if not time or sensor_id is None:
            return jsonify({'error': 'time and sensor_id query parameters are required'}), 400
        
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
            return jsonify({'error': 'Record not found'}), 404
        
        return jsonify({'message': 'Sensor data deleted successfully', 'deleted_count': deleted_count}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<int:sensor_id>', methods=['DELETE'])
def delete_all_sensor_data_by_id(sensor_id):
    """Delete all data for a specific sensor."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM sensor_data WHERE sensor_id = %s"
        cursor.execute(query, (sensor_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': f'Deleted {deleted_count} records for sensor {sensor_id}'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============== AGGREGATION ENDPOINTS ==============

@app.route('/api/sensors/stats', methods=['GET'])
def get_sensor_stats():
    """Get aggregated statistics for sensors."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = request.args.get('hours', type=int, default=24)
        sensor_id = request.args.get('sensor_id', type=int)
        
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
        
        return jsonify({'data': result}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/time-bucket', methods=['GET'])
def get_time_bucket_data():
    """Get time-bucketed aggregations (TimescaleDB feature)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hours = request.args.get('hours', type=int, default=24)
        bucket = request.args.get('bucket', default='1 hour')  # e.g., '1 hour', '15 minutes', '1 day'
        sensor_id = request.args.get('sensor_id', type=int)
        
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
        
        return jsonify({'data': result, 'bucket_size': bucket}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
