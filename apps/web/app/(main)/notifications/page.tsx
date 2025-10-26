'use client';

import React, { useState, useRef, useMemo, useEffect } from 'react'; 
import { AnimatePresence, motion } from 'framer-motion';
import useSWR, { useSWRConfig } from 'swr';
import { api } from '@/lib/api'; 
import { ControlBar } from '@/components/notifications/ControlBar';
import { NotificationItem } from '@/components/notifications/NotificationItem';
import { FocusPanel } from '@/components/notifications/FocusPanel';
import { UndoToast } from '@/components/notifications/UndoToast';
import { Shield, Loader } from 'lucide-react'; 

// --- Interface ---
interface Notification {
    id: number;
    title: string;
    body: string;
    type: string; 
    read: boolean;
    cta: string | null;
    timestamp: string; 
}

// --- 💡API_KEY ---
// baseURL api.ts "http://.../api/v1"
//  KEY '/' 
const API_KEY = '/notifications'; // SWR Key

export default function NotificationsPage() {
    // === SWR DATA FETCHING ===
    // --- 💡  💡 ---
    // (api.get) fetcher
    const { data: notifications, error, isLoading, mutate } = useSWR<Notification[]>(
        API_KEY, 
        (url) => api.get(url).then(res => res.data) // <-- استخدمنا axios fetcher
    );

    // === LOCAL UI STATE ===
    const [filter, setFilter] = useState('All');
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [undoItem, setUndoItem] = useState<(Notification & { originalIndex: number }) | null>(null);
    const undoTimerRef = useRef(null);

    // === HANDLER FUNCTIONS ===
    
    // 5. Mark one as read
    const handleMarkAsRead = async (id: number) => {
        mutate(
            (currentData) =>
                currentData.map(n => (n.id === id ? { ...n, read: true } : n)),
            false 
        );
        try {
            await api.post(`/notifications/${id}/read`);
        } catch (e) {
            mutate(); 
        }
    };

    // 6. Dismiss an item
    const handleDismiss = async (id: number) => {
        const itemToDismiss = notifications.find(n => n.id === id);
        if (!itemToDismiss) return;

        const originalIndex = notifications.findIndex(n => n.id === id);
        
        mutate(
            (currentData) => currentData.filter(n => n.id !== id),
            false
        );

        if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
        setUndoItem({ ...itemToDismiss, originalIndex });
        undoTimerRef.current = setTimeout(() => {
            api.delete(`/notifications/${id}`).catch(() => mutate()); 
            setUndoItem(null);
        }, 5000);
    };

    // 7. Mark all as read
    const handleMarkAllAsRead = async () => {
        mutate(
            (currentData) => currentData.map(n => ({ ...n, read: true })),
            false
        );
        try {
            await api.post('/notifications/read-all');
        } catch (e) {
            mutate(); 
        }
    };

    // 8. Undo dismissal
    const handleUndo = () => {
        if (!undoItem) return;

        clearTimeout(undoTimerRef.current);
        
        mutate(
            (currentData) => {
                const newArray = [...currentData];
                newArray.splice(undoItem.originalIndex, 0, undoItem);
                return newArray;
            },
            false 
        );
        
        setUndoItem(null);
    };

    // === DERIVED STATE (Computed values) ===
    const filteredNotifications = useMemo(() => {
        if (!notifications) return [];
        return notifications.filter(n => {
            if (filter === 'Unread') return !n.read;
            if (filter === 'Orders') return n.type === 'order';
            if (filter === 'Security') return n.type === 'security';
            return true;
        });
    }, [notifications, filter]);

    const unreadCount = useMemo(() => {
        return notifications?.filter(n => !n.read).length ?? 0;
    }, [notifications]);

    const selectedNotification = notifications?.find(n => n.id === selectedId);

    // Clean up timer on component unmount
    useEffect(() => {
        return () => {
            if (undoTimerRef.current) {
                clearTimeout(undoTimerRef.current);
            }
        };
    }, []);

    // === RENDER STATES ===

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-screen" style={{ backgroundColor: '#0B0B0B' }}>
                <Loader className="animate-spin text-cyan-400" size={48} />
            </div>
        );
    }

    if (error) {
         return (
            <div className="flex flex-col justify-center items-center h-screen text-white" style={{ backgroundColor: '#0B0B0B' }}>
                <Shield size={48} className="text-amber-500" />
                <h2 className="text-2xl font-bold mt-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>Access Error</h2>
                <p className="text-gray-400 mt-2">{error.message || "Could not load notifications."}</p>
            </div>
        );
    }
    
    // --- 💡💡 💡💡 ---
    return (
        // --- 1. Wrapper (ProductsPage) ---
        // 
        <div className="min-h-screen w-full text-white" style={{ backgroundColor: '#000000' }}>
            
            {/* --- 2. (ProductsPage) --- */}
            
            <main className="container mx-auto max-w-7xl px-4 pt-24 pb-12">
            
                <ControlBar
                    unreadCount={unreadCount}
                    activeFilter={filter}
                    onFilterChange={setFilter}
                    onMarkAllAsRead={handleMarkAllAsRead}
                />

                <div className="flex flex-col lg:flex-row gap-8 mt-6">
                    
                    <motion.div layout className="flex-1 space-y-3">
                        <AnimatePresence>
                            {filteredNotifications.map((notification) => (
                                <NotificationItem
                                    key={notification.id}
                                    notification={notification}
                                    isSelected={selectedId === notification.id}
                                    onSelect={() => setSelectedId(notification.id)}
                                    onMarkAsRead={handleMarkAsRead}
                                    onDismiss={handleDismiss}
                                />
                            ))}
                        </AnimatePresence>
                        
                        {/* --- "All Caught Up" Feed --- */}
                        {!isLoading && filteredNotifications.length === 0 && (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                className="flex flex-col items-center justify-center text-center p-16 rounded-lg bg-white/5 border border-white/10"
                            >
                                <h3 className="text-xl font-semibold text-white">All Caught Up</h3>
                                <p className="text-gray-400 mt-2">You have no notifications in this category.</p>
                            </motion.div>
                        )}
                    </motion.div>

                    <div className="w-full lg:w-1/3 xl:w-2/5">
                        <AnimatePresence>
                            {selectedNotification && (
                                <FocusPanel
                                    key={selectedNotification.id} 
                                    notification={selectedNotification} 
                                    onClose={() => setSelectedId(null)}
                                />
                            )}
                        </AnimatePresence>
                    </div>
                </div>

            </main> {/* <-main */}

            {/* --- 3. Toast main --- */}
            {/* fixed */}
            <AnimatePresence>
                {undoItem && (
                    <UndoToast
                        message={`Removed "${undoItem.title.substring(0, 20)}..."`}
                        onUndo={handleUndo}
                    />
                )}
            </AnimatePresence>
            
        </div> // <-- wrapper 
    );
}
