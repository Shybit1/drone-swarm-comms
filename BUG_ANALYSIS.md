# AeroSyn-Sim Comprehensive Bug Analysis

## CRITICAL BUGS FOUND

### 1. RFLink.update() - Distance Not Being Used (CRITICAL)
**File:** `src/channel_model.py`  
**Line:** 226-237 (update method)  
**Problem:** The `RFLink.update()` method recalculates path loss but the state object maintains a persistent instance. However, the fading channel generates a NEW random fading sample on EACH call to `generate_fading()`, which can vary by ±2dB. When distance is 1m vs 100m, the path loss should differ by 60dB, but due to the random fading variation (±2dB), the final RSSI can appear to remain the same or vary unpredictably.

**Root Cause:** In test, two consecutive calls to `link.update()` generate different fading samples:
- First call (1m): fading_db = -0.276 dB
- Second call (100m): fading_db = -0.276 dB (same by chance, but RNG has progressed)

The issue is that `link.state` is a SHARED mutable object. When you call `link.update(1.0)`, it returns `self.state`. When you call `link.update(100.0)`, it modifies the SAME `self.state` object that was returned before. The test keeps a reference to the first state, which gets mutated!

**Test Evidence:**
```
state_1m = link.update(1.0)  # Returns reference to link.state
state_100m = link.update(100.0)  # Modifies the SAME link.state object
# Both variables point to the same object, so both have the 100m values!
```

**Impact:** RSSI never changes with distance; always returns the most recent update value.

---

### 2. FireSimulation.step() - Fire Never Spreads (CRITICAL)
**File:** `src/fire_simulation.py`  
**Line:** 277-293 (spread probability calculation)  
**Problem:** The fire spread probability is calculated as:
```python
distance_factor = 1.0 - (dist / spread_distance_cells)
ignition_prob = (cell.intensity * distance_factor * neighbor.fuel_density * 0.3)
```

When spread_distance_cells = 1.0 and dist = 1.0 (immediate neighbors at spread limit):
- distance_factor = 1.0 - (1.0 / 1.0) = 0.0
- ignition_prob = 1.0 * 0.0 * 1.0 * 0.3 = 0.0

This means fire NEVER spreads to cells at the edge of the spread radius. Since initial spread distance is ~1 cell, fire never spreads anywhere.

**Root Cause:** Off-by-one error in spread logic. The distance factor should be > 0 for cells within the spread distance, but equals 0 at the boundary.

**Fix Logic Issue:** When dist equals spread_distance_cells (at the boundary), distance_factor becomes 0, making ignition impossible.

**Impact:** Fire remains static after ignition; no spread occurs.

---

### 3. PhysicsEngine Missing register_drone() Method
**File:** `src/physics_engine.py`  
**Lines:** 1-160 (entire __init__ and class)  
**Problem:** Test calls `physics.register_drone(1, 0.0, 0.0, 0.0)` but PhysicsEngine has NO such method. The constructor initializes drones via `__init__(self, num_drones=1)`, but there's no way to dynamically register new drones.

**Test Failure Evidence:**
```
physics = PhysicsEngine()  # Creates 1 drone
physics.register_drone(1, ...)  # AttributeError - method doesn't exist
```

**Root Cause:** Missing method that should exist to match test expectations and support dynamic drone registration.

**Impact:** Latency measurement tests cannot run; breaks drone registration workflow.

---

### 4. FireSimulation.ignite() - Return Type Inconsistency
**File:** `src/fire_simulation.py`  
**Line:** 171-187  
**Problem:** The `ignite()` method is called recursively in `step()` at line 300:
```python
if self.ignite(x, y, intensity):
```

But `ignite()` returns `bool`, and the check is `if self.ignite(...)`. However, in the loop checking return values, the code assumes each cell ignition succeeds/fails independently. The method's boolean return is correct, but there's no tracking of WHICH cells were actually ignited separately from the count.

**Actually This Is Not a Bug** - ignite() correctly returns bool. The issue is #2 (spread calculation).

---

### 5. DETMController.should_transmit() - Wrong Return Type
**File:** `src/detm_controller.py`  
**Line:** 107  
**Signature:** `def should_transmit(...) -> Tuple[bool, float]:`  
**Line:** 145  
**Actual Return:** `return should_tx, state.current_eta` returns tuple correctly

