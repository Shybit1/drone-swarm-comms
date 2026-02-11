import React, { useRef, useEffect } from 'react';
import { DroneState } from '../utils/types';

interface Props {
  drones: DroneState[];
  width?: number;
  height?: number;
}

export default function DroneScene({ drones, width = 600, height = 400 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;

    // adapt canvas to device pixel ratio
    const dpr = window.devicePixelRatio || 1;
    c.width = width * dpr;
    c.height = height * dpr;
    c.style.width = '100%';
    c.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Draw background
    ctx.fillStyle = '#081229';
    ctx.fillRect(0, 0, width, height);

    // Coordinate transform: world x,y in meters -> canvas
    const scale = Math.max(1, Math.min(3, width / 400)); // simple responsive scale
    const cx = width / 2;
    const cy = height / 2;

    // Draw each drone
    drones.forEach((d) => {
      const x = cx + (d.x || 0) * scale;
      const y = cy - (d.y || 0) * scale;
      // drone body
      ctx.beginPath();
      ctx.fillStyle = d.fire_detected ? 'orange' : '#66d9ff';
      ctx.arc(x, y, 6, 0, Math.PI * 2);
      ctx.fill();
      // label
      ctx.fillStyle = '#fff';
      ctx.font = '10px sans-serif';
      ctx.fillText(String(d.drone_id), x + 8, y + 4);
    });
  }, [drones, width, height]);

  return (
    <div>
      <h3>Drone Scene</h3>
      <div className="scene-canvas" style={{ padding: 6 }}>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
