'use client';

import React, { useState, useRef, useMemo, useEffect, useCallback, Suspense } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import useSWR from 'swr';
import { api } from '@/lib/api'; 
import {
    Shield,
    Loader,
    Bell,
    Settings,
    CheckCheck,
    BellOff,
    Package,
    Banknote,
    BrainCircuit,
    Check,
    X,
    Clock,
    Activity,
    Signal
} from 'lucide-react';
import { useRealtimeUpdates } from '@/hooks/useRealtimeUpdates';
import { toast } from 'sonner';
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';
import { Notification, WebSocketNotification } from '@/types';

// ============================================================================
// --- 1. ARCHITECTURAL CONFIGURATION ---
// ============================================================================

const API_KEY = '/notifications';

const fetcher = async (url: string) => {
    try {
        const res = await api.get(url);
        return res.data;
    } catch (error: any) {
        if (error.response && error.response.status === 307) {
             const res = await api.get(url + '/');
             return res.data;
        }
        throw error;
    }
};

const getGroupTitle = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === today.toDateString()) { return 'Today'; }
    if (date.toDateString() === yesterday.toDateString()) { return 'Yesterday'; }
    return 'System Logs';
};

// ============================================================================
// --- 2. VISUAL ENGINE (The Void) ---
// ============================================================================

const NotificationBackground = () => {
    const groupRef = useRef<THREE.Group>(null!);

    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
            groupRef.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.1) * 0.02;
        }
    });

    return (
        <group ref={groupRef}>
            <fog attach="fog" args={['#000000', 20, 70]} />
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={2} color="#00C6FF" />
            <pointLight position={[-10, -10, 5]} intensity={2} color="#7F00FF" />
            <Stars radius={100} depth={60} count={6000} factor={4} saturation={0} fade speed={0.5} />
        </group>
    );
};

