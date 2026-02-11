#!/bin/bash
# start_all.sh
# Orchestrates the full AeroSyn-Sim stack: backend + API + WebSocket + frontend dev server
# Usage: ./scripts/start_all.sh [--leaders N] [--followers N] [--no-frontend]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Configuration
LEADERS=3
FOLLOWERS=10
DURATION=600
NO_FRONTEND=false
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
    --no-frontend)
      NO_FRONTEND=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--leaders N] [--followers N] [--no-frontend]"
      exit 1
      ;;
  esac
done

mkdir -p "$LOG_DIR"

echo "========================================"
echo "AeroSyn-Sim Full Stack Launch"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Leaders: $LEADERS"
echo "  Followers: $FOLLOWERS"
echo "  Duration: $DURATION seconds"
echo "  Logs: $LOG_DIR/"
echo ""

# Trap to clean up child processes on exit
trap "cleanup" EXIT INT TERM

cleanup() {
  echo ""
  echo "[*] Shutting down AeroSyn-Sim stack..."
  pkill -P $$ || true
  wait
  echo "[*] Stack stopped."
}

# Start backend (Python swarm launcher)
echo "[1/2] Starting Python backend..."
python3 src/swarm_launcher.py \
  --leaders "$LEADERS" \
  --followers "$FOLLOWERS" \
  --duration "$DURATION" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "      Backend PID: $BACKEND_PID"
echo "      Log: $LOG_DIR/backend.log"

# Wait for API to be ready
echo "[*] Waiting for REST API (port 8080) to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; then
    echo "[+] API ready!"
    break
  fi
  echo -n "."
  sleep 1
done
echo ""

# Start frontend dev server (optional)
if [ "$NO_FRONTEND" = false ]; then
  echo "[2/2] Starting React frontend dev server..."
  if [ ! -d "frontend/node_modules" ]; then
    echo "[*] Installing frontend dependencies..."
    (cd frontend && npm install > "../logs/npm_install.log" 2>&1)
  fi
  (cd frontend && npm start) > "$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  echo "      Frontend PID: $FRONTEND_PID"
  echo "      Log: $LOG_DIR/frontend.log"
  echo "[+] Frontend dev server will open in your browser at http://localhost:3000"
else
  echo "[2/2] Frontend disabled (use --no-frontend flag)"
fi

echo ""
echo "========================================"
echo "Stack Ready!"
echo "========================================"
echo ""
echo "Backend API:       http://localhost:8080"
echo "Backend WebSocket: ws://localhost:8081"
if [ "$NO_FRONTEND" = false ]; then
  echo "Frontend (React):   http://localhost:3000"
fi
echo ""
echo "Logs:"
echo "  - Backend:  $LOG_DIR/backend.log"
if [ "$NO_FRONTEND" = false ]; then
  echo "  - Frontend: $LOG_DIR/frontend.log"
fi
echo ""
echo "Press Ctrl+C to shutdown."
echo ""

# Wait for all background processes
wait
