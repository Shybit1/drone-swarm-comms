# AeroSyn-Sim: Cyber-Physical Drone Swarm Simulator

A comprehensive Software-In-The-Loop (SITL) simulator for autonomous multi-agent drone swarms with realistic physics, communication modeling, and fire containment scenarios.

## Overview

AeroSyn-Sim enables research and development of distributed autonomous swarm algorithms in a realistic cyber-physical environment. Features include:

- **Realistic Physics Engine**: Quadrotor dynamics, battery drain, payload management
- **Distributed Autonomy**: Decentralized control algorithms (DETM, stigmergy, Lévy flight)
- **Swarm Intelligence**: Cooperative coordination without central control
- **Communication Modeling**: Channel fading, latency, bandwidth limits, packet loss
- **Fire Simulation**: Dynamic fire spread with environmental factors
- **Real-time Visualization**: 2D/3D drone positions, fire map, swarm metrics
- **Full Web UI**: Control simulation from browser, monitor metrics live
- **Production-Ready**: Type-safe Python/TypeScript, comprehensive tests, Docker support

## Quick Start

### Prerequisites
- Python 3.8+
- Node 16+, npm 8+
- 4GB RAM, Linux/macOS/Windows with WSL2

### Run Everything
```bash
cd aerosyn-sim
npm install  # Install frontend dependencies
./scripts/start_all.sh
# Opens http://localhost:3000 with full UI
```

### Run Backend Only
```bash
./scripts/run_simulation.sh --leaders 3 --followers 10 --duration 300
# Accessible via REST API on http://localhost:8080
```

### Run Components Separately
```bash
# Terminal 1: Backend
python3 src/swarm_launcher.py --leaders 3 --followers 10

# Terminal 2: Frontend
cd frontend && npm start
```

## Key Features

### Drone Swarm Control
- Start/stop simulation with configurable swarm size
- Real-time drone position tracking and battery monitoring
- Leader/follower hierarchy with role-based behaviors
- Distributed decision making (no central controller)

### Fire Containment
- Ignite fires at arbitrary map locations
- Suppress fires with drone payloads
- Real-time fire spread simulation
- Coverage and containment metrics

### Real-time Metrics
- Swarm battery status
- Fire coverage percentage
- Communication throughput (msgs/sec)
- Network latency and reliability

### Web Dashboard
- **Control Panel**: Start/stop simulation, ignite/suppress fires
- **Drone Scene**: 2D canvas visualization of swarm positions
- **Fire Map**: Grid-based fire intensity map
- **Metrics Dashboard**: Live aggregated swarm statistics
- **Responsive Design**: Works on desktop, tablet, mobile

## Architecture

### Backend (Python)
```
src/
├── swarm_launcher.py       # Main entry point
├── drone_node.py           # Individual drone simulation
├── distributed_observer.py # Decentralized state estimation
├── detm_controller.py      # Decentralized trajectory control
├── physics_engine.py       # Quadrotor dynamics
├── fire_simulation.py      # Fire spread modeling
├── channel_model.py        # Network simulation
├── comms_manager.py        # Message routing
├── stigmergy.py            # Stigmergic coordination
├── levy_flight.py          # Lévy flight exploration
├── energy_model.py         # Battery management
├── api_server.py           # REST API (Flask)
├── websocket_server.py     # Live state streaming
└── metrics_collector.py    # Performance monitoring
```

### Frontend (TypeScript/React)
```
frontend/src/
├── App.tsx                 # Main component
├── components/
│   ├── ControlPanel.tsx    # Simulation controls
│   ├── DroneScene.tsx      # Drone visualization
│   ├── FireMap.tsx         # Fire grid visualization
│   └── MetricsDashboard.tsx# Metrics display
├── services/
│   ├── api.ts              # REST client
│   └── websocket.ts        # WebSocket client
├── utils/
│   └── types.ts            # TypeScript interfaces
└── index.css               # Responsive styling
```

## Configuration

Edit `config/simulation_params.yaml` to customize:

```yaml
swarm:
  num_leaders: 3
  num_followers: 10
  initial_altitude: 20.0  # meters
  communication_range: 100.0  # meters

battery:
  capacity_mah: 5000
  discharge_rate: 10  # mAh/s at hover
  payload_drain: 5  # mAh/s when active

fire:
  spread_speed: 0.5  # cells/second
  max_intensity: 1.0
  suppress_rate: 0.1  # intensity reduction per drone

channel:
  path_loss_exp: 2.5
  fading_std: 3.0  # dB
  latency_ms: 50

physics:
  gravity: 9.81  # m/s²
  max_tilt: 45  # degrees
  max_velocity: 15  # m/s
```

## API Endpoints

All endpoints return JSON. Base URL: `http://localhost:8080/api/v1`

### Health Check
```bash
GET /health
# Response: { "status": "ok" }
```

### Simulation Control
```bash
POST /simulation/start
# Body: { "duration_sec": 300, "num_leaders": 3, "num_followers": 10 }
# Response: { "simulation_id": "uuid", "status": "running" }

POST /simulation/stop
# Response: { "status": "stopped" }
```

### Drone State
```bash
GET /drones
# Response: [
#   {
#     "drone_id": 0,
#     "x": 10.5, "y": 20.3, "z": 15.0,
#     "battery_percent": 85.5,
#     "fire_detected": false
#   },
#   ...
# ]
```