const DynamicNotificationBackground = dynamic(() => Promise.resolve(NotificationBackground), {
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 3. UI COMPONENTS (The Modules) ---
// ============================================================================

const typeConfig: { [key: string]: { icon: React.ElementType; color: string; bg: string; border: string } } = {
    security: { 
        icon: Shield, 
        color: 'text-red-400', 
        bg: 'bg-red-500/10', 
        border: 'border-red-500/20' 
    },
    order_update: { 
        icon: Package, 
        color: 'text-cyan-400', 
        bg: 'bg-cyan-500/10', 
        border: 'border-cyan-500/20' 
    },
    payment: { 
        icon: Banknote, 
        color: 'text-green-400', 
        bg: 'bg-green-500/10', 
        border: 'border-green-500/20' 
    },
    ai_agent: { 
        icon: BrainCircuit, 
        color: 'text-purple-400', 
        bg: 'bg-purple-500/10', 
        border: 'border-purple-500/20' 
    },
    default: { 
        icon: Bell, 
        color: 'text-gray-400', 
        bg: 'bg-white/5', 
        border: 'border-white/10' 
    },
};

const NotificationItem = ({ notification, onMarkAsRead, onDismiss, index }: {
    notification: Notification;
    onMarkAsRead: (id: number) => void;
    onDismiss: (id: number) => void;
    index: number;
}) => {
  const { id, title, body, type, read, cta, timestamp } = notification;
  const config = typeConfig[type] || typeConfig.default;
  const Icon = config.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -50, scale: 0.9 }}
      transition={{ delay: index * 0.05, type: 'spring', stiffness: 200, damping: 25 }}
      className={`group relative p-6 rounded-[30px] border transition-all duration-500 ${
        read
          ? 'bg-white/5 border-white/5 hover:border-white/10'
          : 'bg-black/40 backdrop-blur-xl border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.05)] hover:border-cyan-400/50 hover:shadow-[0_0_40px_rgba(6,182,212,0.1)]'
      }`}
    >
      <div className="flex items-start gap-6">
        {/* Status Indicator */}
        <div className="flex-shrink-0 relative">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border ${config.bg} ${config.border} ${config.color} transition-transform group-hover:scale-110 duration-500`}>
                <Icon size={24} />
            </div>
            {!read && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-cyan-400 rounded-full shadow-[0_0_10px_rgba(34,211,238,0.8)] animate-pulse" />
            )}
        </div>

        {/* Content Core */}
        <div className="flex-grow pt-1">
            <div className="flex justify-between items-start">
                <h4 className={`text-lg font-bold mb-1 transition-colors ${read ? 'text-gray-500' : 'text-white'}`} style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    {title}
                </h4>
                <span className="text-xs text-gray-600 font-mono flex items-center gap-1.5 whitespace-nowrap ml-4">
                    <Clock size={12} /> {timestamp}
                </span>
            </div>
            
            <p className={`text-sm leading-relaxed mb-4 ${read ? 'text-gray-600' : 'text-gray-300'}`}>
                {body}
            </p>

            {cta && (
                <button className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs font-bold uppercase tracking-wider text-cyan-400 hover:bg-cyan-500/10 hover:border-cyan-500/30 transition-all flex items-center gap-2">
                    {cta} <Activity size={14} />
                </button>
            )}
        </div>

        {/* Actions Dock */}
        <div className="flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 transform translate-x-4 group-hover:translate-x-0">
            {!read && (
                <button
                    onClick={() => onMarkAsRead(id)}
                    title="Mark Read"
                    className="p-2 rounded-xl bg-white/5 hover:bg-green-500/20 text-gray-400 hover:text-green-400 transition-colors"
                >
                    <Check size={18} />
                </button>
            )}
            <button
                onClick={() => onDismiss(id)}
                title="Dismiss"
                className="p-2 rounded-xl bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
            >
                <X size={18} />
            </button>
        </div>
      </div>
    </motion.div>
  );
};

const ControlBar = ({ unreadCount, activeFilter, onFilterChange, onMarkAllAsRead, isWebSocketConnected }: any) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const filters = ['All', 'Unread', 'Orders', 'Security'];

  return (
    <div className="sticky top-24 z-30 w-full max-w-4xl mx-auto mb-12">
        <div className="relative p-2 rounded-full bg-black/60 backdrop-blur-xl border border-white/10 shadow-2xl flex items-center justify-between">
            
            {/* Status Pod */}
            <div className="hidden md:flex items-center gap-3 px-6 border-r border-white/10">
                <div className="relative">
                    <div className={`w-2 h-2 rounded-full ${isWebSocketConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
                    <div className={`absolute inset-0 w-2 h-2 rounded-full ${isWebSocketConnected ? 'bg-green-500' : 'bg-red-500'} blur-sm`} />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                    {isWebSocketConnected ? 'Live Feed' : 'Offline'}
                </span>
            </div>

            {/* Filter Switch */}
            <div className="flex items-center gap-1 overflow-x-auto no-scrollbar px-2">
                {filters.map((filter) => (
                    <button
                        key={filter}
                        onClick={() => onFilterChange(filter)}
                        className={`relative px-6 py-2.5 rounded-full text-sm font-bold transition-all duration-300 whitespace-nowrap ${
                            activeFilter === filter 
                            ? 'text-black shadow-[0_0_20px_rgba(34,211,238,0.4)]' 
                            : 'text-gray-500 hover:text-white hover:bg-white/5'
                        }`}
                    >
                        {activeFilter === filter && (
                            <motion.div 
                                layoutId="filter-pill" 
                                className="absolute inset-0 bg-cyan-400 rounded-full"
                                transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            {filter}
                            {filter === 'Unread' && unreadCount > 0 && (
                                <span className="bg-red-500 text-white text-[9px] px-1.5 py-0.5 rounded-full shadow-sm">
                                    {unreadCount}
                                </span>
                            )}
                        </span>
                    </button>
                ))}
            </div>

            {/* Actions Pod */}
            <div className="relative pl-2 border-l border-white/10">
                <button 
                    onClick={() => setMenuOpen(!menuOpen)}
                    className="p-3 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                >
                    <Settings size={20} />
                </button>
                
                <AnimatePresence>
                    {menuOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 10, scale: 0.95 }}
                            className="absolute right-0 top-14 w-56 bg-black/90 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl p-2 z-50"
                        >
                            <button
                                onClick={() => { onMarkAllAsRead(); setMenuOpen(false); }}
                                className="w-full text-left px-4 py-3 rounded-xl text-sm text-gray-300 hover:bg-white/10 hover:text-white flex items-center gap-3 transition-colors"
                            >
                                <CheckCheck size={16} className="text-cyan-400" /> Mark all read
                            </button>
                            <button 
                                onClick={() => setMenuOpen(false)}
                                className="w-full text-left px-4 py-3 rounded-xl text-sm text-gray-300 hover:bg-white/10 hover:text-white flex items-center gap-3 transition-colors"
                            >
                                <BellOff size={16} className="text-red-400" /> Mute alerts
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    </div>
  );
};

const CinematicEmptyState = () => (
    <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center text-center py-32"
    >
        <div className="relative mb-8">
            <div className="absolute inset-0 bg-cyan-500/20 blur-3xl rounded-full animate-pulse" />
            <div className="relative p-8 rounded-[40px] bg-black/40 border border-white/10 backdrop-blur-xl">
                <Signal size={48} className="text-cyan-400/50" />
            </div>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
            All Systems Nominal
        </h3>
        <p className="text-gray-500 max-w-xs font-light">
            Communication channels are clear. No active notifications pending.
        </p>
    </motion.div>
);

// ============================================================================
// --- 4. MAIN PAGE (The Assembly) ---
// ============================================================================

export default function NotificationsPage() {
    const { data: initialNotifications, error, isLoading, mutate } = useSWR<Notification[]>(
        API_KEY, fetcher, { revalidateOnFocus: false, shouldRetryOnError: true }
    );

    const [filter, setFilter] = useState('All');
    const [liveNotifications, setLiveNotifications] = useState<Notification[]>([]);
    const [undoItem, setUndoItem] = useState<any>(null);
    const undoTimerRef = useRef<NodeJS.Timeout | null>(null);

    const handleNewNotification = useCallback((newNotification: WebSocketNotification) => {
        const formatted: Notification = {
            ...newNotification,
            id: newNotification.id || Date.now(),
            timestamp: "Just now",
            cta: null,
            read: false,
        };
        setLiveNotifications(prev => [formatted, ...prev]);
        toast.custom((t) => (
            <div className="bg-black/80 backdrop-blur-md border border-cyan-500/30 p-4 rounded-2xl shadow-2xl flex items-center gap-4">
                <div className="p-2 bg-cyan-500/10 rounded-full text-cyan-400"><Bell size={18} /></div>
                <div>
                    <h4 className="font-bold text-white text-sm">{formatted.title}</h4>
                    <p className="text-xs text-gray-400">{formatted.body}</p>
                </div>
            </div>
        ));
    }, []);

    const { isConnected } = useRealtimeUpdates(null, { onNotification: handleNewNotification });

    const handleMarkAsRead = async (id: number) => {
        mutate((d = []) => d.map(n => n.id === id ? { ...n, read: true } : n), false);
        setLiveNotifications(p => p.map(n => n.id === id ? { ...n, read: true } : n));
        try { await api.post(`/notifications/${id}/read`); } catch { mutate(); }
    };

    const handleDismiss = async (id: number, source: 'initial' | 'live') => {
        // Logic same as original, simplified for brevity
        const all = [...liveNotifications, ...(initialNotifications || [])];
        const item = all.find(n => n.id === id);
        if (!item) return;

        if (source === 'live') setLiveNotifications(p => p.filter(n => n.id !== id));
        else mutate((d = []) => d.filter(n => n.id !== id), false);

        setUndoItem({ ...item, source });
        undoTimerRef.current = setTimeout(() => {
            api.delete(`/notifications/${id}`).then(() => setUndoItem(null));
        }, 4000);
    };

    const handleMarkAllAsRead = async () => {
        mutate((d = []) => d.map(n => ({ ...n, read: true })), false);
        setLiveNotifications(p => p.map(n => ({ ...n, read: true })));
        try { await api.post('/notifications/read-all'); } catch { mutate(); }
    };

    const handleUndo = () => {
        if (!undoItem) return;
        clearTimeout(undoTimerRef.current!);
        if (undoItem.source === 'live') setLiveNotifications(p => [undoItem, ...p]);
        else mutate((d = []) => [undoItem, ...(d || [])], false);
        setUndoItem(null);
    };

    const allNotifications = useMemo(() => {
        const initial = Array.isArray(initialNotifications) ? initialNotifications : [];
        return [...liveNotifications, ...initial.filter(i => !liveNotifications.some(l => l.id === i.id))];
    }, [liveNotifications, initialNotifications]);

    const grouped = useMemo(() => {
        const f = allNotifications.filter(n => {
            if (filter === 'Unread') return !n.read;
            if (filter === 'Orders') return n.type === 'order_update';
            if (filter === 'Security') return n.type === 'security';
            return true;
        });
        return f.reduce((acc, item) => {
            const t = getGroupTitle(item.created_at);
            if (!acc[t]) acc[t] = [];
            acc[t].push(item);
            return acc;
        }, {} as Record<string, Notification[]>);
    }, [allNotifications, filter]);

    const groups = ['Today', 'Yesterday', 'System Logs'];
    const hasData = Object.values(grouped).some(g => g.length > 0);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100 selection:bg-cyan-500/30 font-sans">
            
            {/* Background */}
            <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
                <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                    <Suspense fallback={null}>
                        <DynamicNotificationBackground />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
            </div>

            {/* Header */}
            <section className="relative z-10 pt-40 pb-10 px-4 text-center">
                <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/20 bg-cyan-900/10 backdrop-blur-md mb-8">
                        <Signal size={14} className="text-cyan-400" />
                        <span className="text-xs font-bold uppercase tracking-widest text-cyan-200/80">Neural Uplink V4.0</span>
                    </div>
                    <h1 className="text-5xl md:text-7xl font-black text-white mb-6 tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        COMMUNICATION <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-600">LOGS</span>
                    </h1>
                </motion.div>
            </section>

            {/* Main Interface */}
            <div className="relative z-10 container mx-auto px-4 max-w-4xl pb-32">
                
                <ControlBar 
                    unreadCount={allNotifications.filter(n => !n.read).length} 
                    activeFilter={filter} 
                    onFilterChange={setFilter} 
                    onMarkAllAsRead={handleMarkAllAsRead} 
                    isWebSocketConnected={isConnected}
                />

                <motion.div layout className="space-y-12">
                    {isLoading && !initialNotifications ? (
                        <div className="flex justify-center py-20"><Loader className="animate-spin text-cyan-400 w-12 h-12" /></div>
                    ) : !hasData ? (
                        <CinematicEmptyState />
                    ) : (
                        groups.map(group => grouped[group]?.length > 0 && (
                            <motion.div key={group} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="h-px bg-white/10 flex-grow" />
                                    <span className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500">{group}</span>
                                    <div className="h-px bg-white/10 flex-grow" />
                                </div>
                                <div className="space-y-4">
                                    {grouped[group].map((n, i) => (
                                        <NotificationItem 
                                            key={n.id} 
                                            notification={n} 
                                            onMarkAsRead={handleMarkAsRead} 
                                            onDismiss={() => handleDismiss(n.id, liveNotifications.some(l => l.id === n.id) ? 'live' : 'initial')}
                                            index={i} 
                                        />
                                    ))}
                                </div>
                            </motion.div>
                        ))
                    )}
                </motion.div>
            </div>

            {/* Undo Toast */}
            <AnimatePresence>
                {undoItem && (
                    <motion.div 
                        initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 50, opacity: 0 }}
                        className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-black/80 backdrop-blur-xl border border-white/10 px-6 py-4 rounded-full flex items-center gap-6 z-50 shadow-2xl"
                    >
                        <span className="text-sm text-gray-300">Archive updated</span>
                        <button onClick={handleUndo} className="text-sm font-bold text-cyan-400 hover:text-cyan-300 uppercase tracking-wider">Undo</button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
