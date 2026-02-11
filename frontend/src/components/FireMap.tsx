import React from 'react';
import { FireMapState } from '../utils/types';

export default function FireMap({ fire }: { fire?: FireMapState }) {
  if (!fire) return (
    <div className="panel">
      <h3>Fire Map</h3>
      <div>No fire data</div>
    </div>
  );

  const widthPx = Math.min(400, fire.width * 4);
  const heightPx = Math.min(400, fire.height * 4);
  const cellW = Math.max(2, Math.floor(widthPx / fire.width));
  const cellH = Math.max(2, Math.floor(heightPx / fire.height));

  // Render a simple grid of burning cells as colored divs
  const cellMap = new Map<string, number>();
  fire.burning_cells.forEach((c) => {
    const cx = Math.floor(c.x / fire.cell_size_m);
    const cy = Math.floor(c.y / fire.cell_size_m);
    cellMap.set(`${cx},${cy}`, Math.max(cellMap.get(`${cx},${cy}`) || 0, c.intensity));
  });

  const cols = [] as JSX.Element[];
  for (let y = 0; y < fire.height; y++) {
    for (let x = 0; x < fire.width; x++) {
      const intensity = cellMap.get(`${x},${y}`) || 0;
      const color = intensity > 0 ? `rgba(255, ${Math.round(255 - intensity * 255)}, 0, ${Math.min(1, intensity * 1.2)})` : 'transparent';
      cols.push(
        <div key={`${x}-${y}`} style={{ width: cellW, height: cellH, background: color, boxSizing: 'border-box', border: '1px solid rgba(0,0,0,0.03)' }} />
      );
    }
  }

  return (
    <div>
      <h3>Fire Map</h3>
      <div className="fire-grid" style={{ width: widthPx, height: heightPx, display: 'grid', gridTemplateColumns: `repeat(${fire.width}, ${cellW}px)` }}>{cols}</div>
    </div>
  );
}
