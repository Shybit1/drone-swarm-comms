"""
src/detm_controller.py

Dynamic Event-Triggered Mechanism (DETM) Controller

Implements sparse communication for bandwidth-constrained swarms:
- Transmit ONLY when state change exceeds adaptive threshold
- Exponentially decaying threshold η_i(t)
- Per-drone configurable parameters
- Logging of trigger decisions
"""

import math
from dataclasses import dataclass
from typing import Tuple, List, Optional
from constants import (
    DETM_ETA0, DETM_LAMBDA, DETM_MIN_ETA, vector_norm_l2, vector_norm_linf
)
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# DETM STATE
# ============================================================================

@dataclass
class DetmState:
    """Current DETM state for a drone."""
    drone_id: int
    eta0: float                # Initial threshold
    lambda_decay: float        # Exponential decay rate
    norm_type: str            # "l2" or "linf"
    
    # Last transmitted state
    last_transmitted_state: Tuple[float, float, float, float, float, float]  # x,y,z,vx,vy,vz
    last_transmitted_time_us: int
    
    # Current threshold
    current_eta: float
    eta_age_ticks: int
    
    # Statistics
    transmissions_total: int
    triggers_fired: int
    triggers_suppressed: int


# ============================================================================
# DETM TRIGGER LOGIC
# ============================================================================

class DETMController:
    """
    Dynamic Event-Triggered Mechanism
    
    Reduces communication bandwidth by triggering transmissions based on
    state deviation rather than periodic updates.
    
    TRANSMISSION RULE:
        Transmit if ||x(t) - x(t_last)|| > η_i(t)
    
    Where:
        x(t) = [position_x, position_y, position_z, vel_x, vel_y, vel_z]
        η_i(t) = η_0 * exp(-λ * t_since_last_tx)
    
    This ensures:
    - Sparse communication when drone is stationary
    - Guaranteed periodic updates (η decays to near-zero)
    - Smooth stability margin
    
    Attributes:
        states: Dictionary of drone_id -> DetmState
    """
    
    def __init__(self):
        """Initialize DETM controller."""
        self.states: dict = {}
    
    def register_drone(self, drone_id: int, eta0: float = DETM_ETA0,
                      lambda_decay: float = DETM_LAMBDA,
                      norm_type: str = "l2") -> None:
        """
        Register drone for DETM control.
        
        Args:
            drone_id: Unique drone identifier
            eta0: Initial trigger threshold
            lambda_decay: Exponential decay rate
            norm_type: Norm for distance calculation ("l2" or "linf")
        """
        self.states[drone_id] = DetmState(
            drone_id=drone_id,
            eta0=eta0,
            lambda_decay=lambda_decay,
            norm_type=norm_type.lower(),
            last_transmitted_state=(0, 0, 0, 0, 0, 0),
            last_transmitted_time_us=0,
            current_eta=eta0,
            eta_age_ticks=0,
            transmissions_total=0,
            triggers_fired=0,
            triggers_suppressed=0
        )
        logger.info(f"DETM registered drone {drone_id}: η0={eta0}, λ={lambda_decay}, norm={norm_type}")
    
    def should_transmit(self, drone_id: int, time_us: int,
                       x: float, y: float, z: float,
                       vx: float, vy: float, vz: float) -> Tuple[bool, float]:
        """
        Check if drone should transmit state update.
        
        Computes:
        1. Current threshold η_i(t) = η0 * exp(-λ * Δt_since_last_tx)
        2. State error ||x(t) - x(t_last)||
        3. Trigger if error > η_i(t)
        
        Args:
            drone_id: Drone identifier
            time_us: Current simulation time (microseconds)
            x, y, z: Position (meters)
            vx, vy, vz: Velocity (m/s)
        
        Returns:
            (should_transmit, current_eta) tuple
        """
        if drone_id not in self.states:
            logger.warning(f"DETM query for unregistered drone {drone_id}")
            return True, DETM_ETA0  # Default to transmit
        
        state = self.states[drone_id]
        current_state = (x, y, z, vx, vy, vz)
        
        # Calculate time since last transmission
        delta_t_us = time_us - state.last_transmitted_time_us
        delta_t_s = delta_t_us / 1e6
        
        # Compute dynamic threshold: η(t) = η0 * exp(-λ * t)
        state.current_eta = state.eta0 * math.exp(-state.lambda_decay * delta_t_s)
        state.current_eta = max(state.current_eta, DETM_MIN_ETA)  # Floor to prevent numerical issues
        
        # Calculate state error (L2 or L∞ norm)
        if state.norm_type == "l2":
            error = self._calculate_error_l2(current_state, state.last_transmitted_state)
        else:  # "linf"
            error = self._calculate_error_linf(current_state, state.last_transmitted_state)
        
        # Trigger decision
        should_tx = error > state.current_eta
        
        if should_tx:
            state.triggers_fired += 1
            logger.debug(
                f"DETM trigger [drone {drone_id}]: "
                f"error={error:.4f} > η={state.current_eta:.4f}"
            )
        else:
            state.triggers_suppressed += 1
        
        return should_tx, state.current_eta
    
    def record_transmission(self, drone_id: int, time_us: int,
                           x: float, y: float, z: float,
                           vx: float, vy: float, vz: float) -> None:
        """
        Record transmission (update last transmitted state).
        
        Called after a message is sent.
        
        Args:
            drone_id: Drone identifier
            time_us: Transmission time (microseconds)
            x, y, z: Position (meters)
            vx, vy, vz: Velocity (m/s)
        """
        if drone_id not in self.states:
            return
        
        state = self.states[drone_id]
        state.last_transmitted_state = (x, y, z, vx, vy, vz)
        state.last_transmitted_time_us = time_us
        state.transmissions_total += 1
    
    def get_state(self, drone_id: int) -> Optional[DetmState]:
        """Get DETM state for drone."""
        return self.states.get(drone_id)
    
    def get_statistics(self, drone_id: int) -> dict:
        """
        Get DETM statistics for drone.
        
        Returns:
            Dictionary with transmission stats
        """
        if drone_id not in self.states:
            return {}
        
        state = self.states[drone_id]
        total_decisions = state.triggers_fired + state.triggers_suppressed
        suppress_rate = (state.triggers_suppressed / total_decisions * 100.0) \
                       if total_decisions > 0 else 0.0
        
        return {
            "drone_id": drone_id,
            "transmissions_total": state.transmissions_total,
            "triggers_fired": state.triggers_fired,
            "triggers_suppressed": state.triggers_suppressed,
            "suppression_rate_percent": suppress_rate,
            "current_eta": state.current_eta,
            "eta0": state.eta0,
        }
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    @staticmethod
    def _calculate_error_l2(state_current: Tuple[float, ...],
                           state_last: Tuple[float, ...]) -> float:
        """Calculate L2 norm (Euclidean distance) between states."""
        if len(state_current) != len(state_last):
            return float('inf')
        
        sum_sq = sum((c - l)**2 for c, l in zip(state_current, state_last))
        return math.sqrt(sum_sq)
    
    @staticmethod
    def _calculate_error_linf(state_current: Tuple[float, ...],
                             state_last: Tuple[float, ...]) -> float:
        """Calculate L∞ norm (max absolute difference) between states."""
        if len(state_current) != len(state_last):
            return float('inf')
        
        return max(abs(c - l) for c, l in zip(state_current, state_last))
