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
    ListFilter,
    Package,
    Banknote,
    BrainCircuit,
    Check,
    X,
    Clock
} from 'lucide-react';

import { useRealtimeUpdates } from '@/hooks/useRealtimeUpdates';
import { toast } from 'sonner'; 
import dynamic from 'next/dynamic';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';

interface Notification {
    id: number;
    title: string;
    body: string;
    type: string;
    read: boolean;
    cta: string | null;
    timestamp: string; 
    created_at: string; 
}

interface WebSocketNotification {
    id: number;
    type: string;
    title: string;
    body: string;
    created_at: string;
}

const API_KEY = '/notifications';
const fetcher = (url: string) => api.get(url).then(res => res.data);
const getGroupTitle = (dateStr: string) => {
    
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === today.toDateString()) { return 'Today'; }
    if (date.toDateString() === yesterday.toDateString()) { return 'Yesterday'; }
    return 'Older';
};

// ============================================================================
// --- 1. (New) Notification Background Component ---
// ============================================================================
const NotificationBackground = () => {
    const light1Ref = useRef<THREE.PointLight>(null!);
    const light2Ref = useRef<THREE.PointLight>(null!);

    useFrame((state) => {
        const time = state.clock.elapsedTime;
        if (light1Ref.current) {
            light1Ref.current.position.x = Math.sin(time * 0.5) * 15;
            light1Ref.current.position.y = Math.cos(time * 0.5) * 15;
            light1Ref.current.position.z = Math.cos(time * 0.5) * 10;
        }
        if (light2Ref.current) {
            light2Ref.current.position.x = Math.sin(time * 0.3) * -15;
            light2Ref.current.position.y = Math.cos(time * 0.3) * -15;
            light2Ref.current.position.z = Math.sin(time * 0.3) * 5;
        }
    });

    return (
        <>
            <fog attach="fog" args={['#000000', 10, 30]} />
            <ambientLight intensity={1.0} />
            <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={200} color="#00C6FF" />
            <pointLight ref={light2Ref} position={[-10, -10, 5]} intensity={150} color="#7F00FF" />
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        </>
    );
};

const DynamicNotificationBackground = dynamic(() => Promise.resolve(NotificationBackground), { 
    ssr: false,
    loading: () => null
});


