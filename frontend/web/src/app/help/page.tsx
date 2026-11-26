import { AirSparklesIcon } from '@/components/ui/AirSparkles';
//** frontend/web/app/help/page.tsx **//

'use client';

import React, { useState, Suspense, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { 
    Mail, Phone, ChevronDown, Search, 
    Zap, LifeBuoy, Box, ShieldCheck, Activity 
} from 'lucide-react';
import * as THREE from 'three';
import dynamic from 'next/dynamic';

// ============================================================================
// --- 1. DATA MATRIX (The Knowledge Base) ---
// ============================================================================

const faqCategories = [
    {
        id: "operational",
        title: "Operational Protocols",
        items: [
            {
                q: "How fast is delivery?",
                a: "Delivery timing depends on the partner store fulfilling your order and your location. Open your order record for its latest saved status. Live carrier location and delivery estimates are not connected yet."
            },
            {
                q: "What does the AI assistant do?",
                a: "It helps search the store catalog and offers reviewed cart changes. Current catalog price and stock are checked again at checkout; an inventory record is not a delivery promise."
            }
        ]
    },
    {
        id: "logistics",
        title: "Logistics & Tracking",
        items: [
            {
                q: "How do I track my order?",
                a: "Open the tracking page for your order to see its current status, items, and total."
            },
            {
                q: "Is my payment secure?",
                a: "Payments are processed over encrypted channels by our payment providers. Your card details never touch our servers."
            }
        ]
    }
];

const contactModules = [
    {
        icon: AirSparklesIcon,
        title: "AI Neural Assistant",
        desc: "Product questions and reviewed store actions.",
        action: "Initiate Chat",
        color: "cyan"
    },
    {
        icon: Phone,
        title: "Human Override",
        desc: "Human callback is not connected yet.",
        action: "Callback unavailable",
        color: "purple"
    },
    {
        icon: Mail,
        title: "Secure CommLink",
        desc: "An email support destination is not configured yet.",
        action: "Email unavailable",
        color: "green"
    }
];

// ============================================================================
// --- 2. ARCHITECTURAL BACKGROUND (The Grid) ---
// ============================================================================

const NeuralBackground = () => {
    const groupRef = useRef<THREE.Group>(null!);
    
    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
            groupRef.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.1) * 0.02;
        }
    });

    return (
        <group ref={groupRef}>
            <fog attach="fog" args={['#000000', 30, 90]} />
            <ambientLight intensity={0.2} />
            <pointLight position={[10, 10, 10]} intensity={1.5} color="#00C6FF" />
            <Stars radius={120} depth={50} count={6000} factor={4} saturation={0} fade speed={1} />
            {/* Abstract Grid Lines representing support network */}
            {Array.from({ length: 20 }).map((_, i) => (
                <mesh key={i} rotation={[Math.random() * Math.PI, Math.random() * Math.PI, 0]}>
                    <torusGeometry args={[30 + i * 2, 0.05, 16, 100]} />
                    <meshBasicMaterial color="#00C6FF" transparent opacity={0.1} />
                </mesh>
            ))}
        </group>
    );
};