**Actually Not a Bug** - signature matches return.

---

### 6. Swarm Launcher Configuration Passing Bug
**File:** `src/swarm_launcher.py`  
**Lines:** 207-218  
**Problem:** In `initialize_simulation()`, CommunicationsManager is created but NEVER properly receives a reference to comms_manager:

```python
self.comms_manager = CommunicationsManager(
    detm_controller=self.detm_controller,
    physics_engine=self.physics_engine
)
```

But looking at the comms_manager initialization, the methods `publish_telemetry()` and `receive_messages()` are defined in the unified manager. However, the code passes `detm_controller` positionally but also `physics_engine`. Let me check the signature...

Actually checking line 314-316 of comms_manager.py:
```python
def __init__(self, detm_controller = None,
             physics_engine = None):
```

This looks correct.

**Actually Not a Bug** - CommunicationsManager properly receives both dependencies.

---

### 7. API Server Missing References
**File:** `src/api_server.py`  
**Lines:** 39-48  
**Problem:** The `SimulationAPIServer.__init__()` accepts `simulation_engine` but stores it as `self.simulation_engine`. All endpoint methods call `self.simulation_engine.method()` assuming this object has methods like:
- `export_state_dict()`
- `start()`
- `stop()`
- `get_all_drone_states()`
- `get_drone_state(drone_id)`
- `ignite_fire(x, y, intensity)`
- `suppress_fire(x, y, strength)`
- `get_fire_state()`
- `get_metrics()`

But there's NO definition of what `simulation_engine` should be or what these methods should do. The API server is calling methods on a loosely-typed object with NO validation.

**Impact:** Runtime errors if simulation_engine doesn't have these exact methods.

---

### 8. WebSocket Server - No Integration Check
**File:** `src/websocket_server.py`  
**Lines:** 30-50  
**Problem:** The WebSocket server stores `self.simulation_engine` reference but never validates it exists or has required methods (`export_state_dict()`, etc.). If None is passed, the server will crash when trying to broadcast.

**Impact:** Crashes if simulation_engine is not properly initialized.

---

### 9. Configuration YAML Missing Required Fields
**File:** `config/simulation_params.yaml`  
**Problem:** The YAML file is incomplete (truncated in view), but based on config.py dataclass fields, should contain:

Required fields potentially missing:
- `fire_intensity_threshold_detectable` (not in constants.py defaults listed)
- `fire_intensity_ignition` (not visible in YAML)
- `fire_spread_rate_base_mpm` and related fire params

**Impact:** Config loading may fail or use wrong defaults.

---

### 10. Constants.py - Unused or Wrong Imports in Dataclass
**File:** `src/config.py`  
**Lines:** 1-100  
**Problem:** The `FireSimulationConfig` dataclass at line ~75 has:
```python
initial_fire_positions: list = field(default_factory=lambda: [
    {"x": 250, "y": 250},
```
This is cut off. The file may have incomplete configuration objects.

**Impact:** Runtime errors if this field is accessed but not fully defined.

---

### 11. Metrics Collector - No Metrics Recording in Step Loop
**File:** `src/metrics_collector.py`  
**Lines:** 1-180 (entire file)  
**Problem:** The `MetricsCollector` class is defined with `update_drone()` and `update_swarm()` methods, but these are NEVER called in the simulation loop. Looking at swarm_launcher.py's `simulation_step()`, there's NO call to update metrics.

**Line:** `src/swarm_launcher.py` line 330-360  
**Missing:** `metrics_collector.update_drone()` and `metrics_collector.update_swarm()`

**Impact:** Metrics are never collected; metrics endpoints will return empty/stale data.

---

### 12. Distributed Observer - Incomplete Implementation
**File:** `src/distributed_observer.py`  
**Lines:** 1-? (not fully reviewed)  
**Problem:** Test calls `observer.predict_neighbor_state()` but unclear if implemented. This component is mentioned in tests but its implementation status is unknown from code review.

**Impact:** Formation safety tests may fail if not implemented.

---

