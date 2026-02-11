"""
src/drone_node.py

Individual Drone Agent Node

Core autonomy logic for a single drone. Integrates:
- DETM communication gating
- Energy management
- Fire detection and suppression
- Formation/search behaviors
- Distributed observer for formation safety
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional
from enum import IntEnum
import logging

from constants import (
    DroneState, DroneType, SIM_TICK_PERIOD_S,
    BATTERY_MIN_PERCENT, MAX_PAYLOAD_UNITS
)
from physics_engine import PhysicsEngine
from detm_controller import DETMController
from distributed_observer import DistributedObserver
from energy_model import EnergyManager

logger = logging.getLogger(__name__)

# ============================================================================
# DRONE NODE
# ============================================================================

class DroneNode:
    """
    Individual Autonomous Drone Agent
    
    Manages a single drone's:
    - Flight state (position, velocity, battery)
    - Behavior state machine (Search, Suppress, Return, Idle)
    - Energy constraints and overrides
    - Communication via DETM
    - Formation safety via distributed observer
    - Fire detection and suppression
    
    Attributes:
        drone_id: Unique identifier (1-indexed)
        drone_type: LEADER or FOLLOWER role
        physics_engine: Shared physics engine reference
        detm_controller: DETM gating for communications
        observer: Distributed observer for formation safety
        energy_manager: Battery and payload tracking
    """
    
    def __init__(self, drone_id: int, drone_type: DroneType,
                 physics_engine: PhysicsEngine,
                 detm_controller: DETMController,
                 observer: DistributedObserver,
                 home_x: float = 0.0, home_y: float = 0.0, home_z: float = 0.0):
        """
        Initialize drone agent.
        
        Args:
            drone_id: Unique drone ID (1-indexed)
            drone_type: LEADER or FOLLOWER
            physics_engine: Shared physics engine
            detm_controller: Shared DETM controller
            observer: Shared distributed observer
            home_x, home_y, home_z: Home/dock position
        """
        self.drone_id = drone_id
        self.drone_type = drone_type
        self.physics_engine = physics_engine
        self.detm_controller = detm_controller
        self.observer = observer
        
        # Register with DETM
        self.detm_controller.register_drone(drone_id)
        
        # Energy management
        self.energy_manager = energy_manager = physics_engine.energy_mgrs[drone_id]
        
        # Flight state
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.heading_deg = 0.0
        
        # Home position (for RTL)
        self.home_x = home_x
        self.home_y = home_y
        self.home_z = home_z
        
        # Behavior state
        self.state = DroneState.IDLE
        self.state_ticks = 0
        
        # Neighbor tracking (for formation)
        self.neighbor_ids: List[int] = []  # Will be set based on topology
        
        # Fire detection
        self.fire_detected_count = 0
        self.fire_suppression_count = 0
        self.sensor_range_m = 50.0
        
        # Metrics
        self.total_distance_m = 0.0
        self.time_in_search_us = 0
        self.time_in_suppress_us = 0
        self.time_in_rtl_us = 0
        
        logger.info(f"Drone {drone_id} initialized as {drone_type.name}")
    
    def set_neighbors(self, neighbor_ids: List[int]) -> None:
        """
        Set neighbor drones for formation coordination.
        
        Args:
            neighbor_ids: List of neighbor drone IDs
        """
        self.neighbor_ids = neighbor_ids
        self.observer.register_drone(self.drone_id, neighbor_ids)
        logger.info(f"Drone {self.drone_id} neighbors: {neighbor_ids}")
    
    def update_position(self, x: float, y: float, z: float,
                       vx: float, vy: float, vz: float,
                       heading_deg: float) -> None:
        """
        Update drone position (from SITL/simulator).
        
        Args:
            x, y, z: Position (meters)
            vx, vy, vz: Velocity (m/s)
            heading_deg: Heading (degrees)
        """
        # Calculate distance traveled since last update
        dx = x - self.x
        dy = y - self.y
        distance = (dx**2 + dy**2)**0.5
        self.total_distance_m += distance
        
        # Update state
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.heading_deg = heading_deg
        
        # Update physics engine
        self.physics_engine.update_drone_position(
            self.drone_id, x, y, z, vx, vy, vz, heading_deg
        )
    
    def step(self, time_us: int) -> dict:
        """
        Execute one agent logic step.
        
        Implements:
        1. Check RTL override (battery critical, payload empty)
        2. Detect fire in sensor range
        3. State machine transitions
        4. DETM transmission decision
        5. Energy accounting
        
        Args:
            time_us: Current simulation time (microseconds)
        
        Returns:
            Telemetry dictionary for transmission (if DETM triggered)
        """
        self.state_ticks += 1
        
        # ====================================================================
        # 1. HARD OVERRIDES (RTL if critical)
        # ====================================================================
        
        should_rtl, rtl_reason = self.physics_engine.should_rtl_override(self.drone_id)
        
        if should_rtl and self.state != DroneState.RETURN_TO_LAUNCH:
            logger.warning(f"Drone {self.drone_id} RTL override: {rtl_reason}")
            self.state = DroneState.RETURN_TO_LAUNCH
            self.state_ticks = 0
        
        # ====================================================================
        # 2. FIRE DETECTION
        # ====================================================================
        
        fire_detected, fire_intensity = self.physics_engine.detect_fire(
            self.drone_id, self.sensor_range_m
        )
        
        if fire_detected and self.state == DroneState.SEARCH:
            logger.info(f"Drone {self.drone_id} detected fire (intensity={fire_intensity:.2f})")
            self.state = DroneState.SUPPRESS
            self.state_ticks = 0
            self.fire_detected_count += 1
        
        # ====================================================================
        # 3. STATE MACHINE
        # ====================================================================
        
        if self.state == DroneState.IDLE:
            self._step_idle(time_us)
        elif self.state == DroneState.SEARCH:
            self._step_search(time_us)
        elif self.state == DroneState.SUPPRESS:
            self._step_suppress(time_us, fire_intensity)
        elif self.state == DroneState.RETURN_TO_LAUNCH:
            self._step_rtl(time_us)
        elif self.state == DroneState.FORMATION:
            self._step_formation(time_us)
        
        # ====================================================================
        # 4. FORMATION SAFETY (DISTRIBUTED OBSERVER)
        # ====================================================================
        
        self._check_collision_risk(time_us)
        
        # ====================================================================
        # 5. DETM TRANSMISSION DECISION
        # ====================================================================
        
        should_tx, eta = self.detm_controller.should_transmit(
            self.drone_id, time_us, self.x, self.y, self.z, self.vx, self.vy, self.vz
        )
        
        telemetry = None
        if should_tx:
            # Record transmission
            self.detm_controller.record_transmission(
                self.drone_id, time_us, self.x, self.y, self.z, self.vx, self.vy, self.vz
            )
            
            # Build telemetry message
            battery_state = self.physics_engine.get_battery_state(self.drone_id)
            payload_state = self.physics_engine.get_payload_state(self.drone_id)
            
            telemetry = {
                "drone_id": self.drone_id,
                "timestamp_us": time_us,
                "position": {"x": self.x, "y": self.y, "z": self.z},
                "velocity": {"vx": self.vx, "vy": self.vy, "vz": self.vz},
                "battery_percent": battery_state.battery_percent,
                "payload_remaining": payload_state.payload_units,
                "state": self.state.value,
                "fire_detected": fire_detected,
                "fire_intensity": fire_intensity,
                "rssi_dbm": self._get_link_quality(),
            }
        
        return telemetry
    
    # ========================================================================
    # STATE MACHINE IMPLEMENTATIONS
    # ========================================================================
    
    def _step_idle(self, time_us: int) -> None:
        """Idle state - waiting for mission."""
        # Could transition to SEARCH if mission is assigned
        pass
    
    def _step_search(self, time_us: int) -> None:
        """Search state - random exploration."""
        # TODO: Integrate with Lévy flight (Phase 4)
        # For now: simple random walk
        import random
        
        if self.state_ticks > 100:  # Every ~1 second at 100Hz
            # Random waypoint
            heading_delta = random.uniform(-30, 30)
            self.heading_deg += heading_delta
            self.heading_deg %= 360
    
    def _step_suppress(self, time_us: int, fire_intensity: float) -> None:
        """Suppress state - attack fire."""
        if fire_intensity <= 0:
            # Fire no longer detectable
            logger.info(f"Drone {self.drone_id} fire suppressed, resuming search")
            self.state = DroneState.SEARCH
            self.state_ticks = 0
            self.fire_suppression_count += 1
            return
        
        # Suppress fire (use payload)
        suppression_strength = min(1.0, fire_intensity)
        payload_consumed, energy_cost = self.physics_engine.suppress_with_payload(
            self.drone_id, suppression_strength
        )
        
        logger.debug(f"Drone {self.drone_id} suppressing (strength={suppression_strength:.2f})")
        
        # Check if payload depleted
        payload_state = self.physics_engine.get_payload_state(self.drone_id)
        if payload_state.empty:
            logger.info(f"Drone {self.drone_id} payload empty, RTL")
            self.state = DroneState.RETURN_TO_LAUNCH
            self.state_ticks = 0
        
        self.time_in_suppress_us += int(SIM_TICK_PERIOD_S * 1e6)
    
    def _step_rtl(self, time_us: int) -> None:
        """Return-to-Launch state."""
        # Navigate to home position
        # TODO: Implement waypoint navigation
        
        # Check if at home
        distance_to_home = (
            (self.x - self.home_x)**2 + 
            (self.y - self.home_y)**2 + 
            (self.z - self.home_z)**2
        )**0.5
        
        if distance_to_home < 5.0:  # 5 meter tolerance
            logger.info(f"Drone {self.drone_id} at home, landing")
            self.physics_engine.dock_drone(self.drone_id)
            self.state = DroneState.IDLE
            self.state_ticks = 0
        
        self.time_in_rtl_us += int(SIM_TICK_PERIOD_S * 1e6)
    
    def _step_formation(self, time_us: int) -> None:
        """Formation state - maintain relative position."""
        # TODO: Implement formation control
        pass
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _check_collision_risk(self, time_us: int) -> None:
        """
        Check for collision risk with neighbors.
        
        Uses distributed observer for formation safety.
        """
        risky = self.observer.check_collision_risk(
            self.drone_id, time_us, self.x, self.y, self.z,
            min_separation_m=10.0
        )
        
        if risky:
            logger.warning(
                f"Drone {self.drone_id} collision risk with: {[n[0] for n in risky]}"
            )
            # TODO: Implement avoidance maneuver
    
    def _get_link_quality(self) -> int:
        """
        Get average RSSI for drone's communication links.
        
        Returns:
            Average RSSI in dBm, or -120 if no links
        """
        total_rssi = 0.0
        count = 0
        
        for receiver_id in range(1, 50):  # Arbitrary upper limit
            if receiver_id == self.drone_id:
                continue
            
            channel_state = self.physics_engine.get_channel_state(self.drone_id, receiver_id)
            if channel_state is not None:
                total_rssi += channel_state.rssi_dbm
                count += 1
        
        if count == 0:
            return -120
        
        return int(total_rssi / count)
    
    def get_telemetry(self) -> dict:
        """
        Get current drone telemetry (for logging/debug).
        
        Returns:
            Dictionary with full drone state
        """
        battery_state = self.physics_engine.get_battery_state(self.drone_id)
        payload_state = self.physics_engine.get_payload_state(self.drone_id)
        
        return {
            "drone_id": self.drone_id,
            "drone_type": self.drone_type.name,
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "velocity": {"vx": self.vx, "vy": self.vy, "vz": self.vz},
            "state": self.state.name,
            "battery_percent": battery_state.battery_percent,
            "payload_remaining": payload_state.payload_units,
            "total_distance_m": self.total_distance_m,
            "fire_detected_count": self.fire_detected_count,
            "fire_suppression_count": self.fire_suppression_count,
        }
