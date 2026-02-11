"""
src/constants.py

Global constants and configuration defaults for AeroSyn-Sim.
"""

import math
from enum import IntEnum, Enum

# ============================================================================
# SIMULATION TIMING
# ============================================================================

SIM_TICK_RATE_HZ = 100              # Default simulation update frequency
SIM_TICK_PERIOD_S = 1.0 / SIM_TICK_RATE_HZ  # ~0.01s
SIM_TICK_PERIOD_US = int(SIM_TICK_PERIOD_S * 1e6)

# ============================================================================
# DRONE PARAMETERS
# ============================================================================

# Default battery and energy
BATTERY_CAPACITY_MAH = 5000
BATTERY_VOLTAGE_V = 14.8
BATTERY_NOMINAL_ENERGY_WH = (BATTERY_CAPACITY_MAH / 1000.0) * BATTERY_VOLTAGE_V  # Watt-hours
MAX_HOVER_TIME_S = 1200

# Energy drain (normalized 0-1 scale per sim unit)
ENERGY_DRAIN_PER_METER = 0.08      # Energy units lost per meter flown
ENERGY_DRAIN_HOVER_PER_SEC = 0.0001  # Energy units lost per second hovering
BATTERY_MIN_PERCENT = 20.0          # RTL threshold

# Payload
MAX_PAYLOAD_UNITS = 40
PAYLOAD_DRAIN_PER_SUPPRESSION = 1.0

# Flight envelope
MAX_SPEED_MS = 20
CRUISE_SPEED_MS = 15
MAX_ALTITUDE_M = 2000
MIN_ALTITUDE_M = 0

# Drone masses (approximate)
DRONE_MASS_KG = 2.0

# ============================================================================
# MAVLINK / SITL
# ============================================================================

SITL_BASE_PORT = 14550
SITL_PORT_STRIDE = 10
SITL_UDP_OUTPUT_OFFSET = 5

# ============================================================================
# COMMUNICATION
# ============================================================================

# MQTT
MQTT_BROKER_HOST = "127.0.0.1"
MQTT_BROKER_PORT = 1883
MQTT_QOS = 1

# Ad-hoc RF
AD_HOC_BROADCAST_RANGE_M = 100.0

# DETM (Dynamic Event-Triggered Mechanism)
DETM_ETA0 = 0.5                    # Initial trigger threshold (L2 norm)
DETM_LAMBDA = 0.1                  # Exponential decay rate
DETM_MIN_ETA = 0.01                # Minimum threshold (to prevent zero)

# Packet loss and latency
BASE_PACKET_LOSS_PROBABILITY = 0.05
RSSI_PACKET_LOSS_THRESHOLD_DBM = -100

# ============================================================================
# RF CHANNEL MODEL (RICE FADING)
# ============================================================================

# Path loss
REFERENCE_DISTANCE_M = 1.0
PATH_LOSS_EXPONENT = 3.0           # Free space ≈ 2.0, urban ≈ 3.0-4.0
REFERENCE_RSSI_DBM = -40           # RSSI at reference distance

# Fading (Rice distribution)
RICE_K_FACTOR = 8.0                # Ratio of LoS to scattered power
FADING_STD_DB = 2.0

# Receiver characteristics
SENSITIVITY_DBM = -110             # Minimum detectable signal
MAX_RSSI_DBM = 0                   # Max RSSI (clipping)

# Latency injection
BASE_LATENCY_MS = 5
LATENCY_RSSI_SCALE = 50            # ms per dB below reference

# ============================================================================
# FIRE SIMULATION
# ============================================================================

# Grid
FIRE_GRID_WIDTH = 100              # cells
FIRE_GRID_HEIGHT = 100
FIRE_CELL_SIZE_M = 10              # meters per cell

# Fire spread (FARSITE-inspired)
FIRE_SPREAD_RATE_BASE_MPM = 500.0   # Meters per minute base (fast spread for sim)
FIRE_SPREAD_RATE_WIND_SCALE = 2.0
WIND_SPEED_MS = 5.0                # Constant wind
WIND_DIRECTION_DEG = 45            # Degrees (0=North, 90=East)

# Fuel
FUEL_MOISTURE_PERCENT = 50
FUEL_DENSITY_FACTOR = 1.0

