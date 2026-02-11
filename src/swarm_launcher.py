"""
src/swarm_launcher.py

Master Launch Script for AeroSyn-Sim

Spawns N ArduPilot SITL instances dynamically and coordinates their startup.

ARCHITECTURE:
1. Parse command-line arguments (--leaders, --followers)
2. For each drone i:
   - Calculate port: 14550 + 10*i
   - Launch ArduCopter SITL binary
   - Wait for MAVLink heartbeat
   - Set SYSID_THISMAV = i + 1
   - Bridge to MAVROS (if ROS available)
3. Initialize simulation core (physics, drones, etc.)
4. Start main simulation loop

PORT CALCULATION (STRICT):
  Drone i (0-indexed):
  - MAVLink input: 14550 + 10*i
  - MAVLink output: 14555 + 10*i (input + 5)
  - SITL startup uses --out=udp:127.0.0.1:{output_port}

SYSID ASSIGNMENT:
  - Drone i (0-indexed) → SYSID_THISMAV = i + 1
  - Ensures MAVLink uniqueness
  - Used by GCS and MAVROS identification
"""

import subprocess
import argparse
import time
import signal
import sys
import logging
import threading
from typing import List, Dict, Optional
from pathlib import Path
from config import initialize_config, get_config
from physics_engine import PhysicsEngine
from detm_controller import DETMController
from distributed_observer import DistributedObserver
from comms_manager import CommunicationsManager
from drone_node import DroneNode
from api_server import SimulationAPIServer
from constants import DroneType, SIM_TICK_PERIOD_S

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# SITL PROCESS MANAGEMENT
# ============================================================================

