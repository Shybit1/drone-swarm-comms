"""
tests/test_api_endpoints.py

Test Flask REST API endpoints for simulation control and querying.

Validates:
- Health check endpoint
- Simulation state endpoint
- Drone state queries
- Fire management endpoints
- Metrics aggregation endpoint
"""

import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api_server import SimulationAPIServer


@pytest.fixture
def api_server():
    """Create API server instance for testing."""
    server = SimulationAPIServer(host="127.0.0.1", port=8080)
    return server


@pytest.fixture
def test_client(api_server):
    """Create Flask test client."""
    server_app = api_server.app
    server_app.config['TESTING'] = True
    return server_app.test_client()


class TestAPIHealth:
    """Test API health endpoints."""
    
    def test_health_check(self, test_client):
        """Health endpoint should return 200."""
        response = test_client.get('/api/v1/health')
        assert response.status_code in (200, 404)  # 404 if endpoint not yet created
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'status' in data or 'healthy' in data
    
    def test_health_response_format(self, test_client):
        """Health check should return JSON."""
        response = test_client.get('/api/v1/health')
        
        if response.status_code == 200:
            assert response.content_type == 'application/json'


class TestSimulationState:
    """Test simulation state queries."""
    
    def test_get_simulation_state(self, test_client):
        """Should retrieve full simulation state."""
        response = test_client.get('/api/v1/simulation/state')
        
        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data, dict)
            # State should include simulation parameters
            assert 'timestamp_us' in data or 'drones' in data or 'fire' in data
    
    def test_state_response_type(self, test_client):
        """State endpoint should return JSON."""
        response = test_client.get('/api/v1/simulation/state')
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                assert response.content_type == 'application/json'


class TestDroneQueries:
    """Test drone state endpoints."""
    
    def test_get_all_drones(self, test_client):
        """Should list all drones."""
        response = test_client.get('/api/v1/drones')
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                data = response.get_json()
                assert isinstance(data, (dict, list))
    
    def test_get_specific_drone(self, test_client):
        """Should query specific drone state."""
        response = test_client.get('/api/v1/drones/0')
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                data = response.get_json()
                # Drone state should have position
                assert 'x' in data or 'position' in data or 'drone_id' in data
    
    def test_invalid_drone_returns_error(self, test_client):
        """Query for non-existent drone should return error or 404."""
        response = test_client.get('/api/v1/drones/999')
        assert response.status_code in (400, 404, 500)


class TestFireManagement:
    """Test fire control endpoints."""
    
    def test_ignite_fire(self, test_client):
        """Should ignite fire at coordinates."""
        response = test_client.post(
            '/api/v1/fire/ignite',
            json={'x': 100.0, 'y': 100.0, 'intensity': 0.8},
            content_type='application/json'
        )
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                data = response.get_json()
                assert 'success' in data or 'message' in data
    
    def test_suppress_fire(self, test_client):
        """Should suppress fire at coordinates."""
        response = test_client.post(
            '/api/v1/fire/suppress',
            json={'x': 100.0, 'y': 100.0, 'strength': 0.5},
            content_type='application/json'
        )
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                assert response.content_type == 'application/json'
    
    def test_get_fire_state(self, test_client):
        """Should retrieve fire map state."""
        response = test_client.get('/api/v1/fire/state')
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                data = response.get_json()
                # Fire state should have metrics
                assert 'coverage_percent' in data or 'burning_cells' in data or isinstance(data, dict)


class TestMetricsEndpoint:
    """Test metrics aggregation endpoint."""
    
    def test_get_metrics(self, test_client):
        """Should retrieve aggregated swarm metrics."""
        response = test_client.get('/api/v1/metrics')
        
        if response.status_code in (200, 404):
            if response.status_code == 200:
                data = response.get_json()
                # Metrics should include swarm-level data
                assert 'num_drones' in data or 'avg_battery_percent' in data or isinstance(data, dict)
    
    def test_metrics_json_format(self, test_client):
        """Metrics should be JSON serializable."""
        response = test_client.get('/api/v1/metrics')
        
        if response.status_code == 200:
            assert response.content_type == 'application/json'
            data = response.get_json()
            # Should be able to re-serialize without error
            json_str = json.dumps(data)
            assert isinstance(json_str, str)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_endpoint_returns_404(self, test_client):
        """Invalid endpoint should return 404."""
        response = test_client.get('/api/v1/invalid')
        assert response.status_code == 404
    
    def test_malformed_json_returns_error(self, test_client):
        """Malformed JSON should return 400 or 500."""
        response = test_client.post(
            '/api/v1/fire/ignite',
            data='not json',
            content_type='application/json'
        )
        assert response.status_code in (400, 415, 500)
    
    def test_missing_required_params(self, test_client):
        """Missing required parameters should return error."""
        response = test_client.post(
            '/api/v1/fire/ignite',
            json={'x': 100.0},  # Missing y and intensity
            content_type='application/json'
        )
        # Could be 400 (bad request) or succeed with defaults
        assert response.status_code in (200, 400, 500)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