### Fire Control
```bash
POST /fire/ignite
# Body: { "x": 50.0, "y": 50.0, "intensity": 0.8 }
# Response: { "fire_id": "uuid", "status": "ignited" }

POST /fire/suppress
# Body: { "x": 50.0, "y": 50.0, "strength": 0.5 }
# Response: { "suppressed_cells": 12, "coverage": 0.23 }

GET /fire/state
# Response: {
#   "width": 100, "height": 100, "cell_size_m": 1.0,
#   "burning_cells": [
#     { "x": 50, "y": 50, "intensity": 0.8 },
#     ...
#   ]
# }
```

### Metrics
```bash
GET /metrics
# Response: {
#   "num_drones": 13,
#   "avg_battery_percent": 72.5,
#   "fire_coverage_percent": 5.2,
#   "messages_sent_per_sec": 145.3
# }
```

## WebSocket Streaming

Connect to `ws://localhost:8081` to receive real-time state updates:

```javascript
const ws = new WebSocket('ws://localhost:8081');
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'state_update') {
    console.log(msg.state.drones);    // Drone positions
    console.log(msg.state.fire);      // Fire map
    console.log(msg.state.metrics);   // Swarm metrics
  }
};
```

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest

# Specific module
pytest tests/test_fire_spread.py -v

# With coverage
pytest --cov=src
```

Test coverage includes:
- Physics engine (dynamics, battery model)
- Fire simulation (spread, suppression)
- Communication (latency, packet loss, fading)
- Distributed algorithms (DETM, observer, stigmergy)
- API endpoints
- Latency measurements

## Performance Tuning

### Reduce Latency
- Lower `fading_std` in config (less network variability)
- Increase `communication_range` (fewer retransmissions)
- Reduce swarm size (fewer agents to update)

### Increase Throughput
- Increase `eta0` in DETM controller (larger control steps)
- Reduce `lambda` in fire model (fewer spread events)
- Increase API polling interval in frontend

### Visualization Optimization
- Reduce canvas resolution (edit DroneScene.tsx scale factor)
- Disable fire map updates when not needed
- Increase metrics update interval

## Documentation

- **QUICKSTART.md**: Detailed setup guide with all run options
- **IMPLEMENTATION_SUMMARY.md**: Technical deep-dive on algorithms
- **TESTING.md**: Test strategy and coverage details
- **API_REFERENCE.md**: Complete API documentation
- **VERIFICATION.md**: Validation and benchmarking results
- **DEMO.md**: Example scenarios and use cases

## Project Structure

```
aerosyn-sim/
├── src/                    # Python backend (5,390 LOC)
│   ├── swarm_launcher.py
│   ├── drone_node.py
│   ├── physics_engine.py
│   ├── fire_simulation.py
│   ├── channel_model.py
│   ├── comms_manager.py
│   ├── distributed_observer.py
│   ├── detm_controller.py
│   ├── stigmergy.py
│   ├── levy_flight.py
│   ├── energy_model.py
│   ├── api_server.py
│   ├── websocket_server.py
│   └── metrics_collector.py
├── frontend/               # TypeScript/React UI (~700 LOC)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── services/
│   │   ├── utils/
│   │   └── index.css
│   ├── public/
│   └── package.json
├── tests/                  # Test suite (912 LOC)
│   ├── test_fire_spread.py
│   ├── test_detm.py
│   ├── test_distributed_observer.py
│   ├── test_channel_model.py
│   ├── test_api_endpoints.py
│   └── test_latency_measurement.py
├── scripts/                # Deployment scripts
│   ├── start_all.sh       # Full stack orchestrator
│   ├── run_simulation.sh  # Backend launcher
│   └── start_mqtt_broker.sh
├── config/                 # Configuration files
│   ├── simulation_params.yaml
│   └── frontend_config.json
├── proto_msgs/             # Protocol buffers
│   ├── command.proto
│   ├── fire_data.proto
│   ├── metrics.proto
│   └── swarm_telemetry.proto
└── README.md               # This file
```

## Troubleshooting

### Frontend won't start
```bash
cd frontend
npm install
npm start
```

### API connection error
```bash
# Check backend is running
curl http://localhost:8080/api/v1/health

# Check firewall/port conflicts
lsof -i :8080
```

### WebSocket connection failed
```bash
# Ensure WebSocket server is running on port 8081
curl http://localhost:8081/  # Should fail with connection error
netstat -tulpn | grep 8081
```

### Missing Python dependencies
```bash
pip install -r requirements.txt
# Or run setup.py
python3 setup.py develop
```

### Proto files not compiled
```bash
cd proto_msgs
bash compile_proto.sh
cd ..
```

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2GB | 4GB+ |
| Disk | 500MB | 2GB |
| Network | 1Mbps | 10Mbps |
| Python | 3.8 | 3.10+ |
| Node | 14 | 18+ |

## Browser Support

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

[Your License Here]

## Support

For issues, feature requests, or contributions:

1. Check existing documentation in `/docs`
2. Review test suite for usage examples
3. Check troubleshooting section above
4. Examine code comments for implementation details

## Citation

If you use AeroSyn-Sim in your research, please cite:

```bibtex
@software{aerosyn_sim_2024,
  title={AeroSyn-Sim: Cyber-Physical Drone Swarm Simulator},
  author={[Your Name/Organization]},
  year={2024},
  url={https://github.com/[your-repo]}
}
```

---

**Happy swarming!** 🚁🚁🚁
