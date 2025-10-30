'use client';

import React, { useState, Suspense, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { ChevronDown, ShieldCheck } from 'lucide-react';
import * as THREE from 'three';

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

const AnimatedGridBackground = () => {
    const materialRef = useRef<THREE.ShaderMaterial>(null!);
    useFrame(({ clock }) => {
        if (materialRef.current) {
            materialRef.current.uniforms.time.value = clock.getElapsedTime();
        }
    });
    const shader = {
        uniforms: { time: { value: 0 } },
        vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: `
            uniform float time;
            varying vec2 vUv;
            void main() {
                vec2 p = vUv * 2.0 - 1.0;
                float len = length(p);
                float a = atan(p.y, p.x);
                float pulse = sin(len * 10.0 - time * 2.0) * 0.5 + 0.5;
                float strength = smoothstep(0.99, 1.0, pulse) * 0.1;
                gl_FragColor = vec4(0.1, 0.7, 1.0, strength);
            }`
    };
    return (
        <mesh scale={[1.5, 1.5, 1.5]}>
            <planeGeometry args={[20, 20]} />
            <shaderMaterial ref={materialRef} args={[shader]} transparent depthWrite={false} />
        </mesh>
    );
};

const DualModeToggle = ({ mode, setMode }: { mode: 'human' | 'legal', setMode: (mode: 'human' | 'legal') => void }) => (
    <div className="flex justify-center mb-12">
        <div className="bg-black/30 border border-white/10 rounded-full p-1 flex gap-1">
            <button onClick={() => setMode('human')} className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors">
                {mode === 'human' && <motion.div layoutId="toggle-bg" className="absolute inset-0 bg-white/10 rounded-full" />}
                <span className="relative z-10">Human Readable</span>
            </button>
            <button onClick={() => setMode('legal')} className="relative px-6 py-2 rounded-full text-sm font-medium text-white transition-colors">
                {mode === 'legal' && <motion.div layoutId="toggle-bg" className="absolute inset-0 bg-white/10 rounded-full" />}
                <span className="relative z-10">Legal Text</span>
            </button>
        </div>
    </div>
);

const LegalCard = ({ clause, mode, isOpen, onToggle }: { clause: any, mode: 'human' | 'legal', isOpen: boolean, onToggle: () => void }) => (
    <motion.div layout className="bg-black/30 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-lg">
        <motion.div layout className="flex justify-between items-center p-6 cursor-pointer" onClick={onToggle}>
            <h3 className="text-xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>{clause.title}</h3>
            <motion.div animate={{ rotate: isOpen ? 180 : 0 }}>
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
                        <p className="whitespace-pre-wrap">{mode === 'human' ? clause.humanText : clause.legalText}</p>
                        {mode === 'human' && (
                             <div className="mt-4 p-3 bg-cyan-900/50 border border-cyan-500/30 rounded-lg text-sm text-cyan-200">
                                 <strong>AI Note:</strong> Your data is encrypted and anonymized during every transaction.
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    </motion.div>
);

const DataDivider = () => (
    <div className="h-24 w-full flex items-center justify-center">
        <div className="h-px w-full max-w-lg bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
    </div>
);

export default function TermsOfServicePage() {
    const [mode, setMode] = useState<'human' | 'legal'>('human');
    const [expandedCard, setExpandedCard] = useState<number | null>(0);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100">
        
            <section className="relative h-screen w-full flex items-center justify-center text-center overflow-hidden">
                <div className="absolute inset-0 z-0 opacity-40">
                    <Canvas>
                        <Suspense fallback={null}><AnimatedGridBackground /></Suspense>
                    </Canvas>
                </div>
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: "easeOut" }} className="z-10 px-4">
                    <h1 className="text-5xl md:text-7xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Terms of Service
                    </h1>
                    <p className="mt-2 text-cyan-400" style={{ fontFamily: "'Orbitron', sans-serif" }}>Powered by AI Transparency</p>
                    <p className="mt-6 text-lg text-gray-300 max-w-3xl mx-auto" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
                        These aren’t just rules. They’re shared understandings between humans and intelligent systems.
                    </p>
                </motion.div>
            </section>

            <section className="container mx-auto px-4 py-24 max-w-4xl">
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

            <DataDivider />

            <footer className="py-20 px-4 text-center relative">
                <div className="flex flex-col items-center gap-4">
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
