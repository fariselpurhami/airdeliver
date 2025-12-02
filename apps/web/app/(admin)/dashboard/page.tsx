//** apps/web/app/(admin)/dashboard/page.tsx **//

'use client';

import CinematicBackground from '@/components/ui/CinematicBackground';
import React, { useEffect, useRef, Suspense, useState } from 'react';
import { useSession } from 'next-auth/react';
import useSWR from 'swr';
import { motion, useMotionValue, useSpring, useInView } from 'framer-motion';
import {
    AlertCircle, Lock, Loader2, DollarSign, Package,
    HardDrive, Wifi, Clock, BarChart2, Zap,
    Users, Truck, Activity, Server, Database, ShieldCheck
} from 'lucide-react';
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid
} from 'recharts';
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Float } from '@react-three/drei';
import * as THREE from 'three';

interface Stats {
    total_revenue: number;
    total_orders: number;
    total_products: number;
    active_drones: number;
    pending_deliveries: number;
    active_users_today: number;
}
interface Order {
    id: number;
    user_id: number;
    status: string;
    total_price: number;
    created_at: string;
}
interface PaginatedOrdersResponse {
    orders: Order[];
    total_orders: number;
}
interface RevenueData { name: string; revenue: number; }
interface ActivityEvent { id: string; icon: React.ReactNode; description: string; time: string; color: string; }

const mockRevenueData: RevenueData[] = [
    { name: '00:00', revenue: 420 }, { name: '04:00', revenue: 350 }, { name: '08:00', revenue: 900 },
    { name: '12:00', revenue: 1200 }, { name: '16:00', revenue: 1500 }, { name: '20:00', revenue: 1100 },
    { name: '24:00', revenue: 800 },
];
const mockActivityData: ActivityEvent[] = [
    { id: '1', icon: <Package size={14} />, description: 'Order #1045 dispatched', time: '2m ago', color: 'text-cyan-400' },
    { id: '2', icon: <Wifi size={14} />, description: 'Drone Fleet Sync Complete', time: '12m ago', color: 'text-green-400' },
    { id: '3', icon: <Zap size={14} />, description: 'High demand detected in Sector 7', time: '28m ago', color: 'text-yellow-400' },
    { id: '4', icon: <Database size={14} />, description: 'Inventory Manifest Updated', time: '45m ago', color: 'text-purple-400' },
];

const fetcher = async (url: string) => {
    return {
        total_revenue: 124500,
        total_orders: 843,
        total_products: 156,
        active_drones: 42,
        pending_deliveries: 12,
        active_users_today: 890
    } as Stats;
};

// ============================================================================
// --- 1. ARCHITECTURAL BACKGROUND ---
// ============================================================================
const DashboardBackground = () => {
    return (
        <>
            <fog attach="fog" args={['#000000', 10, 40]} />
            <ambientLight intensity={0.5} />
            <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={0.5} />
            <Float speed={1} rotationIntensity={0.2} floatIntensity={0.2}>
                <mesh position={[10, 0, -10]} rotation={[0, 0, Math.PI / 4]}>
                    <torusGeometry args={[8, 0.1, 16, 100]} />
                    <meshBasicMaterial color="#00C6FF" transparent opacity={0.1} />
                </mesh>
            </Float>
        </>
    );
};

const DynamicDashboardBackground = dynamic(() => Promise.resolve(DashboardBackground), {
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. COMPONENTS ---
// ============================================================================

const AnimatedCounter = ({ value, prefix = "" }: { value: number, prefix?: string }) => {
    const ref = useRef<HTMLSpanElement>(null);
    const motionValue = useMotionValue(0);
    const springValue = useSpring(motionValue, { damping: 60, stiffness: 80 });
    const isInView = useInView(ref, { once: true });

    useEffect(() => { if (isInView) motionValue.set(value); }, [motionValue, isInView, value]);

    useEffect(() => {
        return springValue.on("change", (latest) => {
            if (ref.current) {
                ref.current.textContent = `${prefix}${Intl.NumberFormat('en-US').format(Math.round(latest))}`;
            }
        });
    }, [springValue, prefix]);

    return <span ref={ref} className="tabular-nums tracking-tight">0</span>;
};

const StatCard = ({ title, value, icon: Icon, color = "cyan", delay = 0 }: any) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay }}
        whileHover={{ y: -5 }}
        className="group relative overflow-hidden rounded-[32px] bg-black/40 backdrop-blur-xl border border-white/10 p-6 flex flex-col justify-between h-40"
    >
        <div className={`absolute -right-4 -top-4 w-24 h-24 bg-${color}-500/10 blur-[40px] rounded-full group-hover:bg-${color}-500/20 transition-colors`} />

        <div className="flex justify-between items-start relative z-10">
            <div className={`p-3 rounded-2xl bg-${color}-500/10 border border-${color}-500/20 text-${color}-400`}>
                <Icon size={20} />
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white/5 border border-white/5">
                <span className={`w-1.5 h-1.5 rounded-full bg-${color}-400 animate-pulse`} />
                <span className="text-[9px] text-gray-400 font-mono uppercase tracking-wider">Live</span>
            </div>
        </div>

        <div className="relative z-10">
            <h3 className="text-3xl font-black text-white mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                <AnimatedCounter value={value} prefix={title.includes('Revenue') ? '$' : ''} />
            </h3>
            <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{title}</p>
        </div>

        <div className={`absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-${color}-500/50 to-transparent opacity-50 group-hover:opacity-100 transition-opacity`} />
    </motion.div>
);

