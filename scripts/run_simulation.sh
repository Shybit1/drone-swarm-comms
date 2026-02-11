#!/bin/bash
# run_simulation.sh
# Launches the AeroSyn-Sim backend with configurable drone count and duration
# Usage: ./scripts/run_simulation.sh [--leaders N] [--followers N] [--duration SECONDS] [--config FILE]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Default parameters
LEADERS=3
FOLLOWERS=10
DURATION=300
CONFIG="config/simulation_params.yaml"
LOG_DIR="logs"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --leaders)
      LEADERS="$2"
      shift 2
      ;;
    --followers)
      FOLLOWERS="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --config)
      CONFIG="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--leaders N] [--followers N] [--duration SECONDS] [--config FILE]"
      exit 1
      ;;
  esac
done

# Create logs directory
mkdir -p "$LOG_DIR"

# Check Python environment
if ! command -v python3 &> /dev/null; then
  echo "ERROR: python3 not found. Please install Python 3.8+"
  exit 1
fi

# Verify dependencies
echo "[*] Checking Python dependencies..."
python3 -c "import pymavlink, paho, protobuf, numpy, scipy, flask" 2>/dev/null || {
  echo "[!] Missing dependencies. Installing from requirements.txt..."
  pip install -r requirements.txt
}

# Verify proto compilation
echo "[*] Checking Protocol Buffer messages..."
if [ ! -f "src/swarm_telemetry_pb2.py" ]; then
  echo "[*] Compiling Protocol Buffer messages..."
  cd proto_msgs && bash compile_proto.sh && cd ..
fi

# Start the simulation
echo "[*] Starting AeroSyn-Sim backend"
echo "    Leaders: $LEADERS"
echo "    Followers: $FOLLOWERS"
echo "    Duration: $DURATION seconds"
echo "    Config: $CONFIG"
echo "[*] Logs: $LOG_DIR/simulation.log"
echo ""

python3 src/swarm_launcher.py \
  --leaders "$LEADERS" \
  --followers "$FOLLOWERS" \
  --config "$CONFIG" \
  --duration "$DURATION" \
  2>&1 | tee "$LOG_DIR/simulation.log"

echo ""
echo "[*] Simulation complete. Logs saved to $LOG_DIR/simulation.log"
