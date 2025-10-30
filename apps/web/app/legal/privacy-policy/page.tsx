'use client';

import React, { useState, Suspense, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Lock, EyeOff, ShieldCheck, FileText, ChevronDown } from 'lucide-react';
import * as THREE from 'three';

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

const FlowingParticles = () => {
    const pointsRef = useRef<THREE.Points>(null!);
    const count = 5000;
    const positions = useMemo(() => {
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count * 3; i++) {
            pos[i] = (Math.random() - 0.5) * 15;
        }
        return pos;
    }, [count]);

    useFrame((state, delta) => {
        if (pointsRef.current) {
            pointsRef.current.position.y += delta * 0.05;
            if (pointsRef.current.position.y > 5) {
                pointsRef.current.position.y = -5;
            }
        }
    });

    return (
        <points ref={pointsRef}>
            <bufferGeometry>
                <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
            </bufferGeometry>
            <pointsMaterial attach="material" size={0.005} color="#00E6FF" transparent opacity={0.5} />
        </points>
    );
};

const EthicsCard = ({ icon, title, text, delay }: { icon: React.ReactNode; title: string; text: string; delay: number }) => (
    <motion.div
        variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
        transition={{ duration: 0.7, delay }}
        className="p-6 bg-white/[.05] backdrop-blur-lg border border-white/10 rounded-2xl text-center"
    >
        <div className="flex justify-center mb-4 text-cyan-400">{icon}</div>
        <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
        <p className="text-gray-400 text-sm leading-relaxed">{text}</p>
    </motion.div>
);

const DualModeToggle = ({ mode, setMode }: { mode: 'human' | 'legal', setMode: (mode: 'human' | 'legal') => void }) => (
    <div className="flex justify-center mb-12">
        <div className="bg-black/30 border border-white/10 rounded-full p-1 flex gap-1">
            <button onClick={() => setMode('human')} className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors">
                {mode === 'human' && <motion.div layoutId="privacy-toggle-bg" className="absolute inset-0 bg-white/10 rounded-full" />}
                <span className="relative z-10">Human Mode</span>
            </button>
            <button onClick={() => setMode('legal')} className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors">
                {mode === 'legal' && <motion.div layoutId="privacy-toggle-bg" className="absolute inset-0 bg-white/10 rounded-full" />}
                <span className="relative z-10">Legal Mode</span>
            </button>
        </div>
    </div>
);

const PolicySection = ({ clause, mode, isOpen, onToggle }: { clause: any, mode: 'human' | 'legal', isOpen: boolean, onToggle: () => void }) => (
    <motion.div layout className="bg-black/30 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-lg">
        <motion.header layout className="flex justify-between items-center p-6 cursor-pointer" onClick={onToggle}>
            <div>
                <h3 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>{clause.title}</h3>
                <p className="text-sm text-gray-400 mt-1">{clause.summary}</p>
            </div>
            <motion.div animate={{ rotate: isOpen ? 180 : 0 }}>
                <ChevronDown className="text-gray-400" />
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

export default function PrivacyPolicyPage() {
    const [mode, setMode] = useState<'human' | 'legal'>('human');
    const [expandedSection, setExpandedSection] = useState<number | null>(0);

    return (
        <div className="min-h-screen w-full bg-black text-white" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
           
            <section className="relative h-screen w-full flex items-center justify-center text-center overflow-hidden">
                <div className="absolute inset-0 z-0 opacity-60">
                    <Canvas camera={{ position: [0, 0, 5], fov: 75 }}>
                        <Suspense fallback={null}><FlowingParticles /></Suspense>
                    </Canvas>
                </div>
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: "easeOut" }} className="z-10 px-4">
                    <h1 className="text-5xl md:text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-gray-400" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Your Data. Your Intelligence. Your Control.
                    </h1>
                    <p className="mt-6 text-lg text-gray-300 max-w-3xl mx-auto">
                        At airdeliver, privacy isn’t a checkbox — it’s our core protocol.
                    </p>
                </motion.div>
            </section>

          
            <section className="py-24 px-4 container mx-auto text-center">
                <motion.h2 initial={{ opacity: 0, y:20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-4xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    Built on Trust. Secured by AI.
                </motion.h2>
                <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.2 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto">
                    <EthicsCard icon={<Lock size={32} />} title="Encryption by Default" text="Every bit of data is encrypted before transmission." delay={0} />
                    <EthicsCard icon={<EyeOff size={32} />} title="Zero Human Access" text="Your data is never seen or handled manually by our team." delay={0.1} />
                    <EthicsCard icon={<FileText size={32} />} title="Adaptive Anonymization" text="Our AI continuously masks identifiers to preserve privacy." delay={0.2} />
                    <EthicsCard icon={<ShieldCheck size={32} />} title="Transparent Auditing" text="You have the power to trace every data interaction." delay={0.3} />
                </motion.div>
            </section>

           
            <section className="py-24 px-4 bg-black bg-grid-white/[0.05]">
                <div className="container mx-auto max-w-4xl">
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

          
            <section className="py-24 px-4 text-center">
                <h2 className="text-3xl font-bold mb-8 text-gray-400" style={{ fontFamily: "'Orbitron', sans-serif" }}>Our Commitments</h2>
                <div className="flex justify-center gap-8 flex-wrap">
                    {['GDPR', 'CCPA', 'ISO/IEC 27001', 'AI Ethics Council'].map((badge, i) => (
                        <motion.div key={i} whileHover={{ scale: 1.1, y: -5 }} className="px-6 py-3 bg-white/5 border border-white/10 rounded-lg text-gray-300 font-semibold">
                            {badge}
                        </motion.div>
                    ))}
                </div>
                <p className="mt-8 text-sm text-gray-500">airdeliver operates under full international compliance and continuous AI auditing.</p>
            </section>

         
            <footer className="py-24 px-4 text-center">
                 <p className="text-2xl text-gray-300 mb-8 max-w-3xl mx-auto" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
                    “We believe privacy is not about hiding data — it’s about giving you power over it.”
                </p>
                <p className="mt-16 text-xs text-gray-600">
                    airdeliver © 2025 — The Future of Private AI Commerce.
                </p>
            </footer>
        </div>
    );
}