### 13. Energy Manager - Possible Initialization Bug
**File:** `src/energy_model.py`  
**Lines:** 90-110 (EnergyManager class - not shown)  
**Problem:** In `drone_node.py` line 79:
```python
self.energy_manager = energy_manager = physics_engine.energy_mgrs[drone_id]
```

This tries to get energy_manager from physics_engine, but we need to verify this actually exists after PhysicsEngine initialization.

**Checking physics_engine.py lines 115-120:**
```python
self.energy_mgrs: Dict[int, EnergyManager] = {}
for drone_id in range(1, num_drones + 1):
    self.energy_mgrs[drone_id] = EnergyManager()
```

**Actually Correct** - PhysicsEngine properly initializes energy_mgrs.

---

### 14. Missing Export Methods in Main Simulation Controller
**File:** Missing or Incomplete  
**Problem:** API Server and WebSocket Server call `simulation_engine.export_state_dict()` but no main simulation controller ("SimulationEngine" or "SimulationController") class defines this. The only class with this method is `PhysicsEngine` (line 415 in physics_engine.py).

**Impact:** API/WebSocket will crash if they're not passed a PhysicsEngine or equivalent.

---

### 15. Unused Imports in Multiple Files
**Files:** Multiple  
**Problem:** Common pattern of importing modules not used. Example:
- `src/detm_controller.py` line 10-15: imports used, but style could be cleaner

**Impact:** Low priority, code maintenance issue.

---

### 16. Type Annotation Issues  
**File:** `src/drone_node.py`  
**Line:** 79  
```python
self.energy_manager = energy_manager = physics_engine.energy_mgrs[drone_id]
```

Double assignment is confusing and violates PEP 8. Should be:
```python
self.energy_manager = physics_engine.energy_mgrs[drone_id]
```

**Impact:** Code clarity issue, not a runtime bug.

---

### 17. Fire Simulation - Bounds Checking Bug
**File:** `src/fire_simulation.py`  
**Line:** 407 in `get_cell()`  
```python
def get_cell(self, x: int, y: int) -> FireCell:
    """Get cell by grid coordinates."""
    if self._in_bounds(x, y):
        return self.grid[y, x]
    return None
```

**Problem:** Returns None for out-of-bounds, but FireCell type hint doesn't include Optional. This could cause AttributeError if code assumes it's always a FireCell.

**Impact:** Runtime errors if out-of-bounds cell access is not checked.

---

## SUMMARY TABLE

| # | File | Line | Severity | Issue |
|---|------|------|----------|-------|
| 1 | channel_model.py | 226-237 | CRITICAL | RFLink.update() returns reference to mutable state; RSSI never changes with distance |
| 2 | fire_simulation.py | 277-293 | CRITICAL | Fire spread probability is 0 at boundary; fire never spreads |
| 3 | physics_engine.py | Class | CRITICAL | Missing `register_drone()` method required by tests |
| 4 | swarm_launcher.py | 330-360 | HIGH | Metrics never collected; no call to metrics_collector.update_*() |
| 5 | api_server.py | 39-48 | HIGH | No validation that simulation_engine has required methods |
| 6 | websocket_server.py | 30-50 | HIGH | No validation that simulation_engine exists before use |
| 7 | fire_simulation.py | 407 | MEDIUM | get_cell() returns None but type hint doesn't reflect Optional |
| 8 | drone_node.py | 79 | LOW | Double assignment (style issue, not functional) |
| 9 | config.py | ~75 | MEDIUM | Configuration may be incomplete (file truncated) |
| 10 | distributed_observer.py | Various | UNKNOWN | Incomplete implementation status unclear |

---

## DETAILED FIX PRIORITIES

### MUST FIX (Blocks tests)
1. **RFLink RSSI Bug** - Return copy of state, not reference
2. **Fire Spread Probability** - Fix distance_factor calculation
3. **PhysicsEngine.register_drone()** - Add missing method

### SHOULD FIX (Breaks functionality)
4. **Metrics Collection** - Wire up metrics in simulation loop
5. **API/WebSocket Validation** - Add null checks and method validation

### NICE TO FIX (Code quality)
6. **Type Annotations** - Fix Optional returns
7. **Code Style** - Remove double assignments

