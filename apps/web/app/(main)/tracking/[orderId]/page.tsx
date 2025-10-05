// file: apps/web/app/(main)/tracking/[orderId]/page.tsx
// version: 2.0.0 (Live WebSocket Tracking)
// date: 2025-09-30
// author: Gemini

'use client';

import { useEffect, useState } from 'react';
import { FiLoader, FiMapPin, FiPackage } from 'react-icons/fi';

// Define a type for the position data we expect from the WebSocket
interface DronePosition {
  lat: number;
  lon: number;
  status: string;
}

// A simple placeholder map component
const MapPlaceholder = ({ coords }: { coords: DronePosition | null }) => {
  return (
    <div className="relative w-full h-96 bg-gray-200 dark:bg-gray-800 rounded-lg overflow-hidden border shadow-inner">
      {/* A simple grid pattern for the map background */}
      <div 
        className="absolute inset-0"
        style={{
          backgroundImage: 'linear-gradient(rgba(0,0,0,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.1) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />
      {coords && (
        <div
          className="absolute w-8 h-8 bg-blue-500 rounded-full border-4 border-white shadow-lg transition-all duration-1000 ease-linear flex items-center justify-center"
          style={{ 
            // Mock position calculation for visual representation
            top: `calc(50% + ${(coords.lat - 34.0522) * 2000}px)`,
            left: `calc(50% + ${(coords.lon + 118.2437) * 2000}px)`,
          }}
        >
          <FiPackage size={16} className="text-white" />
        </div>
      )}
    </div>
  );
};

export default function TrackingPage({ params }: { params: { orderId: string } }) {
  const { orderId } = params;
  const [dronePosition, setDronePosition] = useState<DronePosition | null>(null);
  const [connectionStatus, setConnectionStatus] = useState('Connecting...');

  useEffect(() => {
    // Construct the WebSocket URL. Use 'ws' for http and 'wss' for https.
    const wsUrl = `ws://localhost:8000/ws/track/${orderId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setConnectionStatus('Live');
    
    ws.onmessage = (event) => {
      const data: DronePosition = JSON.parse(event.data);
      setDronePosition(data);
    };

    ws.onclose = () => setConnectionStatus('Connection Lost');
    ws.onerror = () => setConnectionStatus('Error');

    // Cleanup function to close the connection when the component unmounts
    return () => {
      ws.close();
    };
  }, [orderId]);

  return (
    <div className="py-12 max-w-4xl mx-auto text-center">
      <h1 className="text-4xl font-bold mb-2">Tracking Order #{orderId}</h1>
      <div className="flex items-center justify-center gap-2 mb-8 text-lg">
        {connectionStatus === 'Live' && <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />}
        {connectionStatus === 'Connecting...' && <FiLoader className="animate-spin" />}
        <p className="text-foreground/70">
          Status: <span className="font-semibold">{connectionStatus}</span>
        </p>
      </div>
      
      <MapPlaceholder coords={dronePosition} />

      <div className="mt-6 p-4 border rounded-lg text-left bg-background/50">
        <h3 className="font-bold flex items-center gap-2 mb-2"><FiMapPin /> Current Coordinates</h3>
        {dronePosition ? (
          <p className="font-mono text-sm">
            Lat: {dronePosition.lat.toFixed(4)}, Lon: {dronePosition.lon.toFixed(4)}
          </p>
        ) : (
          <p className="text-sm text-foreground/60">Waiting for first position update...</p>
        )}
      </div>
    </div>
  );
}