# Fire control
SUPPRESSION_EFFECTIVENESS = 0.9
INTENSITY_DECAY_FACTOR = 0.95      # Natural decay per tick

# Fire thresholds
FIRE_INTENSITY_THRESHOLD_DETECTABLE = 0.1
FIRE_INTENSITY_IGNITION = 0.5

# ============================================================================
# SWARM INTELLIGENCE
# ============================================================================

# K-means clustering
KMEANS_N_CLUSTERS = 3
KMEANS_MAX_ITERATIONS = 100

# Lévy flight
LEVY_ALPHA = 1.5                   # Tail exponent
LEVY_STEP_SCALE_M = 50             # Typical step length
LEVY_ANGULAR_SCALE_DEG = 180       # Angular randomness

# Stigmergy (pheromone)
PHEROMONE_GRID_WIDTH = 100
PHEROMONE_GRID_HEIGHT = 100
PHEROMONE_DEPOSIT_STRENGTH = 1.0
PHEROMONE_DECAY_FACTOR = 0.95
PHEROMONE_GRADIENT_THRESHOLD = 0.1

# Distributed observer
OBSERVER_UPDATE_INTERVAL_MS = 50
OBSERVER_LATENCY_TIMEOUT_MS = 500

# ============================================================================
# DRONE STATE ENUMS
# ============================================================================

class DroneState(IntEnum):
    """Drone operational state."""
    IDLE = 0
    SEARCH = 1
    SUPPRESS = 2
    RETURN_TO_LAUNCH = 3
    RETURN_TO_DOCK = 4
    FORMATION = 5

class DroneType(IntEnum):
    """Drone role in swarm."""
    LEADER = 0
    FOLLOWER = 1

# ============================================================================
# COMMAND TYPES
# ============================================================================

class CommandType(IntEnum):
    """External command types."""
    NOP = 0
    TAKEOFF = 1
    LAND = 2
    RETURN_TO_LAUNCH = 3
    RETURN_TO_DOCK = 4
    GOTO_POSITION = 5
    SUPPRESS_FIRE = 6
    HOLD = 7
    RESUME = 8
    SET_BATTERY_OVERRIDE = 9

# ============================================================================
# COORDINATE FRAMES
# ============================================================================

class CoordinateFrame(Enum):
    """Coordinate system convention."""
    NED = "NED"                    # North-East-Down (ArduPilot standard)
    ENU = "ENU"                    # East-North-Up (ROS standard)
    ECEF = "ECEF"                  # Earth-Centered Earth-Fixed

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def distance_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance in 2D (horizontal plane)."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def distance_3d(x1: float, y1: float, z1: float,
                x2: float, y2: float, z2: float) -> float:
    """Euclidean distance in 3D."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

def vector_norm_l2(vx: float, vy: float, vz: float = 0.0) -> float:
    """L2 norm (Euclidean norm) of a vector."""
    return math.sqrt(vx**2 + vy**2 + vz**2)

def vector_norm_linf(vx: float, vy: float, vz: float = 0.0) -> float:
    """L-infinity norm (max absolute value) of a vector."""
    return max(abs(vx), abs(vy), abs(vz))

def rssi_to_linear_power(rssi_dbm: float) -> float:
    """Convert RSSI (dBm) to linear power (Watts)."""
    # P(W) = 10^(P(dBm)/10 - 3)
    return 10.0**((rssi_dbm - 30.0) / 10.0)

def linear_power_to_rssi(power_w: float) -> float:
    """Convert linear power (Watts) to RSSI (dBm)."""
    # P(dBm) = 10 * log10(P(W)) + 30
    if power_w <= 0:
        return MAX_RSSI_DBM
    return 10.0 * math.log10(power_w) + 30.0

def decibel_to_linear(db: float) -> float:
    """Convert decibels to linear ratio."""
    return 10.0**(db / 10.0)

def linear_to_decibel(linear: float) -> float:
    """Convert linear ratio to decibels."""
    if linear <= 0:
        return -200.0  # Very negative dB
    return 10.0 * math.log10(linear)

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))

def exponential_decay(initial: float, decay_factor: float, steps: int) -> float:
    """Compute exponential decay over n steps."""
    return initial * (decay_factor ** steps)