const RevenueChart = ({ data }: { data: RevenueData[] }) => {
    return (
        <div className="relative h-full w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis
                        dataKey="name"
                        stroke="#4b5563"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        fontFamily="'Orbitron', sans-serif"
                    />
                    <YAxis
                        stroke="#4b5563"
                        fontSize={10}
                        tickFormatter={(val) => `$${val}`}
                        tickLine={false}
                        axisLine={false}
                        fontFamily="'Orbitron', sans-serif"
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            backdropFilter: 'blur(10px)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '12px',
                            boxShadow: '0 10px 40px rgba(0,0,0,0.5)'
                        }}
                        itemStyle={{ color: '#06b6d4', fontFamily: 'monospace' }}
                        labelStyle={{ color: '#9ca3af', fontSize: '10px', textTransform: 'uppercase', marginBottom: '4px' }}
                    />
                    <Area
                        type="monotone"
                        dataKey="revenue"
                        stroke="#06b6d4"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorRevenue)"
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

const ActivityTimeline = ({ events }: { events: ActivityEvent[] }) => {
    return (
        <div className="space-y-4">
            {events.map((event, idx) => (
                <div key={idx} className="relative pl-6 pb-2 border-l border-white/5 last:border-0">
                    <div className={`absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full border-2 border-black ${event.color.replace('text-', 'bg-')}`} />
                    <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs font-bold ${event.color} font-mono uppercase`}>{event.description.split(' ')[0]}</span>
                        <span className="text-[10px] text-gray-500 font-mono">{event.time}</span>
                    </div>
                    <p className="text-sm text-gray-300">{event.description}</p>
                </div>
            ))}
        </div>
    );
};

function DashboardContent() {
    const { data: statsData } = useSWR<Stats>('/api/v1/admin/stats', fetcher);
    const stats = statsData || {
        total_revenue: 124500, total_orders: 843, total_products: 156,
        active_drones: 42, pending_deliveries: 12, active_users_today: 890
    };

    return (
        <div className="w-full max-w-[1600px] mx-auto p-6 md:p-10 space-y-8 mt-20 relative z-10">

            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8"
            >
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                            <Activity size={18} className="text-cyan-400" />
                        </div>
                        <span className="text-xs font-mono text-cyan-400/70 uppercase tracking-[0.3em]">Command Center</span>
                    </div>
                    <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        SYSTEM OVERVIEW
                    </h1>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono text-gray-500 bg-white/5 border border-white/5 px-4 py-2 rounded-full backdrop-blur-md">
                    <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> ONLINE</span>
                    <span className="h-3 w-[1px] bg-white/10" />
                    <span className="flex items-center gap-2"><Server size={12} /> US-EAST-1</span>
                </div>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard title="Total Revenue" value={stats.total_revenue} icon={DollarSign} color="cyan" delay={0.1} />
                <StatCard title="Active Drones" value={stats.active_drones} icon={Wifi} color="purple" delay={0.2} />
                <StatCard title="Orders Today" value={stats.total_orders} icon={Package} color="blue" delay={0.3} />
                <StatCard title="Pending Drops" value={stats.pending_deliveries} icon={Truck} color="yellow" delay={0.4} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="lg:col-span-2 min-h-[400px] rounded-[40px] bg-black/40 backdrop-blur-xl border border-white/10 p-8 shadow-2xl relative overflow-hidden"
                >
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500/50 to-transparent opacity-50" />
                    <div className="flex items-center justify-between mb-8">
                        <h2 className="text-xl font-bold text-white flex items-center gap-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            <BarChart2 className="text-cyan-400" /> Revenue Stream
                        </h2>
                        <div className="flex gap-2">
                            {['1H', '24H', '7D', '30D'].map(p => (
                                <button key={p} className={`px-3 py-1 text-[10px] font-bold rounded-lg border transition-all ${p === '24H' ? 'bg-cyan-500 text-black border-cyan-500' : 'bg-transparent text-gray-500 border-white/10 hover:border-white/20'}`}>
                                    {p}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="h-[300px]">
                        <RevenueChart data={mockRevenueData} />
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="rounded-[40px] bg-black/40 backdrop-blur-xl border border-white/10 p-8 shadow-2xl relative overflow-hidden"
                >
                    <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-l from-purple-500/50 to-transparent opacity-50" />
                    <h2 className="text-xl font-bold text-white mb-8 flex items-center gap-3" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        <Clock className="text-purple-400" /> Neural Feed
                    </h2>
                    <ActivityTimeline events={mockActivityData} />

                    <div className="mt-8 pt-4 border-t border-white/5">
                        <button className="w-full py-3 rounded-2xl bg-white/5 border border-white/5 text-xs font-bold text-gray-400 hover:bg-white/10 hover:text-white transition-all uppercase tracking-widest">
                            View System Logs
                        </button>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}

export default function AdminDashboardPage() {
    const { data: session, status } = useSession();

    if (status === 'loading') {
        return <div className="min-h-screen w-full bg-black flex items-center justify-center"><Loader2 className="w-10 h-10 text-cyan-400 animate-spin" /></div>;
    }

    if (status === 'unauthenticated' || session?.user?.role !== 'admin') {
        return <div className="min-h-screen bg-black flex items-center justify-center text-red-500"><Lock className="mr-2" /> Access Restricted</div>;
    }

    return (
        <div className="min-h-screen w-full bg-black text-gray-100 relative overflow-y-auto overflow-x-hidden selection:bg-cyan-500/30" style={{ fontFamily: "'Montserrat', sans-serif" }}>
            <div className="fixed inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none z-0" />
            
            <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
                <Canvas camera={{ position: [0, 0, 20], fov: 45 }}>
                    <Suspense fallback={null}>
                        <DynamicDashboardBackground />
                    </Suspense>
                </Canvas>
            </div>
            
            <Suspense fallback={null}>
                <DashboardContent />
            </Suspense>
        </div>
    );
}
