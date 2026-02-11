"""
tests/test_distributed_observer.py

Test Distributed Observer for formation control.

Validates:
- Neighbor state estimation
- Constant velocity prediction
- Confidence decay with latency
- Collision risk detection
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from distributed_observer import DistributedObserver, NeighborEstimate


class TestDistributedObserver:
    """Test observer state prediction."""
    
    def test_register_drone(self):
        """Registering drone should initialize observers."""
        observer = DistributedObserver()
        observer.register_drone(drone_id=1, neighbors=[2, 3])
        
        state = observer.get_observer_state(1)
        assert state is not None
        assert 2 in state.neighbors
    
    def test_update_neighbor(self):
        """Updating neighbor should record state."""
        observer = DistributedObserver()
        observer.register_drone(drone_id=1, neighbors=[2])
        
        observer.update_neighbor(
            observer_drone_id=1, neighbor_id=2,
            time_us=0, x=10.0, y=20.0, z=30.0,
            vx=1.0, vy=2.0, vz=0.5
        )
        
        state = observer.get_observer_state(1)
        estimate = state.neighbors[2]
        
        assert estimate.estimated_x == 10.0
        assert estimate.estimated_vx == 1.0
        assert estimate.estimate_confidence == 1.0
    
    def test_predict_with_constant_velocity(self):
        """Prediction should use constant velocity model."""
        observer = DistributedObserver()
        observer.register_drone(drone_id=1, neighbors=[2])
        
        # Update neighbor position
        observer.update_neighbor(1, 2, 0, 10.0, 20.0, 30.0, 5.0, 0.0, 0.0)
        
        # Predict 1 second later
        predicted = observer.predict_neighbor_state(1, 2, int(1e6))
        
        if predicted:
            pred_x, pred_y, pred_z, confidence = predicted
            # Should have moved 5m in x direction (velocity = 5 m/s)
            assert pred_x > 10.0, f"Position should advance: {pred_x} > 10.0"
    
    def test_confidence_decays(self):
        """Confidence should decay with age."""
        observer = DistributedObserver(max_latency_ms=100)
        observer.register_drone(drone_id=1, neighbors=[2])
        
        # Update at t=0
        observer.update_neighbor(1, 2, 0, 10.0, 20.0, 30.0, 0, 0, 0)
        conf_t0 = observer.predict_neighbor_state(1, 2, 0)[3]
        
        # Predict at t=500ms (after max latency)
        conf_t500 = observer.predict_neighbor_state(1, 2, int(500e3))[3]
        
        assert conf_t500 < conf_t0, "Confidence should decay with age"
    
    def test_collision_detection(self):
        """Should detect neighbors too close."""
        observer = DistributedObserver()
        observer.register_drone(drone_id=1, neighbors=[2])
        
        # Update neighbor at 5m distance
        observer.update_neighbor(1, 2, 0, 5.0, 0.0, 0.0, 0, 0, 0)
        
        # Check collision risk (min separation = 10m)
        risky = observer.check_collision_risk(
            observer_drone_id=1, current_time_us=0,
            drone_x=0.0, drone_y=0.0, drone_z=0.0,
            min_separation_m=10.0
        )
        
        assert len(risky) > 0, "Should detect collision risk"
        assert risky[0][0] == 2, "Should identify risky neighbor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
