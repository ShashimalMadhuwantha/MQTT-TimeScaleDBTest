# TimescaleDB IoT Sensor Platform

A complete IoT sensor data platform with TimescaleDB, MQTT broker, and Flask REST API.

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│ IoT Sensors │────▶│  Mosquitto  │────▶│  MQTT Consumer  │
│   (MQTT)    │     │   Broker    │     │  (mqtt_app.py)  │
└─────────────┘     └─────────────┘     └────────┬────────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Postman   │────▶│  Flask API  │────▶│   TimescaleDB   │
│   Client    │     │  (app.py)   │     │   (PostgreSQL)  │
└─────────────┘     └─────────────┘     └─────────────────┘
```

## 📋 Prerequisites

- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/downloads)

## 🚀 Quick Start

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd timescale-project
```

### Step 2: Start Docker Containers

```bash
docker compose up -d
```

This starts:
- **TimescaleDB** on port `5432`
- **Mosquitto MQTT Broker** on port `1883`

### Step 3: Verify Containers are Running

```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                                  PORTS                    NAMES
xxxx           timescale/timescaledb-ha:pg14-latest   0.0.0.0:5432->5432/tcp   timescaledb
xxxx           eclipse-mosquitto:2                    0.0.0.0:1883->1883/tcp   mosquitto
```

### Step 4: Initialize the Database

Connect to TimescaleDB and create the sensor_data table:

```bash
docker exec -it timescaledb psql -U myuser -d mydb
```

Run these SQL commands:

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create sensor data table
CREATE TABLE sensor_data (
    time        TIMESTAMPTZ       NOT NULL,
    sensor_id   INT               NOT NULL,
    temperature DOUBLE PRECISION  NULL,
    humidity    DOUBLE PRECISION  NULL,
    PRIMARY KEY (time, sensor_id)
);

-- Convert to hypertable (TimescaleDB feature)
SELECT create_hypertable('sensor_data', 'time');

-- Exit psql
\q
```

### Step 5: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Configure Environment

The `.env` file is pre-configured with default values:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=mypassword
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=sensors/#
```

### Step 7: Start the Flask API

```bash
python app.py
```

API runs at: `http://localhost:5000`

### Step 8: Start the MQTT Consumer (Optional)

In a new terminal:

```bash
python mqtt_app.py
```

This listens for MQTT messages and stores them in TimescaleDB.

## 🧪 Testing

### Test the API

```bash
# Health check
curl http://localhost:5000/health

# Get all sensor data
curl http://localhost:5000/api/sensors
```

### Test MQTT Publishing

```bash
python test_mqtt.py
```

## 📁 Project Structure

```
timescale-project/
├── docker-compose.yml    # Docker services configuration
├── app.py                # Flask REST API
├── mqtt_app.py           # MQTT subscriber/consumer
├── test_mqtt.py          # MQTT test publisher
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── README.md             # This file
└── mosquitto/
    └── config/
        └── mosquitto.conf  # MQTT broker configuration
```

## 🔌 Services

| Service | Port | Description |
|---------|------|-------------|
| TimescaleDB | 5432 | Time-series database |
| Mosquitto | 1883 | MQTT broker |
| Flask API | 5000 | REST API |

## 🔐 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| TimescaleDB | myuser | mypassword |
| Database | mydb | - |

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check API and database health |

### Sensor Data CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sensors` | Get all sensor data |
| GET | `/api/sensors/<sensor_id>` | Get data for a specific sensor |
| POST | `/api/sensors` | Create new sensor data |
| POST | `/api/sensors/bulk` | Create multiple sensor data entries |
| PUT | `/api/sensors` | Update sensor data |
| DELETE | `/api/sensors?time=<time>&sensor_id=<id>` | Delete specific sensor data |
| DELETE | `/api/sensors/<sensor_id>` | Delete all data for a sensor |

### Aggregations (TimescaleDB Features)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sensors/stats` | Get aggregated statistics |
| GET | `/api/sensors/time-bucket` | Get time-bucketed aggregations |

## Example Requests

### Create Sensor Data

```bash
curl -X POST http://localhost:5000/api/sensors \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": 1, "temperature": 25.5, "humidity": 45.0}'
```

### Create with Custom Timestamp

```bash
curl -X POST http://localhost:5000/api/sensors \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": 1, "temperature": 25.5, "humidity": 45.0, "time": "2025-12-09T10:00:00+05:30"}'
```

### Bulk Insert

```bash
curl -X POST http://localhost:5000/api/sensors/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"sensor_id": 1, "temperature": 23.5, "humidity": 40.0},
    {"sensor_id": 2, "temperature": 24.0, "humidity": 42.0},
    {"sensor_id": 3, "temperature": 22.8, "humidity": 38.5}
  ]'
```

### Get All Sensor Data

```bash
# Get all data from last 24 hours (default)
curl http://localhost:5000/api/sensors

# Filter by sensor_id
curl http://localhost:5000/api/sensors?sensor_id=1

# Custom time range and limit
curl http://localhost:5000/api/sensors?hours=48&limit=50
```

### Get Data for Specific Sensor

```bash
curl http://localhost:5000/api/sensors/1?hours=12
```

### Update Sensor Data

```bash
curl -X PUT http://localhost:5000/api/sensors \
  -H "Content-Type: application/json" \
  -d '{"time": "2025-12-09T10:00:00+05:30", "sensor_id": 1, "temperature": 26.0}'
```

### Delete Sensor Data

```bash
# Delete specific record
curl -X DELETE "http://localhost:5000/api/sensors?time=2025-12-09T10:00:00%2B05:30&sensor_id=1"

# Delete all data for a sensor
curl -X DELETE http://localhost:5000/api/sensors/1
```

### Get Statistics

```bash
# Stats for all sensors (last 24 hours)
curl http://localhost:5000/api/sensors/stats

# Stats for specific sensor
curl http://localhost:5000/api/sensors/stats?sensor_id=1&hours=48
```

### Time Bucket Aggregations

```bash
# Hourly averages (default)
curl http://localhost:5000/api/sensors/time-bucket

# 15-minute buckets
curl "http://localhost:5000/api/sensors/time-bucket?bucket=15%20minutes"

# Daily averages
curl "http://localhost:5000/api/sensors/time-bucket?bucket=1%20day&hours=168"
```

## Response Format

All responses are in JSON format:

### Success Response

```json
{
  "data": [...],
  "count": 10
}
```

### Error Response

```json
{
  "error": "Error message"
}
```

## Docker Deployment

You can also run the Flask API in Docker. Add this service to your `docker-compose.yml`:

```yaml
  flask-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=timescaledb
      - DB_PORT=5432
      - DB_NAME=mydb
      - DB_USER=myuser
      - DB_PASSWORD=mypassword
    depends_on:
      - timescaledb
```

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
```
