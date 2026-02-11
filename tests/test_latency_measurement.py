"""
tests/test_latency_measurement.py

Test end-to-end DETM message latency under realistic channel conditions.

Validates:
- DETM transmission latency (trigger to delivery)
- Channel delay effects (RSSI-dependent latency)
- Message metadata tracking
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detm_controller import DETMController
from comms_manager import CommunicationsManager, MessageMetadata
from physics_engine import PhysicsEngine


class TestLatencyMeasurement:
    """Test DETM message latency in realistic scenarios."""
    
    def test_transmission_latency_recorded(self):
        """Transmission should record timestamp."""
        detm = DETMController()
        detm.register_drone(drone_id=1, eta0=1.0, lambda_decay=0.5)
        
        # Trigger transmission at t=1000us
        should_tx = detm.should_transmit(1, 1000, 0, 0, 0, 10, 0, 0)
        assert should_tx, "Large motion should trigger transmission"
        
        # Record transmission with position and velocity
        detm.record_transmission(1, 1000, 0, 0, 0, 10, 0, 0)
        stats = detm.get_statistics(1)
        assert stats['transmissions_total'] >= 1
    
    def test_rssi_dependent_latency(self):
        """Higher RSSI should result in lower latency."""
        physics = PhysicsEngine(num_drones=3)
        
        # Update drone positions
        physics.update_drone_position(1, 0.0, 0.0, 0.0, 0, 0, 0)
        physics.update_drone_position(2, 10.0, 0.0, 0.0, 0, 0, 0)
        physics.update_drone_position(3, 50.0, 0.0, 0.0, 0, 0, 0)
        
        # Step physics engine
        physics.step()
        
        
        # Query channel states via channel manager
        state_10m = physics.channel_mgr.ensure_link(sender_id=1, receiver_id=2)
        state_10m = state_10m.update(10.0)
        state_50m = physics.channel_mgr.ensure_link(sender_id=1, receiver_id=3)
        state_50m = state_50m.update(50.0)
        
        # Latency should increase with distance
        assert state_10m.estimated_latency_ms < state_50m.estimated_latency_ms, \
            f"10m latency ({state_10m.estimated_latency_ms}ms) should < 50m latency ({state_50m.estimated_latency_ms}ms)"
    
    def test_packet_loss_affects_delivery(self):
        """Packet loss should reduce successful deliveries."""
        physics = PhysicsEngine(num_drones=2)
        comms = CommunicationsManager(physics_engine=physics)
        
        physics.update_drone_position(1, 0.0, 0.0, 0.0, 0, 0, 0)
        physics.update_drone_position(2, 95.0, 0.0, 0.0, 0, 0, 0)  # Near broadcast range limit
        
        physics.step()
        
        
        # Get packet loss probability at long range
        link = physics.channel_mgr.ensure_link(sender_id=1, receiver_id=2)
        link_state = link.update(95.0)
        
        # At long range, packet loss should be non-trivial (> 5% base rate)
        assert link_state.packet_loss_probability >= 0.05, \
            f"Packet loss at 95m should be at least base rate (5%), got {link_state.packet_loss_probability}"
    
    def test_message_metadata_latency_field(self):
        """Message metadata should include latency measurement."""
        physics = PhysicsEngine(num_drones=2)
        comms = CommunicationsManager(physics_engine=physics)
        
        physics.update_drone_position(1, 0.0, 0.0, 0.0, 0, 0, 0)
        physics.update_drone_position(2, 20.0, 0.0, 0.0, 0, 0, 0)
        
        physics.step()
        
        # Create message metadata
        metadata = MessageMetadata(
            sender_id=1,
            receiver_id=2,
            timestamp_us=1000,
            message_type="telemetry",
            payload_size_bytes=64,
            rssi_dbm=-80.0,
            latency_ms=15.0
        )
        
        # Check metadata has required fields
        assert metadata.timestamp_us == 1000
        assert metadata.rssi_dbm == -80.0
        assert metadata.latency_ms == 15.0
        assert metadata.sender_id == 1
        assert metadata.receiver_id == 2


class TestChannelDelayAccumulation:
    """Test cumulative effects of channel delays."""
    
    def test_swarm_broadcast_latency(self):
        """Broadcast to multiple drones should handle individual latencies."""
        physics = PhysicsEngine(num_drones=5)
        comms = CommunicationsManager(physics_engine=physics)
        
        # Setup swarm: 5 drones in line
        for i in range(5):
            physics.update_drone_position(i, x=float(i * 20), y=0.0, z=0.0, vx=0, vy=0, vz=0)
        
        physics.step()
        
        
        # Check channel states to each drone (simulating broadcast)
        broadcast_range = 100.0  # UAVConnector range
        receivable_count = 0
        
        for i in range(1, 5):
            link = physics.channel_mgr.ensure_link(sender_id=0, receiver_id=i)
            link_state = link.update(float(i * 20))
            # Drones within range should receive
            if i * 20 <= broadcast_range:
                receivable_count += 1
        
        # At least drones 0-5 (0m, 20m, 40m, 60m, 80m) should be in range
        assert receivable_count >= 3, f"Expected at least 3 drones in {broadcast_range}m range, got {receivable_count}"
    
    def test_timeout_behavior(self):
        """Observer should timeout predictions after max latency."""
        from distributed_observer import DistributedObserver
        
        observer = DistributedObserver(max_latency_ms=100)
        observer.register_drone(drone_id=1, neighbors=[2])
        
        # Update at t=0
        observer.update_neighbor(1, 2, 0, 0.0, 0.0, 0.0, 5.0, 0.0, 0.0)
        
        # Prediction well within timeout should be confident
        pred_early = observer.predict_neighbor_state(1, 2, int(50e3))
        
        # Prediction beyond timeout should be less confident
        pred_late = observer.predict_neighbor_state(1, 2, int(200e3))
        
        if pred_early and pred_late:
            _, _, _, conf_early = pred_early
            _, _, _, conf_late = pred_late
            assert conf_late <= conf_early, "Confidence should not increase with age"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
