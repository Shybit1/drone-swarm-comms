import React, { useEffect, useState, useCallback } from 'react';
import ControlPanel from './components/ControlPanel';
import DroneScene from './components/DroneScene';
import FireMap from './components/FireMap';
import MetricsDashboard from './components/MetricsDashboard';
import api from './services/api';
import ws from './services/websocket';
import { DroneState, FireMapState, SwarmMetrics } from './utils/types';
import './index.css';

function App() {
  const [drones, setDrones] = useState<DroneState[]>([]);
  const [fire, setFire] = useState<FireMapState | undefined>(undefined);
  const [metrics, setMetrics] = useState<SwarmMetrics | undefined>(undefined);

  const refreshState = useCallback(async () => {
    try {
      const ds = (await api.getDrones()) || [];
      setDrones(ds);
      const f = await api.getFireState();
      setFire(f);
      const m = await api.getMetrics();
      setMetrics(m);
    } catch (err) {
      console.warn('refresh failed', err);
    }
  }, []);

  useEffect(() => {
    // initial fetch
    refreshState();
    // connect websocket
    ws.connect();
    const off = ws.onMessage((msg) => {
      // handle messages
      if (msg.type === 'state_update' && msg.state) {
        // state may include drones, fire, metrics
        if (msg.state.drones) setDrones(msg.state.drones as DroneState[]);
        if (msg.state.fire) setFire(msg.state.fire as FireMapState);
        if (msg.state.metrics) setMetrics(msg.state.metrics as SwarmMetrics);
      }
    });

    return () => {
      off();
      ws.disconnect();
    };
  }, [refreshState]);

  return (
    <div className="app-container">
      <h1 style={{ marginTop: 0 }}>AeroSyn-Sim — Frontend Control</h1>
      <div className="grid-main">
        <div className="left-col">
          <div className="panel">
            <ControlPanel onRefresh={refreshState} />
          </div>

          <div className="panel">
            <MetricsDashboard metrics={metrics} />
          </div>
        </div>

        <div className="panel" style={{ minHeight: 600 }}>
          <DroneScene drones={drones} width={900} height={600} />
        </div>

        <div className="panel">
          <FireMap fire={fire} />
        </div>
      </div>
    </div>
  );
}

export default App;
