import { DroneState, FireMapState, SwarmMetrics } from '../utils/types';

const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8080';

async function jsonFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...opts,
  });
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch (err) {
    return text;
  }
}

export async function startSimulation() {
  return jsonFetch('/api/v1/simulation/start', { method: 'POST' });
}

export async function stopSimulation() {
  return jsonFetch('/api/v1/simulation/stop', { method: 'POST' });
}

export async function getSimulationState(): Promise<any> {
  return jsonFetch('/api/v1/simulation/state');
}

export async function getDrones(): Promise<DroneState[]> {
  return jsonFetch('/api/v1/drones');
}

export async function getDrone(droneId: number): Promise<DroneState> {
  return jsonFetch(`/api/v1/drones/${droneId}`);
}

export async function igniteFire(x: number, y: number, intensity = 0.8) {
  return jsonFetch('/api/v1/fire/ignite', {
    method: 'POST',
    body: JSON.stringify({ x, y, intensity }),
  });
}

export async function suppressFire(x: number, y: number, strength = 0.5) {
  return jsonFetch('/api/v1/fire/suppress', {
    method: 'POST',
    body: JSON.stringify({ x, y, strength }),
  });
}

export async function getFireState(): Promise<FireMapState> {
  return jsonFetch('/api/v1/fire/state');
}

export async function getMetrics(): Promise<SwarmMetrics> {
  return jsonFetch('/api/v1/metrics');
}

export default {
  startSimulation,
  stopSimulation,
  getSimulationState,
  getDrones,
  getDrone,
  igniteFire,
  suppressFire,
  getFireState,
  getMetrics,
};

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  // add other VITE_... vars here
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
