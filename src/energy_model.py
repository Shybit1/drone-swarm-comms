"""
src/energy_model.py

Battery and Payload Management for Autonomous Drones

Models realistic energy constraints:
- Battery capacity and voltage
- Energy drain based on flight dynamics (distance, hover, aggressiveness)
- Payload capacity tracking
- Hard RTL override when critical thresholds reached
"""

import math
from dataclasses import dataclass
from constants import (
    BATTERY_CAPACITY_MAH, BATTERY_VOLTAGE_V, BATTERY_NOMINAL_ENERGY_WH,
    MAX_HOVER_TIME_S, ENERGY_DRAIN_PER_METER, ENERGY_DRAIN_HOVER_PER_SEC,
    BATTERY_MIN_PERCENT, MAX_PAYLOAD_UNITS, PAYLOAD_DRAIN_PER_SUPPRESSION,
    clamp
)
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ENERGY STATE
# ============================================================================

@dataclass
class BatteryState:
    """Battery state snapshot."""
    battery_percent: float         # 0.0 to 100.0
    battery_mah_remaining: float   # Remaining capacity (mAh)
    battery_energy_wh: float       # Remaining energy (Watt-hours)
    voltage_v: float               # Current voltage (V)
    
    # Derived metrics
    time_to_empty_s: float         # Estimated time until depletion (seconds)
    critical: bool                 # True if below 20%
    depleted: bool                 # True if 0%


@dataclass
class PayloadState:
    """Payload state snapshot."""
    payload_units: int             # Current payload units
    max_payload_units: int         # Maximum capacity
    payload_percent: float         # 0.0 to 100.0
    empty: bool                    # True if 0 units


# ============================================================================
# BATTERY MODEL
# ============================================================================

