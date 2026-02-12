"""Tests for admin backend APIs."""
import pytest
from flask import Flask
from api.control import control_bp
from api.config import config_bp, init_config_api
from api.logs import logs_bp, add_log_entry
from api.health import health_bp, update_task_status
import json
import tempfile
from pathlib import Path


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.register_blueprint(control_bp, url_prefix='/api/control')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(logs_bp, url_prefix='/api/logs')
    app.register_blueprint(health_bp, url_prefix='/api/health')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    """Configure API auth for tests."""
    monkeypatch.setenv('VALUESCAN_API_KEY', 'test-api-key')


@pytest.fixture
def auth_headers():
    return {'X-API-Key': 'test-api-key'}


@pytest.fixture
def temp_config():
    """Create temporary config file."""
    project_root = Path(__file__).resolve().parents[1]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir=project_root) as f:
        config = {"version": "3.0.0", "test": "value"}
        json.dump(config, f)
        temp_path = Path(f.name)

    init_config_api(temp_path)
    yield temp_path
    temp_path.unlink(missing_ok=True)


class TestControlAPI:
    """Test control API endpoints."""

    def test_start_scheduler(self, client, auth_headers):
        response = client.post('/api/control/scheduler/start', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_stop_scheduler(self, client, auth_headers):
        response = client.post('/api/control/scheduler/stop', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_trigger_anomaly(self, client, auth_headers):
        response = client.post('/api/control/trigger/anomaly', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_trigger_macro(self, client, auth_headers):
        response = client.post('/api/control/trigger/macro', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_trigger_ai_brief(self, client, auth_headers):
        response = client.post('/api/control/trigger/ai_brief', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_trigger_news(self, client, auth_headers):
        response = client.post('/api/control/trigger/news', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_trigger_econ(self, client, auth_headers):
        response = client.post('/api/control/trigger/econ', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'


class TestConfigAPI:
    """Test config API endpoints."""

    def test_get_config(self, client, temp_config, auth_headers):
        response = client.get('/api/config', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'config' in data

    def test_update_config(self, client, temp_config, auth_headers):
        new_config = {"version": "3.0.0", "signal_monitor": {}}
        response = client.put('/api/config',
                            data=json.dumps(new_config),
                            content_type='application/json',
                            headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'restart_required' in data

    def test_get_config_history(self, client, temp_config, auth_headers):
        response = client.get('/api/config/history', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'history' in data


class TestLogsAPI:
    """Test logs API endpoints."""

    def test_query_logs(self, client, auth_headers):
        add_log_entry('INFO', 'test', 'Test message')
        response = client.get('/api/logs?level=INFO&limit=10', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'logs' in data

    def test_stream_logs(self, client, auth_headers):
        response = client.get('/api/logs/stream', headers=auth_headers)
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'


class TestHealthAPI:
    """Test health API endpoints."""

    def test_get_health(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['version'] == '3.0.0'
        assert 'uptime_seconds' in data
        assert 'tasks' in data
        assert 'queue_backlog' in data

    def test_task_status_update(self, client):
        update_task_status('anomaly_detection', 'running',
                          last_run='2026-02-10T00:00:00',
                          next_run='2026-02-10T01:00:00')
        response = client.get('/api/health')
        data = response.get_json()
        assert data['tasks']['anomaly_detection']['status'] == 'running'
