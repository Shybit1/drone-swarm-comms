import React, { useState } from 'react';
import api from '../services/api';

export default function ControlPanel({ onRefresh }: { onRefresh: () => void }) {
  const [igniteX, setIgniteX] = useState('100');
  const [igniteY, setIgniteY] = useState('100');
  const [intensity, setIntensity] = useState('0.8');
  const [strength, setStrength] = useState('0.5');
  const [status, setStatus] = useState<string>('idle');

  async function handleStart() {
    setStatus('starting');
    try {
      await api.startSimulation();
      setStatus('running');
    } catch (err) {
      setStatus('error');
    }
    onRefresh();
  }

  async function handleStop() {
    setStatus('stopping');
    try {
      await api.stopSimulation();
      setStatus('stopped');
    } catch (err) {
      setStatus('error');
    }
    onRefresh();
  }

  async function handleIgnite(e: React.FormEvent) {
    e.preventDefault();
    await api.igniteFire(Number(igniteX), Number(igniteY), Number(intensity));
    onRefresh();
  }

  async function handleSuppress(e: React.FormEvent) {
    e.preventDefault();
    await api.suppressFire(Number(igniteX), Number(igniteY), Number(strength));
    onRefresh();
  }

  return (
    <div>
      <h3>Control Panel</h3>
      <div className="control-actions" style={{ marginBottom: 8 }}>
        <button onClick={handleStart}>Start Simulation</button>
        <button className="secondary" onClick={handleStop}>Stop Simulation</button>
        <button className="secondary" onClick={onRefresh}>Refresh State</button>
      </div>

      <form onSubmit={handleIgnite} style={{ marginBottom: 8 }}>
        <h4>Fire Controls</h4>
        <div className="form-row">
          <input value={igniteX} onChange={(e) => setIgniteX(e.target.value)} placeholder="x" />
          <input value={igniteY} onChange={(e) => setIgniteY(e.target.value)} placeholder="y" />
          <input value={intensity} onChange={(e) => setIntensity(e.target.value)} placeholder="intensity" />
          <button type="submit">Ignite</button>
        </div>
      </form>

      <form onSubmit={handleSuppress}>
        <h4>Suppress</h4>
        <div className="form-row">
          <input value={igniteX} onChange={(e) => setIgniteX(e.target.value)} placeholder="x" />
          <input value={igniteY} onChange={(e) => setIgniteY(e.target.value)} placeholder="y" />
          <input value={strength} onChange={(e) => setStrength(e.target.value)} placeholder="strength" />
          <button type="submit">Suppress</button>
        </div>
      </form>

      <div style={{ marginTop: 10 }}>
        <strong>Local status:</strong> {status}
      </div>
    </div>
  );
}