class SITLProcess:
    """Manages a single ArduPilot SITL instance."""
    
    def __init__(self, drone_id: int, port: int, sitl_binary: str,
                 vehicle: str = "ArduCopter", frame: str = "quad"):
        """
        Initialize SITL process.
        
        Args:
            drone_id: Drone identifier (0-indexed)
            port: Base port for this drone
            sitl_binary: Path to sim_vehicle.py
            vehicle: Vehicle type (ArduCopter, ArduPlane, etc.)
            frame: Frame type (quad, hexa, etc.)
        """
        self.drone_id = drone_id
        self.sysid = drone_id + 1  # 1-indexed for SYSID
        self.port = port
        self.sitl_binary = sitl_binary
        self.vehicle = vehicle
        self.frame = frame
        self.process: Optional[subprocess.Popen] = None
        self.started = False
    
    def start(self) -> bool:
        """
        Launch SITL process.
        
        Command format:
        ./Tools/autotest/sim_vehicle.py -v ArduCopter -f quad \\
            -I {drone_id} \\
            --out=udp:127.0.0.1:{output_port}
        
        Returns:
            True if started successfully
        """
        output_port = self.port + 5  # Output port is +5 from base
        
        cmd = [
            str(self.sitl_binary),
            "-v", self.vehicle,
            "-f", self.frame,
            "-I", str(self.drone_id),
            f"--out=udp:127.0.0.1:{output_port}"
        ]
        
        try:
            logger.info(f"Starting SITL for drone {self.sysid}: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self.started = True
            logger.info(f"Drone {self.sysid} SITL PID: {self.process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start SITL for drone {self.sysid}: {e}")
            return False
    
    def stop(self) -> None:
        """Terminate SITL process."""
        if self.process and self.started:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info(f"Drone {self.sysid} SITL terminated")
            except subprocess.TimeoutExpired:
                logger.warning(f"Drone {self.sysid} SITL did not terminate, killing...")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping drone {self.sysid}: {e}")
    
    def is_running(self) -> bool:
        """Check if process is still running."""
        if not self.process:
            return False
        return self.process.poll() is None


# ============================================================================
# SWARM LAUNCHER
# ============================================================================

class SwarmLauncher:
    """
    Master Launcher for Drone Swarm
    
    Orchestrates:
    1. SITL instance spawning
    2. MAVLink parameter configuration
    3. Physics engine initialization
    4. Drone agent initialization
    5. Main simulation loop
    """
    
    def __init__(self, num_leaders: int, num_followers: int):
        """
        Initialize swarm launcher.
        
        Args:
            num_leaders: Number of leader drones
            num_followers: Number of follower drones
        """
        self.num_leaders = num_leaders
        self.num_followers = num_followers
        self.total_drones = num_leaders + num_followers
        
        # Load configuration
        self.config = get_config()
        
        # SITL processes
        self.sitl_processes: Dict[int, SITLProcess] = {}
        
        # Simulation components
        self.physics_engine: Optional[PhysicsEngine] = None
        self.detm_controller: Optional[DETMController] = None
        self.observer: Optional[DistributedObserver] = None
        self.comms_manager: Optional[CommunicationsManager] = None
        self.drone_nodes: Dict[int, DroneNode] = {}
        self.api_server: Optional[SimulationAPIServer] = None
        
        # State
        self.running = False
        self.ticks = 0
        self.time_us = 0
        
        logger.info(
            f"SwarmLauncher initialized: "
            f"{num_leaders} leaders + {num_followers} followers = {self.total_drones} total"
        )
    
    def initialize_simulation(self) -> bool:
        """
        Initialize physics and drone agent subsystems.
        
        Returns:
            True if successful
        """
        try:
            # Initialize physics engine
            self.physics_engine = PhysicsEngine(
                num_drones=self.total_drones,
                seed=self.config.simulation.random_seed
            )
            logger.info("PhysicsEngine initialized")
            
            # Initialize control systems
            self.detm_controller = DETMController()
            self.observer = DistributedObserver()
            logger.info("DETM and observer initialized")
            
            # Initialize communications
            self.comms_manager = CommunicationsManager(
                detm_controller=self.detm_controller,
                physics_engine=self.physics_engine
            )
            logger.info("CommunicationsManager initialized")
            
            # Create drone agents
            for i in range(self.total_drones):
                drone_id = i + 1  # 1-indexed
                
                # Determine drone type
                if i < self.num_leaders:
                    drone_type = DroneType.LEADER
                else:
                    drone_type = DroneType.FOLLOWER
                
                # Create drone node
                drone = DroneNode(
                    drone_id=drone_id,
                    drone_type=drone_type,
                    physics_engine=self.physics_engine,
                    detm_controller=self.detm_controller,
                    observer=self.observer,
                    home_x=self.config.swarm.home_latitude,
                    home_y=self.config.swarm.home_longitude,
                    home_z=self.config.swarm.home_altitude_m
                )
                
                self.drone_nodes[drone_id] = drone
                self.comms_manager.register_drone(drone_id)
                logger.info(f"Drone {drone_id} ({drone_type.name}) agent created")
            
            # Set up neighbor relationships (formation topology)
            # Simple topology: each follower binds to nearest leader
            leader_ids = list(range(1, self.num_leaders + 1))
            for follower_id in range(self.num_leaders + 1, self.total_drones + 1):
                neighbors = leader_ids  # Followers observe leaders
                self.drone_nodes[follower_id].set_neighbors(neighbors)
            
            logger.info("Swarm agents initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Simulation initialization failed: {e}", exc_info=True)
            return False
    
    def launch_sitl_instances(self) -> bool:
        """
        Launch all SITL instances.
        
        Returns:
            True if all launched successfully
        """
        config = self.config
        
        for i in range(self.total_drones):
            drone_id = i
            port = config.swarm.base_port + (config.swarm.sitl_port_stride * i)
            
            sitl = SITLProcess(
                drone_id=drone_id,
                port=port,
                sitl_binary=config.swarm.sitl_binary_path,
                vehicle=config.swarm.sitl_vehicle,
                frame=config.swarm.sitl_frame
            )
            
            if not sitl.start():
                logger.error(f"Failed to start drone {i}")
                return False
            
            self.sitl_processes[drone_id] = sitl
            
            # Small delay between launches
            time.sleep(0.5)
        
        logger.info(f"All {self.total_drones} SITL instances launched")
        
        # Wait for startup
        time.sleep(5)
        
        # Check all running
        for drone_id, sitl in self.sitl_processes.items():
            if not sitl.is_running():
                logger.error(f"Drone {drone_id} SITL crashed after launch")
                return False
        
        return True
    
    def simulation_step(self) -> None:
        """
        Execute one simulation step.
        
        Orchestrates:
        1. Physics updates
        2. Drone agent logic
        3. Communication
        4. Metrics collection
        """
        # Execute physics step
        physics_snapshot = self.physics_engine.step()
        self.ticks = physics_snapshot.tick
        self.time_us = physics_snapshot.time_us
        
        # Update each drone agent
        for drone_id, drone in self.drone_nodes.items():
            # Get drone position from physics (normally from SITL)
            # TODO: Connect to actual MAVProxy/pymavlink
            pos = physics_snapshot.drone_positions.get(drone_id)
            if pos:
                drone.update_position(pos.x, pos.y, pos.z,
                                    pos.vx, pos.vy, pos.vz, pos.heading_deg)
            
            # Execute drone logic
            telemetry = drone.step(self.time_us)
            
            # If DETM triggered, publish telemetry
            if telemetry:
                # TODO: Serialize with Protobuf and send
                pass
    
    def run(self, max_duration_s: int = 3600) -> None:
        """
        Main simulation loop.
        
        Args:
            max_duration_s: Maximum simulation duration
        """
        self.running = True
        start_time = time.time()
        
        logger.info(f"Starting simulation loop (max {max_duration_s}s)")
        
        try:
            while self.running:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > max_duration_s:
                    logger.info(f"Simulation timeout after {elapsed:.1f}s")
                    break
                
                # Execute simulation step
                self.simulation_step()
                
                # Sleep to maintain tick rate
                sleep_time = SIM_TICK_PERIOD_S - (time.time() - start_time - (self.ticks * SIM_TICK_PERIOD_S))
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # Log progress
                if self.ticks % 1000 == 0:
                    logger.info(f"Tick {self.ticks}, sim_time={self.time_us/1e6:.1f}s")
        
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    
    # ========================================================================
    # API SERVER SUPPORT METHODS
    # ========================================================================
    
    def export_state_dict(self) -> dict:
        """Export current simulation state as dictionary."""
        try:
            state = {
                "running": self.running,
                "time_s": self.time_s,
                "drones": self.get_all_drone_states(),
                "fire": self.get_fire_state(),
                "metrics": self.get_metrics()
            }
            return state
        except Exception as e:
            logger.error(f"Error exporting state: {e}")
            return {"error": str(e)}
    
    def get_all_drone_states(self) -> list:
        """Get state of all drones."""
        try:
            states = []
            for agent in self.agents.values():
                state = agent.export_state()
                states.append(state)
            return states
        except Exception as e:
            logger.error(f"Error getting all drone states: {e}")
            return []
    
    def get_drone_state(self, drone_id: int) -> dict:
        """Get state of specific drone."""
        try:
            if drone_id not in self.agents:
                return {"error": f"Drone {drone_id} not found"}
            agent = self.agents[drone_id]
            return agent.export_state()
        except Exception as e:
            logger.error(f"Error getting drone {drone_id} state: {e}")
            return {"error": str(e)}
    
    def ignite_fire(self, x: float, y: float, intensity: float = 1.0) -> bool:
        """Ignite fire at world coordinates."""
        try:
            return self.physics_engine.ignite_fire_world(x, y, intensity)
        except Exception as e:
            logger.error(f"Error igniting fire: {e}")
            return False
    
    def suppress_fire(self, x: float, y: float, strength: float) -> float:
        """Suppress fire at world coordinates."""
        try:
            return self.physics_engine.suppress_fire_world(x, y, strength)
        except Exception as e:
            logger.error(f"Error suppressing fire: {e}")
            return 0.0
    
    def get_fire_state(self) -> dict:
        """Get fire simulation state."""
        try:
            return self.physics_engine.get_fire_state()
        except Exception as e:
            logger.error(f"Error getting fire state: {e}")
            return {"error": str(e)}
    
    def get_metrics(self) -> dict:
        """Get simulation metrics."""
        try:
            return self.metrics_collector.export_metrics()
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {"error": str(e)}

    def shutdown(self) -> None:
        """Shutdown all subsystems."""
        logger.info("Shutting down swarm...")
        
        self.running = False
        
        # Stop all SITL instances
        for drone_id, sitl in self.sitl_processes.items():
            sitl.stop()
        
        logger.info("Swarm shutdown complete")
    
    def signal_handler(self, signum, frame) -> None:
        """Handle SIGINT/SIGTERM."""
        logger.info(f"Received signal {signum}")
        self.shutdown()
        sys.exit(0)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Parse arguments and launch swarm."""
    parser = argparse.ArgumentParser(
        description="Launch AeroSyn drone swarm simulation"
    )
    parser.add_argument("--leaders", type=int, default=3,
                       help="Number of leader drones")
    parser.add_argument("--followers", type=int, default=6,
                       help="Number of follower drones")
    parser.add_argument("--config", type=str, default=None,
                       help="Path to simulation_params.yaml")
    parser.add_argument("--duration", type=int, default=3600,
                       help="Simulation duration (seconds)")
    
    args = parser.parse_args()
    
    # Initialize configuration
    initialize_config(args.config)
    
    # Create launcher
    launcher = SwarmLauncher(args.leaders, args.followers)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, launcher.signal_handler)
    signal.signal(signal.SIGTERM, launcher.signal_handler)
    
    # Initialize simulation
    if not launcher.initialize_simulation():
        logger.error("Failed to initialize simulation")
        sys.exit(1)
    
    # Launch SITL instances
    if not launcher.launch_sitl_instances():
        logger.error("Failed to launch SITL instances")
        launcher.shutdown()
        sys.exit(1)
    
    # Start API server in background thread
    try:
        launcher.api_server = SimulationAPIServer(
            host="0.0.0.0", 
            port=8080,
            simulation_engine=launcher
        )
        api_thread = threading.Thread(target=launcher.api_server.run, daemon=True)
        api_thread.start()
        logger.info("API server started in background thread")
    except Exception as e:
        logger.warning(f"Failed to start API server: {e}")
    
    # Run simulation
    launcher.run(max_duration_s=args.duration)


if __name__ == "__main__":
    main()
