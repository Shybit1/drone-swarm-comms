"""
src/config.py

Configuration loader for AeroSyn-Sim.
Loads YAML simulation parameters and merges with environment overrides.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# DATA CLASSES FOR TYPE-SAFE CONFIG
# ============================================================================

@dataclass
class SimulationConfig:
    """Top-level simulation configuration."""
    name: str = "AeroSyn Disaster Response Swarm Simulation"
    version: str = "1.0.0"
    tick_rate_hz: int = 100
    max_sim_time_s: int = 3600
    random_seed: int = 42

@dataclass
class SwarmConfig:
    """Swarm-specific configuration."""
    num_leaders: int = 3
    num_followers: int = 6
    sitl_binary_path: str = "./Tools/autotest/sim_vehicle.py"
    sitl_vehicle: str = "ArduCopter"
    sitl_frame: str = "quad"
    base_port: int = 14550
    sitl_port_stride: int = 10
    udp_output_offset: int = 5
    home_latitude: float = 40.2338
    home_longitude: float = -111.0934
    home_altitude_m: float = 1300
    max_speed_ms: float = 20
    cruise_speed_ms: float = 15
    max_altitude_m: float = 2000
    battery_capacity_mah: int = 5000
    battery_voltage_v: float = 14.8
    max_hover_time_s: int = 1200
    energy_drain_per_meter: float = 0.08
    energy_drain_hover_per_sec: float = 0.0001
    battery_min_percent: float = 20.0
    max_payload_units: int = 40
    payload_drain_suppress: float = 1.0
    leader_binding_radius_m: float = 500

@dataclass
class CommunicationConfig:
    """Communication parameters."""
    mqtt_broker_host: str = "127.0.0.1"
    mqtt_broker_port: int = 1883
    mqtt_qos: int = 1
    ad_hoc_broadcast_range_m: float = 100.0
    detm_enabled: bool = True
    detm_eta0: float = 0.5
    detm_lambda: float = 0.1
    detm_norm: str = "l2"
    packet_loss_probability: float = 0.05
    packet_loss_rssi_threshold_dbm: float = -100

@dataclass
class ChannelModelConfig:
    """RF channel model parameters."""
    reference_distance_m: float = 1.0
    path_loss_exponent: float = 3.0
    reference_rssi_dbm: float = -40
    rice_k_factor: float = 8.0
    fading_std_db: float = 2.0
    sensitivity_dbm: float = -110
    max_rssi_dbm: float = 0
    base_latency_ms: float = 5
    latency_rssi_scale: float = 50

@dataclass
class FireSimulationConfig:
    """Fire simulation parameters."""
    grid_width_cells: int = 100
    grid_height_cells: int = 100
    cell_size_meters: float = 10
    spread_rate_base_mpm: float = 5.0
    spread_rate_wind_scale: float = 2.0
    wind_speed_ms: float = 5.0
    wind_direction_deg: float = 45
    fuel_moisture_percent: float = 50
    fuel_density_factor: float = 1.0
    suppression_effectiveness: float = 0.9
    intensity_decay_factor: float = 0.95
    initial_fire_positions: list = field(default_factory=lambda: [
        {"x": 250, "y": 250},
        {"x": 750, "y": 750}
    ])

@dataclass
class SwarmIntelligenceConfig:
    """Swarm intelligence algorithm parameters."""
    kmeans_n_clusters: int = 3
    kmeans_max_iterations: int = 100
    levy_alpha: float = 1.5
    levy_step_scale: float = 50
    levy_angular_scale: float = 180
    pheromone_grid_width: int = 100
    pheromone_grid_height: int = 100
    pheromone_deposit_strength: float = 1.0
    pheromone_decay_factor: float = 0.95
    pheromone_threshold: float = 0.1
    observer_update_interval_ms: int = 50
    observer_latency_timeout_ms: int = 500

@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = "INFO"
    log_file: str = "aerosyn_sim.log"
    log_drone_telemetry: bool = True
    log_fire_state: bool = True
    log_detm_triggers: bool = True

@dataclass
class MetricsConfig:
    """Metrics collection configuration."""
    enable_metrics_collection: bool = True
    metrics_publish_interval_ms: int = 100
    latency_recording_enabled: bool = True

@dataclass
class FrontendConfig:
    """Frontend server configuration."""
    web_server_host: str = "0.0.0.0"
    web_server_port: int = 8080
    api_base_path: str = "/api/v1"
    websocket_endpoint: str = "/ws"
    max_visible_drones: int = 50
    fire_visualization_scale: float = 1.0
    heatmap_update_frequency_ms: int = 200

@dataclass
class AeroSynConfig:
    """Master configuration object."""
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    swarm: SwarmConfig = field(default_factory=SwarmConfig)
    communication: CommunicationConfig = field(default_factory=CommunicationConfig)
    channel_model: ChannelModelConfig = field(default_factory=ChannelModelConfig)
    fire_simulation: FireSimulationConfig = field(default_factory=FireSimulationConfig)
    swarm_intelligence: SwarmIntelligenceConfig = field(default_factory=SwarmIntelligenceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    frontend: FrontendConfig = field(default_factory=FrontendConfig)

# ============================================================================
# CONFIGURATION LOADER
# ============================================================================

class ConfigLoader:
    """Loads and manages AeroSyn configuration."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize config loader.
        
        Args:
            config_file: Path to YAML config file. If None, uses default.
        """
        self.config_file = config_file or self._find_default_config()
        self.config: AeroSynConfig = self._load_config()

    @staticmethod
    def _find_default_config() -> str:
        """Find the default config file in project structure."""
        candidates = [
            Path(__file__).parent.parent / "config" / "simulation_params.yaml",
            Path.cwd() / "config" / "simulation_params.yaml",
        ]
        for path in candidates:
            if path.exists():
                logger.info(f"Found config file: {path}")
                return str(path)
        raise FileNotFoundError(
            "Could not find simulation_params.yaml. "
            "Please ensure it exists in ./config/ directory."
        )

    def _load_config(self) -> AeroSynConfig:
        """Load configuration from YAML file."""
        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Config file is empty: {self.config_file}")

        return self._parse_config(data)

    @staticmethod
    def _parse_config(data: Dict[str, Any]) -> AeroSynConfig:
        """Parse YAML data into typed config objects."""
        config = AeroSynConfig()

        # Parse each section
        if "simulation" in data:
            config.simulation = SimulationConfig(**data["simulation"])
        if "swarm" in data:
            config.swarm = SwarmConfig(**data["swarm"])
        if "communication" in data:
            config.communication = CommunicationConfig(**data["communication"])
        if "channel_model" in data:
            config.channel_model = ChannelModelConfig(**data["channel_model"])
        if "fire_simulation" in data:
            config.fire_simulation = FireSimulationConfig(**data["fire_simulation"])
        if "swarm_intelligence" in data:
            config.swarm_intelligence = SwarmIntelligenceConfig(**data["swarm_intelligence"])
        if "logging" in data:
            config.logging = LoggingConfig(**data["logging"])
        if "metrics" in data:
            config.metrics = MetricsConfig(**data["metrics"])
        if "frontend" in data:
            config.frontend = FrontendConfig(**data["frontend"])

        return config

    def get_config(self) -> AeroSynConfig:
        """Return loaded configuration."""
        return self.config

    def override_param(self, key_path: str, value: Any) -> None:
        """
        Override a configuration parameter.
        
        Key path format: "section.subsection.param"
        Example: config.override_param("swarm.num_leaders", 5)
        """
        parts = key_path.split('.')
        obj = self.config
        
        # Navigate to parent object
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        # Set the value
        setattr(obj, parts[-1], value)
        logger.info(f"Config override: {key_path} = {value}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for serialization)."""
        def dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                result = {}
                for field_name, field_obj in obj.__dataclass_fields__.items():
                    value = getattr(obj, field_name)
                    if hasattr(value, '__dataclass_fields__'):
                        result[field_name] = dataclass_to_dict(value)
                    elif isinstance(value, list):
                        result[field_name] = value
                    else:
                        result[field_name] = value
                return result
            return obj

        return dataclass_to_dict(self.config)

# ============================================================================
# GLOBAL CONFIG INSTANCE (SINGLETON PATTERN)
# ============================================================================

_global_config: Optional[ConfigLoader] = None

def initialize_config(config_file: Optional[str] = None) -> AeroSynConfig:
    """Initialize global configuration."""
    global _global_config
    _global_config = ConfigLoader(config_file)
    return _global_config.get_config()

def get_config() -> AeroSynConfig:
    """Get the global configuration."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader()
    return _global_config.get_config()

def override_config(key_path: str, value: Any) -> None:
    """Override a global configuration parameter."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader()
    _global_config.override_param(key_path, value)
