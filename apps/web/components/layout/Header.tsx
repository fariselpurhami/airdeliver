//** apps/web/components/layout/Header.tsx **//

'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from 'next-themes';
import { Home, Package, User, ShoppingCart, Sun, Moon, Menu, X as CloseIcon, Bell, Wifi, Activity } from 'lucide-react';
import { useCartStore } from '@/hooks/useCartStore'; 

const navItems = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/products', label: 'Products', icon: Package },
    { href: '/profile', label: 'Profile', icon: User },
];

const ThemeToggle = () => {
    const [mounted, setMounted] = useState(false);
    const { theme, setTheme } = useTheme();

    useEffect(() => setMounted(true), []);

    if (!mounted) {
        return <div className="w-10 h-10" />; 
    }

    const isDark = theme === 'dark';

    return (
        <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className="relative w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors group"
            aria-label="Toggle theme"
        >
            <div className="absolute inset-0 bg-cyan-500/20 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
            <AnimatePresence initial={false} mode="wait">
                <motion.div
                    key={isDark ? 'moon' : 'sun'}
                    initial={{ y: -20, opacity: 0, rotate: -90 }}
                    animate={{ y: 0, opacity: 1, rotate: 0 }}
                    exit={{ y: 20, opacity: 0, rotate: 90 }}
                    transition={{ duration: 0.2 }}
                >
                    {isDark ? (
                      <Moon size={18} className="text-cyan-200" />
                    ) : (
                      <Sun size={18} className="text-amber-400" />
		            )}
                </motion.div>
            </AnimatePresence>
        </button>
    );
};

export default function Header() {
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const cartItems = useCartStore((state) => state.items);
    const totalItems = cartItems.reduce((total, item) => total + item.quantity, 0);
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    if (!isMounted) {
        return <header className="fixed top-0 left-0 right-0 z-50 h-20 bg-black" />;
    }

    return (
        <>
            <motion.header
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="fixed top-0 left-0 right-0 z-50 h-20 bg-black/60 backdrop-blur-2xl border-b border-white/5 shadow-[0_4px_30px_rgba(0,0,0,0.5)]"
            >
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" />

                <div className="container mx-auto px-6 h-full flex justify-between items-center">
                    
                    <Link href="/" className="group flex items-center gap-3">
                        <div className="relative">
                            <span className="text-2xl font-bold text-white tracking-tight group-hover:text-cyan-400 transition-colors duration-500" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                airdeliver
                            </span>
                            <span className="absolute top-0 left-0 -ml-[1px] text-2xl font-bold text-cyan-500 opacity-0 group-hover:opacity-50 group-hover:animate-pulse" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                airdeliver
                            </span>
                        </div>
                        
                        <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-white/10 ml-4 h-6">
                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-green-500/10 border border-green-500/20">
                                <Wifi size={10} className="text-green-400" />
                                <span className="text-[9px] font-mono text-green-400 tracking-wider">ONLINE</span>
                            </div>
                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">
                                <Activity size={10} className="text-cyan-400" />
                                <span className="text-[9px] font-mono text-cyan-400 tracking-wider">STABLE</span>
                            </div>
                        </div>
                    </Link>

                    <nav className="hidden md:flex items-center bg-white/5 border border-white/5 rounded-full p-1.5 backdrop-blur-md">
                        {navItems.map((item) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link 
                                    key={item.href} 
                                    href={item.href} 
                                    className={`relative px-6 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all duration-300 ${isActive ? 'text-black' : 'text-gray-400 hover:text-white'}`}
                                >
                                    <span className="relative z-10">{item.label}</span>
                                    {isActive && (
                                        <motion.div
                                            layoutId="active-pill"
                                            className="absolute inset-0 bg-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.6)]"
                                            style={{ borderRadius: 9999 }}
                                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                                        />
                                    )}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="hidden md:flex items-center gap-3">
                        <div className="flex items-center gap-1 bg-white/5 border border-white/5 rounded-full p-1.5">
                            <Link href="/cart" className="relative p-2.5 rounded-full text-gray-400 hover:text-white hover:bg-white/10 transition-all group" aria-label="Cart">
                                <ShoppingCart size={18} />
                                {totalItems > 0 && (
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        className="absolute top-1 right-1 w-2 h-2 bg-cyan-400 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.8)]"
                                    />
                                )}
                            </Link>
                            
                            <div className="w-[1px] h-4 bg-white/10 mx-1" />

                            <Link href="/notifications" className="relative p-2.5 rounded-full text-gray-400 hover:text-white hover:bg-white/10 transition-all" aria-label="Notifications">
                                <Bell size={18} />
                            </Link>
                        </div>

                        <div className="bg-white/5 border border-white/5 rounded-full p-1">
                            <ThemeToggle />
                        </div>
                    </div>
                    
                    <div className="md:hidden">
                        <button 
                            onClick={() => setMobileMenuOpen(true)} 
                            className="p-2.5 text-white hover:bg-white/10 rounded-full transition-colors border border-transparent hover:border-white/10"
                        >
                            <Menu size={24} />
                        </button>
                    </div>
                </div>
            </motion.header>

            <AnimatePresence>
                {mobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-xl md:hidden"
                    >
                        <motion.div
                            initial={{ x: "100%" }}
                            animate={{ x: "0%" }}
                            exit={{ x: "100%" }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            className="absolute right-0 top-0 bottom-0 w-[80%] max-w-sm bg-black/90 border-l border-white/10 p-6 flex flex-col"
                        >
                            <div className="flex justify-between items-center mb-10 border-b border-white/5 pb-6">
                                <span className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    airdeliver
                                </span>
                                <button onClick={() => setMobileMenuOpen(false)} className="p-2 text-gray-400 hover:text-white transition-colors">
                                    <CloseIcon size={24} />
                                </button>
                            </div>

                            <nav className="flex flex-col gap-2">
                                {navItems.map((item) => (
                                    <Link 
                                        key={item.href} 
                                        href={item.href} 
                                        onClick={() => setMobileMenuOpen(false)} 
                                        className={`flex items-center gap-4 p-4 rounded-xl text-sm font-bold uppercase tracking-wider transition-all ${
                                            pathname === item.href 
                                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                                            : 'text-gray-400 hover:bg-white/5'
                                        }`}
                                    >
                                        <item.icon size={20} /> {item.label}
                                    </Link>
                                ))}
                            </nav>

                            <div className="mt-auto space-y-4 border-t border-white/5 pt-6">
                                <Link href="/cart" onClick={() => setMobileMenuOpen(false)} className="flex items-center justify-between p-4 rounded-xl bg-white/5 text-gray-300">
                                    <div className="flex items-center gap-3">
                                        <ShoppingCart size={20} />
                                        <span className="text-sm font-medium">Cart</span>
                                    </div>
                                    {totalItems > 0 && (
                                        <span className="bg-cyan-500 text-black text-xs font-bold px-2 py-1 rounded-full">
                                            {totalItems}
                                        </span>
                                    )}
                                </Link>
                                
                                <div className="flex justify-center p-2">
                                    <ThemeToggle />
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
