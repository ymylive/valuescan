# Admin Backend API Documentation

## Overview

The admin backend API provides comprehensive control and monitoring capabilities for the ValuScan system.

## Base URL

All endpoints are prefixed with `/api/`

## Authentication

Currently uses the existing admin token authentication from the main server.

---

## Control API

### Start Scheduler

**Endpoint:** `POST /api/control/scheduler/start`

**Description:** Start the task scheduler

**Response:**
```json
{
  "status": "success",
  "message": "Scheduler started"
}
```

### Stop Scheduler

**Endpoint:** `POST /api/control/scheduler/stop`

**Description:** Stop the task scheduler

**Response:**
```json
{
  "status": "success",
  "message": "Scheduler stopped"
}
```

### Trigger Anomaly Detection

**Endpoint:** `POST /api/control/trigger/anomaly`

**Description:** Manually trigger anomaly detection for all assets

**Response:**
```json
{
  "status": "success",
  "message": "Anomaly detection triggered"
}
```

### Trigger Macro Analysis

**Endpoint:** `POST /api/control/trigger/macro`

**Description:** Manually trigger macro analysis

**Response:**
```json
{
  "status": "success",
  "message": "Macro analysis triggered"
}
```

### Trigger AI Brief

**Endpoint:** `POST /api/control/trigger/ai_brief`

**Description:** Manually trigger AI brief generation

**Response:**
```json
{
  "status": "success",
  "message": "AI brief triggered"
}
```

### Trigger News Fetch

**Endpoint:** `POST /api/control/trigger/news`

**Description:** Manually trigger news data fetch

**Response:**
```json
{
  "status": "success",
  "message": "News fetch triggered"
}
```

### Trigger Economic Data Fetch

**Endpoint:** `POST /api/control/trigger/econ`

**Description:** Manually trigger economic data fetch

**Response:**
```json
{
  "status": "success",
  "message": "Economic data fetch triggered"
}
```

---

## Config API

### Get Configuration

**Endpoint:** `GET /api/config`

**Description:** Get current system configuration

**Response:**
```json
{
  "status": "success",
  "config": {
    "version": "3.0.0",
    ...
  }
}
```

### Update Configuration

**Endpoint:** `PUT /api/config`

**Description:** Update system configuration with validation

**Request Body:**
```json
{
  "version": "3.0.0",
  ...
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Config updated",
  "restart_required": true
}
```

**Notes:**
- Configuration is validated before applying
- Returns `restart_required` flag if system restart is needed
- All changes are logged with timestamp

### Get Configuration History

**Endpoint:** `GET /api/config/history`

**Description:** Get recent configuration changes

**Response:**
```json
{
  "status": "success",
  "history": [
    {
      "timestamp": "2026-02-10T00:00:00",
      "config": {...}
    }
  ]
}
```

---

## Logs API

### Query Logs

**Endpoint:** `GET /api/logs`

**Description:** Query system logs with filters

**Query Parameters:**
- `level` (optional): Log level filter (INFO, WARNING, ERROR)
- `module` (optional): Module name filter
- `since` (optional): ISO 8601 timestamp to filter logs after
- `limit` (optional): Maximum number of logs to return (default: 100)

**Example:**
```
GET /api/logs?level=INFO&module=anomaly&since=2026-02-10T00:00:00&limit=50
```

**Response:**
```json
{
  "status": "success",
  "logs": [
    {
      "timestamp": "2026-02-10T00:00:00",
      "level": "INFO",
      "module": "anomaly",
      "message": "Log message"
    }
  ],
  "count": 50
}
```

### Stream Logs

**Endpoint:** `GET /api/logs/stream`

**Description:** Stream logs in real-time using Server-Sent Events (SSE)

**Response:** SSE stream with log events

**Example Event:**
```
data: {"timestamp": "2026-02-10T00:00:00", "level": "INFO", "module": "anomaly", "message": "Log message"}
```

---

## Health API

### Get System Health

**Endpoint:** `GET /api/health`

**Description:** Get system health status and task information

**Response:**
```json
{
  "version": "3.0.0",
  "uptime_seconds": 3600,
  "tasks": {
    "anomaly_detection": {
      "status": "running",
      "last_run": "2026-02-10T00:00:00",
      "next_run": "2026-02-10T01:00:00"
    },
    "macro_analysis": {
      "status": "idle",
      "last_run": null,
      "next_run": null
    },
    "ai_brief": {
      "status": "idle",
      "last_run": null,
      "next_run": null
    },
    "news_fetch": {
      "status": "idle",
      "last_run": null,
      "next_run": null
    },
    "econ_fetch": {
      "status": "idle",
      "last_run": null,
      "next_run": null
    }
  },
  "queue_backlog": 0
}
```

**Task Status Values:**
- `running`: Task is currently executing
- `idle`: Task is not running
- `error`: Task encountered an error

---

## Error Responses

All endpoints return error responses in the following format:

```json
{
  "status": "error",
  "message": "Error description"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad request (invalid input)
- `404`: Resource not found
- `500`: Internal server error

---

## Integration

To integrate these APIs into the main server, add the following to `api/server.py`:

```python
from api.control import control_bp
from api.config import config_bp, init_config_api
from api.logs import logs_bp
from api.health import health_bp

# Register blueprints
app.register_blueprint(control_bp, url_prefix='/api/control')
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(logs_bp, url_prefix='/api/logs')
app.register_blueprint(health_bp, url_prefix='/api/health')

# Initialize config API
init_config_api(Path('path/to/config.json'))
```

---

## Future Enhancements

1. **Control API**: Integrate with actual scheduler and task pipelines
2. **Config API**: Add comprehensive schema validation
3. **Logs API**: Implement actual log file tailing and filtering
4. **Health API**: Connect to real task queue and monitoring system
5. **Authentication**: Add role-based access control for different admin operations
