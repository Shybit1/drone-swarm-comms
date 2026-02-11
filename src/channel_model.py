"""
src/channel_model.py

RF Channel Modeling with Rice Fading Distribution

Implements realistic over-the-air communication constraints:
- Log-distance path loss (distance-dependent attenuation)
- Rice fading (stochastic amplitude variations)
- RSSI calculation and packet loss injection
- Latency modeling based on signal quality
"""

import numpy as np
import math
from dataclasses import dataclass, replace
from typing import Tuple
from constants import (
    REFERENCE_DISTANCE_M, PATH_LOSS_EXPONENT, REFERENCE_RSSI_DBM,
    RICE_K_FACTOR, FADING_STD_DB, SENSITIVITY_DBM, MAX_RSSI_DBM,
    BASE_LATENCY_MS, LATENCY_RSSI_SCALE, BASE_PACKET_LOSS_PROBABILITY,
    RSSI_PACKET_LOSS_THRESHOLD_DBM, decibel_to_linear, linear_to_decibel, clamp
)
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# RICE FADING CHANNEL
# ============================================================================

class RiceFadingChannel:
    """
    Rice Fading Channel Model
    
    Models the combined effect of Line-of-Sight (LoS) and scattered multipath
    propagation between two drones. The Rice distribution is parameterized by
    the K-factor (ratio of LoS power to scattered power).
    
    High K-factor → strong LoS, low fading
    Low K-factor → weak LoS, high fading
    
    Attributes:
        k_factor: Rice K-factor (dimensionless ratio)
        fading_std_db: Standard deviation of fading in decibels
        rng: Numpy random number generator (seeded for reproducibility)
    """
    
    def __init__(self, k_factor: float = RICE_K_FACTOR,
                 fading_std_db: float = FADING_STD_DB,
                 seed: int = None):
        """
        Initialize Rice fading channel.
        
        Args:
            k_factor: Rice K-factor (8.0 typical for urban LoS)
            fading_std_db: Standard deviation of fading (dB)
            seed: RNG seed for deterministic fading
        """
        self.k_factor = k_factor
        self.fading_std_db = fading_std_db
        self.rng = np.random.RandomState(seed)
    
    def generate_fading(self) -> float:
        """
        Generate a Rice fading sample.
        
        Returns fading as dB value (positive = gain, negative = loss).
        
        Mathematical Background:
        - Rice distribution: r ~ Rice(ν, σ)
          where ν is LoS amplitude, σ is RMS of scattered components
        - K = ν²/(2σ²) ≡ ratio of LoS power to scattered power
        - We model fading as Gaussian for computational simplicity
          (valid approximation for moderate K-factor)
        
        Returns:
            Fading value in decibels
        """
        # Gaussian approximation to Rice fading
        # Mean is 0 dB (no average gain/loss)
        fading_db = self.rng.normal(loc=0.0, scale=self.fading_std_db)
        return fading_db
    
    def get_k_factor(self) -> float:
        """Return current K-factor."""
        return self.k_factor
    
    def set_k_factor(self, k_factor: float) -> None:
        """Update K-factor (affects fading severity)."""
        self.k_factor = max(0.1, k_factor)


# ============================================================================
# PATH LOSS MODEL
# ============================================================================

