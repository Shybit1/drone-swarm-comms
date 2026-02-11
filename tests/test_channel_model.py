"""
tests/test_channel_model.py

Test RF channel modeling with Rice fading.

Validates:
- Path loss calculation (distance-dependent)
- RSSI computation
- Packet loss probability
- Latency injection
- Rice fading statistics
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from channel_model import (
    PathLossModel, RiceFadingChannel, RFLink, ChannelManager,
    REFERENCE_DISTANCE_M, PATH_LOSS_EXPONENT, REFERENCE_RSSI_DBM
)


class TestPathLossModel:
    """Test path loss calculations."""
    
    def test_path_loss_at_reference_distance(self):
        """At reference distance, path loss should be 0."""
        model = PathLossModel()
        loss = model.calculate_path_loss(REFERENCE_DISTANCE_M)
        assert abs(loss) < 0.01, f"Path loss at reference distance should be ~0, got {loss}"
    
    def test_path_loss_increases_with_distance(self):
        """Path loss should increase with distance."""
        model = PathLossModel()
        loss_1m = model.calculate_path_loss(1.0)
        loss_10m = model.calculate_path_loss(10.0)
        loss_100m = model.calculate_path_loss(100.0)
        
        assert loss_1m < loss_10m < loss_100m, "Path loss should increase with distance"
    
    def test_rssi_at_reference_distance(self):
        """RSSI at reference distance should equal reference RSSI."""
        model = PathLossModel()
        rssi = model.calculate_rssi(REFERENCE_DISTANCE_M)
        assert abs(rssi - REFERENCE_RSSI_DBM) < 0.1


class TestRiceFadingChannel:
    """Test Rice fading distribution."""
    
    def test_fading_generation(self):
        """Fading should be randomly distributed around 0."""
        channel = RiceFadingChannel(seed=42)
        
        samples = [channel.generate_fading() for _ in range(1000)]
        mean = np.mean(samples)
        std = np.std(samples)
        
        # Mean should be close to 0
        assert abs(mean) < 0.5, f"Fading mean should be ~0, got {mean}"
        
        # Std should match configured value (approximately)
        assert 1.5 < std < 2.5, f"Fading std should be ~2, got {std}"
    
    def test_deterministic_with_seed(self):
        """Same seed should produce same sequence."""
        channel1 = RiceFadingChannel(seed=42)
        channel2 = RiceFadingChannel(seed=42)
        
        samples1 = [channel1.generate_fading() for _ in range(10)]
        samples2 = [channel2.generate_fading() for _ in range(10)]
        
        assert samples1 == samples2, "Same seed should produce same fading"


class TestRFLink:
    """Test RF link channel modeling."""
    
    def test_link_rssi_decreases_with_distance(self):
        """RSSI should decrease with distance."""
        path_loss = PathLossModel()
        fading = RiceFadingChannel(seed=42)
        link = RFLink(sender_id=1, receiver_id=2, path_loss_model=path_loss,
                     fading_channel=fading)
        
        state_1m = link.update(1.0)
        state_100m = link.update(100.0)
        
        assert state_1m.rssi_dbm > state_100m.rssi_dbm, \
            "RSSI should decrease with distance"
    
    def test_link_quality_normalized(self):
        """Link quality should be between 0 and 1."""
        path_loss = PathLossModel()
        fading = RiceFadingChannel(seed=42)
        link = RFLink(sender_id=1, receiver_id=2, path_loss_model=path_loss,
                     fading_channel=fading)
        
        for distance in [1, 10, 50, 100, 200]:
            state = link.update(float(distance))
            assert 0 <= state.link_quality <= 1, \
                f"Link quality out of range: {state.link_quality}"
    
    def test_packet_loss_increases_at_low_rssi(self):
        """Packet loss should increase when RSSI is very low."""
        path_loss = PathLossModel()
        fading = RiceFadingChannel(seed=42)
        link = RFLink(sender_id=1, receiver_id=2, path_loss_model=path_loss,
                     fading_channel=fading)
        
        # Close range: low loss
        state_close = link.update(5.0)
        loss_close = state_close.packet_loss_probability
        
        # Far range: higher loss
        state_far = link.update(500.0)
        loss_far = state_far.packet_loss_probability
        
        assert loss_far >= loss_close, "Packet loss should increase at far range"


class TestChannelManager:
    """Test multi-drone channel management."""
    
    def test_ensure_link_creates_new(self):
        """ensure_link should create new links on demand."""
        mgr = ChannelManager(seed=42)
        
        link = mgr.ensure_link(1, 2)
        assert link is not None
        assert link.sender_id == 1
        assert link.receiver_id == 2
    
    def test_ensure_link_reuses_existing(self):
        """ensure_link should reuse existing link."""
        mgr = ChannelManager(seed=42)
        
        link1 = mgr.ensure_link(1, 2)
        link2 = mgr.ensure_link(1, 2)
        
        assert link1 is link2, "Should reuse same link object"
    
    def test_update_link_state(self):
        """update_link should update and return state."""
        mgr = ChannelManager(seed=42)
        
        state = mgr.update_link(1, 2, distance_m=50.0)
        
        assert state.distance_m == 50.0
        assert state.rssi_dbm < REFERENCE_RSSI_DBM  # Should have path loss


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
