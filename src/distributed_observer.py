"""
src/distributed_observer.py

Distributed Observer for Formation Control

Estimates neighbor states between DETM updates to prevent formation collisions
under communication delays and packet loss.

Each drone maintains estimates of its neighbors' states and uses these
estimates for local collision avoidance and formation maintenance.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List
from constants import vector_norm_l2, clamp
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# OBSERVER STATE
# ============================================================================

@dataclass
class NeighborEstimate:
    """Estimated state of a neighbor drone."""
    neighbor_id: int
    estimated_x: float          # Estimated position
    estimated_y: float
    estimated_z: float
    estimated_vx: float        # Estimated velocity
    estimated_vy: float
    estimated_vz: float
    estimate_time_us: int       # Time of last update
    estimate_age_ticks: int     # Ticks since update
    estimate_confidence: float  # 0-1 confidence level
    
    # For velocity-based prediction
    velocity_model_stale: bool  # True if using constant velocity assumption


@dataclass
class LocalizationObserverState:
    """Local observer state for a drone."""
    drone_id: int
    max_latency_ticks: int      # Maximum acceptable latency before degrading confidence
    constant_velocity_timeout_ticks: int  # Ticks to use constant velocity assumption
    confidence_decay_rate: float  # Confidence decay per tick without update
    neighbors: Dict[int, NeighborEstimate] = field(default_factory=dict)


# ============================================================================
# DISTRIBUTED OBSERVER
# ============================================================================

class DistributedObserver:
    """
    Distributed Observer for Swarm Formation Control
    
    Estimates neighbor states between DETM updates using:
    1. Last received state + constant velocity model
    2. Graceful confidence degradation with age
    3. Hard timeout → assume stationary
    
    This prevents formation collisions even with:
    - Sparse DETM-gated communication
    - RF packet loss
    - Time-varying network delays
    
    DESIGN PRINCIPLE:
    "Assume neighbor continues at last known velocity until proven otherwise."
    
    Attributes:
        local_states: Dictionary of drone_id -> LocalizationObserverState
    """
    
    def __init__(self, max_latency_ms: int = 500,
                 constant_velocity_timeout_ms: int = 200,
                 confidence_decay_factor: float = 0.95):
        """
        Initialize distributed observer.
        
        Args:
            max_latency_ms: Maximum acceptable latency
            constant_velocity_timeout_ms: Time to use constant velocity
            confidence_decay_factor: Confidence decay per tick
        """
        self.local_states: Dict[int, LocalizationObserverState] = {}
        self.max_latency_ticks = int(max_latency_ms / 10)  # Assuming 100Hz tick = 10ms
        self.constant_velocity_timeout_ticks = int(constant_velocity_timeout_ms / 10)
        self.confidence_decay_factor = confidence_decay_factor
    
    def register_drone(self, drone_id: int, neighbors: List[int]) -> None:
        """
        Register drone for observation.
        
        Args:
            drone_id: Drone identifier
            neighbors: List of neighbor drone IDs to track
        """
        self.local_states[drone_id] = LocalizationObserverState(
            drone_id=drone_id,
            max_latency_ticks=self.max_latency_ticks,
            constant_velocity_timeout_ticks=self.constant_velocity_timeout_ticks,
            confidence_decay_rate=self.confidence_decay_factor,
        )
        
        for neighbor_id in neighbors:
            self.local_states[drone_id].neighbors[neighbor_id] = NeighborEstimate(
                neighbor_id=neighbor_id,
                estimated_x=0, estimated_y=0, estimated_z=0,
                estimated_vx=0, estimated_vy=0, estimated_vz=0,
                estimate_time_us=0,
                estimate_age_ticks=0,
                estimate_confidence=0.0,
                velocity_model_stale=True
            )
        
        logger.info(f"Observer registered drone {drone_id} with {len(neighbors)} neighbors")
    
    def update_neighbor(self, observer_drone_id: int, neighbor_id: int,
                       time_us: int,
                       x: float, y: float, z: float,
                       vx: float, vy: float, vz: float) -> None:
        """
        Update estimate when receiving DETM message from neighbor.
        
        Args:
            observer_drone_id: Drone doing the observing
            neighbor_id: Neighbor being observed
            time_us: Timestamp of received state
            x, y, z: Neighbor position
            vx, vy, vz: Neighbor velocity
        """
        if observer_drone_id not in self.local_states:
            return
        
        observer = self.local_states[observer_drone_id]
        if neighbor_id not in observer.neighbors:
            # Auto-register unknown neighbor
            observer.neighbors[neighbor_id] = NeighborEstimate(
                neighbor_id=neighbor_id,
                estimated_x=x, estimated_y=y, estimated_z=z,
                estimated_vx=vx, estimated_vy=vy, estimated_vz=vz,
                estimate_time_us=time_us,
                estimate_age_ticks=0,
                estimate_confidence=1.0,
                velocity_model_stale=False
            )
            logger.debug(f"Auto-registered neighbor {neighbor_id} to drone {observer_drone_id}")
            return
        
        # Update existing neighbor estimate
        estimate = observer.neighbors[neighbor_id]
        estimate.estimated_x = x
        estimate.estimated_y = y
        estimate.estimated_z = z
        estimate.estimated_vx = vx
        estimate.estimated_vy = vy
        estimate.estimated_vz = vz
        estimate.estimate_time_us = time_us
        estimate.estimate_age_ticks = 0
        estimate.estimate_confidence = 1.0  # Confidence resets to max on update
        estimate.velocity_model_stale = False
    
    def predict_neighbor_state(self, observer_drone_id: int,
                              neighbor_id: int,
                              current_time_us: int) -> Optional[Tuple[float, float, float, float]]:
        """
        Predict neighbor's current state using constant velocity model.
        
        Updates age and confidence, returns predicted position + confidence.
        
        Args:
            observer_drone_id: Drone doing the predicting
            neighbor_id: Neighbor being predicted
            current_time_us: Current simulation time
        
        Returns:
            (x, y, z, confidence) tuple, or None if neighbor not found
        """
        if observer_drone_id not in self.local_states:
            return None
        
        observer = self.local_states[observer_drone_id]
        if neighbor_id not in observer.neighbors:
            return None
        
        estimate = observer.neighbors[neighbor_id]
        
        # Age the estimate
        estimate.estimate_age_ticks += 1
        
        # Decay confidence with age
        # Confidence = initial * decay_factor^age
        max_age_ticks = 100  # ~1 second at 100Hz
        age_ratio = min(estimate.estimate_age_ticks / max_age_ticks, 1.0)
        estimate.estimate_confidence = (1.0 - 0.8 * age_ratio)  # 1.0 → 0.2 over 100 ticks
        
        # Check if latency timeout exceeded
        if estimate.estimate_age_ticks > observer.max_latency_ticks:
            # Use constant velocity model
            if not estimate.velocity_model_stale:
                logger.debug(
                    f"Drone {observer_drone_id}: "
                    f"neighbor {neighbor_id} entering constant velocity model"
                )
                estimate.velocity_model_stale = True
        
        # Check if constant velocity timeout exceeded
        if estimate.estimate_age_ticks > observer.constant_velocity_timeout_ticks:
            # Assume neighbor is stationary
            estimate.estimated_vx = 0
            estimate.estimated_vy = 0
            estimate.estimated_vz = 0
        
        # Predict position based on velocity
        time_delta_s = (current_time_us - estimate.estimate_time_us) / 1e6
        predicted_x = estimate.estimated_x + estimate.estimated_vx * time_delta_s
        predicted_y = estimate.estimated_y + estimate.estimated_vy * time_delta_s
        predicted_z = estimate.estimated_z + estimate.estimated_vz * time_delta_s
        
        return (predicted_x, predicted_y, predicted_z, estimate.estimate_confidence)
    
    def get_separation_to_neighbor(self, observer_drone_id: int,
                                  neighbor_id: int,
                                  current_time_us: int,
                                  drone_x: float, drone_y: float, drone_z: float) -> Optional[float]:
        """
        Calculate current separation to neighbor (using estimate).
        
        Args:
            observer_drone_id: Drone position
            neighbor_id: Neighbor being checked
            current_time_us: Current time
            drone_x, drone_y, drone_z: Observer's current position
        
        Returns:
            3D distance in meters, or None if prediction fails
        """
        pred = self.predict_neighbor_state(observer_drone_id, neighbor_id, current_time_us)
        if pred is None:
            return None
        
        pred_x, pred_y, pred_z, _ = pred
        
        dx = pred_x - drone_x
        dy = pred_y - drone_y
        dz = pred_z - drone_z
        
        return math.sqrt(dx**2 + dy**2 + dz**2)
    
    def check_collision_risk(self, observer_drone_id: int,
                            current_time_us: int,
                            drone_x: float, drone_y: float, drone_z: float,
                            min_separation_m: float = 5.0) -> List[Tuple[int, float]]:
        """
        Check for collision risk with neighbors.
        
        Returns list of (neighbor_id, separation_m) for drones too close.
        
        Args:
            observer_drone_id: Drone checking
            current_time_us: Current time
            drone_x, drone_y, drone_z: Observer's position
            min_separation_m: Minimum safe separation
        
        Returns:
            List of (neighbor_id, separation) tuples for neighbors within risk threshold
        """
        if observer_drone_id not in self.local_states:
            return []
        
        observer = self.local_states[observer_drone_id]
        risky_neighbors = []
        
        for neighbor_id, estimate in observer.neighbors.items():
            separation = self.get_separation_to_neighbor(
                observer_drone_id, neighbor_id, current_time_us,
                drone_x, drone_y, drone_z
            )
            
            if separation is not None and separation < min_separation_m:
                risky_neighbors.append((neighbor_id, separation))
        
        return risky_neighbors
    
    def get_observer_state(self, drone_id: int) -> Optional[LocalizationObserverState]:
        """Get full observer state for drone."""
        return self.local_states.get(drone_id)
    
    def step(self) -> None:
        """
        Execute one observer step (age estimates, decay confidence).
        
        Called every tick by main simulation loop.
        """
        for observer in self.local_states.values():
            for estimate in observer.neighbors.values():
                # Estimate aging is handled in predict_neighbor_state
                pass
