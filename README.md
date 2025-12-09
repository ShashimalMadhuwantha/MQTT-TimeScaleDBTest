# TimescaleDB Flask API

A RESTful API for managing IoT sensor data stored in TimescaleDB.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file with your database credentials:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=mypassword
```

### 3. Run the API

```bash
python app.py
```

The API will be available at `http://localhost:5000`

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
