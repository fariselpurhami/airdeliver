
'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from 'next-themes';
import { Home, Package, User, ShoppingCart, Sun, Moon, Menu, X as CloseIcon, Bell } from 'lucide-react';
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
            className="relative w-10 h-10 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 transition-colors"
            aria-label="Toggle theme"
        >
            <AnimatePresence initial={false} mode="wait">
                <motion.div
                    key={isDark ? 'moon' : 'sun'}
                    initial={{ y: -20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: 20, opacity: 0 }}
                    transition={{ duration: 0.2 }}
		   
                >
                    {isDark ? (
                      <Moon size={20} className="text-white" />
                    ) : (
                      <Sun size={20} className="text-white" />
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
        return <header className="fixed top-0 left-0 right-0 z-50 h-20" />;
    }

    return (
        <>
            <motion.header
                className="fixed top-0 left-0 right-0 z-50 border-b backdrop-blur-xl border-cyan-400/30 shadow-lg shadow-cyan-500/20"
            >
                
                <div 
                    className="container mx-auto px-4 flex justify-between items-center h-20"
                >
                    
                    <Link href="/" className="text-2xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        airdeliver
                    </Link>

                    <nav className="hidden md:flex items-center gap-2 bg-white/5 p-1 rounded-full">
                        {navItems.map((item) => (
                           
                            <Link key={item.href} href={item.href} className={`relative px-4 py-2 rounded-full text-sm font-medium transition-colors ${pathname === item.href ? 'text-white' : 'text-gray-400 hover:text-white'}`}>
                                
                                
                                {item.label}

                                {pathname === item.href && (
                                    <motion.div
                                        layoutId="active-pill"
                                        className="absolute inset-0 bg-gradient-to-r from-cyan-500/30 to-violet-500/30 rounded-full"
                                        style={{ borderRadius: 9999 }}
                                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                                    />
                                )}
                            </Link>
                        ))}
                    </nav>

                  
                    <div className="hidden md:flex items-center gap-4">
                     
                        <Link href="/cart" className="relative p-2 rounded-full text-gray-300 hover:text-white hover:bg-white/10" aria-label="Cart">
                            <ShoppingCart size={22} />
                            {totalItems > 0 && (
                                <motion.div
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-cyan-400 text-black text-xs font-bold flex items-center justify-center rounded-full"
                                >
                                    {totalItems}
                                </motion.div>
                            )}
                        </Link>
                        
                     
                        <Link href="/notifications" className="relative p-2 rounded-full text-gray-300 hover:text-white hover:bg-white/10" aria-label="Notifications">
                            <Bell size={22} />
                          
                        </Link>

                        <ThemeToggle />
                    </div>
                    
                
                    <div className="md:hidden">
                        <button onClick={() => setMobileMenuOpen(true)} className="p-2 text-white">
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
                        className="fixed inset-0 z-50 bg-black/80 backdrop-blur-lg md:hidden"
                    >
                        <motion.div
                            initial={{ y: "-100%" }}
                            animate={{ y: "0%" }}
                            exit={{ y: "-100%" }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            className="bg-black p-4 border-b border-white/10"
                        >
                            <div className="flex justify-between items-center mb-8">
                                <Link href="/" className="text-2xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    airdeliver
                                </Link>
                                <button onClick={() => setMobileMenuOpen(false)} className="p-2 text-white">
                                    <CloseIcon size={24} />
                                </button>
                            </div>
                            <nav className="flex flex-col gap-4">
                                {navItems.map((item) => (
                                    <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)} className={`flex items-center gap-3 p-3 rounded-lg text-lg ${pathname === item.href ? 'bg-white/10 text-white' : 'text-gray-400'}`}>
                                        <item.icon size={22} /> {item.label}
                                    </Link>
                                ))}
                                
                            
                                <Link href="/notifications" onClick={() => setMobileMenuOpen(false)} className="relative flex items-center gap-3 p-3 rounded-lg text-lg text-gray-400">
                                    <Bell size={22} />
                                    <span>Notifications</span>
                                </Link>

                                <Link href="/cart" onClick={() => setMobileMenuOpen(false)} className="relative flex items-center gap-3 p-3 rounded-lg text-lg text-gray-400">
                                    <ShoppingCart size={22} />
                                    <span>Cart</span>
                                    {totalItems > 0 && (
                                        <div className="absolute left-10 top-2 w-5 h-5 bg-cyan-400 text-black text-xs font-bold flex items-center justify-center rounded-full">
                                            {totalItems}
                                        </div>
                                    )}
                                </Link>
                                <div className="mt-4 flex justify-center">
                                    <ThemeToggle />
                                </div>
                            </nav>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
