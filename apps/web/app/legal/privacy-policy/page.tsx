'use client';

import React, { useState, Suspense, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { Lock, EyeOff, ShieldCheck, FileText, ChevronDown } from 'lucide-react';
import * as THREE from 'three';
import dynamic from 'next/dynamic';

const policyClauses = [
  {
    title: "Information We Collect",
    summary: "Only what’s needed to make your delivery intelligent.",
    legalText: "We collect information necessary for the provision of our services, including: account details (name, email), delivery information (address, recipient details), and transaction data. We also collect anonymized operational data from our autonomous fleet, such as flight duration and route efficiency, to improve our services. We do not collect personal data beyond what is required for operational and legal compliance."
  },
  {
    title: "How We Use Your Data",
    summary: "To power our AI, secure your delivery, and improve our network.",
    legalText: "Your data is used to: a) Process and fulfill your orders via our autonomous network. b) Communicate with you regarding your account and transactions. c) Train our AI models for route optimization and predictive logistics in an anonymized, aggregated form. d) Comply with legal obligations and regulations. Your personal data is never used for third-party marketing purposes."
  },
  {
    title: "Your Rights & Controls",
    summary: "You have full control to access, edit, or delete your data at any time.",
    legalText: "You retain the right to access, rectify, or erase your personal data stored on our platform. You may also object to or restrict certain data processing activities. All data management requests can be made through your user profile dashboard or by contacting our Data Protection Officer. We are committed to processing all requests in compliance with GDPR and CCPA regulations within the legally stipulated timeframes."
  }
];

// ============================================================================
// --- 1. (New) Background Component ---
// ============================================================================
const PrivacyBackground = () => {
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

const DynamicPrivacyBackground = dynamic(() => Promise.resolve(PrivacyBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 2. (Re-styled) Sub-Components ---
// ============================================================================
const EthicsCard = ({ icon, title, text, delay }: { icon: React.ReactNode; title: string; text: string; delay: number }) => (
    <motion.div
        variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
        transition={{ duration: 0.7, delay }}
        whileHover={{ 
            scale: 1.03, 
            y: -5,
            borderColor: 'rgba(0, 198, 255, 0.7)', 
            boxShadow: '0 0 24px rgba(0, 198, 255, 0.3)' 
        }}
        className="p-6 bg-black/30 backdrop-blur-xl border border-cyan-400/30 rounded-2xl text-center shadow-lg shadow-cyan-500/10"
    >
        <div className="flex justify-center mb-4 text-cyan-400">{icon}</div>
        <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
        <p className="text-gray-400 text-sm leading-relaxed">{text}</p>
    </motion.div>
);

const DualModeToggle = ({ mode, setMode }: { mode: 'human' | 'legal', setMode: (mode: 'human' | 'legal') => void }) => (
    <div className="flex justify-center mb-12">
        <div className="bg-black/50 backdrop-blur-lg border border-cyan-400/30 rounded-full p-1 flex gap-1 shadow-lg shadow-cyan-500/10">
            <button 
                onClick={() => setMode('human')} 
                className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors"
            >
                {mode === 'human' && (
                    <motion.div 
                        layoutId="privacy-toggle-bg" 
                        className="absolute inset-0 bg-cyan-500/30 border border-cyan-500/50 rounded-full"
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    />
                )}
                <span className="relative z-10">Human Mode</span>
            </button>
            <button 
                onClick={() => setMode('legal')} 
                className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors"
            >
                {mode === 'legal' && (
                    <motion.div 
                        layoutId="privacy-toggle-bg" 
                        className="absolute inset-0 bg-cyan-500/30 border border-cyan-500/50 rounded-full"
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    />
                )}
                <span className="relative z-10">Legal Mode</span>
            </button>
        </div>
    </div>
);

const PolicySection = ({ clause, mode, isOpen, onToggle }: { clause: any, mode: 'human' | 'legal', isOpen: boolean, onToggle: () => void }) => (
    <motion.div 
        layout 
        className="bg-black/50 backdrop-blur-xl border border-cyan-400/30 rounded-2xl overflow-hidden shadow-lg shadow-cyan-500/10"
        whileHover={{ borderColor: 'rgba(0, 198, 255, 0.7)', boxShadow: '0 0 24px rgba(0, 198, 255, 0.3)' }}
    >
        <motion.header layout className="flex justify-between items-center p-6 cursor-pointer" onClick={onToggle}>
            <div>
                <h3 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>{clause.title}</h3>
                <p className="text-sm text-gray-400 mt-1">{clause.summary}</p>
            </div>
            <motion.div animate={{ rotate: isOpen ? 180 : 0 }} className="text-cyan-400">
                <ChevronDown />
            </motion.div>
        </motion.header>
        <AnimatePresence>
            {isOpen && (
                <motion.section
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.5, ease: "easeInOut" }}
                >
                    <div className="px-6 pb-6 text-gray-300" style={{ fontFamily: "'Inter', sans-serif" }}>
                        <p className="whitespace-pre-wrap leading-relaxed">{mode === 'human' ? clause.humanText : clause.legalText}</p>
                    </div>
                </motion.section>
            )}
        </AnimatePresence>
    </motion.div>
);

// ============================================================================
// --- 3. (Re-built) Main Page Component ---
// ============================================================================
export default function PrivacyPolicyPage() {
    const [mode, setMode] = useState<'human' | 'legal'>('human');
    const [expandedSection, setExpandedSection] = useState<number | null>(0);

    return (
        <div className="min-h-screen w-full bg-black text-white" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
           
            <div className="fixed inset-0 z-0 opacity-70">
                <Canvas>
                    <Suspense fallback={null}>
                        <DynamicPrivacyBackground />
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
                            THE DATA PACT
                        </motion.span>
                    </h1>
                    <p className="mt-6 text-lg text-gray-300 max-w-3xl mx-auto">
                        At airdeliver, privacy isn’t a checkbox — it’s our core protocol.
                    </p>
                </motion.div>
            </section>

          
            <section className="py-24 px-4 container mx-auto text-center relative z-10">
                <motion.h2 
                    initial={{ opacity: 0, y:20 }} 
                    whileInView={{ opacity: 1, y: 0 }} 
                    viewport={{ once: true }} 
                    className="text-4xl md:text-5xl font-bold mb-16" 
                    style={{ fontFamily: "'Orbitron', sans-serif" }}
                >
                    Built on Trust. Secured by AI.
                </motion.h2>
                <motion.div 
                    initial="hidden" 
                    whileInView="visible" 
                    viewport={{ once: true, amount: 0.2 }} 
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-6xl mx-auto"
                >
                    <EthicsCard icon={<Lock size={32} />} title="Encryption by Default" text="Every bit of data is encrypted before transmission." delay={0} />
                    <EthicsCard icon={<EyeOff size={32} />} title="Zero Human Access" text="Your data is never seen or handled manually by our team." delay={0.1} />
                    <EthicsCard icon={<FileText size={32} />} title="Adaptive Anonymization" text="Our AI continuously masks identifiers to preserve privacy." delay={0.2} />
                    <EthicsCard icon={<ShieldCheck size={32} />} title="Transparent Auditing" text="You have the power to trace every data interaction." delay={0.3} />
                </motion.div>
            </section>

           
            <section className="py-24 px-4 relative z-10">
                <div className="container mx-auto max-w-5xl">
                    <DualModeToggle mode={mode} setMode={setMode} />
                    <motion.div layout className="space-y-4">
                        {policyClauses.map((clause, index) => (
                            <PolicySection 
                                key={index} 
                                clause={clause} 
                                mode={mode} 
                                isOpen={expandedSection === index} 
                                onToggle={() => setExpandedSection(expandedSection === index ? null : index)}
                            />
                        ))}
                    </motion.div>
                </div>
            </section>
          
            <footer className="relative z-10 py-24 px-4 text-center bg-black/50 backdrop-blur-lg border-t border-cyan-400/20 mt-24">
                 <h2 className="text-3xl font-bold mb-8 text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>Our Commitments</h2>
                <div className="flex justify-center gap-6 flex-wrap max-w-4xl mx-auto">
                    {['GDPR', 'CCPA', 'ISO/IEC 27001', 'AI Ethics Council'].map((badge, i) => (
                        <motion.div 
                            key={i} 
                            whileHover={{ scale: 1.1, y: -5, borderColor: 'rgba(0, 198, 255, 0.7)', boxShadow: '0 0 24px rgba(0, 198, 255, 0.3)' }} 
                            className="px-6 py-3 bg-black/30 backdrop-blur-lg border border-cyan-400/30 rounded-lg text-gray-300 font-semibold"
                        >
                            {badge}
                        </motion.div>
                    ))}
                </div>
                <p className="mt-16 text-xs text-gray-600">
                    airdeliver © 2025 — The Future of Private AI Commerce.
                </p>
            </footer>
        </div>
    );
}
