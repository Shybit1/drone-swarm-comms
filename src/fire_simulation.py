"""
src/fire_simulation.py

Fire Propagation Engine (FARSITE-Inspired Model)

Models realistic wildfire dynamics:
- 2D cellular grid representing forest
- Wind-driven directional spread
- Fuel density and moisture effects
- Fire suppression via drone payloads
- Deterministic propagation (seeded RNG)
"""

import numpy as np
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Set
from enum import IntEnum
from constants import (
    FIRE_GRID_WIDTH, FIRE_GRID_HEIGHT, FIRE_CELL_SIZE_M,
    FIRE_SPREAD_RATE_BASE_MPM, FIRE_SPREAD_RATE_WIND_SCALE,
    WIND_SPEED_MS, WIND_DIRECTION_DEG,
    FUEL_MOISTURE_PERCENT, FUEL_DENSITY_FACTOR,
    SUPPRESSION_EFFECTIVENESS, INTENSITY_DECAY_FACTOR,
    FIRE_INTENSITY_THRESHOLD_DETECTABLE, FIRE_INTENSITY_IGNITION,
    SIM_TICK_PERIOD_S
)
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# FIRE CELL STATE
# ============================================================================

class CellState(IntEnum):
    """Fire state of a grid cell."""
    NO_FIRE = 0        # No fire present
    BURNING = 1        # Active fire
    BURNED = 2         # Previously burned
    SUPPRESSED = 3     # Actively suppressed


@dataclass
class FireCell:
    """State of a single fire cell."""
    x: int                      # Grid x coordinate
    y: int                      # Grid y coordinate
    state: CellState            # Current state
    intensity: float            # Burn intensity (0.0 to 1.0)
    fuel_density: float         # Remaining fuel (0.0 to 1.0)
    temperature_k: float        # Temperature (Kelvin)
    ignition_time_us: int       # Time of ignition (microseconds)
    suppression_age_ticks: int  # Ticks since suppression applied
    
    def is_burning(self) -> bool:
        return self.state == CellState.BURNING and self.intensity > 0
    
    def is_detectable(self) -> bool:
        return self.intensity >= FIRE_INTENSITY_THRESHOLD_DETECTABLE


# ============================================================================
# WIND MODEL
# ============================================================================

class WindModel:
    """
    Wind model affecting fire spread direction and rate.
    
    Wind is constant magnitude and direction for simplicity.
    (Real-world fire simulations use spatiotemporal wind fields from weather models)
    
    Attributes:
        wind_speed_ms: Wind speed (m/s)
        wind_direction_deg: Wind direction (degrees, 0=North, 90=East)
    """
    
    def __init__(self, speed_ms: float = WIND_SPEED_MS,
                 direction_deg: float = WIND_DIRECTION_DEG):
        """
        Initialize wind model.
        
        Args:
            speed_ms: Wind speed (m/s)
            direction_deg: Direction (0-360 degrees)
        """
        self.wind_speed_ms = speed_ms
        self.wind_direction_deg = direction_deg % 360.0
    
    def get_wind_vector(self) -> Tuple[float, float]:
        """
        Get wind as (vx, vy) components (m/s).
        
        Coordinate system: x=East, y=North
        Direction 0° = North = (0, 1)
        Direction 90° = East = (1, 0)
        
        Returns:
            (vx, vy) tuple in m/s
        """
        angle_rad = math.radians(90.0 - self.wind_direction_deg)  # Convert to math convention
        vx = self.wind_speed_ms * math.cos(angle_rad)
        vy = self.wind_speed_ms * math.sin(angle_rad)
        return vx, vy
    
    def set_wind(self, speed_ms: float, direction_deg: float) -> None:
        """Update wind parameters."""
        self.wind_speed_ms = max(0.0, speed_ms)
        self.wind_direction_deg = direction_deg % 360.0


# ============================================================================
# FIRE PROPAGATION ENGINE
# ============================================================================

