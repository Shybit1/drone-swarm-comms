export interface DroneState {
  drone_id: number;
  x: number;
  y: number;
  z?: number;
  vx?: number;
  vy?: number;
  vz?: number;
  battery_percent?: number;
  payload_remaining?: number;
  fire_detected?: boolean;
  rssi_dbm?: number;
}

export interface FireCell {
  x: number;
  y: number;
  intensity: number; // 0..1
}

export interface FireMapState {
  width: number;
  height: number;
  cell_size_m: number;
  burning_cells: FireCell[];
}

export interface SwarmMetrics {
  num_drones?: number;
  avg_battery_percent?: number;
  fire_coverage_percent?: number;
  messages_sent_per_sec?: number;
}
