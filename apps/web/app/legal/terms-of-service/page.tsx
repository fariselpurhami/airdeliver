'use client';

import React, { useState, Suspense, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { ChevronDown, ShieldCheck, Cpu } from 'lucide-react';
import * as THREE from 'three';
import dynamic from 'next/dynamic';

const clauses = [
  {
    title: "1. Data & Privacy Integrity",
    humanText: "We protect your data the same way we protect our AI cores—with maximum security and respect.",
    legalText: "airdeliver is committed to ensuring the confidentiality and integrity of your personal information. All user data is processed using end-to-end encryption (E2EE) protocols. Data collected is used exclusively for service optimization, route planning, and transaction processing. We do not sell, trade, or otherwise transfer your personally identifiable information to outside parties. Anonymized aggregate data may be used for system-wide performance analysis."
  },
  {
    title: "2. Service & Autonomous Operations",
    humanText: "Our AI and drone fleet operate autonomously. We guarantee performance based on real-time system capabilities.",
    legalText: "The services provided by airdeliver are operated by a fully autonomous system. Service availability, delivery times, and operational efficiency are subject to real-time conditions including, but not limited to, weather, fleet availability, and network status. While our AI strives for optimal performance, we do not guarantee uninterrupted service. Any predicted delivery times are estimates and not contractual obligations."
  },
  {
    title: "3. User Responsibilities",
    humanText: "You are responsible for providing accurate delivery information and using the service lawfully.",
    legalText: "Users of the airdeliver platform agree to provide accurate and complete information for all transactions, including delivery addresses and contact details. Users shall not use the service for any unlawful purpose, including the transport of illicit, hazardous, or prohibited materials. Violation of these terms may result in immediate suspension of the user's account and potential legal action."
  },
];

// ============================================================================
// --- 1. (New) Background Component ---
// ============================================================================
const TermsBackground = () => {
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

const DynamicTermsBackground = dynamic(() => Promise.resolve(TermsBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. (Re-styled) Sub-Components ---
// ============================================================================
const DualModeToggle = ({ mode, setMode }: { mode: 'human' | 'legal', setMode: (mode: 'human' | 'legal') => void }) => (
    <div className="flex justify-center mb-12">
        <div className="bg-black/50 backdrop-blur-lg border border-cyan-400/30 rounded-full p-1 flex gap-1 shadow-lg shadow-cyan-500/10">
            <button 
                onClick={() => setMode('human')} 
                className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors"
            >
                {mode === 'human' && <motion.div layoutId="toggle-bg" className="absolute inset-0 bg-cyan-500/30 border border-cyan-500/50 rounded-full" />}
                <span className="relative z-10">Human Readable</span>
            </button>
            <button 
                onClick={() => setMode('legal')} 
                className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors"
            >
                {mode === 'legal' && <motion.div layoutId="toggle-bg" className="absolute inset-0 bg-cyan-500/30 border border-cyan-500/50 rounded-full" />}
                <span className="relative z-10">Legal Text</span>
            </button>
        </div>
    </div>
);

const LegalCard = ({ clause, mode, isOpen, onToggle }: { clause: any, mode: 'human' | 'legal', isOpen: boolean, onToggle: () => void }) => (
    <motion.div 
        layout 
        className="bg-black/50 backdrop-blur-xl border border-cyan-400/30 rounded-2xl overflow-hidden shadow-lg shadow-cyan-500/10"
        whileHover={{ borderColor: 'rgba(0, 198, 255, 0.7)', boxShadow: '0 0 24px rgba(0, 198, 255, 0.3)' }}
    >
        <motion.div layout className="flex justify-between items-center p-6 cursor-pointer" onClick={onToggle}>
            <h3 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>{clause.title}</h3>
            <motion.div animate={{ rotate: isOpen ? 180 : 0 }} className="text-cyan-400">
                <ChevronDown />
            </motion.div>
        </motion.div>
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                >
                    <div className="px-6 pb-6 text-gray-400" style={{ fontFamily: "'Inter', sans-serif" }}>
                        <p className="whitespace-pre-wrap leading-relaxed">{mode === 'human' ? clause.humanText : clause.legalText}</p>
                        {mode === 'human' && (
                             <div className="mt-4 p-4 bg-black/30 border border-cyan-500/30 rounded-lg text-sm text-cyan-200 flex items-center gap-3">
                                 <Cpu size={20} className="flex-shrink-0" />
                                 <strong>AI Note:</strong> Your data is encrypted and anonymized during every transaction.
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    </motion.div>
);

// ============================================================================
// --- 3. (Re-built) Main Page Component ---
// ============================================================================
export default function TermsOfServicePage() {
    const [mode, setMode] = useState<'human' | 'legal'>('human');
    const [expandedCard, setExpandedCard] = useState<number | null>(0);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100">
            
            <div className="fixed inset-0 z-0 opacity-70">
                <Canvas>
                    <Suspense fallback={null}>
                        <DynamicTermsBackground />
                    </Suspense>
                </Canvas>
            </div>
        
            <section className="relative h-screen w-full flex items-center justify-center text-center overflow-hidden">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ duration: 1, ease: "easeOut" }} 
                    className="z-10 px-4"
                >
                    <h1 className="text-5xl md:text-7xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        <motion.span
                            className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                            animate={{
                            filter: [
                                'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))',
                                'drop-shadow(0 0 16px rgba(0, 198, 255, 0.8)) drop-shadow(0 0 16px rgba(168, 85, 247, 0.8))',
                                'drop-shadow(0 0 4px rgba(0, 198, 255, 0.4)) drop-shadow(0 0 4px rgba(168, 85, 247, 0.4))'
                            ]
                            }}
                            transition={{
                            duration: 3,
                            repeat: Infinity,
                            ease: "easeInOut"
                            }}
                        >
                            THE PACT
                        </motion.span>
                    </h1>
                    <p className="mt-2 text-cyan-400" style={{ fontFamily: "'Orbitron', sans-serif" }}>Powered by AI Transparency</p>
                    <p className="mt-6 text-lg text-gray-300 max-w-3xl mx-auto" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
                        These aren’t just rules. They’re shared understandings between humans and intelligent systems.
                    </p>
                </motion.div>
            </section>

            <section className="relative z-10 container mx-auto px-4 py-24 max-w-5xl">
                <DualModeToggle mode={mode} setMode={setMode} />
                <motion.div layout className="space-y-4">
                    {clauses.map((clause, index) => (
                        <LegalCard 
                            key={index} 
                            clause={clause} 
                            mode={mode} 
                            isOpen={expandedCard === index} 
                            onToggle={() => setExpandedCard(expandedCard === index ? null : index)}
                        />
                    ))}
                </motion.div>
            </section>

            <footer className="relative z-10 py-20 px-4 text-center mt-12 w-full bg-black/30 backdrop-blur-lg border-t border-cyan-400/20">
                <div className="flex flex-col items-center gap-4 max-w-5xl mx-auto">
                    <div className="relative flex items-center gap-2 border border-green-400/50 bg-green-900/50 text-green-300 px-4 py-2 rounded-lg">
                        <ShieldCheck size={18} />
                        <span className="font-semibold text-sm">AI Verified Document</span>
                    </div>
                    <p className="mt-4 text-xs text-gray-500">
                        © 2025 airdeliver — Operates Under Ethical AI Compliance.
                    </p>
                </div>
            </footer>
        </div>
    );
}
