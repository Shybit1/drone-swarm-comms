"""
src/levy_flight.py

Lévy Flight for Autonomous Search

Implements heavy-tailed step-length distribution for efficient exploration
when no fire or pheromone gradient is detected.

Mathematical basis:
- Lévy distribution has infinite mean (long jumps occur)
- Better coverage than Gaussian random walk
- Used by animals in foraging behavior
"""

import numpy as np
import math
from typing import Tuple
from constants import (
    LEVY_ALPHA, LEVY_STEP_SCALE_M, LEVY_ANGULAR_SCALE_DEG
)
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# LEVY FLIGHT GENERATOR
# ============================================================================

class LevyFlightGenerator:
    """
    Lévy Flight Step Generator
    
    Produces steps with heavy-tailed length distribution (power-law tail).
    This enables:
    - Rare long jumps (exploration)
    - Frequent short steps (local search)
    - Better coverage than Gaussian walk
    
    Parameters:
    - α (alpha): Tail exponent (1.0-2.0)
      - α → 2.0: approaches Gaussian (normal random walk)
      - α → 1.0: extreme jumps (Cauchy distribution)
      - typical: 1.5
    
    - β (beta): scale of steps
    
    Implementation uses Mantegna's algorithm:
    X = Z / |Y|^(1/α)
    where Z, Y ~ Normal(0,1)
    """
    
    def __init__(self, alpha: float = LEVY_ALPHA,
                 step_scale_m: float = LEVY_STEP_SCALE_M,
                 angular_scale_deg: float = LEVY_ANGULAR_SCALE_DEG,
                 seed: int = None):
        """
        Initialize Lévy flight generator.
        
        Args:
            alpha: Tail exponent (1.0-2.0)
            step_scale_m: Typical step length (meters)
            angular_scale_deg: Angular randomness (degrees)
            seed: RNG seed
        """
        self.alpha = alpha
        self.step_scale_m = step_scale_m
        self.angular_scale_deg = angular_scale_deg
        self.rng = np.random.RandomState(seed)
        
        # Mantegna parameter
        self.sigma = (
            math.gamma(1 + alpha) * math.sin(math.pi * alpha / 2.0) /
            (math.gamma((1 + alpha) / 2.0) * alpha * (2.0**((alpha - 1.0) / 2.0)))
        )**( 1.0 / alpha)
    
    def generate_step(self, current_heading_deg: float = 0.0) \
            -> Tuple[float, float, float]:
        """
        Generate one Lévy flight step.
        
        Args:
            current_heading_deg: Current heading (for turning)
        
        Returns:
            (delta_x, delta_y, new_heading_deg) tuple
        """
        # Mantegna algorithm for Lévy step
        u = self.rng.normal(0, self.sigma, size=2)
        v = self.rng.normal(0, 1, size=2)
        step = u / (np.abs(v)**(1.0 / self.alpha))
        
        # Step magnitude and direction
        magnitude = np.linalg.norm(step) * self.step_scale_m
        
        # Random heading change
        heading_delta = self.rng.uniform(
            -self.angular_scale_deg / 2,
            self.angular_scale_deg / 2
        )
        new_heading = (current_heading_deg + heading_delta) % 360.0
        
        # Convert heading to Cartesian displacement
        angle_rad = math.radians(new_heading)
        delta_x = magnitude * math.cos(angle_rad)
        delta_y = magnitude * math.sin(angle_rad)
        
        return delta_x, delta_y, new_heading
    
    def generate_trajectory(self, num_steps: int, start_heading_deg: float = 0.0) \
            -> np.ndarray:
        """
        Generate a Lévy flight trajectory.
        
        Args:
            num_steps: Number of steps
            start_heading_deg: Initial heading
        
        Returns:
            (num_steps, 3) array of [delta_x, delta_y, heading]
        """
        trajectory = np.zeros((num_steps, 3))
        current_heading = start_heading_deg
        
        for i in range(num_steps):
            dx, dy, heading = self.generate_step(current_heading)
            trajectory[i] = [dx, dy, heading]
            current_heading = heading
        
        return trajectory
    
    def estimate_return_probability(self, num_steps: int,
                                   max_distance_m: float) -> float:
        """
        Estimate probability of returning within distance after N steps.
        
        For Lévy flights with α < 2, this is a complex calculation.
        We use empirical estimation via sampling.
        
        Args:
            num_steps: Number of steps
            max_distance_m: Max distance threshold
        
        Returns:
            Probability (0-1)
        """
        # Sample multiple trajectories
        num_samples = 100
        returns = 0
        
        for _ in range(num_samples):
            trajectory = self.generate_trajectory(num_steps)
            total_x = trajectory[:, 0].sum()
            total_y = trajectory[:, 1].sum()
            distance = math.sqrt(total_x**2 + total_y**2)
            
            if distance < max_distance_m:
                returns += 1
        
        return returns / num_samples
    
    def set_parameters(self, alpha: float = None,
                      step_scale_m: float = None,
                      angular_scale_deg: float = None) -> None:
        """Update Lévy flight parameters."""
        if alpha is not None:
            self.alpha = alpha
            # Recalculate sigma
            self.sigma = (
                math.gamma(1 + alpha) * math.sin(math.pi * alpha / 2.0) /
                (math.gamma((1 + alpha) / 2.0) * alpha * (2.0**((alpha - 1.0) / 2.0)))
            )**(1.0 / alpha)
        
        if step_scale_m is not None:
            self.step_scale_m = step_scale_m
        
        if angular_scale_deg is not None:
            self.angular_scale_deg = angular_scale_deg
        
        logger.info(
            f"Lévy flight params: α={self.alpha}, scale={self.step_scale_m}m, "
            f"angular={self.angular_scale_deg}°"
        )