class PathLossModel:
    """
    Log-Distance Path Loss Model
    
    Models how signal strength decreases with distance based on:
    - Free space path loss (exponent ~2.0)
    - Urban/obstacle-rich environments (exponent ~3.0-4.0)
    
    Formula:
      PL(d) = PL(d₀) + 10n*log₁₀(d/d₀)
    
    Where:
      d = distance between drones
      d₀ = reference distance (1m)
      n = path loss exponent
      PL(d₀) = reference path loss at d₀
    
    Attributes:
        reference_distance_m: Reference distance (usually 1m)
        path_loss_exponent: Exponent n (2.0-4.0)
        reference_rssi_dbm: RSSI at reference distance
    """
    
    def __init__(self, reference_distance_m: float = REFERENCE_DISTANCE_M,
                 path_loss_exponent: float = PATH_LOSS_EXPONENT,
                 reference_rssi_dbm: float = REFERENCE_RSSI_DBM):
        """
        Initialize path loss model.
        
        Args:
            reference_distance_m: Reference distance (m)
            path_loss_exponent: Path loss exponent
            reference_rssi_dbm: RSSI at reference distance (dBm)
        """
        self.reference_distance_m = reference_distance_m
        self.path_loss_exponent = path_loss_exponent
        self.reference_rssi_dbm = reference_rssi_dbm
    
    def calculate_path_loss(self, distance_m: float) -> float:
        """
        Calculate path loss at given distance.
        
        Args:
            distance_m: Distance between devices (meters)
        
        Returns:
            Path loss in dB (positive value, higher = more loss)
        """
        if distance_m <= 0:
            return 0.0  # No loss at zero distance (unrealistic but safe)
        
        # PL(d) = PL(d₀) + 10n*log₁₀(d/d₀)
        path_loss_db = 10.0 * self.path_loss_exponent * \
                       math.log10(distance_m / self.reference_distance_m)
        return path_loss_db
    
    def calculate_rssi(self, distance_m: float) -> float:
        """
        Calculate RSSI (received signal strength) at given distance.
        
        Args:
            distance_m: Distance between devices (meters)
        
        Returns:
            RSSI in dBm
        """
        path_loss = self.calculate_path_loss(distance_m)
        # RSSI = reference_rssi - path_loss
        rssi = self.reference_rssi_dbm - path_loss
        # Clamp to physically realizable range
        return clamp(rssi, -200.0, MAX_RSSI_DBM)


# ============================================================================
# RF LINK CHANNEL (COMBINED MODEL)
# ============================================================================

@dataclass
class ChannelState:
    """State of RF link between two drones."""
    distance_m: float              # Current distance
    path_loss_db: float            # Free-space path loss
    fading_db: float               # Rice fading
    total_loss_db: float           # Combined loss
    rssi_dbm: float                # Received Signal Strength Indicator
    link_quality: float            # Normalized 0-1 (1=excellent, 0=none)
    packet_loss_probability: float # Probability of dropped packet
    estimated_latency_ms: float    # Latency (milliseconds)


class RFLink:
    """
    RF Link between two drones
    
    Combines path loss, fading, and applies realistic effects:
    - RSSI calculation
    - Packet loss injection
    - Latency modeling
    - Link quality estimation
    """
    
    def __init__(self, sender_id: int, receiver_id: int,
                 path_loss_model: PathLossModel,
                 fading_channel: RiceFadingChannel):
        """
        Initialize RF link.
        
        Args:
            sender_id: ID of sending drone
            receiver_id: ID of receiving drone
            path_loss_model: Configured path loss model
            fading_channel: Configured fading channel
        """
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.path_loss_model = path_loss_model
        self.fading_channel = fading_channel
        self.state = ChannelState(
            distance_m=0, path_loss_db=0, fading_db=0, total_loss_db=0,
            rssi_dbm=REFERENCE_RSSI_DBM, link_quality=1.0,
            packet_loss_probability=0, estimated_latency_ms=0
        )
    
    def update(self, distance_m: float) -> ChannelState:
        """
        Update RF link state based on current distance.
        
        Args:
            distance_m: Current distance between drones (meters)
        
        Returns:
            Updated ChannelState
        """
        # Calculate path loss based on distance
        self.state.distance_m = distance_m
        self.state.path_loss_db = self.path_loss_model.calculate_path_loss(distance_m)
        
        # Generate fading sample
        self.state.fading_db = self.fading_channel.generate_fading()
        
        # Total loss = path loss + fading
        self.state.total_loss_db = self.state.path_loss_db + self.state.fading_db
        
        # RSSI = reference - total loss
        self.state.rssi_dbm = self.path_loss_model.reference_rssi_dbm - self.state.total_loss_db
        self.state.rssi_dbm = clamp(self.state.rssi_dbm, -200.0, MAX_RSSI_DBM)
        
        # Calculate link quality (0-1 scale)
        # Quality = 0 at sensitivity threshold, 1 at reference distance
        rssi_range = REFERENCE_RSSI_DBM - SENSITIVITY_DBM
        current_range = self.state.rssi_dbm - SENSITIVITY_DBM
        link_quality = clamp(current_range / rssi_range, 0.0, 1.0)
        self.state.link_quality = link_quality
        
        # Packet loss probability
        # - Base loss rate (5%)
        # - Additional loss if RSSI drops below threshold
        self.state.packet_loss_probability = BASE_PACKET_LOSS_PROBABILITY
        if self.state.rssi_dbm < RSSI_PACKET_LOSS_THRESHOLD_DBM:
            # Increase loss exponentially as RSSI drops
            threshold_exceeded_db = RSSI_PACKET_LOSS_THRESHOLD_DBM - self.state.rssi_dbm
            additional_loss = 0.1 * (threshold_exceeded_db / 10.0)  # ~10% per 10dB
            self.state.packet_loss_probability = clamp(
                self.state.packet_loss_probability + additional_loss, 0.0, 1.0
            )
        
        # Latency modeling
        # - Base latency (5ms)
        # - Additional latency if link quality degrades
        self.state.estimated_latency_ms = BASE_LATENCY_MS
        if self.state.rssi_dbm < self.path_loss_model.reference_rssi_dbm:
            # RSSI below reference → add latency
            rssi_delta_db = self.path_loss_model.reference_rssi_dbm - self.state.rssi_dbm
            additional_latency = rssi_delta_db * (LATENCY_RSSI_SCALE / 10.0)
            self.state.estimated_latency_ms += additional_latency
        
        # Return a copy to prevent aliasing issues in tests/clients
        return replace(self.state)
    
    def get_state(self) -> ChannelState:
        """Return current channel state."""
        return self.state
    
    def is_connected(self) -> bool:
        """Check if link is above sensitivity threshold."""
        return self.state.rssi_dbm >= SENSITIVITY_DBM


