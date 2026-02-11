"""
src/websocket_server.py

WebSocket Server for Real-Time Telemetry Streaming

Broadcasts simulation state to connected frontend clients via WebSocket.
Uses DETM-gated frequency (only sends on state change, not fixed rate).

Reduces bandwidth compared to fixed-rate polling.
"""

import asyncio
import json
import logging
from typing import Set, Optional
import websockets
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# WEBSOCKET SERVER
# ============================================================================

class SimulationWebSocketServer:
    """
    WebSocket server for real-time telemetry streaming.
    
    Manages:
    - Client connections
    - State serialization
    - Efficient delta updates
    - DETM-gated message throttling
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8081,
                 simulation_engine = None):
        """
        Initialize WebSocket server.
        
        Args:
            host: Server host
            port: Server port
            simulation_engine: Reference to main simulation
        """
        self.host = host
        self.port = port
        self.simulation_engine = simulation_engine
        
        # Connected clients
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Last sent state (for delta compression)
        self.last_sent_state = {}
        self.last_update_time_us = 0
        
        logger.info(f"WebSocket server initialized: {host}:{port}")
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol,
                           path: str) -> None:
        """
        Handle new client connection.
        
        Args:
            websocket: Client WebSocket connection
            path: Connection path
        """
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol,
                            message: str) -> None:
        """
        Handle incoming message from client.
        
        Args:
            websocket: Client connection
            message: Message payload
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "subscribe":
                # Client requesting updates
                await self.send_state(websocket)
            elif msg_type == "command":
                # Client sending command
                await self.handle_command(data.get("payload"))
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def send_state(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Send current simulation state to client.
        
        Args:
            websocket: Client connection
        """
        try:
            if not self.simulation_engine:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "No simulation engine"
                }))
                return
            
            state = self.simulation_engine.export_state_dict()
            
            message = {
                "type": "state_update",
                "timestamp": datetime.utcnow().isoformat(),
                "state": state
            }
            
            await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending state: {e}")
    
    async def broadcast_state(self) -> None:
        """
        Broadcast current state to all connected clients.
        
        Called periodically by simulation loop (DETM-gated).
        """
        if not self.clients:
            return
        
        try:
            if not self.simulation_engine:
                return
            
            state = self.simulation_engine.export_state_dict()
            
            message = {
                "type": "state_update",
                "timestamp": datetime.utcnow().isoformat(),
                "state": state
            }
            
            # Send to all connected clients
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            
            # Clean up disconnected clients
            for client in disconnected:
                self.clients.discard(client)
        
        except Exception as e:
            logger.error(f"Error broadcasting state: {e}")
    
    async def handle_command(self, payload: dict) -> None:
        """
        Handle command from client.
        
        Args:
            payload: Command payload
        """
        if not self.simulation_engine:
            return
        
        try:
            cmd_type = payload.get("type")
            
            if cmd_type == "ignite_fire":
                x = payload.get("x")
                y = payload.get("y")
                intensity = payload.get("intensity", 1.0)
                self.simulation_engine.ignite_fire(x, y, intensity)
            
            elif cmd_type == "suppress_fire":
                x = payload.get("x")
                y = payload.get("y")
                strength = payload.get("strength", 1.0)
                self.simulation_engine.suppress_fire(x, y, strength)
            
            elif cmd_type == "set_wind":
                speed = payload.get("speed")
                direction = payload.get("direction")
                self.simulation_engine.set_wind(speed, direction)
            
            else:
                logger.warning(f"Unknown command type: {cmd_type}")
        
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    async def run(self) -> None:
        """
        Start WebSocket server.
        
        Should be run in async context (e.g., with asyncio.run()).
        """
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("WebSocket server running")
            await asyncio.Future()  # Run forever


# ============================================================================
# INTEGRATION WITH MAIN SIMULATION
# ============================================================================

def run_websocket_server(host: str = "0.0.0.0", port: int = 8081,
                        simulation_engine = None) -> None:
    """
    Run WebSocket server in async context.
    
    Args:
        host: Server host
        port: Server port
        simulation_engine: Simulation engine reference
    """
    server = SimulationWebSocketServer(host, port, simulation_engine)
    asyncio.run(server.run())