class FireSimulation:
    """
    Fire Propagation Engine
    
    Models wildfire spread using cellular automata with:
    - Distance-based spread (fire spreads to adjacent cells)
    - Wind acceleration (spread faster downwind)
    - Fuel limitation (can't burn without fuel)
    - Suppression mechanism (drone payloads reduce intensity)
    - Deterministic physics (seeded RNG for reproducibility)
    
    Attributes:
        grid: 2D numpy array of FireCell objects
        wind_model: WindModel instance
        time_step_s: Simulation time step (seconds)
    """
    
    def __init__(self, width: int = FIRE_GRID_WIDTH,
                 height: int = FIRE_GRID_HEIGHT,
                 cell_size_m: float = FIRE_CELL_SIZE_M,
                 seed: int = None):
        """
        Initialize fire simulation.
        
        Args:
            width: Grid width (cells)
            height: Grid height (cells)
            cell_size_m: Physical size of each cell (meters)
            seed: RNG seed for deterministic spread
        """
        self.width = width
        self.height = height
        self.cell_size_m = cell_size_m
        self.rng = np.random.RandomState(seed)
        
        # Initialize grid with empty cells
        self.grid = np.empty((height, width), dtype=object)
        for y in range(height):
            for x in range(width):
                self.grid[y, x] = FireCell(
                    x=x, y=y, state=CellState.NO_FIRE, intensity=0.0,
                    fuel_density=FUEL_DENSITY_FACTOR,
                    temperature_k=293.0,  # ~20°C ambient
                    ignition_time_us=0, suppression_age_ticks=0
                )
        
        # Wind model
        self.wind_model = WindModel()
        
        # Simulation tick counter
        self.ticks = 0
        self.time_us = 0
        self.total_burned_cells = 0
    
    def ignite(self, x: int, y: int, intensity: float = 1.0) -> bool:
        """
        Ignite fire at grid cell.
        
        Args:
            x, y: Grid coordinates
            intensity: Initial intensity (0-1)
        
        Returns:
            True if successful, False if coordinates invalid
        """
        if not self._in_bounds(x, y):
            return False
        
        cell = self.grid[y, x]
        cell.state = CellState.BURNING
        cell.intensity = max(intensity, FIRE_INTENSITY_IGNITION)
        cell.ignition_time_us = self.time_us
        cell.temperature_k = 500.0  # Active fire temperature
        
        logger.info(f"Fire ignited at ({x}, {y}), intensity={intensity:.2f}")
        return True
    
    def suppress(self, x: int, y: int, strength: float) -> float:
        """
        Apply suppression (water/foam) to cell.
        
        Reduces intensity based on suppression effectiveness.
        
        Args:
            x, y: Grid coordinates
            strength: Suppression strength (0-1)
        
        Returns:
            Intensity reduction applied
        """
        if not self._in_bounds(x, y):
            return 0.0
        
        cell = self.grid[y, x]
        
        # Calculate intensity reduction
        reduction = cell.intensity * strength * SUPPRESSION_EFFECTIVENESS
        cell.intensity = max(0.0, cell.intensity - reduction)
        cell.suppression_age_ticks = 0
        
        if cell.intensity <= 0:
            cell.state = CellState.SUPPRESSED
            cell.temperature_k = 300.0
            logger.debug(f"Fire suppressed at ({x}, {y})")
        
        return reduction
    
    def step(self) -> Tuple[int, int]:
        """
        Execute one simulation step (FARSITE-inspired propagation).
        
        Returns:
            (newly_ignited_cells, suppressed_cells) tuple
        """
        self.ticks += 1
        self.time_us += int(SIM_TICK_PERIOD_S * 1e6)
        
        # Get wind vector
        wind_vx, wind_vy = self.wind_model.get_wind_vector()
        
        # Collect cells to ignite in this step
        cells_to_ignite: List[Tuple[int, int, float]] = []
        
        # Iterate through burning cells
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y, x]
                
                if not cell.is_burning():
                    continue
                
                # Intensity decay (natural burndown over time)
                cell.intensity *= INTENSITY_DECAY_FACTOR
                
                # Temperature follows intensity
                cell.temperature_k = 300.0 + cell.intensity * 700.0  # 300-1000K range
                
                # Fuel consumption from burning
                fuel_burn_rate = cell.intensity * 0.01  # Small fuel drain per step
                cell.fuel_density = max(0.0, cell.fuel_density - fuel_burn_rate)
                
                # Stop burning if no fuel
                if cell.fuel_density <= 0.0 or cell.intensity <= 0.001:
                    cell.state = CellState.BURNED
                    cell.intensity = 0.0
                    self.total_burned_cells += 1
                    continue
                
                # Fire spread to adjacent cells (8-neighbor Moore neighborhood)
                # Spread distance and speed based on wind and fuel
                spread_distance_cells = self._calculate_spread_distance(
                    cell, wind_vx, wind_vy
                )
                
                # Check all neighboring cells within spread distance
                neighbors = self._get_neighbors_within_distance(
                    x, y, spread_distance_cells
                )
                
                for nx, ny, dist in neighbors:
                    neighbor = self.grid[ny, nx]
                    
                    # Only spread to cells with fuel and no active suppression
                    if neighbor.state != CellState.NO_FIRE or neighbor.fuel_density <= 0:
                        continue
                    
                    # Probability of ignition based on:
                    # - Distance from source (farther = less likely)
                    # - Source intensity (stronger fire = more likely)
                    # - Fuel available (more fuel = more likely)
                    # Distance factor: max 1.0 at center, min 0.2 at edge (ensures boundary spread)
                    distance_factor = 0.2 + 0.8 * (1.0 - (dist / (spread_distance_cells + 0.1)))
                    ignition_prob = (cell.intensity * distance_factor * 
                                   neighbor.fuel_density * 0.5)
                    ignition_prob = min(1.0, ignition_prob)
                    
                    if self.rng.rand() < ignition_prob:
                        # Ignite with reduced intensity based on distance
                        ignition_intensity = cell.intensity * distance_factor * 0.5
                        cells_to_ignite.append((nx, ny, ignition_intensity))
        
        # Apply ignitions
        newly_ignited = 0
        for x, y, intensity in cells_to_ignite:
            if self.ignite(x, y, intensity):
                newly_ignited += 1
        
        # Age suppression effects
        suppressed_cells = 0
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y, x]
                if cell.suppression_age_ticks >= 0:
                    cell.suppression_age_ticks += 1
        
        return newly_ignited, suppressed_cells
    
    def get_fire_state(self) -> dict:
        """
        Get global fire state summary.
        
        Returns:
            Dictionary with fire statistics
        """
        burning_count = 0
        burned_count = 0
        max_intensity = 0.0
        total_fuel_remaining = 0.0
        perimeter_cells = 0
        
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y, x]
                if cell.is_burning():
                    burning_count += 1
                    max_intensity = max(max_intensity, cell.intensity)
                    
                    # Count perimeter (burning cells adjacent to non-burning)
                    for nx, ny in self._get_8_neighbors(x, y):
                        neighbor = self.grid[ny, nx]
                        if neighbor.state in [CellState.NO_FIRE, CellState.SUPPRESSED]:
                            perimeter_cells += 1
                            break
                elif cell.state == CellState.BURNED:
                    burned_count += 1
                
                total_fuel_remaining += cell.fuel_density
        
        fire_coverage = (burning_count / (self.width * self.height)) * 100.0 if burning_count > 0 else 0.0
        
        return {
            "total_burning_cells": burning_count,
            "total_burned_cells": burned_count,
            "max_intensity": max_intensity,
            "fire_coverage_percent": fire_coverage,
            "perimeter_cells": perimeter_cells,
            "total_fuel_remaining": total_fuel_remaining,
            "wind_speed_ms": self.wind_model.wind_speed_ms,
            "wind_direction_deg": self.wind_model.wind_direction_deg,
        }
    
    def get_cells_by_state(self, state: CellState) -> List[Tuple[int, int, FireCell]]:
        """
        Get all cells in a given state.
        
        Args:
            state: CellState to filter
        
        Returns:
            List of (x, y, cell) tuples
        """
        result = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y, x].state == state:
                    result.append((x, y, self.grid[y, x]))
        return result
    
    def detect_fire(self, world_x: float, world_y: float,
                   sensor_range_m: float) -> Tuple[bool, float]:
        """
        Simulate fire detection by drone sensor.
        
        Returns detected fire state within sensor range.
        
        Args:
            world_x, world_y: Drone position (meters)
            sensor_range_m: Detection range (meters)
        
        Returns:
            (fire_detected, intensity) tuple
        """
        # Convert world coordinates to grid coordinates
        grid_x = int(world_x / self.cell_size_m)
        grid_y = int(world_y / self.cell_size_m)
        
        if not self._in_bounds(grid_x, grid_y):
            return False, 0.0
        
        cell = self.grid[int(grid_y), int(grid_x)]
        
        if cell.is_detectable():
            return True, cell.intensity
        return False, 0.0
    
    def get_cell(self, x: int, y: int) -> FireCell:
        """Get cell by grid coordinates."""
        if self._in_bounds(x, y):
            return self.grid[y, x]
        return None
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are in bounds."""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def _calculate_spread_distance(self, cell: FireCell,
                                  wind_vx: float, wind_vy: float) -> float:
        """
        Calculate fire spread distance for this step.
        
        Accounts for:
        - Base spread rate (FIRE_SPREAD_RATE_BASE_MPM)
        - Wind acceleration (faster downwind, slower upwind)
        - Fuel availability
        - Cell size
        
        Args:
            cell: Source cell
            wind_vx, wind_vy: Wind vector (m/s)
        
        Returns:
            Spread distance in cells
        """
        # Base spread rate (meters per minute) → cells per step
        spread_mpm = FIRE_SPREAD_RATE_BASE_MPM * cell.fuel_density
        
        # Wind enhancement: wind component along fire spread direction
        # Simplified: magnitude of wind speeds up spread
        wind_magnitude = math.sqrt(wind_vx**2 + wind_vy**2)
        wind_factor = 1.0 + (wind_magnitude / WIND_SPEED_MS) * FIRE_SPREAD_RATE_WIND_SCALE
        
        spread_mpm *= wind_factor
        
        # Convert to cells per step
        spread_m_per_step = (spread_mpm / 60.0) * SIM_TICK_PERIOD_S
        spread_cells = spread_m_per_step / self.cell_size_m
        
        return max(1.0, spread_cells)
    
    def _get_neighbors_within_distance(self, x: int, y: int,
                                      distance: float) -> List[Tuple[int, int, float]]:
        """
        Get all neighbors within distance (Euclidean).
        
        Args:
            x, y: Center coordinates
            distance: Distance threshold (cells)
        
        Returns:
            List of (nx, ny, dist) tuples
        """
        neighbors = []
        search_radius = int(distance) + 1
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = x + dx, y + dy
                if not self._in_bounds(nx, ny):
                    continue
                
                dist = math.sqrt(dx**2 + dy**2)
                if dist <= distance:
                    neighbors.append((nx, ny, dist))
        
        return neighbors
    
    def _get_8_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get 8 immediate neighbors (Moore neighborhood)."""
        neighbors = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny):
                    neighbors.append((nx, ny))
        return neighbors
