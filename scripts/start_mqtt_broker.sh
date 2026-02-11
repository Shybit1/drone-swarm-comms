#!/bin/bash
# start_mqtt_broker.sh
# Starts a local MQTT broker for distributed communication testing (optional)
# Note: AeroSyn-Sim uses in-memory MQTT simulation by default

set -e

echo "[*] MQTT Broker Setup (Optional)"
echo ""
echo "AeroSyn-Sim includes an in-memory MQTT broker simulation in comms_manager.py"
echo "For real MQTT testing with Mosquitto:"
echo ""

# Check if mosquitto is installed
if command -v mosquitto &> /dev/null; then
  echo "[+] Mosquitto found. Starting broker on port 1883..."
  mosquitto -v -p 1883 &
  BROKER_PID=$!
  echo "[*] Mosquitto PID: $BROKER_PID"
  echo "[*] Press Ctrl+C to stop"
  wait $BROKER_PID
else
  echo "[!] Mosquitto not installed."
  echo ""
  echo "To install Mosquitto:"
  echo "  Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients"
  echo "  macOS: brew install mosquitto"
  echo ""
  echo "Or use Docker:"
  echo "  docker run -it -p 1883:1883 eclipse-mosquitto"
  echo ""
  echo "For this simulation, the in-memory MQTT broker in comms_manager.py is sufficient."
  exit 1
fi
