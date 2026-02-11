"""
src/api_server.py

REST API Server for AeroSyn-Sim

Provides HTTP endpoints for:
- Simulation control (start, stop, pause)
- Fire ignition/suppression
- Configuration updates
- State queries
- Metrics streaming
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP SETUP
# ============================================================================

class SimulationAPIServer:
    """
    REST API server for simulation control.
    
    Endpoints:
    - GET /api/v1/health
    - GET /api/v1/simulation/state
    - POST /api/v1/simulation/start
    - POST /api/v1/simulation/stop
    - POST /api/v1/simulation/pause
    - GET /api/v1/drones
    - GET /api/v1/drones/{drone_id}
    - POST /api/v1/fire/ignite
    - POST /api/v1/fire/suppress
    - GET /api/v1/fire/state
    - GET /api/v1/metrics
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 simulation_engine = None):
        """
        Initialize API server.
        
        Args:
            host: Server host
            port: Server port
            simulation_engine: Reference to main simulation controller
        """
        self.host = host
        self.port = port
        self.simulation_engine = simulation_engine
        
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Register routes
        self._register_routes()
        
        logger.info(f"API server initialized: {host}:{port}")
    
    def _register_routes(self) -> None:
        """Register all API endpoints."""
        
        @self.app.route('/api/v1/health', methods=['GET'])
        def health():
            """Health check."""
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0"
            }), 200
        
        @self.app.route('/api/v1/simulation/state', methods=['GET'])
        def get_sim_state():
            """Get simulation state."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                state = self.simulation_engine.export_state_dict()
                return jsonify(state), 200
            except Exception as e:
                logger.error(f"Error getting sim state: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/simulation/start', methods=['POST'])
        def start_sim():
            """Start simulation."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                self.simulation_engine.start()
                return jsonify({"status": "started"}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/simulation/stop', methods=['POST'])
        def stop_sim():
            """Stop simulation."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                self.simulation_engine.stop()
                return jsonify({"status": "stopped"}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/drones', methods=['GET'])
        def get_drones():
            """Get all drone states."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                drones = self.simulation_engine.get_all_drone_states()
                return jsonify({"drones": drones}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/drones/<int:drone_id>', methods=['GET'])
        def get_drone(drone_id: int):
            """Get specific drone state."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                state = self.simulation_engine.get_drone_state(drone_id)
                if not state:
                    return jsonify({"error": "Drone not found"}), 404
                return jsonify(state), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/fire/ignite', methods=['POST'])
        def ignite_fire():
            """Ignite fire at coordinates."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                data = request.get_json()
                x = data.get("x")
                y = data.get("y")
                intensity = data.get("intensity", 1.0)
                
                if x is None or y is None:
                    return jsonify({"error": "Missing x or y"}), 400
                
                success = self.simulation_engine.ignite_fire(x, y, intensity)
                
                if success:
                    return jsonify({"status": "fire_ignited", "x": x, "y": y}), 200
                else:
                    return jsonify({"error": "Failed to ignite fire"}), 500
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/fire/suppress', methods=['POST'])
        def suppress_fire():
            """Suppress fire at coordinates."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                data = request.get_json()
                x = data.get("x")
                y = data.get("y")
                strength = data.get("strength", 1.0)
                
                if x is None or y is None:
                    return jsonify({"error": "Missing x or y"}), 400
                
                reduction = self.simulation_engine.suppress_fire(x, y, strength)
                
                return jsonify({
                    "status": "suppression_applied",
                    "x": x, "y": y,
                    "intensity_reduction": reduction
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/fire/state', methods=['GET'])
        def get_fire_state():
            """Get fire state."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                fire_state = self.simulation_engine.get_fire_state()
                return jsonify(fire_state), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/metrics', methods=['GET'])
        def get_metrics():
            """Get aggregated metrics."""
            if not self.simulation_engine:
                return jsonify({"error": "No simulation engine"}), 500
            
            try:
                metrics = self.simulation_engine.get_metrics()
                return jsonify(metrics), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    def run(self, debug: bool = False) -> None:
        """
        Start API server.
        
        Args:
            debug: Enable Flask debug mode
        """
        logger.info(f"Starting API server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
    
    def get_app(self):
        """Get Flask app (for testing/deployment)."""
        return self.app