# ============================================================================
# CHANNEL MANAGER (MULTI-DRONE)
# ============================================================================

class ChannelManager:
    """
    Manages RF links between all drones in swarm.
    
    Tracks bidirectional communication links, calculates RSSI, packet loss,
    and latency between all drone pairs.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize channel manager.
        
        Args:
            seed: RNG seed for reproducible fading
        """
        self.seed = seed
        self.path_loss_model = PathLossModel()
        self.fading_channel = RiceFadingChannel(seed=seed)
        self.links: dict = {}  # Dictionary of RF links: (sender_id, receiver_id) -> RFLink
    
    def ensure_link(self, sender_id: int, receiver_id: int) -> RFLink:
        """
        Get or create RF link between two drones.
        
        Args:
            sender_id: Sending drone ID
            receiver_id: Receiving drone ID
        
        Returns:
            RFLink object
        """
        key = (sender_id, receiver_id)
        if key not in self.links:
            self.links[key] = RFLink(sender_id, receiver_id,
                                     self.path_loss_model, self.fading_channel)
        return self.links[key]
    
    def update_link(self, sender_id: int, receiver_id: int,
                    distance_m: float) -> ChannelState:
        """
        Update RF link state and return channel state.
        
        Args:
            sender_id: Sending drone ID
            receiver_id: Receiving drone ID
            distance_m: Current distance between drones
        
        Returns:
            ChannelState with RSSI, latency, packet loss
        """
        link = self.ensure_link(sender_id, receiver_id)
        return link.update(distance_m)
    
    def get_channel_state(self, sender_id: int, receiver_id: int) -> ChannelState:
        """
        Get current channel state between two drones.
        
        Args:
            sender_id: Sending drone ID
            receiver_id: Receiving drone ID
        
        Returns:
            ChannelState
        """
        link = self.ensure_link(sender_id, receiver_id)
        return link.get_state()
    
    def is_link_connected(self, sender_id: int, receiver_id: int) -> bool:
        """
        Check if link is active (above sensitivity threshold).
        
        Args:
            sender_id: Sending drone ID
            receiver_id: Receiving drone ID
        
        Returns:
            True if link is connected
        """
        link = self.ensure_link(sender_id, receiver_id)
        return link.is_connected()
    
    def get_all_link_states(self) -> dict:
        """
        Get all current link states.
        
        Returns:
            Dictionary of all link states: (sender_id, receiver_id) -> ChannelState
        """
        return {key: link.get_state() for key, link in self.links.items()}
