// file: apps/web/app/(main)/tracking/[orderId]/page.tsx

'use client';

import { useEffect, useState, useMemo } from 'react';
import { FiLoader, FiMapPin, FiPackage, FiAlertTriangle } from 'react-icons/fi'; // Added FiAlertTriangle
import { motion, AnimatePresence } from 'framer-motion'; // Added Framer Motion
import useSWR from 'swr'; // Added SWR
import { api } from '@/lib/api'; // Added api instance
import { useRealtimeUpdates } from '@/hooks/useRealtimeUpdates'; // <-- استيراد الـ Hook الجديد

// Interface لنفس شكل بيانات الطلب اللي بيرجعها API /orders/{orderId}
// (عدّلها لو الـ API بيرجع شكل مختلف)
interface OrderDetails {
    id: number;
    status: string;
    // ... other order details ...
    mission?: { // Assuming mission details might be nested
        assigned_drone?: {
            drone_id_str: string; // The public ID we need
        } | null;
    } | null;
    // OR maybe the drone ID is directly on the order
    // drone_id_str?: string | null;
}

// Interface لبيانات الـ Telemetry اللي جاية من الـ Hook
interface TelemetryPayload {
  lat: number;
  lon: number;
  alt_m?: number; // Optional based on hook
  battery_pct?: number; // Optional based on hook
  flight_mode?: string | null; // Optional based on hook
  status?: string; // Original page used status, map flight_mode?
}

// --- مكون الخريطة (زي ما هو تقريباً، بس بيستقبل TelemetryPayload) ---
const MapPlaceholder = ({ coords }: { coords: TelemetryPayload | null }) => {
  // Simplified position calculation (needs a real map library like Leaflet/Mapbox for accuracy)
  // Calculate relative position based on a known center (e.g., Cairo)
  const centerLat = 30.0444;
  const centerLon = 31.2357;
  const scaleFactor = 5000; // Adjust for desired map scale representation

  const topOffset = coords ? `calc(50% + ${(coords.lat - centerLat) * -scaleFactor}px)` : '50%';
  const leftOffset = coords ? `calc(50% + ${(coords.lon - centerLon) * scaleFactor}px)` : '50%';

  return (
    <div className="relative w-full h-96 bg-gray-900 border border-cyan-900/50 rounded-lg overflow-hidden shadow-inner">
      {/* Grid pattern */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage: 'linear-gradient(rgba(6,182,212,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,0.1) 1px, transparent 1px)',
          backgroundSize: '30px 30px',
        }}
      />
      {/* Drone Marker */}
      <AnimatePresence>
          {coords && (
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              className="absolute w-8 h-8 bg-cyan-500 rounded-full border-4 border-black/50 shadow-lg flex items-center justify-center transform -translate-x-1/2 -translate-y-1/2"
              style={{
                top: topOffset,
                left: leftOffset,
              }}
            >
              <FiPackage size={16} className="text-black" />
            </motion.div>
          )}
      </AnimatePresence>
       {/* You could add markers for origin/destination here */}
    </div>
  );
};

