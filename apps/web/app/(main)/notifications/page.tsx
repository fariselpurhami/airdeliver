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
    Signal, RefreshCw, ChevronLeft, ChevronRight, ArrowUpRight, Inbox
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { toast } from 'sonner';
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';
import { Notification } from '@/types';
import Link from 'next/link';

// ============================================================================
// --- 1. ARCHITECTURAL CONFIGURATION ---
// ============================================================================

// Keep the legacy list route available to other consumers.

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
    return 'Earlier';
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

interface NotificationTypeStyle {
    icon: LucideIcon;
    color: string;
    bg: string;
    border: string;
}
const typeConfig: Record<string, NotificationTypeStyle> & { default: NotificationTypeStyle } = {
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
      className={`group relative p-5 sm:p-6 rounded-[26px] border transition-all duration-500 ${
        read
          ? 'bg-slate-950/50 border-white/10 hover:border-white/20'
          : 'bg-gradient-to-br from-cyan-950/40 via-slate-950/80 to-violet-950/30 backdrop-blur-xl border-cyan-400/25 shadow-[0_12px_50px_rgba(0,0,0,0.25)] hover:border-cyan-300/50'
      }`}
    >
      <div className="flex items-start gap-3 sm:gap-6">
        {/* Status Indicator */}
        <div className="flex-shrink-0 relative">
            <div className={`w-11 h-11 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center border ${config.bg} ${config.border} ${config.color} transition-transform group-hover:scale-110 duration-500`}>
                <Icon size={24} />
            </div>
            {!read && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-cyan-400 rounded-full shadow-[0_0_10px_rgba(34,211,238,0.8)] animate-pulse" />
            )}
        </div>

        {/* Content Core */}
        <div className="flex-grow min-w-0 pt-1">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-2">
                <h4 className={`text-base sm:text-lg font-semibold mb-1 leading-snug transition-colors ${read ? 'text-slate-300' : 'text-white'}`}>
                    {title}
                </h4>
                <span className="text-xs text-gray-400 font-mono flex items-center gap-1.5 sm:whitespace-nowrap sm:ml-4">
                    <Clock size={12} /> {timestamp}
                </span>
            </div>
            
            <p className={`text-sm leading-relaxed mb-4 ${read ? 'text-slate-400' : 'text-slate-300'}`}>
                {body}
            </p>

            {cta && /^\/tracking\/[1-9]\d{0,9}$/.test(cta) && Number(cta.split('/').at(-1))<=2147483647 && (
                <Link href={cta} className="inline-flex min-h-11 px-4 py-2 rounded-xl bg-cyan-400/10 border border-cyan-300/20 text-sm font-semibold text-cyan-200 hover:bg-cyan-400/20 hover:border-cyan-300/40 transition-all items-center gap-2">
                    Open order <ArrowUpRight size={16} />
                </Link>
            )}
        </div>

        {/* Actions Dock */}
        <div className="flex shrink-0 flex-col gap-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-300">
            {!read && (
                <button
                    onClick={() => onMarkAsRead(id)}
                    title="Mark Read"
                    className="min-w-10 min-h-10 p-2 rounded-xl bg-white/5 hover:bg-green-500/20 text-gray-400 hover:text-green-400 transition-colors"
                >
                    <Check size={18} />
                </button>
            )}
            <button
                onClick={() => onDismiss(id)}
                title="Dismiss"
                className="min-w-10 min-h-10 p-2 rounded-xl bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
            >
                <X size={18} />
            </button>
        </div>
      </div>
    </motion.div>
  );
};

