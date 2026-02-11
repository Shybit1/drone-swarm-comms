# AeroSyn-Sim Quick Start Guide

## Overview

AeroSyn-Sim is a comprehensive cyber-physical software-in-the-loop (SITL) simulator for autonomous drone swarms. This guide walks you through launching the full system: Python backend + REST API + React frontend.

## Prerequisites

### System Requirements
- **OS**: Linux (tested on Ubuntu 20.04+), macOS, or Windows WSL2
- **Python**: 3.8+
- **Node.js**: 16+ (for React frontend)
- **npm**: 8+

### Quick Environment Check
```bash
python3 --version
npm --version
curl --version
```

## Installation

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Compile Protocol Buffer Messages
```bash
cd proto_msgs
bash compile_proto.sh
cd ..
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

## Running the Simulation

### Option A: Full Stack (Backend + API + WebSocket + Frontend)

**All-in-one command** (starts backend + React dev server):
```bash
./scripts/start_all.sh
```

This will:
1. Launch the Python backend (3 leaders, 10 followers, 10 min duration)
2. Start Flask REST API on `http://localhost:8080`
3. Start WebSocket server on `ws://localhost:8081`
4. Launch React frontend dev server on `http://localhost:3000`

Then open your browser to **http://localhost:3000**

---

### Option B: Backend Only (Headless)

**Start just the simulation backend**:
```bash
./scripts/run_simulation.sh --leaders 3 --followers 10 --duration 300
```

Arguments:
- `--leaders N`: Number of leader drones (default: 3)
- `--followers N`: Number of follower drones (default: 10)
- `--duration SECONDS`: Simulation duration in seconds (default: 300)
- `--config FILE`: Path to YAML config file (default: config/simulation_params.yaml)

API will be available at `http://localhost:8080`

---

### Option C: Backend + Frontend Separately

**Terminal 1 - Start the backend**:
```bash
python3 src/swarm_launcher.py --leaders 3 --followers 10 --duration 600
```

**Terminal 2 - Start the frontend**:
```bash
cd frontend
npm start
```

Frontend will open at **http://localhost:3000**

---

## Using the Frontend

### Control Panel (Left Sidebar)
- **Start/Stop Simulation**: Launch or stop the swarm
- **Refresh State**: Pull latest state from backend
- **Fire Controls**: Ignite fire at (x, y) with intensity (0-1)
- **Suppress**: Reduce fire intensity at (x, y) with strength (0-1)

### Drone Scene (Center)
- **Canvas visualization** of drone positions (scale: 2 pixels per meter)
- **Orange drones** = fire detected
- **Cyan drones** = nominal state
- **Drone ID** labeled above each dot

### Fire Map (Right Sidebar)
- **Grid visualization** of fire cells
- **Color intensity** represents fire intensity (0-1)
- **Yellow-orange** = active fire
- **Dark** = no fire

### Metrics Dashboard (Bottom Left)
- **Num drones**: Total swarm size
- **Avg battery**: Average battery percentage
- **Fire coverage**: Percentage of cells burning
- **Messages/sec**: Network throughput

---

## API Endpoints

The backend exposes a REST API on port **8080**:

### Health & State
```bash
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/simulation/state
```

### Drone Queries
```bash
curl http://localhost:8080/api/v1/drones                    # List all drones
curl http://localhost:8080/api/v1/drones/0                  # Get drone 0 state
```

### Fire Control
```bash
# Ignite fire at (100, 100) with intensity 0.8
curl -X POST http://localhost:8080/api/v1/fire/ignite \
  -H "Content-Type: application/json" \
  -d '{"x": 100.0, "y": 100.0, "intensity": 0.8}'

# Suppress at (100, 100) with strength 0.5
curl -X POST http://localhost:8080/api/v1/fire/suppress \
  -H "Content-Type: application/json" \
  -d '{"x": 100.0, "y": 100.0, "strength": 0.5}'
```

### Metrics
```bash
curl http://localhost:8080/api/v1/metrics                    # Swarm metrics
curl http://localhost:8080/api/v1/fire/state                 # Fire map
```

---

## WebSocket Streaming

Connect to `ws://localhost:8081` for real-time state updates.