class BatteryModel:
    """
    Battery Model for Autonomous Drones
    
    Models realistic battery characteristics:
    - Capacity (mAh)
    - Voltage (V) - approximately constant during discharge
    - Energy content (Wh = mAh * V / 1000)
    - Discharge rate based on flight dynamics
    
    Energy Drain Model:
    - Horizontal flight: energy_drain = distance * ENERGY_DRAIN_PER_METER
    - Hovering: energy_drain = time * ENERGY_DRAIN_HOVER_PER_SEC
    - Climbing/aggressive maneuvers: additional multiplier
    
    Attributes:
        capacity_mah: Nominal capacity
        nominal_voltage_v: Nominal voltage
        total_energy_wh: Total energy capacity
        remaining_energy_wh: Current remaining energy
    """
    
    def __init__(self, capacity_mah: float = BATTERY_CAPACITY_MAH,
                 voltage_v: float = BATTERY_VOLTAGE_V):
        """
        Initialize battery.
        
        Args:
            capacity_mah: Battery capacity (mAh)
            voltage_v: Nominal voltage (V)
        """
        self.capacity_mah = capacity_mah
        self.nominal_voltage_v = voltage_v
        self.total_energy_wh = (capacity_mah / 1000.0) * voltage_v
        self.remaining_energy_wh = self.total_energy_wh
        self.nominal_drain_rate = 1.0 / (MAX_HOVER_TIME_S * 3600)  # Energy fraction per second
    
    def get_state(self) -> BatteryState:
        """
        Get current battery state.
        
        Returns:
            BatteryState snapshot
        """
        battery_percent = clamp(
            (self.remaining_energy_wh / self.total_energy_wh) * 100.0, 0.0, 100.0
        )
        
        # Estimate time to empty at current voltage
        # Assume discharge rate is approximately constant
        if self.nominal_drain_rate > 0:
            time_to_empty = self.remaining_energy_wh / \
                          (self.total_energy_wh * self.nominal_drain_rate)
        else:
            time_to_empty = float('inf')
        
        return BatteryState(
            battery_percent=battery_percent,
            battery_mah_remaining=(self.remaining_energy_wh / self.nominal_voltage_v) * 1000.0,
            battery_energy_wh=self.remaining_energy_wh,
            voltage_v=self.nominal_voltage_v,
            time_to_empty_s=time_to_empty,
            critical=(battery_percent < BATTERY_MIN_PERCENT),
            depleted=(battery_percent <= 0.0)
        )
    
    def drain_flight(self, distance_m: float,
                     aggressiveness: float = 1.0) -> float:
        """
        Drain battery for horizontal flight.
        
        Args:
            distance_m: Distance flown (meters)
            aggressiveness: Multiplier for aggressive maneuvers (1.0 = normal)
        
        Returns:
            Energy consumed (Wh)
        """
        # Energy = distance * energy_per_meter * aggressiveness
        energy_consumed = distance_m * ENERGY_DRAIN_PER_METER * aggressiveness
        self.remaining_energy_wh = max(0.0, self.remaining_energy_wh - energy_consumed)
        return energy_consumed
    
    def drain_hover(self, time_s: float) -> float:
        """
        Drain battery for hovering.
        
        Args:
            time_s: Time hovering (seconds)
        
        Returns:
            Energy consumed (Wh)
        """
        # Energy = time * energy_per_second
        energy_consumed = time_s * ENERGY_DRAIN_HOVER_PER_SEC
        self.remaining_energy_wh = max(0.0, self.remaining_energy_wh - energy_consumed)
        return energy_consumed
    
    def drain_custom(self, energy_wh: float) -> float:
        """
        Drain battery by custom amount.
        
        Args:
            energy_wh: Energy to drain (Wh)
        
        Returns:
            Energy actually drained (clamped to 0)
        """
        energy_drained = min(energy_wh, self.remaining_energy_wh)
        self.remaining_energy_wh -= energy_drained
        return energy_drained
    
    def charge(self, energy_wh: float) -> float:
        """
        Charge battery.
        
        Args:
            energy_wh: Energy to add (Wh)
        
        Returns:
            Energy actually added (clamped to max)
        """
        energy_added = min(energy_wh, self.total_energy_wh - self.remaining_energy_wh)
        self.remaining_energy_wh += energy_added
        return energy_added
    
    def charge_percent(self, percent: float) -> None:
        """
        Charge to percentage.
        
        Args:
            percent: Target percentage (0-100)
        """
        self.remaining_energy_wh = clamp(
            (percent / 100.0) * self.total_energy_wh, 0.0, self.total_energy_wh
        )
    
    def is_critical(self) -> bool:
        """Check if battery is below critical threshold."""
        return self.get_state().critical
    
    def is_depleted(self) -> bool:
        """Check if battery is fully depleted."""
        return self.get_state().depleted


# ============================================================================
# PAYLOAD MODEL
# ============================================================================

class PayloadModel:
    """
    Payload (water/foam) capacity tracking.
    
    Models a finite resource (e.g., water/suppression agent) that drones
    consume when suppressing fires. Payload must be replenished at dock.
    
    Attributes:
        max_payload_units: Maximum capacity
        payload_units: Current payload
    """
    
    def __init__(self, max_payload_units: int = MAX_PAYLOAD_UNITS):
        """
        Initialize payload.
        
        Args:
            max_payload_units: Maximum capacity
        """
        self.max_payload_units = max_payload_units
        self.payload_units = max_payload_units
    
    def get_state(self) -> PayloadState:
        """
        Get current payload state.
        
        Returns:
            PayloadState snapshot
        """
        payload_percent = clamp(
            (self.payload_units / self.max_payload_units) * 100.0, 0.0, 100.0
        )
        
        return PayloadState(
            payload_units=self.payload_units,
            max_payload_units=self.max_payload_units,
            payload_percent=payload_percent,
            empty=(self.payload_units <= 0)
        )
    
    def consume(self, units: float) -> float:
        """
        Consume payload.
        
        Args:
            units: Payload units to consume
        
        Returns:
            Payload actually consumed (clamped to remaining)
        """
        consumed = min(units, self.payload_units)
        self.payload_units = max(0, self.payload_units - units)
        return consumed
    
    def replenish(self, units: float) -> float:
        """
        Replenish payload.
        
        Args:
            units: Payload units to add
        
        Returns:
            Payload actually added (clamped to max)
        """
        added = min(units, self.max_payload_units - self.payload_units)
        self.payload_units = min(self.max_payload_units, self.payload_units + units)
        return added
    
    def refill(self) -> None:
        """Completely refill payload."""
        self.payload_units = self.max_payload_units
    
    def is_empty(self) -> bool:
        """Check if payload is empty."""
        return self.payload_units <= 0