// ============================================================================
// --- 2. (Main Page Component) ---
// ============================================================================
export default function NotificationsPage() {
   
    const { data: initialNotifications, error, isLoading, mutate } = useSWR<Notification[]>(
        API_KEY,
        fetcher,
        { revalidateOnFocus: false }
    );

    const [filter, setFilter] = useState('All');
    const [liveNotifications, setLiveNotifications] = useState<Notification[]>([]); 
    const [undoItem, setUndoItem] = useState<(Notification & { originalIndex: number; source: 'initial' | 'live' }) | null>(null);
    const undoTimerRef = useRef<NodeJS.Timeout | null>(null);

    const handleNewNotification = useCallback((newNotification: WebSocketNotification) => {
        console.log("New notification received via WebSocket:", newNotification);
      
        const formattedNotification = {
            ...newNotification,
            timestamp: "Just now", 
            cta: null, 
            read: false, 
        } as Notification; 

        setLiveNotifications(prev => {
  
            if (prev.some(n => n.id === formattedNotification.id)) {
                return prev;
            }
            
            if (initialNotifications?.some(n => n.id === formattedNotification.id)) {
               
            }
            return [formattedNotification, ...prev];
        });
        
        toast.info(formattedNotification.body, { description: formattedNotification.title });
    }, [initialNotifications]); 

    const { isConnected: isWebSocketConnected } = useRealtimeUpdates(null, {
        onNotification: handleNewNotification 
    });

    const handleMarkAsRead = async (id: number) => {
    
        mutate((currentData = []) => currentData.map(n => (n.id === id ? { ...n, read: true } : n)), false);
        setLiveNotifications(prev => prev.map(n => (n.id === id ? { ...n, read: true } : n)));
        try {
            await api.post(`/notifications/${id}/read`);
           
        } catch (e) {
            toast.error("Failed to mark as read. Reverting.");
            mutate(); 
            setLiveNotifications(prev => prev.map(n => (n.id === id ? { ...n, read: false } : n))); 
        }
    };

    const handleDismiss = async (id: number, source: 'initial' | 'live') => {
        const allNotifications = [...liveNotifications, ...(initialNotifications || [])];
        const itemToDismiss = allNotifications.find(n => n.id === id);
        if (!itemToDismiss) return;

        const originalIndex = allNotifications.findIndex(n => n.id === id);

        if (source === 'live') {
            setLiveNotifications(prev => prev.filter(n => n.id !== id));
        } else {
            mutate((currentData = []) => currentData.filter(n => n.id !== id), false);
        }

        if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
        setUndoItem({ ...itemToDismiss, originalIndex, source }); 
        undoTimerRef.current = setTimeout(() => {
            api.delete(`/notifications/${id}`)
                .then(() => setUndoItem(null)) 
                .catch(() => {
                    toast.error("Failed to dismiss notification. Reverting.");
                    handleUndo(); 
                });
        }, 5000);
    };

     const handleMarkAllAsRead = async () => {
        
        mutate((currentData = []) => currentData.map(n => ({ ...n, read: true })), false);
        setLiveNotifications(prev => prev.map(n => ({ ...n, read: true })));
        try {
             await api.post('/notifications/read-all');
             
        } catch (e) {
             toast.error("Failed to mark all as read. Reverting.");
             mutate(); 
             setLiveNotifications(prev => prev.map(n => ({ ...n, read: false }))); 
        }
    };

    const handleUndo = () => {
        if (!undoItem) return;
        clearTimeout(undoTimerRef.current!);

       
        if (undoItem.source === 'live') {
            setLiveNotifications(prev => {
                const newArray = [undoItem, ...prev];
              
                return newArray.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            });
        } else {
            mutate((currentData = []) => {
                const newArray = [undoItem, ...(currentData || [])];
               
                return newArray.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            }, false);
        }
        setUndoItem(null);
    };

    useEffect(() => {
        
        return () => { if (undoTimerRef.current) clearTimeout(undoTimerRef.current); };
    }, []); 

    const allNotifications = useMemo(() => {
       
        const initialFiltered = (initialNotifications || []).filter(
            initial => !liveNotifications.some(live => live.id === initial.id)
        );
        return [...liveNotifications, ...initialFiltered];
    }, [liveNotifications, initialNotifications]);

    const groupedNotifications = useMemo(() => {
       
        const filtered = allNotifications.filter(n => {
            if (filter === 'Unread') return !n.read;
            if (filter === 'Orders') return n.type === 'order_update'; 
            if (filter === 'Security') return n.type === 'security';
            return true; 
        });
       
        return filtered.reduce((groups, item) => {
            const groupTitle = getGroupTitle(item.created_at);
            groups[groupTitle] = groups[groupTitle] || [];
            groups[groupTitle].push(item);
            return groups;
        }, {} as Record<string, Notification[]>);
    }, [allNotifications, filter]);

    const groupOrder = ['Today', 'Yesterday', 'Older'];
    const totalFilteredCount = Object.values(groupedNotifications).reduce((sum, group) => sum + group.length, 0);
    const unreadCount = useMemo(() => allNotifications.filter(n => !n.read).length, [allNotifications]);

    if (isLoading && !initialNotifications) { 
        return <LoadingSpinner />;
     }
    if (error) {
         return <ErrorDisplay error={error} />; 
    }

    return (
        <div className="relative min-h-screen w-full text-white flex flex-col items-center justify-start p-4 bg-black">
            
            <div className="absolute inset-0 z-0 opacity-70">
                <Canvas>
                    <Suspense fallback={null}>
                        <DynamicNotificationBackground />
                    </Suspense>
                </Canvas>
            </div>

            <div className="w-full max-w-6xl flex flex-col items-center relative z-10">

                <ControlBar
                    unreadCount={unreadCount}
                    activeFilter={filter}
                    onFilterChange={setFilter}
                    onMarkAllAsRead={handleMarkAllAsRead}
                    isWebSocketConnected={isWebSocketConnected}
                />

                <motion.div layout className="w-full mt-8">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={filter} 
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.25, ease: 'easeInOut' }}
                            className="space-y-3"
                        >
                           
                            {totalFilteredCount === 0 ? (
                                <CinematicEmptyState />
                            ) : (
                                groupOrder.map(groupTitle => (
                                    groupedNotifications[groupTitle]?.length > 0 && ( 
                                        <motion.div key={groupTitle} layout>
                                            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider my-4"
                                                style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                                {groupTitle}
                                            </h2>
                                            <div className="space-y-3">
                                                {groupedNotifications[groupTitle].map((notification, index) => {
                                                  
                                                    const source: 'live' | 'initial' = liveNotifications.some(n => n.id === notification.id) ? 'live' : 'initial';
                                                    return (
                                                        <NotificationItem
                                                            key={`${source}-${notification.id}`} 
                                                            notification={notification}
                                                            onMarkAsRead={handleMarkAsRead}
                                                            onDismiss={() => handleDismiss(notification.id, source)}
                                                            index={index} 
                                                        />
                                                    );
                                                })}
                                            </div>
                                        </motion.div>
                                    )
                                ))
                            )}
                        </motion.div>
                    </AnimatePresence>
                </motion.div>
            </div>

            <AnimatePresence>
                {undoItem && (
                    <UndoToast
                        message={`Removed "${undoItem.title.substring(0, 20)}..."`}
                        onUndo={handleUndo}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}


// ============================================================================
// --- 3. (Re-styled) Sub-Components ---
// ============================================================================

const typeConfig: { [key: string]: { icon: React.ElementType; color: string } } = {
    security: { icon: Shield, color: 'text-red-400' },
    order_update: { icon: Package, color: 'text-cyan-400' },
    payment: { icon: Banknote, color: 'text-green-400' },
    ai_agent: { icon: BrainCircuit, color: 'text-purple-400' },
    default: { icon: Bell, color: 'text-gray-400' },
};
const getIcon = (type: string) => {
    const config = typeConfig[type] || typeConfig.default;
    return <config.icon className={`w-5 h-5 ${config.color}`} />;
};

const filters = ['All', 'Unread', 'Orders', 'Security']; 
const ControlBar = ({ unreadCount, activeFilter, onFilterChange, onMarkAllAsRead, isWebSocketConnected }: {
    unreadCount: number;
    activeFilter: string;
    onFilterChange: (filter: string) => void;
    onMarkAllAsRead: () => void;
    isWebSocketConnected: boolean;
}) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-3 items-center py-4 sticky top-[72px] z-30 bg-black/30 backdrop-blur-lg rounded-b-lg gap-4 sm:gap-0">
     
      {/* --- العنوان (اليسار) --- */}
      <div className="flex sm:justify-start justify-center">
          <div className="relative flex items-center gap-3 sm:ml-6">
             <span
                  className={`w-2.5 h-2.5 rounded-full ${isWebSocketConnected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.7)]' : 'bg-gray-600'}`}
                  title={isWebSocketConnected ? 'Real-time connection active' : 'Real-time connection inactive'}
             />
            <div className='relative'> 
                <motion.h1 
                    className="text-2xl font-bold" 
                    style={{ fontFamily: "'Orbitron', sans-serif" }}
                >
                  <motion.span
                    className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                    animate={{
                      filter: [
                        'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 2px rgba(168, 85, 247, 0.4))',
                        'drop-shadow(0 0 10px rgba(0, 198, 255, 0.8)) drop-shadow(0 0 10px rgba(168, 85, 247, 0.8))',
                        'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 2px rgba(168, 85, 247, 0.4))'
                      ]
                    }}
                    transition={{
                      duration: 3,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  >
                    Notifications
                  </motion.span>
                </motion.h1>
            </div>
            {unreadCount > 0 && (
                <motion.div
                  initial={{ scale: 0 }} animate={{ scale: 1 }}
                  className="flex items-center justify-center w-7 h-7 rounded-full bg-cyan-400 text-black text-xs font-bold shadow-lg shadow-cyan-500/50">
                  {unreadCount}
                </motion.div>
             )}
          </div>
      </div>

      {/* --- الفلاتر (المنتصف) --- */}
      <div className="flex items-center justify-center gap-2 flex-wrap">
         {filters.map((filter, index) => (
          <React.Fragment key={filter}>
            <button
              onClick={() => onFilterChange(filter)}
              className={`group relative py-1 px-3 transition-colors duration-200 ${
                activeFilter === filter
                  ? 'text-cyan-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <span className="relative z-10">{filter}</span>
              {activeFilter === filter && (
                 <motion.div
                    layoutId="filter-underline"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400"
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                 />
              )}
            </button>
            {index < filters.length - 1 && ( <span className="text-gray-700">|</span> )}
          </React.Fragment>
        ))}
      </div>

      {/* --- الإعدادات (اليمين) --- */}
      <div className="relative hidden sm:flex justify-end sm:mr-6">
         <button onClick={() => setMenuOpen(!menuOpen)} className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-white/10 transition-colors">
            <Settings size={20} />
         </button>
         <AnimatePresence>
            {menuOpen && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute right-0 top-10 w-48 bg-black/50 backdrop-blur-lg border border-cyan-400/30 rounded-md shadow-2xl shadow-cyan-500/20 z-20"
                >
                    <button
                        onClick={onMarkAllAsRead}
                        className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-white/10 flex items-center gap-2"
                    >
                        <CheckCheck size={16} /> Mark all as read
                    </button>
                    <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-white/10 flex items-center gap-2">
                        <BellOff size={16} /> Mute notifications
                    </button>
                </motion.div>
            )}
         </AnimatePresence>
      </div>
    </div>
  );
};

const CinematicEmptyState = () => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.5, ease: 'easeInOut' }}
      className="flex flex-col items-center justify-center text-center pt-48 pb-24 px-6"
    >
      <Bell size={64} className="text-cyan-400/30 mb-6" />
      <h3
        className="text-xl font-semibold text-white mb-2"
        style={{ fontFamily: "'Orbitron', sans-serif" }}
      >
        All Clear
      </h3>
      <p className="text-gray-500 max-w-xs">
        You have no new notifications. We'll let you know when something new comes up.
      </p>
    </motion.div>
  );
};

const NotificationItem = ({ notification, onMarkAsRead, onDismiss, index }: {
    notification: Notification;
    onMarkAsRead: (id: number) => void;
    onDismiss: (id: number) => void;
    index: number;
}) => {
  const { id, title, body, type, read, cta, timestamp } = notification;
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -50, transition: { duration: 0.2 } }}
      transition={{ delay: index * 0.05, type: 'spring', stiffness: 200, damping: 25 }}
      whileHover={{ scale: 1.02, y: -2 }}
      className={`w-full flex items-start p-4 rounded-xl transition-all duration-300 ease-in-out ${
        read 
          ? 'bg-black/10 backdrop-blur-sm border border-gray-800/50' 
          : 'bg-black/30 backdrop-blur-lg border border-cyan-400/30 shadow-lg shadow-cyan-500/10'
      } hover:border-cyan-400/80`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <AnimatePresence>
        {!read && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            className="w-2.5 h-2.5 bg-cyan-400 rounded-full mr-4 mt-1.5 flex-shrink-0 shadow-[0_0_6px_rgba(0,198,255,0.7)]"
            title="Unread"
          />
        )}
      </AnimatePresence>
      <div className={`mr-4 mt-1 flex-shrink-0 ${read ? 'opacity-30' : ''}`}>
        {getIcon(type)}
      </div>
    
      <div className="flex-grow">
        <h4 className={`font-semibold ${read ? 'text-gray-500' : 'text-gray-100'}`}>
          {title}
        </h4>
        <p className={`text-sm ${read ? 'text-gray-600' : 'text-gray-400'}`}>
          {body}
        </p>
        <div className="flex items-center gap-4 mt-2">
          <span className="text-xs text-gray-500 flex items-center gap-1.5">
            <Clock size={12} /> {timestamp}
          </span>
          {cta && (
            <button className="text-xs font-semibold text-cyan-400 hover:text-cyan-300">
              {cta}
            </button>
          )}
        </div>
      </div>
      {/* Actions */}
      <motion.div
        className="flex flex-col sm:flex-row items-center gap-2 ml-4 flex-shrink-0"
        animate={{ opacity: isHovered || !read ? 1 : 0, x: isHovered || !read ? 0 : 5 }}
        transition={{ duration: 0.2 }}
      >
        {!read && (
          <button
            onClick={() => onMarkAsRead(id)}
            title="Mark as read"
            className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <Check size={16} />
          </button>
        )}
        <button
          onClick={() => onDismiss(id)}
          title="Dismiss"
          className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-red-900/50 transition-colors"
        >
          <X size={16} />
        </button>
      </motion.div>
    </motion.div>
  );
};

const UndoToast = ({ message, onUndo }: { message: string; onUndo: () => void }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-black/50 backdrop-blur-lg border border-cyan-400/50 text-white py-3 px-5 rounded-lg shadow-2xl shadow-cyan-500/20 flex items-center justify-between z-50"
    >
      <span className="text-sm mr-6">{message}</span>
      <button
        onClick={onUndo}
        className="text-sm font-bold text-cyan-400 hover:text-cyan-300 uppercase tracking-wider"
      >
        Undo
      </button>
    </motion.div>
  );
};

const LoadingSpinner = () => (
    <div className="flex items-center justify-center min-h-screen w-full" style={{ backgroundColor: '#000000' }}>
        <Loader className="w-12 h-12 text-cyan-400 animate-spin" />
    </div>
);
const ErrorDisplay = ({ error }: { error: Error }) => (
     <div className="flex flex-col items-center justify-center min-h-screen w-full text-red-400" style={{ backgroundColor: '#000000' }}>
         <Shield size={48} className="mb-4" />
        <h3 className="text-xl font-semibold">Error Loading Notifications</h3>
        <p className="text-gray-500">{error.message}</p>
    </div>
);