**Example JavaScript**:
```javascript
const ws = new WebSocket('ws://localhost:8081');
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  console.log('State update:', msg.state);
};
```

Expected message format:
```json
{
  "type": "state_update",
  "timestamp": "2024-01-01T12:00:00Z",
  "state": {
    "drones": [...],
    "fire": {...},
    "metrics": {...}
  }
}
```

---

## Configuration

Edit `config/simulation_params.yaml` to customize physics and behavior:

```yaml
swarm:
  num_leaders: 3
  num_followers: 10
  detm_eta0: 1.0              # DETM initial threshold (meters)
  detm_lambda: 0.5            # Decay constant

battery:
  capacity_mah: 5000
  energy_drain_per_meter: 0.08
  rtl_threshold_percent: 20   # Return-to-launch at 20%

fire:
  spread_rate_mpm: 30         # Fire spread rate (m/min)
  suppression_effectiveness: 0.9

channel:
  path_loss_exponent: 3.0     # Urban environment
  rice_k_factor: 8.0          # Moderate fading
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_channel_model.py -v

# Generate coverage report
pytest tests/ --cov=src --cov-report=html
```

---

## Troubleshooting

### "python3 command not found"
```bash
# Use python instead of python3
python src/swarm_launcher.py --leaders 3 --followers 10
```

### "Port 8080 already in use"
```bash
# Kill the process using the port (Linux/macOS)
lsof -ti:8080 | xargs kill -9

# Or use a different port (requires code change)
```

### "Cannot connect to WebSocket"
- Ensure backend is running on the same machine
- Check firewall rules (ports 8080, 8081)
- Verify `ws://localhost:8081` in browser console

### "React dev server won't start"
```bash
# Clear Node cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### "Missing protobuf files"
```bash
cd proto_msgs
bash compile_proto.sh
cd ..
```

---

## Directory Structure

```
aerosyn-sim/
├── src/                       # Python backend
│   ├── swarm_launcher.py      # Main orchestrator
│   ├── api_server.py          # Flask REST API
│   ├── websocket_server.py    # WebSocket server
│   └── ... (physics, control, swarm modules)
├── frontend/                  # React TypeScript UI
│   ├── src/
│   │   ├── App.tsx            # Main component
│   │   ├── components/        # UI components
│   │   ├── services/          # API & WebSocket clients
│   │   └── utils/             # TypeScript types
│   ├── package.json
│   └── tsconfig.json
├── scripts/                   # Deployment helpers
│   ├── start_all.sh          # Full stack launcher
│   ├── run_simulation.sh      # Backend only
│   └── start_mqtt_broker.sh   # MQTT setup (optional)
├── config/
│   ├── simulation_params.yaml # Physics & control tuning
│   └── frontend_config.json
├── tests/                     # Pytest test suite (6 modules)
├── proto_msgs/               # Protocol Buffer schemas
└── README.md
```

---

## Performance Tuning

### Reduce Latency
- Lower `detm_lambda` in config (faster threshold decay = more messages)
- Increase `broadcast_range_m` for longer RF range

### Reduce Network Traffic
- Increase `detm_eta0` (higher transmission threshold)
- Increase `detm_lambda` (slower threshold decay)
- Reduce `num_followers`

### Improve Visualization
- Edit `frontend/src/components/DroneScene.tsx` to change scale factor
- Adjust grid cell size in `FireMap.tsx`

---

## Next Steps

1. **Explore the UI**: Start/stop simulation, ignite/suppress fires, watch metrics
2. **Run Tests**: Validate physics with `pytest tests/ -v`
3. **Customize Config**: Edit `config/simulation_params.yaml` for custom scenarios
4. **Integrate with ROS 2**: Use MAVROS bridge for real drone swarms
5. **Advanced**: Implement per-drone detail panels or time-series charts in frontend

---

## Support & Documentation

- **Full Docs**: See `IMPLEMENTATION_SUMMARY.md`, `TESTING.md`, `PROJECT_STATUS.md`
- **API Docs**: See `API_REFERENCE.md`
- **Architecture**: See `IMPLEMENTATION_SUMMARY.md` for physics models
- **Test Guide**: See `TESTING.md` for comprehensive test descriptions

---

**Version**: 1.0 RC  
**Status**: Production-Ready  
**Last Updated**: 2024
