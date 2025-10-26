'use client';

import React, { useState, useRef, useMemo, useEffect } from 'react';
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

// --- Interface ---
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
// --- 1. المكون الرئيسي للصفحة (Main Page Component) ---
// ============================================================================
export default function NotificationsPage() {
    const { data: notifications, error, isLoading, mutate } = useSWR<Notification[]>(
        API_KEY,
        fetcher
    );

    // --- State Management ---
    const [filter, setFilter] = useState('All');
    // const [selectedId, setSelectedId] = useState<number | null>(null); // Removed for simplified layout
    const [undoItem, setUndoItem] = useState<(Notification & { originalIndex: number }) | null>(null);
    const undoTimerRef = useRef(null);

    // --- Handlers ---
    const handleMarkAsRead = async (id: number) => {
        mutate(
            (currentData = []) => currentData.map(n => (n.id === id ? { ...n, read: true } : n)), false);
        try { await api.post(`/notifications/${id}/read`); } catch (e) { mutate(); }
    };
    const handleDismiss = async (id: number) => {
        const currentNotifications = notifications || [];
        const itemToDismiss = currentNotifications.find(n => n.id === id);
        if (!itemToDismiss) return;
        const originalIndex = currentNotifications.findIndex(n => n.id === id);
        mutate((currentData = []) => currentData.filter(n => n.id !== id), false);
        if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
        setUndoItem({ ...itemToDismiss, originalIndex });
        undoTimerRef.current = setTimeout(() => {
            api.delete(`/notifications/${id}`).catch(() => mutate());
            setUndoItem(null);
        }, 5000);
    };
    const handleMarkAllAsRead = async () => {
        mutate((currentData = []) => currentData.map(n => ({ ...n, read: true })), false);
        try { await api.post('/notifications/read-all'); } catch (e) { mutate(); }
    };
    const handleUndo = () => {
        if (!undoItem) return;
        clearTimeout(undoTimerRef.current);
        mutate((currentData = []) => {
            const newArray = [...currentData];
            newArray.splice(undoItem.originalIndex, 0, undoItem);
            return newArray;
        }, false);
        setUndoItem(null);
    };
    useEffect(() => {
        return () => { if (undoTimerRef.current) clearTimeout(undoTimerRef.current); };
    }, []);

    // --- Computed Values ---
    const groupedNotifications = useMemo(() => {
        if (!notifications) return {};
        const filtered = notifications.filter(n => {
            if (filter === 'Unread') return !n.read;
            if (filter === 'Orders') return n.type === 'order';
            if (filter === 'Security') return n.type === 'security';
            return true;
        });
        return filtered.reduce((groups, item) => {
            const groupTitle = getGroupTitle(item.created_at);
            if (!groups[groupTitle]) { groups[groupTitle] = []; }
            groups[groupTitle].push(item);
            return groups;
        }, {} as Record<string, Notification[]>);
    }, [notifications, filter]);

    const groupOrder = ['Today', 'Yesterday', 'Older'];
    const totalFilteredCount = Object.values(groupedNotifications).reduce((sum, group) => sum + group.length, 0);
    const unreadCount = useMemo(() => (notifications || []).filter(n => !n.read).length, [notifications]);

    // --- Render States ---
    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-screen" style={{ backgroundColor: '#000000' }}>
                <Loader className="animate-spin text-cyan-400" size={48} />
            </div>
        );
     }
    if (error) {
         return (
            <div className="flex flex-col justify-center items-center h-screen text-white" style={{ backgroundColor: '#000000' }}>
                <Shield size={48} className="text-amber-500" />
                <h2 className="text-2xl font-bold mt-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>Access Error</h2>
                <p className="text-gray-400 mt-2">{error.message || "Could not load notifications."}</p>
            </div>
        );
    }

    // --- Main Render ---
    return (
        <div
            className="min-h-screen w-full text-white flex flex-col items-center justify-start pt-20 p-4" // Align top with padding
            style={{ backgroundColor: '#000000' }}
        >
            <div className="w-full max-w-4xl flex flex-col items-center"> {/* Wider content area */}

                <ControlBar
                    unreadCount={unreadCount}
                    activeFilter={filter}
                    onFilterChange={setFilter}
                    onMarkAllAsRead={handleMarkAllAsRead}
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
                            {!isLoading && totalFilteredCount === 0 ? (
                                <CinematicEmptyState />
                            ) : (
                                groupOrder.map(groupTitle => (
                                    groupedNotifications[groupTitle] && (
                                        <motion.div key={groupTitle} layout className="w-full">
                                            {/* Optional: Group title */}
                                            {/* <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider my-4">{groupTitle}</h2> */}
                                            <div className="space-y-3">
                                                {groupedNotifications[groupTitle].map((notification, index) => (
                                                    <NotificationItem
                                                        key={notification.id}
                                                        notification={notification}
                                                        onMarkAsRead={handleMarkAsRead}
                                                        onDismiss={handleDismiss}
                                                        index={index}
                                                    />
                                                ))}
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
// --- 2. المكونات الفرعية (Sub-Components) معرفة هنا ---
// ============================================================================

// --- مكون: شريط التحكم ---
const filters = ['All', 'Unread', 'Orders', 'Security'];
const ControlBar = ({ unreadCount, activeFilter, onFilterChange, onMarkAllAsRead }) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="w-full flex flex-col sm:flex-row justify-center sm:justify-between items-center py-4 border-b border-gray-700"> {/* Bottom border */}

      {/* Title + Glow Line */}
      <div className="relative mb-4 sm:mb-0">
        <div className="flex items-center justify-center sm:justify-start gap-3">
          <h1 className="text-2xl font-bold" style={{ fontFamily: "'Orbitron', sans-serif" }}> {/* Larger Title */}
            Notifications
          </h1>
          {/* Optional: Unread count badge */}
          {/* {unreadCount > 0 && (...)} */}
        </div>
         {/* --- 💡 تأكد من وجود هذا الـ Div --- */}
        <div className="glow-line-animation" /> {/* The animated glow line */}
      </div>

      {/* Filters */}
      <div className="flex items-center justify-center gap-2 flex-wrap">
        {filters.map((filter, index) => (
          <React.Fragment key={filter}>
            <button
              onClick={() => onFilterChange(filter)}
              className={`group relative px-4 py-2 rounded-full text-base font-medium transition-colors duration-300 {/* Larger Filter Text */}
                  ${activeFilter === filter
                      ? 'text-cyan-400' // Active color
                      : 'text-gray-500 hover:text-gray-300' // Inactive color
                  }`}
            >
              <span className="relative z-10">{filter}</span>
              {/* Optional: Underline glow on hover for inactive */}
              {activeFilter !== filter && (
                 <motion.div
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 blur-[2px] opacity-0
                               group-hover:opacity-100 transition-opacity"
                 />
              )}
            </button>
            {index < filters.length - 1 && (
              <span className="text-gray-700">|</span> // Separator
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Settings Icon */}
      <div className="relative hidden sm:block">
        <button
          onClick={() => setMenuOpen(!menuOpen)} // Re-enabled menu toggle
          className="p-2 rounded-lg text-gray-500 hover:text-gray-300 transition-colors"
        >
          <Settings size={20} /> {/* Slightly larger icon */}
        </button>
         {/* Settings Dropdown Menu */}
         <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="absolute top-12 right-0 w-60 bg-gray-900 border border-white/10 rounded-lg shadow-xl z-50 p-2"
              style={{ backgroundColor: '#050505' }}
            >
              <button className="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors">
                <BellOff size={16} />
                <span>Pause notifications</span>
              </button>
              <button className="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors">
                <ListFilter size={16} />
                <span>Notification preferences</span>
              </button>
              <div className="h-px bg-white/10 my-1"></div>
              <button
                onClick={() => {
                  onMarkAllAsRead();
                  setMenuOpen(false);
                }}
                className="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              >
                <CheckCheck size={18} />
                <span>Mark all as read</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

// --- مكون: الحالة الفارغة ---
const CinematicEmptyState = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center text-center p-12 rounded-lg bg-black border border-gray-800" // Increased padding
    >
       {/* Pulsing Bell Icon */}
       <motion.div
         animate={{ scale: [1, 1.05, 1], opacity: [1, 0.8, 1] }}
         transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
         className="relative mb-6"
       >
         <div className="absolute inset-0 bg-cyan-400 rounded-full blur-xl opacity-50"></div>
         <Bell size={48} className="text-cyan-300 relative z-10" />
       </motion.div>
      <h3
        className="text-xl font-semibold text-white mb-2 leading-tight" // Larger + Tight
      >
        You're all caught up
      </h3>
      <p className="text-base text-gray-500 max-w-xs opacity-80"> {/* Larger + Less faded */}
        No notifications at the moment.
        <br />
        Stay tuned, updates appear here in real time.
      </p>
    </motion.div>
  );
};

// --- مكون: عنصر الإشعار ---
const typeConfig = {
    order: { icon: Package, color: 'text-cyan-400' },
    security: { icon: Shield, color: 'text-amber-500' },
    payment: { icon: Banknote, color: 'text-green-400' },
    system: { icon: BrainCircuit, color: 'text-violet-400' },
    default: { icon: BrainCircuit, color: 'text-gray-500' }
};
const getIcon = (type: string) => {
    const config = typeConfig[type] || typeConfig.default;
    const IconComponent = config.icon;
    return <IconComponent className={config.color} size={20} />;
};
const NotificationItem = ({ notification, onMarkAsRead, onDismiss, index }) => {
    const { id, type, title, body, timestamp, read, cta } = notification;
    const borderColor = read ? 'border-gray-800' : (type === 'security' ? 'border-amber-500' : 'border-cyan-400');
    const glowClass = !read ? (type === 'security' ? 'shadow-[0_0_15px_-3px_rgba(245,158,11,0.3)]' : 'shadow-[0_0_15px_-3px_rgba(6,182,212,0.3)]') : '';
    const handleActionClick = (e, action) => { e.stopPropagation(); action(id); };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -50, transition: { duration: 0.2 } }}
            transition={{ delay: index * 0.07, duration: 0.3, ease: "easeOut" }}
            className={`group relative flex items-start gap-4 p-4 rounded-lg cursor-pointer transition-all duration-300 border-l-2
                ${read ? 'opacity-70 hover:opacity-100 bg-black/20' : 'bg-white/5'}
                 hover:bg-white/10
                ${borderColor} ${glowClass}
            `}
            // Removed onClick related to selection
        >
            <div className="flex-shrink-0 mt-1">{getIcon(type)}</div>
            <div className="flex-1">
                <h3 className={`font-semibold ${read ? 'text-gray-300' : 'text-white'}`}>{title}</h3>
                <p className="text-sm text-gray-400 mt-1 line-clamp-2">{body}</p>
                <span className="text-xs text-gray-500 mt-2 block">{timestamp}</span>
            </div>
            <div className="flex flex-col items-end gap-2 ml-4">
                {cta && (<button onClick={(e) => e.stopPropagation()} className="px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap bg-cyan-400 text-black hover:bg-cyan-300 transition-colors"> {cta} </button>)}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 h-8">
                    {!read && (<button onClick={(e) => handleActionClick(e, onMarkAsRead)} title="Mark as read" className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white"> <Check size={16} /> </button>)}
                    <button title="Snooze" className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white"> <Clock size={16} /> </button>
                    <button onClick={(e) => handleActionClick(e, onDismiss)} title="Dismiss" className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white"> <X size={16} /> </button>
                </div>
            </div>
        </motion.div>
    );
};

// --- مكون: رسالة التراجع ---
const UndoToast = ({ message, onUndo }) => {
    return (
        <motion.div
            layout
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex items-center justify-between gap-4 p-4 rounded-lg shadow-lg bg-gray-900 border border-cyan-400/30"
            style={{ backgroundColor: '#111' }}
        >
            <span className="text-gray-300 text-sm">{message}</span>
            <button
                onClick={onUndo}
                className="px-3 py-1 rounded-full text-sm font-semibold bg-cyan-400 text-black hover:bg-cyan-300 transition-colors"
            >
                Undo
            </button>
        </motion.div>
    );
};
