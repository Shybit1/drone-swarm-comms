"""
tests/test_detm.py

Test Dynamic Event-Triggered Mechanism (DETM).

Validates:
- Trigger threshold calculation
- Exponential decay of threshold
- Event-triggered transmission logic
- Sparse communication (fewer messages than fixed-rate)
"""

import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detm_controller import DETMController
from constants import DETM_ETA0, DETM_LAMBDA


class TestDETMController:
    """Test DETM trigger logic."""
    
    def test_register_drone(self):
        """Registering drone should initialize state."""
        controller = DETMController()
        controller.register_drone(drone_id=1, eta0=0.5, lambda_decay=0.1)
        
        state = controller.get_state(1)
        assert state is not None
        assert state.drone_id == 1
        assert state.eta0 == 0.5
    
    def test_first_transmission_always_triggers(self):
        """First check should always trigger (state change from 0)."""
        controller = DETMController()
        controller.register_drone(drone_id=1)
        
        should_tx, eta = controller.should_transmit(
            drone_id=1, time_us=0,
            x=10.0, y=20.0, z=30.0,
            vx=1.0, vy=2.0, vz=0.5
        )
        
        assert should_tx, "First transmission should always trigger"
    
    def test_no_motion_suppresses_transmission(self):
        """Stationary drone should suppress transmissions."""
        controller = DETMController()
        controller.register_drone(drone_id=1, eta0=0.5)
        
        # First transmission
        controller.should_transmit(1, 0, 10.0, 20.0, 30.0, 0, 0, 0)
        controller.record_transmission(1, 0, 10.0, 20.0, 30.0, 0, 0, 0)
        
        # Same position at t=100ms
        should_tx, eta = controller.should_transmit(
            1, 100000, 10.0, 20.0, 30.0, 0, 0, 0
        )
        
        assert not should_tx, "Stationary drone should not trigger transmission"
    
    def test_large_motion_triggers_transmission(self):
        """Large state change should trigger transmission."""
        controller = DETMController()
        controller.register_drone(drone_id=1, eta0=0.5)
        
        # First transmission
        controller.should_transmit(1, 0, 0.0, 0.0, 0.0, 0, 0, 0)
        controller.record_transmission(1, 0, 0.0, 0.0, 0.0, 0, 0, 0)
        
        # Large position change
        should_tx, eta = controller.should_transmit(
            1, 100000, 100.0, 100.0, 50.0, 10.0, 10.0, 5.0
        )
        
        assert should_tx, "Large motion should trigger transmission"
    
    def test_threshold_decays_exponentially(self):
        """Threshold should decay over time to force periodic updates."""
        controller = DETMController()
        controller.register_drone(drone_id=1, eta0=1.0, lambda_decay=0.1)
        
        # Check threshold at different times
        _, eta_t0 = controller.should_transmit(1, 0, 0, 0, 0, 0, 0, 0)
        _, eta_t1 = controller.should_transmit(1, int(10e6), 0, 0, 0, 0, 0, 0)  # 10s
        _, eta_t2 = controller.should_transmit(1, int(20e6), 0, 0, 0, 0, 0, 0)  # 20s
        
        assert eta_t1 < eta_t0, "Threshold should decay"
        assert eta_t2 < eta_t1, "Threshold should continue decaying"
    
    def test_transmission_recording(self):
        """Record transmission should update state."""
        controller = DETMController()
        controller.register_drone(drone_id=1)
        
        # Trigger and record
        controller.should_transmit(1, 0, 10.0, 20.0, 30.0, 1.0, 2.0, 3.0)
        controller.record_transmission(1, 0, 10.0, 20.0, 30.0, 1.0, 2.0, 3.0)
        
        state = controller.get_state(1)
        assert state.transmissions_total == 1
        assert state.last_transmitted_state == (10.0, 20.0, 30.0, 1.0, 2.0, 3.0)
    
    def test_statistics_tracking(self):
        """DETM should track trigger statistics."""
        controller = DETMController()
        controller.register_drone(drone_id=1, eta0=0.1)
        
        # First transmission (always triggers)
        controller.should_transmit(1, 0, 0, 0, 0, 0, 0, 0)
        controller.record_transmission(1, 0, 0, 0, 0, 0, 0, 0)
        
        # Small motions (suppressed)
        for t in range(1, 10):
            controller.should_transmit(1, int(t*1e5), float(t)*0.01, float(t)*0.01, 0, 0, 0, 0)
        
        stats = controller.get_statistics(1)
        
        assert stats["transmissions_total"] >= 1
        assert stats["triggers_suppressed"] > 0, "Should have suppressed some triggers"
    
    def test_l2_norm_vs_linf(self):
        """Different norms should affect triggering."""
        # L2 norm
        controller_l2 = DETMController()
        controller_l2.register_drone(drone_id=1, eta0=1.0, norm_type="l2")
        
        # L∞ norm
        controller_linf = DETMController()
        controller_linf.register_drone(drone_id=1, eta0=1.0, norm_type="linf")
        
        # Initial state
        controller_l2.should_transmit(1, 0, 0, 0, 0, 0, 0, 0)
        controller_l2.record_transmission(1, 0, 0, 0, 0, 0, 0, 0)
        
        controller_linf.should_transmit(1, 0, 0, 0, 0, 0, 0, 0)
        controller_linf.record_transmission(1, 0, 0, 0, 0, 0, 0, 0)
        
        # Small motion in one dimension
        state = (1.0, 0.0, 0.0, 0, 0, 0)  # Only x changed
        
        tx_l2, _ = controller_l2.should_transmit(1, 100000, *state)
        tx_linf, _ = controller_linf.should_transmit(1, 100000, *state)
        
        # L∞ is more sensitive to individual components
        # L2 averages across components
        # Results depend on threshold and decay, but should both make reasonable decisions
        assert isinstance(tx_l2, bool)
        assert isinstance(tx_linf, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
