"""
src/stigmergy.py

Stigmergic Coordination via Digital Pheromones

Implements indirect swarm coordination through environmental marking.
When a drone detects fire, it deposits pheromone. Followers sense
the gradient and move toward higher concentrations.
"""

import numpy as np
import math
from typing import Tuple, List
from constants import (
    PHEROMONE_GRID_WIDTH, PHEROMONE_GRID_HEIGHT,
    PHEROMONE_DEPOSIT_STRENGTH, PHEROMONE_DECAY_FACTOR,
    PHEROMONE_GRADIENT_THRESHOLD
)
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# PHEROMONE GRID
# ============================================================================

class PheromoneGrid:
    """
    Digital Pheromone Grid for Swarm Coordination
    
    Models indirect communication via environmental markers:
    - Fire detected → drone deposits pheromone
    - Pheromone decays exponentially
    - Neighbors sense gradient → move toward source
    
    This enables decentralized, stigmergic behavior without
    explicit drone-to-drone communication.
    
    Attributes:
        grid: 2D numpy array of pheromone values (0-1)
        width, height: Grid dimensions
        cell_size_m: Physical size of each cell
    """
    
    def __init__(self, width: int = PHEROMONE_GRID_WIDTH,
                 height: int = PHEROMONE_GRID_HEIGHT,
                 cell_size_m: float = 10.0):
        """
        Initialize pheromone grid.
        
        Args:
            width: Grid width (cells)
            height: Grid height (cells)
            cell_size_m: Physical size per cell (meters)
        """
        self.width = width
        self.height = height
        self.cell_size_m = cell_size_m
        self.grid = np.zeros((height, width), dtype=np.float32)
        self.total_pheromone = 0.0
    
    def deposit(self, world_x: float, world_y: float,
               strength: float = PHEROMONE_DEPOSIT_STRENGTH,
               radius_cells: int = 3) -> None:
        """
        Deposit pheromone at world location.
        
        Deposits in a circular region (Gaussian falloff).
        
        Args:
            world_x, world_y: World coordinates (meters)
            strength: Pheromone strength (0-1)
            radius_cells: Deposition radius (cells)
        """
        # Convert world to grid coordinates
        grid_x = int(world_x / self.cell_size_m)
        grid_y = int(world_y / self.cell_size_m)
        
        if not self._in_bounds(grid_x, grid_y):
            return
        
        # Gaussian deposit pattern
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                cy = grid_y + dy
                cx = grid_x + dx
                
                if not self._in_bounds(cx, cy):
                    continue
                
                # Distance-based falloff
                distance = math.sqrt(dx**2 + dy**2)
                if distance > radius_cells:
                    continue
                
                # Gaussian falloff: exp(-distance^2 / (2*sigma^2))
                sigma = radius_cells / 2.0
                falloff = math.exp(-(distance**2) / (2 * sigma**2))
                deposit_amount = strength * falloff
                
                # Add pheromone (clamped to 1.0)
                self.grid[cy, cx] = min(1.0, self.grid[cy, cx] + deposit_amount)
                self.total_pheromone += deposit_amount
    
    def decay(self, factor: float = PHEROMONE_DECAY_FACTOR) -> None:
        """
        Decay all pheromone.
        
        Args:
            factor: Decay factor (0.95 = 5% loss per step)
        """
        self.grid *= factor
        self.total_pheromone *= factor
    
    def sense(self, world_x: float, world_y: float,
             sensor_range_cells: int = 2) -> float:
        """
        Sense pheromone at location.
        
        Averages over sensor range.
        
        Args:
            world_x, world_y: Sensing location (world coords)
            sensor_range_cells: Range of sensor
        
        Returns:
            Sensed pheromone value (0-1)
        """
        grid_x = int(world_x / self.cell_size_m)
        grid_y = int(world_y / self.cell_size_m)
        
        if not self._in_bounds(grid_x, grid_y):
            return 0.0
        
        # Average pheromone in sensor range
        total = 0.0
        count = 0
        
        for dy in range(-sensor_range_cells, sensor_range_cells + 1):
            for dx in range(-sensor_range_cells, sensor_range_cells + 1):
                cy = grid_y + dy
                cx = grid_x + dx
                
                if self._in_bounds(cx, cy):
                    total += self.grid[cy, cx]
                    count += 1
        
        return (total / count) if count > 0 else 0.0
    
    def sense_gradient(self, world_x: float, world_y: float,
                      sample_distance_m: float = 10.0) \
            -> Tuple[float, float, float]:
        """
        Sense pheromone gradient (direction of increasing pheromone).
        
        Uses central differences to estimate gradient direction.
        
        Args:
            world_x, world_y: Sensing location
            sample_distance_m: Distance for gradient sampling
        
        Returns:
            (gradient_magnitude, heading_deg, confidence) tuple
        """
        # Sample at 4 cardinal directions
        north = self.sense(world_x, world_y + sample_distance_m)
        south = self.sense(world_x, world_y - sample_distance_m)
        east = self.sense(world_x + sample_distance_m, world_y)
        west = self.sense(world_x - sample_distance_m, world_y)
        
        # Gradient components
        grad_x = (east - west) / (2 * sample_distance_m)
        grad_y = (north - south) / (2 * sample_distance_m)
        
        # Gradient magnitude
        magnitude = math.sqrt(grad_x**2 + grad_y**2)
        
        # Gradient direction (heading)
        if magnitude > 0:
            heading_deg = math.degrees(math.atan2(grad_y, grad_x))
            heading_deg = (heading_deg + 90) % 360  # Convert to compass bearing
        else:
            heading_deg = 0.0
        
        # Confidence based on magnitude
        # If magnitude < threshold, gradient is too weak to follow
        confidence = max(0.0, (magnitude - PHEROMONE_GRADIENT_THRESHOLD) / 0.1)
        confidence = min(1.0, confidence)
        
        return magnitude, heading_deg, confidence
    
    def clear(self) -> None:
        """Clear all pheromone."""
        self.grid.fill(0.0)
        self.total_pheromone = 0.0
    
    def get_total(self) -> float:
        """Get total pheromone in grid."""
        return float(self.total_pheromone)
    
    def export_grid(self) -> np.ndarray:
        """Export grid for visualization."""
        return self.grid.copy()
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are in bounds."""
        return 0 <= x < self.width and 0 <= y < self.height


# ============================================================================
# STIGMERGIC BEHAVIOR
# ============================================================================

class StigmergicBehavior:
    """
    Drone behavior based on pheromone sensing.
    
    Switches between:
    - Random search (low pheromone)
    - Gradient climbing (high pheromone gradient)
    - Convergence (near source)
    """
    
    def __init__(self, pheromone_grid: PheromoneGrid):
        """
        Initialize stigmergic behavior.
        
        Args:
            pheromone_grid: Shared pheromone grid
        """
        self.pheromone_grid = pheromone_grid
        self.last_sensed_value = 0.0
        self.gradient_count = 0
    
    def decide_heading(self, drone_x: float, drone_y: float,
                      current_heading_deg: float) -> Tuple[float, str]:
        """
        Decide next heading based on pheromone gradient.
        
        Returns heading and behavior state.
        
        Args:
            drone_x, drone_y: Current position
            current_heading_deg: Current heading
        
        Returns:
            (new_heading_deg, behavior_state) tuple
        """
        # Sense pheromone and gradient
        pheromone_value = self.pheromone_grid.sense(drone_x, drone_y)
        gradient_mag, gradient_heading, confidence = \
            self.pheromone_grid.sense_gradient(drone_x, drone_y)
        
        self.last_sensed_value = pheromone_value
        
        # Behavior decision tree
        if pheromone_value < PHEROMONE_GRADIENT_THRESHOLD:
            # Low pheromone: continue search
            return current_heading_deg, "search"
        
        if confidence > 0.5:
            # Strong gradient: climb it
            self.gradient_count += 1
            return gradient_heading, "climbing"
        
        # Weak gradient: maintain heading
        return current_heading_deg, "searching_locally"
    
    def deposit_marker(self, drone_x: float, drone_y: float,
                      fire_intensity: float) -> None:
        """
        Deposit pheromone when fire detected.
        
        Args:
            drone_x, drone_y: Drone position
            fire_intensity: Fire intensity (0-1)
        """
        strength = PHEROMONE_DEPOSIT_STRENGTH * fire_intensity
        self.pheromone_grid.deposit(drone_x, drone_y, strength, radius_cells=3)
        
        logger.debug(f"Pheromone deposited at ({drone_x}, {drone_y}), strength={strength:.2f}")
