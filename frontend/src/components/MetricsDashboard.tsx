import React from 'react';
import { SwarmMetrics } from '../utils/types';

export default function MetricsDashboard({ metrics }: { metrics?: SwarmMetrics }) {
  if (!metrics) return (
    <div className="panel">
      <h3>Metrics</h3>
      <div>No metrics yet</div>
    </div>
  );

  return (
    <div>
      <h3>Metrics</h3>
      <ul className="metrics-list">
        <li><strong>Num drones:</strong> {metrics.num_drones ?? '—'}</li>
        <li><strong>Avg battery:</strong> {metrics.avg_battery_percent?.toFixed(1) ?? '—'}%</li>
        <li><strong>Fire coverage:</strong> {metrics.fire_coverage_percent?.toFixed(1) ?? '—'}%</li>
        <li><strong>Messages/sec:</strong> {metrics.messages_sent_per_sec ?? '—'}</li>
      </ul>
    </div>
  );
}