const ControlBar = ({ unreadCount, activeFilter, onFilterChange, onMarkAllAsRead }: any) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const filters = ['All', 'Unread', 'Orders', 'Security'];

  return (
    <div className="relative z-30 w-full mb-7">
        <div className="relative p-1.5 rounded-2xl bg-white/[0.035] backdrop-blur-xl border border-white/10 flex items-center justify-between gap-2">
            
            {/* Filter Switch */}
            <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto no-scrollbar">
                {filters.map((filter) => (
                    <button
                        key={filter}
                        onClick={() => onFilterChange(filter)}
                        className={`relative shrink-0 px-2 sm:px-5 py-3 rounded-xl text-[11px] sm:text-sm font-bold transition-all duration-300 whitespace-nowrap ${
                            activeFilter === filter 
                            ? 'text-black shadow-[0_0_20px_rgba(34,211,238,0.4)]' 
                            : 'text-slate-400 hover:text-white hover:bg-white/5'
                        }`}
                    >
                        {activeFilter === filter && (
                            <motion.div 
                                layoutId="filter-pill" 
                                className="absolute inset-0 bg-cyan-400 rounded-xl"
                                transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-1 sm:gap-2">
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
            <div className="relative shrink-0 border-l border-white/10 pl-1">
                <button 
                    aria-label="Notification settings" onClick={() => setMenuOpen(!menuOpen)}
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
                                disabled title="Alert preferences are not available yet"
                                className="w-full text-left px-4 py-3 rounded-xl text-sm text-gray-500 flex items-center gap-3 opacity-60"
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
        className="flex flex-col items-center justify-center text-center py-14 px-5 rounded-3xl bg-white/[0.025] border border-white/10"
    >
        <div className="relative mb-6">
            <div className="absolute inset-0 bg-cyan-500/20 blur-3xl rounded-full animate-pulse" />
            <div className="relative p-5 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl">
                <Inbox size={36} className="text-cyan-300" />
            </div>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">
            No notices in this view
        </h3>
        <p className="text-slate-400 max-w-sm text-sm leading-relaxed">
            No saved notifications match this page and filter.
        </p>
    </motion.div>
);

// ============================================================================
// --- 4. MAIN PAGE (The Assembly) ---
// ============================================================================

export default function NotificationsPage() {
    const [page,setPage]=useState(1);
    const [mutationError,setMutationError]=useState('');
    const {data:history,error,isLoading,mutate:mutateHistory}=useSWR<{items:Notification[],total:number}>(
        `/notifications/history?page=${page}&limit=20`,fetcher,{revalidateOnFocus:true,shouldRetryOnError:false,refreshInterval:60000,refreshWhenHidden:false,refreshWhenOffline:false}
    );
    const initialNotifications=history?.items;
    const mutate=async(updater?: (items:Notification[])=>Notification[],revalidate?:boolean)=>{
        if(typeof updater==='function')return mutateHistory(current=>current?{...current,items:updater(current.items)}:current,revalidate);
        return mutateHistory();
    };

    const [filter, setFilter] = useState('All');
    const [liveNotifications, setLiveNotifications] = useState<Notification[]>([]);
    const [isDeleting,setIsDeleting]=useState(false);
    const [undoItem, setUndoItem] = useState<(Notification & {source: 'initial' | 'live'}) | null>(null);
    const undoTimerRef = useRef<NodeJS.Timeout | null>(null);

    // No live notification socket exists in the backend; the list is REST-fed.

    const handleMarkAsRead = async (id: number) => {
        try { await api.post(`/notifications/${id}/read`);setMutationError('');await mutate(); } catch { setMutationError('Read status could not be saved. Refresh to check the current state.');void mutate(); }
    };

    const handleDismiss = async (id: number, source: 'initial' | 'live') => {
        if(undoTimerRef.current)return;
        const all = [...liveNotifications, ...(initialNotifications || [])];
        const item = all.find(n => n.id === id);
        if (!item) return;

        if (source === 'live') setLiveNotifications(p => p.filter(n => n.id !== id));
        else mutate((d:Notification[] = []) => d.filter(n => n.id !== id), false);

        setUndoItem({ ...item, source });
        undoTimerRef.current = setTimeout(() => {
            setIsDeleting(true);
            api.delete(`/notifications/${id}`).then(() => {undoTimerRef.current=null;setUndoItem(null);setMutationError('');void mutate();}).catch(()=>{undoTimerRef.current=null;setUndoItem(null);setMutationError('Dismissal could not be confirmed. Refresh to check your notifications.');void mutate();}).finally(()=>setIsDeleting(false));
        }, 4000);
    };

    const handleMarkAllAsRead = async () => {
        try { await api.post('/notifications/read-all');setMutationError('');await mutate(); } catch { setMutationError('Read status could not be saved. Refresh to check the current state.');void mutate(); }
    };

    const handleUndo = () => {
        if (!undoItem || isDeleting) return;
        clearTimeout(undoTimerRef.current!);
        if (undoItem.source === 'live') setLiveNotifications(p => [undoItem, ...p]);
        else mutate((d:Notification[] = []) => [undoItem, ...(d || []).filter(n=>n.id!==undoItem.id)], false);
        undoTimerRef.current=null;
        setUndoItem(null);
    };

    const allNotifications = useMemo(() => {
        const initial = Array.isArray(initialNotifications) ? initialNotifications : [];
        return [...liveNotifications, ...initial.filter(i => !liveNotifications.some(l => l.id === i.id))].filter(n=>n.id!==undoItem?.id);
    }, [liveNotifications, initialNotifications,undoItem]);

    useEffect(()=>{setLiveNotifications([]);},[page]);
    useEffect(()=>()=>{if(undoTimerRef.current)clearTimeout(undoTimerRef.current);},[]);

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

    const groups = ['Today', 'Yesterday', 'Earlier'];
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

            <div aria-hidden="true" className="fixed inset-0 pointer-events-none z-0" style={{background:'radial-gradient(ellipse at 15% 15%,rgba(6,182,212,.14),transparent 48%),radial-gradient(ellipse at 90% 45%,rgba(124,58,237,.13),transparent 52%)'}} />
            <div aria-hidden="true" className="fixed inset-0 pointer-events-none z-0 opacity-20" style={{backgroundImage:'linear-gradient(rgba(148,163,184,.12) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.12) 1px,transparent 1px)',backgroundSize:'64px 64px',maskImage:'linear-gradient(to bottom,black,transparent)'}} />
            <main className="relative z-10 mx-auto max-w-6xl px-5 sm:px-8 pt-28 sm:pt-36 pb-24">
                <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-slate-400 mb-8">
                    <Link href="/profile" className="hover:text-white transition-colors">Your account</Link><ChevronRight size={14}/><span className="text-cyan-200">Notifications</span>
                </nav>
                <section className="mb-9 sm:mb-12 max-w-3xl">
                    <p className="text-xs font-semibold tracking-[.16em] text-cyan-300 mb-4">airdeliver / your updates</p>
                    <h1 className="text-4xl sm:text-6xl font-semibold tracking-tight text-white mb-4">Your notifications<span className="text-cyan-300">.</span></h1>
                    <p className="text-base sm:text-lg leading-relaxed text-slate-300 max-w-2xl">Order updates, account activity and saved notices. Everything you need to catch up, in one place.</p>
                </section>
                <div className="grid lg:grid-cols-[minmax(0,1fr)_280px] gap-6 lg:gap-8 items-start">
                <section aria-label="Saved notifications" className="min-w-0 rounded-[30px] border border-white/10 bg-slate-950/60 backdrop-blur-2xl p-4 sm:p-7 shadow-[0_24px_100px_rgba(0,0,0,.3)]">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                        <div><h2 className="text-lg font-semibold text-white">Saved updates</h2><p className="text-sm text-slate-400 mt-1">{history?`${history.total} saved ${history.total===1?'notification':'notifications'}`:'Checking your saved history'}</p></div>
                        <button type="button" onClick={()=>void mutate()} className="inline-flex items-center gap-2 min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-medium text-slate-200 hover:bg-white/10 transition-colors"><RefreshCw size={15}/>Refresh notifications</button>
                    </div>
                    {error&&<p role="alert" className="rounded-xl border border-amber-300/30 bg-amber-300/5 p-4 mb-5 text-sm text-amber-200">Notifications could not be refreshed. Any notices below are the last saved view.</p>}
                    {mutationError&&<p role="alert" className="rounded-xl border border-amber-300/30 bg-amber-300/5 p-4 mb-5 text-sm text-amber-200">{mutationError}</p>}
                    <ControlBar unreadCount={allNotifications.filter(n=>!n.read).length} activeFilter={filter} onFilterChange={setFilter} onMarkAllAsRead={handleMarkAllAsRead}/>
                <motion.div layout className="space-y-7">
                    {isLoading && !initialNotifications ? (
                        <div role="status" aria-label="Loading notifications" className="space-y-4"><p className="flex items-center gap-2 text-sm text-slate-400"><Loader size={16} className="animate-spin"/>Loading your saved updates</p>{[1,2,3].map(i=><div key={i} className="h-32 rounded-3xl border border-white/5 bg-white/[0.03] animate-pulse"/>)}</div>
                    ) : error && !history ? (
                        <p className="text-center text-slate-400 py-16">The saved history is unavailable. Use Refresh notifications to try again.</p>
                    ) : !hasData ? (
                        <CinematicEmptyState />
                    ) : (
                        groups.map(group => {
                            const items = grouped[group];
                            if (!items || items.length === 0) return null;
                            return (
                            <motion.div key={group} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="h-px bg-white/10 flex-grow" />
                                    <span className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{group}</span>
                                    <div className="h-px bg-white/10 flex-grow" />
                                </div>
                                <div className="space-y-4">
                                    {items.map((n, i) => (
                                        <NotificationItem 
                                            key={n.id} 
                                            notification={n} 
                                            onMarkAsRead={handleMarkAsRead} 
                                            onDismiss={() => {if(!undoItem)void handleDismiss(n.id, liveNotifications.some(l => l.id === n.id) ? 'live' : 'initial');}}
                                            index={i} 
                                        />
                                    ))}
                                </div>
                            </motion.div>
                            );
                        })
                    )}
                </motion.div>
                    <div className="flex flex-wrap items-center justify-between gap-3 mt-7 pt-6 border-t border-white/10">
                        <p className="text-sm text-slate-400">Page <span className="text-white">{page}</span>{history?` of ${Math.max(1,Math.ceil(history.total/20))}`:''}</p>
                        <div className="flex gap-2">
                            <button disabled={page===1 || !!undoItem} onClick={()=>setPage(p=>p-1)} className="inline-flex items-center gap-1 min-h-11 px-3 rounded-xl border border-white/10 bg-white/5 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-30"><ChevronLeft size={16}/>Previous</button>
                            <button disabled={!history || page*20>=history.total || !!undoItem} onClick={()=>setPage(p=>p+1)} className="inline-flex items-center gap-1 min-h-11 px-4 rounded-xl border border-cyan-300/20 bg-cyan-400/10 text-sm text-cyan-200 hover:bg-cyan-400/20 disabled:opacity-30">Next<ChevronRight size={16}/></button>
                        </div>
                        <p className="text-xs text-slate-500 w-full">Filters apply to the current page. New notices may move older updates to the next page.</p>
                    </div>
                </section>
                <aside className="space-y-4">
                    <div className="rounded-[26px] border border-cyan-300/15 bg-gradient-to-br from-cyan-950/40 to-slate-950/80 backdrop-blur-xl p-6">
                        <div className="w-11 h-11 rounded-2xl border border-cyan-300/20 bg-cyan-400/10 flex items-center justify-center text-cyan-300 mb-5"><Bell size={21}/></div>
                        <h2 className="text-base font-semibold text-white mb-3">Saved here, for you</h2>
                        <p className="text-sm leading-relaxed text-slate-300">These are saved in-app notices, not proof an email or push was delivered.</p>
                        <p className="text-sm leading-relaxed text-slate-400 mt-4">Checks every minute while visible and online. You can refresh at any time.</p>
                    </div>
                    <div className="rounded-[26px] border border-white/10 bg-white/[0.025] backdrop-blur-xl p-6">
                        <h2 className="text-base font-semibold text-white mb-3">Looking for an order?</h2>
                        <p className="text-sm text-slate-400 leading-relaxed mb-5">Open an order update to see its latest saved status and details.</p>
                        <Link href="/profile" className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-200 hover:text-white">View order history<ArrowUpRight size={16}/></Link>
                    </div>
                </aside>
                </div>
            </main>

            {/* Undo Toast */}
            <AnimatePresence>
                {undoItem && (
                    <motion.div 
                        initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 50, opacity: 0 }}
                        className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-black/80 backdrop-blur-xl border border-white/10 px-6 py-4 rounded-full flex items-center gap-6 z-50 shadow-2xl"
                    >
                        <span className="text-sm text-gray-300">Dismissal pending</span>
                        <button onClick={handleUndo} disabled={isDeleting} className="text-sm font-bold text-cyan-400 hover:text-cyan-300 uppercase tracking-wider">Undo</button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