# ============================================================================
# SEARCH BEHAVIOR
# ============================================================================

class SearchBehavior:
    """
    Search behavior using Lévy flight.
    
    Encapsulates the logic for drone-level search:
    - Generate waypoints using Lévy flight
    - Track current position and heading
    - Provide next waypoint on demand
    """
    
    def __init__(self, start_x: float = 0.0, start_y: float = 0.0,
                 levy_gen: LevyFlightGenerator = None):
        """
        Initialize search behavior.
        
        Args:
            start_x, start_y: Starting position
            levy_gen: Lévy flight generator (creates new if None)
        """
        self.x = start_x
        self.y = start_y
        self.heading_deg = 0.0
        
        self.levy_gen = levy_gen or LevyFlightGenerator()
        self.waypoint_queue: list = []
        self.current_step = 0
    
    def generate_search_plan(self, num_steps: int = 10) -> None:
        """
        Generate search waypoints using Lévy flight.
        
        Args:
            num_steps: Number of steps to plan
        """
        trajectory = self.levy_gen.generate_trajectory(num_steps, self.heading_deg)
        
        self.waypoint_queue = []
        for i, (dx, dy, heading) in enumerate(trajectory):
            waypoint_x = self.x + dx
            waypoint_y = self.y + dy
            self.waypoint_queue.append({
                "x": waypoint_x,
                "y": waypoint_y,
                "heading": heading
            })
        
        logger.debug(f"Search plan generated: {num_steps} waypoints")
    
    def get_next_waypoint(self) -> dict:
        """
        Get next search waypoint.
        
        If queue is empty, generate new plan.
        
        Returns:
            {"x": float, "y": float, "heading": float} waypoint dict
        """
        if not self.waypoint_queue:
            self.generate_search_plan(num_steps=10)
        
        if self.waypoint_queue:
            waypoint = self.waypoint_queue.pop(0)
            self.x = waypoint["x"]
            self.y = waypoint["y"]
            self.heading_deg = waypoint["heading"]
            self.current_step += 1
            return waypoint
        
        # Fallback: static waypoint
        return {"x": self.x, "y": self.y, "heading": self.heading_deg}
    
    def update_position(self, x: float, y: float, heading_deg: float) -> None:
        """Update search behavior with actual position."""
        self.x = x
        self.y = y
        self.heading_deg = heading_deg