const DynamicBackground = dynamic(() => Promise.resolve(NeuralBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 3. UI COMPONENTS (The Interface) ---
// ============================================================================

const SearchMatrix = () => (
    <div className="relative max-w-2xl mx-auto w-full group">
        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-purple-600 rounded-full blur opacity-25 group-hover:opacity-50 transition duration-1000" />
        <div className="relative flex items-center bg-black/80 backdrop-blur-xl border border-white/10 rounded-full p-2 pl-6 shadow-2xl">
            <Search className="text-gray-400 w-6 h-6 mr-4" />
            <input 
                type="text" 
                placeholder="Query the Knowledge Base..." 
                className="w-full bg-transparent text-white placeholder-gray-500 focus:outline-none font-medium text-lg"
            />
            <button className="bg-white/10 hover:bg-white/20 text-white px-6 py-3 rounded-full font-bold uppercase tracking-wider text-xs transition-colors border border-white/5">
                Scan
            </button>
        </div>
    </div>
);

const SupportModule = ({ data, index }: { data: typeof contactModules[0], index: number }) => {
    const colors: Record<string, string> = {
        cyan: "from-cyan-500/20 to-cyan-500/5 border-cyan-500/30 text-cyan-400",
        purple: "from-purple-500/20 to-purple-500/5 border-purple-500/30 text-purple-400",
        green: "from-green-500/20 to-green-500/5 border-green-500/30 text-green-400",
    };

    return (
        <motion.div 
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.1 }}
            className={`relative p-8 rounded-[40px] bg-gradient-to-br ${colors[data.color]} border backdrop-blur-xl overflow-hidden group cursor-pointer`}
        >
            <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-700">
                <data.icon size={120} />
            </div>
            
            <div className="relative z-10 flex flex-col h-full justify-between">
                <div className="mb-8">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center bg-black/40 border border-white/10 mb-6 text-${data.color}-400`}>
                        <data.icon size={24} />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>{data.title}</h3>
                    <p className="text-gray-300 font-light">{data.desc}</p>
                </div>
                
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-white group-hover:gap-4 transition-all">
                    <span>{data.action}</span>
                    <Zap size={14} className={`text-${data.color}-400`} fill="currentColor" />
                </div>
            </div>
        </motion.div>
    );
};

const FAQCapsule = ({ item }: { item: { q: string, a: string } }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <motion.div 
            layout
            onClick={() => setIsOpen(!isOpen)}
            className={`group border border-white/5 rounded-3xl overflow-hidden transition-all duration-500 ${isOpen ? 'bg-white/10 border-cyan-500/30' : 'bg-white/5 hover:bg-white/10'}`}
        >
            <div className="p-6 flex justify-between items-center cursor-pointer">
                <h4 className={`text-lg font-medium transition-colors ${isOpen ? 'text-cyan-400' : 'text-gray-200'}`}>
                    {item.q}
                </h4>
                <div className={`p-2 rounded-full transition-all ${isOpen ? 'bg-cyan-500/20 text-cyan-400 rotate-180' : 'bg-white/5 text-gray-400'}`}>
                    <ChevronDown size={20} />
                </div>
            </div>
            <AnimatePresence>
                {isOpen && (
                    <motion.div 
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-6 pb-6"
                    >
                        <p className="text-gray-400 leading-relaxed border-t border-white/5 pt-4">
                            {item.a}
                        </p>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

// ============================================================================
// --- 4. MAIN PAGE (The Assembly) ---
// ============================================================================

export default function HelpPage() {
    return (
        <div className="min-h-screen w-full bg-black text-gray-100 selection:bg-cyan-500/30">
            
            {/* Background */}
            <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
                <Canvas camera={{ position: [0, 0, 15], fov: 45 }}>
                    <Suspense fallback={null}>
                        <DynamicBackground />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
            </div>

            <section className="relative z-10 pt-40 pb-20 px-4">
                <div className="container mx-auto max-w-4xl text-center">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }} 
                        animate={{ opacity: 1, y: 0 }} 
                        transition={{ duration: 0.8 }}
                    >
                        <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/30 bg-cyan-900/20 backdrop-blur-md mb-8">
                            <LifeBuoy size={14} className="text-cyan-400" />
                            <span className="text-xs font-bold uppercase tracking-widest text-cyan-300">Support Command Center</span>
                        </span>
                        
                        <h1 className="text-5xl md:text-7xl font-black text-white mb-8 tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                            SYSTEM <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-600">ASSISTANCE</span>
                        </h1>
                        
                        <p className="text-xl text-gray-400 max-w-2xl mx-auto font-light mb-12">
                            Our autonomous agents and human specialists are standing by. How can we optimize your experience today?
                        </p>

                        <SearchMatrix />
                    </motion.div>
                </div>
            </section>

            <section className="relative z-10 container mx-auto px-4 max-w-7xl py-12">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {contactModules.map((mod, i) => (
                        <SupportModule key={i} data={mod} index={i} />
                    ))}
                </div>
            </section>

            <section className="relative z-10 container mx-auto px-4 max-w-4xl py-24">
                <div className="text-center mb-16">
                    <h2 className="text-3xl font-bold text-white mb-4" style={{ fontFamily: "'Orbitron', sans-serif" }}>Knowledge Archive</h2>
                    <p className="text-gray-500">Frequently accessed data points.</p>
                </div>

                <div className="space-y-12">
                    {faqCategories.map((cat, i) => (
                        <div key={cat.id}>
                            <h3 className="text-lg font-bold text-cyan-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                                <Box size={16} /> {cat.title}
                            </h3>
                            <div className="space-y-4">
                                {cat.items.map((item, j) => (
                                    <FAQCapsule key={j} item={item} />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            <footer className="relative z-10 py-12 text-center border-t border-white/5 bg-black/40 backdrop-blur-lg">
                <div className="flex flex-col md:flex-row justify-center items-center gap-6 text-xs text-gray-600 tracking-widest">
                    <span className="flex items-center gap-2"><Activity size={14} className="text-green-500" /> support system online</span>
                    <span className="flex items-center gap-2"><ShieldCheck size={14} className="text-cyan-500" /> secure connection</span>
                    <span>© {new Date().getFullYear()} airdeliver</span>
                </div>
            </footer>

        </div>
    );
}
