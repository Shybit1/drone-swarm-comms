"""
src/physics_engine.py

Master Physics Engine for AeroSyn-Sim

Orchestrates all physics-based simulation:
- Fire propagation
- Channel modeling (RF fading)
- Energy depletion
- Wind effects
- Global state management

This is the AUTHORITATIVE physics source. All agents consume outputs from here.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional
import logging
from pathlib import Path

from constants import (
    SIM_TICK_RATE_HZ, SIM_TICK_PERIOD_S, SIM_TICK_PERIOD_US,
    FIRE_GRID_WIDTH, FIRE_GRID_HEIGHT, FIRE_CELL_SIZE_M
)
from channel_model import ChannelManager, ChannelState
from energy_model import EnergyManager, BatteryState, PayloadState
from fire_simulation import FireSimulation, CellState, FireCell

logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL PHYSICS STATE
# ============================================================================

@dataclass
class DronePosition:
    """Drone position and velocity state."""
    drone_id: int
    x: float                # meters
    y: float                # meters
    z: float                # altitude (meters)
    vx: float               # velocity (m/s)
    vy: float
    vz: float
    heading_deg: float      # heading (degrees)


@dataclass
class PhysicsSnapshot:
    """Complete physics state snapshot at a moment in time."""
    time_us: int
    tick: int
    
    # Drone positions
    drone_positions: Dict[int, DronePosition]
    
    # Fire state
    fire_state: dict
    
    # Channel states (bidirectional links)
    channel_states: Dict[Tuple[int, int], ChannelState]
    
    # Energy states
    energy_states: Dict[int, Tuple[BatteryState, PayloadState]]


# ============================================================================
# PHYSICS ENGINE
# ============================================================================

class PhysicsEngine:
    """
    Master Physics Engine
    
    Manages all physics subsystems:
    1. Fire simulation (cellular automata propagation)
    2. Channel model (RF fading, RSSI, latency)
    3. Energy model (battery and payload tracking)
    4. Wind dynamics
    5. Collision detection
    
    Design principle: All agents query THIS engine, not individual simulators.
    This ensures consistency and avoids state desynchronization.
    
    Attributes:
        fire_sim: FireSimulation instance
        channel_mgr: ChannelManager for RF links
        energy_mgrs: Dictionary of drone ID -> EnergyManager
        wind_speed_ms, wind_direction_deg: Global wind
    """
    
    def __init__(self, num_drones: int = 1, seed: int = 42):
        """
        Initialize physics engine.
        
        Args:
            num_drones: Number of drones in swarm
            seed: RNG seed for reproducible physics
        """
        self.num_drones = num_drones
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        
        # Initialize subsystems
        self.fire_sim = FireSimulation(
            width=FIRE_GRID_WIDTH,
            height=FIRE_GRID_HEIGHT,
            cell_size_m=FIRE_CELL_SIZE_M,
            seed=seed
        )
        
        self.channel_mgr = ChannelManager(seed=seed)
        
        # Energy managers for each drone
        self.energy_mgrs: Dict[int, EnergyManager] = {}
        for drone_id in range(1, num_drones + 1):
            self.energy_mgrs[drone_id] = EnergyManager()
        
        # Drone position tracking
        self.drone_positions: Dict[int, DronePosition] = {}
        for drone_id in range(1, num_drones + 1):
            self.drone_positions[drone_id] = DronePosition(
                drone_id=drone_id, x=0, y=0, z=0,
                vx=0, vy=0, vz=0, heading_deg=0
            )
        
        # Simulation time
        self.ticks = 0
        self.time_us = 0
        
        logger.info(f"PhysicsEngine initialized: {num_drones} drones, seed={seed}")
    
    def step(self) -> PhysicsSnapshot:
        """
        Execute one physics simulation step.
        
        Updates:
        1. Fire propagation
        2. Wind effects
        3. RF channel states (for current drone positions)
        
        Returns:
            PhysicsSnapshot with all current physics state
        """
        self.ticks += 1
        self.time_us += SIM_TICK_PERIOD_US
        
        # Fire propagation
        newly_ignited, suppressed = self.fire_sim.step()
        
        if newly_ignited > 0 or suppressed > 0:
            logger.debug(f"Fire step: +{newly_ignited} ignited, {suppressed} suppressed")
        
        # Update channel states (RF propagation)
        # This depends on current drone positions
        self._update_channel_states()
        
        # Create snapshot
        snapshot = PhysicsSnapshot(
            time_us=self.time_us,
            tick=self.ticks,
            drone_positions=self.drone_positions.copy(),
            fire_state=self.fire_sim.get_fire_state(),
            channel_states=self.channel_mgr.get_all_link_states(),
            energy_states={
                drone_id: self.energy_mgrs[drone_id].get_energy_state()
                for drone_id in self.energy_mgrs.keys()
            }
        )
        
        return snapshot
    
    def update_drone_position(self, drone_id: int, x: float, y: float, z: float,
                             vx: float = 0, vy: float = 0, vz: float = 0,
                             heading_deg: float = 0) -> None:
        """
        Update drone position in physics engine.
        
        Called by drone nodes to report current state.
        
        Args:
            drone_id: Drone identifier
            x, y, z: Position (meters)
            vx, vy, vz: Velocity (m/s)
            heading_deg: Heading (degrees)
        """
        if drone_id not in self.drone_positions:
            logger.warning(f"Unknown drone_id: {drone_id}")
            return
        
        pos = self.drone_positions[drone_id]
        pos.x = x
        pos.y = y
        pos.z = z
        pos.vx = vx
        pos.vy = vy
        pos.vz = vz
        pos.heading_deg = heading_deg
    
    def get_drone_position(self, drone_id: int) -> DronePosition:
        """Get drone position state."""
        return self.drone_positions.get(drone_id)
    
    # ========================================================================
    # FIRE SIMULATION INTERFACE
    # ========================================================================
    
    def ignite_fire(self, grid_x: int, grid_y: int, intensity: float = 1.0) -> bool:
        """Ignite fire at grid cell."""
        return self.fire_sim.ignite(grid_x, grid_y, intensity)
    
    def ignite_fire_world(self, world_x: float, world_y: float,
                         intensity: float = 1.0) -> bool:
        """Ignite fire at world coordinates (converts to grid)."""
        grid_x = int(world_x / FIRE_CELL_SIZE_M)
        grid_y = int(world_y / FIRE_CELL_SIZE_M)
        return self.ignite_fire(grid_x, grid_y, intensity)
    
    def suppress_fire(self, grid_x: int, grid_y: int, strength: float) -> float:
        """Suppress fire at grid cell."""
        return self.fire_sim.suppress(grid_x, grid_y, strength)
    
    def suppress_fire_world(self, world_x: float, world_y: float,
                           strength: float) -> float:
        """Suppress fire at world coordinates."""
        grid_x = int(world_x / FIRE_CELL_SIZE_M)
        grid_y = int(world_y / FIRE_CELL_SIZE_M)
        return self.suppress_fire(grid_x, grid_y, strength)
    
    def get_fire_state(self) -> dict:
        """Get global fire state."""
        return self.fire_sim.get_fire_state()
    
    def get_fire_cell(self, grid_x: int, grid_y: int) -> FireCell:
        """Get fire cell state."""
        return self.fire_sim.get_cell(grid_x, grid_y)
    
    def detect_fire(self, drone_id: int, sensor_range_m: float) \
            -> Tuple[bool, float]:
        """
        Detect fire from drone position.
        
        Args:
            drone_id: Drone ID
            sensor_range_m: Detection range (meters)
        
        Returns:
            (fire_detected, intensity) tuple
        """
        pos = self.get_drone_position(drone_id)
        if pos is None:
            return False, 0.0
        
        return self.fire_sim.detect_fire(pos.x, pos.y, sensor_range_m)
    
    def set_wind(self, speed_ms: float, direction_deg: float) -> None:
        """Update wind parameters."""
        self.fire_sim.wind_model.set_wind(speed_ms, direction_deg)
        logger.info(f"Wind updated: {speed_ms} m/s @ {direction_deg}°")
    
    # ========================================================================
    # CHANNEL MODEL INTERFACE
    # ========================================================================
    
    def get_channel_state(self, sender_id: int,
                         receiver_id: int) -> Optional[ChannelState]:
        """Get RF channel state between two drones."""
        return self.channel_mgr.get_channel_state(sender_id, receiver_id)
    
    def is_link_connected(self, sender_id: int, receiver_id: int) -> bool:
        """Check if RF link is active."""
        return self.channel_mgr.is_link_connected(sender_id, receiver_id)
    
    # ========================================================================
    # ENERGY MODEL INTERFACE
    # ========================================================================
    
    def get_battery_state(self, drone_id: int) -> BatteryState:
        """Get battery state for drone."""
        if drone_id not in self.energy_mgrs:
            return None
        return self.energy_mgrs[drone_id].battery.get_state()
    
    def get_payload_state(self, drone_id: int) -> PayloadState:
        """Get payload state for drone."""
        if drone_id not in self.energy_mgrs:
            return None
        return self.energy_mgrs[drone_id].payload.get_state()
    
    def should_rtl_override(self, drone_id: int) -> Tuple[bool, str]:
        """
        Check if drone should trigger RTL override.
        
        Returns:
            (should_rtl, reason) tuple
        """
        if drone_id not in self.energy_mgrs:
            return False, "none"
        return self.energy_mgrs[drone_id].should_rtl_override()
    
    def update_drone_energy(self, drone_id: int, distance_m: float,
                           hover_time_s: float,
                           aggressiveness: float = 1.0) -> float:
        """
        Update drone energy for flight segment.
        
        Args:
            drone_id: Drone ID
            distance_m: Distance flown (meters)
            hover_time_s: Time hovering (seconds)
            aggressiveness: Maneuver aggressiveness (1.0=normal)
        
        Returns:
            Energy consumed (Wh)
        """
        if drone_id not in self.energy_mgrs:
            return 0.0
        return self.energy_mgrs[drone_id].update_flight(
            distance_m, hover_time_s, aggressiveness
        )
    
    def suppress_with_payload(self, drone_id: int,
                             strength: float) -> Tuple[float, float]:
        """
        Execute fire suppression action (uses drone payload).
        
        Args:
            drone_id: Drone ID
            strength: Suppression strength (0-1)
        
        Returns:
            (payload_consumed, energy_cost) tuple
        """
        if drone_id not in self.energy_mgrs:
            return 0.0, 0.0
        return self.energy_mgrs[drone_id].update_suppression(strength)
    
    def dock_drone(self, drone_id: int) -> None:
        """Dock drone (refill battery and payload)."""
        if drone_id not in self.energy_mgrs:
            return
        self.energy_mgrs[drone_id].dock()
    
    # ========================================================================
    # GLOBAL STATE QUERIES
    # ========================================================================
    
    def get_distance_between_drones(self, drone_id_1: int,
                                    drone_id_2: int) -> float:
        """
        Calculate distance between two drones (horizontal, 2D).
        
        Args:
            drone_id_1, drone_id_2: Drone IDs
        
        Returns:
            Distance in meters (or None if either drone not found)
        """
        pos1 = self.get_drone_position(drone_id_1)
        pos2 = self.get_drone_position(drone_id_2)
        
        if pos1 is None or pos2 is None:
            return None
        
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        return (dx**2 + dy**2)**0.5
    
    def get_distance_3d(self, drone_id_1: int, drone_id_2: int) -> float:
        """
        Calculate 3D distance between two drones.
        
        Args:
            drone_id_1, drone_id_2: Drone IDs
        
        Returns:
            Distance in meters (or None if either drone not found)
        """
        pos1 = self.get_drone_position(drone_id_1)
        pos2 = self.get_drone_position(drone_id_2)
        
        if pos1 is None or pos2 is None:
            return None
        
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        dz = pos2.z - pos1.z
        return (dx**2 + dy**2 + dz**2)**0.5
    
    def get_time(self) -> Tuple[int, int]:
        """
        Get current simulation time.
        
        Returns:
            (ticks, time_us) tuple
        """
        return self.ticks, self.time_us
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    def _update_channel_states(self) -> None:
        """
        Update all RF channel states based on current drone positions.
        
        Called every physics step. Iterates through all drone pairs and
        updates RSSI, latency, packet loss based on distance.
        """
        for sender_id in range(1, self.num_drones + 1):
            for receiver_id in range(1, self.num_drones + 1):
                if sender_id == receiver_id:
                    continue
                
                distance = self.get_distance_between_drones(sender_id, receiver_id)
                if distance is not None:
                    self.channel_mgr.update_link(sender_id, receiver_id, distance)
    
    def export_state_dict(self) -> dict:
        """
        Export full physics state as dictionary (for logging/serialization).
        
        Returns:
            Dictionary representation of physics state
        """
        return {
            "time_us": self.time_us,
            "tick": self.ticks,
            "num_drones": self.num_drones,
            "fire_state": self.get_fire_state(),
            "drone_positions": {
                drone_id: {
                    "x": pos.x, "y": pos.y, "z": pos.z,
                    "vx": pos.vx, "vy": pos.vy, "vz": pos.vz
                }
                for drone_id, pos in self.drone_positions.items()
            },
            "wind": {
                "speed_ms": self.fire_sim.wind_model.wind_speed_ms,
                "direction_deg": self.fire_sim.wind_model.wind_direction_deg,
            }
        }