# ============================================================================
# ENERGY MANAGER (COMBINED)
# ============================================================================

class EnergyManager:
    """
    Combined Battery + Payload Manager
    
    Tracks both battery and payload state. Enforces hard overrides:
    - RTL if battery < 20%
    - RTL if payload == 0 (cannot suppress without it)
    
    Attributes:
        battery: Battery model
        payload: Payload model
    """
    
    def __init__(self, battery_capacity_mah: float = BATTERY_CAPACITY_MAH,
                 battery_voltage_v: float = BATTERY_VOLTAGE_V,
                 max_payload_units: int = MAX_PAYLOAD_UNITS):
        """
        Initialize energy manager.
        
        Args:
            battery_capacity_mah: Battery capacity
            battery_voltage_v: Battery voltage
            max_payload_units: Max payload capacity
        """
        self.battery = BatteryModel(battery_capacity_mah, battery_voltage_v)
        self.payload = PayloadModel(max_payload_units)
    
    def should_rtl_override(self) -> Tuple[bool, str]:
        """
        Check if drone should trigger Return-to-Launch override.
        
        Hard constraints:
        - Battery < 20% → must return to charge
        - Payload == 0 → cannot suppress without supplies
        
        Returns:
            (should_rtl, reason) tuple
        """
        if self.battery.is_critical():
            return True, "battery_critical"
        if self.payload.is_empty():
            return True, "payload_empty"
        return False, "none"
    
    def update_flight(self, distance_m: float, hover_time_s: float,
                      aggressiveness: float = 1.0) -> float:
        """
        Update energy consumption for flight segment.
        
        Args:
            distance_m: Distance flown
            hover_time_s: Time hovering
            aggressiveness: Maneuver aggressiveness multiplier
        
        Returns:
            Total energy consumed (Wh)
        """
        energy_consumed = self.battery.drain_flight(distance_m, aggressiveness)
        energy_consumed += self.battery.drain_hover(hover_time_s)
        return energy_consumed
    
    def update_suppression(self, strength: float) -> Tuple[float, float]:
        """
        Update energy for fire suppression action.
        
        Args:
            strength: Suppression strength (0-1)
        
        Returns:
            (payload_consumed, energy_cost) tuple
        """
        payload_consumed = self.payload.consume(
            PAYLOAD_DRAIN_PER_SUPPRESSION * strength
        )
        # Suppression doesn't directly drain battery (payload handling does)
        return payload_consumed, 0.0
    
    def dock(self) -> None:
        """Dock drone: refill battery and payload."""
        self.battery.charge_percent(100.0)
        self.payload.refill()
        logger.info("Drone docked: battery charged, payload refilled")
    
    def get_energy_state(self) -> Tuple[BatteryState, PayloadState]:
        """
        Get current energy state.
        
        Returns:
            (BatteryState, PayloadState) tuple
        """
        return self.battery.get_state(), self.payload.get_state()
    
    def export_telemetry(self) -> dict:
        """
        Export energy telemetry for messaging.
        
        Returns:
            Dictionary suitable for Protobuf serialization
        """
        battery_state = self.battery.get_state()
        payload_state = self.payload.get_state()
        
        return {
            "battery_percent": battery_state.battery_percent,
            "fuel_distance_m": int(battery_state.battery_percent * 100),  # Rough estimate
            "payload_remaining": payload_state.payload_units,
        }
