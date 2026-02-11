"""
src/metrics_collector.py

Performance Metrics Aggregation for AeroSyn-Sim

Collects and aggregates:
- Per-drone metrics (distance, energy, fire suppression)
- Swarm-level metrics (coverage, communication efficiency)
- Network metrics (RSSI, latency, packet loss)
- Fire statistics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# METRICS STRUCTURES
# ============================================================================

@dataclass
class DroneMetrics:
    """Per-drone metrics snapshot."""
    drone_id: int
    timestamp_us: int
    
    # Navigation
    total_distance_m: float
    battery_percent: float
    payload_remaining: int
    
    # Fire suppression
    fires_detected: int
    fires_suppressed: int
    total_suppression_strength: float
    
    # Communication
    messages_sent: int
    messages_received: int
    average_rssi_dbm: float
    
    # Behavior
    state: str
    time_in_search_us: int
    time_in_suppress_us: int
    time_in_rtl_us: int


@dataclass
class SwarmMetrics:
    """Swarm-level aggregated metrics."""
    timestamp_us: int
    
    # Swarm size
    num_drones: int
    num_active_drones: int
    num_idle_drones: int
    
    # Fire state
    total_burning_cells: int
    fire_coverage_percent: float
    
    # Energy
    average_battery_percent: float
    num_critical_battery: int
    
    # Communication
    total_messages_sent: int
    average_message_interval_ms: float
    
    # Drone metrics
    drone_metrics: Dict[int, DroneMetrics] = field(default_factory=dict)


# ============================================================================
# METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """
    Collects and aggregates simulation metrics.
    
    Maintains:
    - History of per-drone metrics
    - Real-time swarm-level aggregates
    - Fire statistics
    - Network statistics
    """
    
    def __init__(self, history_length: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            history_length: Max snapshots to keep in history
        """
        self.history_length = history_length
        self.drone_history: Dict[int, deque] = {}  # drone_id -> deque of DroneMetrics
        self.swarm_history: deque = deque(maxlen=history_length)
        
        self.current_metrics: Optional[SwarmMetrics] = None
    
    def update_drone(self, drone_id: int, metrics: DroneMetrics) -> None:
        """
        Record metrics for a drone.
        
        Args:
            drone_id: Drone identifier
            metrics: DroneMetrics snapshot
        """
        if drone_id not in self.drone_history:
            self.drone_history[drone_id] = deque(maxlen=self.history_length)
        
        self.drone_history[drone_id].append(metrics)
    
    def update_swarm(self, swarm_metrics: SwarmMetrics) -> None:
        """
        Record swarm-level metrics.
        
        Args:
            swarm_metrics: SwarmMetrics snapshot
        """
        self.current_metrics = swarm_metrics
        self.swarm_history.append(swarm_metrics)
    
    def get_drone_history(self, drone_id: int) -> List[DroneMetrics]:
        """Get metrics history for drone."""
        if drone_id not in self.drone_history:
            return []
        return list(self.drone_history[drone_id])
    
    def get_drone_latest(self, drone_id: int) -> Optional[DroneMetrics]:
        """Get latest metrics for drone."""
        if drone_id not in self.drone_history:
            return None
        if len(self.drone_history[drone_id]) == 0:
            return None
        return self.drone_history[drone_id][-1]
    
    def get_swarm_history(self) -> List[SwarmMetrics]:
        """Get swarm metrics history."""
        return list(self.swarm_history)
    
    def get_swarm_latest(self) -> Optional[SwarmMetrics]:
        """Get latest swarm metrics."""
        return self.current_metrics
    
    def export_summary(self) -> dict:
        """
        Export metrics summary for external consumption.
        
        Returns:
            Dictionary with aggregated metrics
        """
        if not self.current_metrics:
            return {}
        
        metrics = self.current_metrics
        
        return {
            "timestamp_us": metrics.timestamp_us,
            "num_drones": metrics.num_drones,
            "num_active": metrics.num_active_drones,
            "fire_coverage_percent": metrics.fire_coverage_percent,
            "average_battery_percent": metrics.average_battery_percent,
            "total_messages": metrics.total_messages_sent,
            "drones": {
                drone_id: {
                    "battery_percent": m.battery_percent,
                    "payload": m.payload_remaining,
                    "distance_m": m.total_distance_m,
                    "state": m.state,
                }
                for drone_id, m in metrics.drone_metrics.items()
            }
        }