// --- المكون الرئيسي للصفحة ---
export default function TrackingPage({ params }: { params: { orderId: string } }) {
  const { orderId } = params;

  // --- 1. جلب بيانات الطلب لمعرفة droneId ---
  const orderApiUrl = `/orders/${orderId}`;
  const swrFetcher = (url: string) => api.get(url).then(res => res.data);
  const { data: orderData, error: orderError, isLoading: isLoadingOrder } = useSWR<OrderDetails>(orderApiUrl, swrFetcher);

  // استخراج droneId من بيانات الطلب
  const droneId = useMemo(() => {
      // Adjust based on your actual OrderDetails structure
      return orderData?.mission?.assigned_drone?.drone_id_str || null;
      // Or: return orderData?.drone_id_str || null;
  }, [orderData]);

  // --- 2. استخدام الـ Hook الجديد مع droneId ---
  // الـ Hook هيبدأ الاتصال فقط لما droneId يبقى متاح
  const { latestTelemetry, isConnected } = useRealtimeUpdates(droneId);

  // --- تحديد حالة الاتصال للعرض ---
  const connectionStatus = useMemo(() => {
      if (!droneId && !isLoadingOrder) return 'No drone assigned'; // حالة لو مفيش درون
      if (isLoadingOrder) return 'Loading Order...';
      if (isConnected) return 'Live Tracking';
      // Hook doesn't provide detailed connecting/error states yet, simplify
      if (droneId) return 'Connecting...'; // Assume connecting if droneId exists but not connected
      return 'Unavailable';
  }, [isConnected, droneId, isLoadingOrder]);


  // --- عرض حالة التحميل الأولية للطلب ---
  if (isLoadingOrder) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center bg-black text-white p-4">
        <FiLoader className="animate-spin text-cyan-400 text-4xl mb-4" />
        <h1 className="text-2xl font-bold mb-2 text-gray-300">Loading Order #{orderId}...</h1>
      </div>
    );
  }

  // --- عرض حالة الخطأ لو فشل جلب الطلب ---
  if (orderError) {
      return (
          <div className="min-h-screen flex flex-col items-center justify-center text-center bg-black text-white p-4">
              <FiAlertTriangle className="text-red-500 text-4xl mb-4" />
              <h1 className="text-2xl font-bold mb-2 text-red-400">Error Loading Order #{orderId}</h1>
              <p className="text-red-300 bg-red-900/50 p-3 rounded border border-red-800 max-w-md">
                   {(orderError as any)?.message || 'Could not fetch order details.'}
              </p>
          </div>
      );
  }

  // --- العرض الأساسي للصفحة ---
  return (
    <div className="min-h-screen bg-black text-white pt-24 pb-12"> {/* Added min-h-screen and padding */}
        <div className="max-w-4xl mx-auto text-center px-4"> {/* Added container */}
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>Tracking Order #{orderId}</h1>
            <div className="flex items-center justify-center gap-2 mb-8 text-lg">
                {isConnected && <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />}
                {!isConnected && droneId && <FiLoader className="animate-spin text-gray-500" />}
                <p className={`font-semibold ${isConnected ? 'text-green-400' : 'text-gray-500'}`}>
                    {connectionStatus}
                </p>
            </div>

            <MapPlaceholder coords={latestTelemetry} />

            {/* --- عرض تفاصيل إضافية (اختياري) --- */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-left"
            >
                <div className="p-4 border border-white/10 rounded-lg bg-white/5 backdrop-blur-sm">
                    <h3 className="font-semibold text-cyan-400 flex items-center gap-2 mb-1"><FiMapPin size={16} /> Location</h3>
                    {latestTelemetry ? (
                    <p className="font-mono text-sm text-gray-300">
                        Lat: {latestTelemetry.lat.toFixed(5)}, Lon: {latestTelemetry.lon.toFixed(5)}
                    </p>
                    ) : (
                    <p className="text-sm text-gray-500 italic">Waiting...</p>
                    )}
                </div>
                 <div className="p-4 border border-white/10 rounded-lg bg-white/5 backdrop-blur-sm">
                    <h3 className="font-semibold text-cyan-400 flex items-center gap-2 mb-1">Status</h3>
                    <p className="text-sm text-gray-300 capitalize">
                         {latestTelemetry?.flight_mode?.toLowerCase() || (isConnected ? 'Idle' : 'Unavailable')}
                    </p>
                </div>
                 <div className="p-4 border border-white/10 rounded-lg bg-white/5 backdrop-blur-sm">
                    <h3 className="font-semibold text-cyan-400 flex items-center gap-2 mb-1">Battery</h3>
                    {latestTelemetry?.battery_pct !== undefined ? (
                         <p className="text-sm text-gray-300 font-semibold">
                            {latestTelemetry.battery_pct}%
                         </p>
                    ) : (
                         <p className="text-sm text-gray-500 italic">Waiting...</p>
                    )}
                </div>
            </motion.div>
        </div>
    </div>
  );
}
