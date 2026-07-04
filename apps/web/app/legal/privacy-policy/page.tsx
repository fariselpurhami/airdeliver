//** apps/web/app/legal/privacy-policy/page.tsx **//

'use client';

import React, { useState, Suspense, useRef, useEffect, memo } from 'react';
import { motion, AnimatePresence, useScroll, useSpring, useReducedMotion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { 
    Shield, Lock, Eye, Server, Radio, Fingerprint, 
    FileKey, ChevronRight, ScanFace, Globe, CheckCircle2
} from 'lucide-react';
import * as THREE from 'three';

// ============================================================================
// --- 1. DATA PROTOCOLS (The Secure Ledger) ---
// ============================================================================

const privacyProtocols = [
  {
    id: "data-collection",
    icon: Server,
    title: "1. Data Collection Architecture",
    humanText: "We collect only the essentials: who you are, where you want your package, and how to pay. We don't spy on your personal life.",
    legalText: "airdeliver collects the following categories of data: (a) Personal Identifiers (Name, Email, Phone); (b) Financial Data (tokenized payment credentials via Stripe); (c) Transactional Metadata (Order history, preferences). Collection occurs solely at the point of user entry or automated system interaction. We strictly prohibit the collection of extraneous behavioral data unrelated to logistical fulfillment."
  },
  {
    id: "geo-spatial",
    icon: Radio,
    title: "2. Geo-Spatial Intelligence",
    humanText: "Our drones need precise coordinates to land safely. We track delivery locations, not your movements.",
    legalText: "To enable Level 5 Autonomous Delivery, we process high-precision Geo-Spatial Data including latitude, longitude, and altitude of designated Drop Zones. This data is utilized exclusively for flight path optimization and obstacle avoidance algorithms. User location tracking is active only during the 'Last Mile' delivery phase and is purged from active cache post-delivery."
  },
  {
    id: "ai-training",
    icon: Fingerprint,
    title: "3. AI Model Training",
    humanText: "We use delivery data to make our robots smarter. Don't worry, your personal details are stripped out first.",
    legalText: "Anonymized, aggregated operational data (e.g., flight times, weather responses, route efficiency) is ingested by our Neural Network to enhance fleet autonomy. This process employs Differential Privacy techniques to ensure that no individual user's data can be reverse-engineered or isolated from the aggregate dataset."
  },
  {
    id: "data-sharing",
    icon: Globe,
    title: "4. Third-Party Protocols",
    humanText: "We don't sell your data. We only share it with the bank to process payments and the cloud to keep the lights on.",
    legalText: "airdeliver maintains a strict 'No-Sale' policy regarding user data. Data disclosure is limited to: (a) Payment Processors (for transaction settlement); (b) Cloud Infrastructure Providers (AWS/GCP for encrypted storage); (c) Law Enforcement (only upon presentation of a valid, court-ordered warrant). All third-party processors are bound by Data Processing Agreements (DPA) compliant with GDPR/CCPA."
  },
  {
    id: "security-measures",
    icon: Shield,
    title: "5. Security Encryption",
    humanText: "We use bank-grade security. Your data is locked in a digital vault that even we can't easily open.",
    legalText: "All data at rest is encrypted using AES-256 standards. Data in transit is secured via TLS 1.3 protocols. Access control follows the Principle of Least Privilege (PoLP), ensuring that human access to raw user data is restricted to authorized security personnel only, and logged immutably for audit purposes."
  },
  {
    id: "user-rights",
    icon: FileKey,
    title: "6. User Sovereignty",
    humanText: "It's your data. You can ask to see it, fix it, or delete it whenever you want.",
    legalText: "In compliance with GDPR and CCPA, users retain full sovereignty over their data. Rights include: Right to Access, Right to Rectification, Right to Erasure ('Right to be Forgotten'), and Right to Data Portability. Requests can be initiated via the 'Security Protocol' section of the user profile or by contacting our Data Protection Officer (DPO)."
  }
];

// ============================================================================
// --- 2. ARCHITECTURAL BACKGROUND (The Digital Shield) ---
// ============================================================================

const PrivacyBackground = memo(() => {
    const groupRef = useRef<THREE.Group>(null!);
    const prefersReducedMotion = useReducedMotion();

    useFrame((state) => {
        if (groupRef.current && !prefersReducedMotion) {
            groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.03;
            groupRef.current.rotation.z = Math.sin(state.clock.getElapsedTime() * 0.1) * 0.05;
        }
    });

    return (
        <group ref={groupRef}>
            <fog attach="fog" args={['#000000', 20, 80]} />
            <ambientLight intensity={0.3} />
            <pointLight position={[15, 15, 15]} intensity={2} color="#10B981" /> 
            <pointLight position={[-15, -10, 5]} intensity={1} color="#06B6D4" />
            <Stars radius={120} depth={40} count={6000} factor={4} saturation={0} fade speed={prefersReducedMotion ? 0 : 0.5} />
        </group>
    );
});
PrivacyBackground.displayName = 'PrivacyBackground';

// ============================================================================
// --- 3. UI COMPONENTS (The Interface) ---
// ============================================================================

interface ToggleSwitchProps {
    mode: 'human' | 'legal';
    setMode: (m: 'human' | 'legal') => void;
}

const ToggleSwitch = memo(({ mode, setMode }: ToggleSwitchProps) => (
    <div 
        role="group" 
        aria-label="Toggle language mode"
        className="flex items-center gap-2 bg-black/40 backdrop-blur-xl border border-white/10 p-2 rounded-full w-fit mx-auto sticky top-24 z-20 shadow-2xl shadow-green-900/10"
    >
        <button 
            onClick={() => setMode('human')}
            aria-pressed={mode === 'human'}
            className={`relative px-8 py-3 rounded-full text-sm font-bold uppercase tracking-wider transition-all duration-300 ${mode === 'human' ? 'text-black' : 'text-gray-400 hover:text-white'}`}
        >
            {mode === 'human' && (
                <motion.div layoutId="privacy-mode" className="absolute inset-0 bg-green-400 rounded-full shadow-[0_0_20px_rgba(74,222,128,0.5)]" />
            )}
            <span className="relative z-10 flex items-center gap-2"><ScanFace size={16} aria-hidden="true" /> Human</span>
        </button>
        <button 
            onClick={() => setMode('legal')}
            aria-pressed={mode === 'legal'}
            className={`relative px-8 py-3 rounded-full text-sm font-bold uppercase tracking-wider transition-all duration-300 ${mode === 'legal' ? 'text-black' : 'text-gray-400 hover:text-white'}`}
        >
            {mode === 'legal' && (
                <motion.div layoutId="privacy-mode" className="absolute inset-0 bg-white rounded-full shadow-[0_0_20px_rgba(255,255,255,0.5)]" />
            )}
            <span className="relative z-10 flex items-center gap-2"><FileKey size={16} aria-hidden="true" /> Protocol</span>
        </button>
    </div>
));
ToggleSwitch.displayName = 'ToggleSwitch';

interface NavItemProps {
    id: string;
    title: string;
    active: boolean;
}

const NavItem = memo(({ id, title, active }: NavItemProps) => (
    <a 
        href={`#${id}`}
        aria-current={active ? 'step' : undefined}
        className={`group flex items-center justify-between w-full p-4 rounded-2xl border transition-all duration-300 ${active ? 'bg-green-900/20 border-green-500/50 text-white' : 'bg-transparent border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5'}`}
    >
        <span className="text-sm font-medium truncate pr-4">{title}</span>
        <div className={`w-2 h-2 rounded-full transition-colors ${active ? 'bg-green-400 shadow-[0_0_8px_#4ade80]' : 'bg-gray-700 group-hover:bg-gray-500'}`} />
    </a>
));
NavItem.displayName = 'NavItem';

interface ProtocolCardProps {
    data: typeof privacyProtocols[0];
    mode: 'human' | 'legal';
}

const ProtocolCard = memo(({ data, mode }: ProtocolCardProps) => {
    return (
        <motion.div 
            id={data.id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6 }}
            className="group relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-[40px] p-8 md:p-12 mb-8 overflow-hidden transition-all hover:border-green-500/30 will-change-transform"
        >
            <div className="absolute -top-20 -right-20 w-64 h-64 bg-green-500/10 rounded-full blur-[80px] opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

            <div className="relative z-10 flex flex-col gap-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 rounded-2xl bg-white/5 border border-white/5 text-green-400">
                        <data.icon size={28} aria-hidden="true" />
                    </div>
                    <h3 className="text-2xl font-bold text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        {data.title}
                    </h3>
                </div>
                
                <div className="relative min-h-[80px]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={mode}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.3 }}
                            className="will-change-transform"
                        >
                            {mode === 'human' ? (
                                <div className="pl-6 border-l-2 border-green-500/50">
                                    <p className="text-lg text-green-100/90 font-medium leading-relaxed">
                                        &quot;{data.humanText}&quot;
                                    </p>
                                </div>
                            ) : (
                                <div className="bg-black/40 rounded-2xl p-6 border border-white/5 font-mono text-sm text-gray-400 leading-relaxed text-justify shadow-inner">
                                    <span className="text-green-500/50 select-none mr-2">{'>'}</span>
                                    {data.legalText}
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
});
ProtocolCard.displayName = 'ProtocolCard';

// ============================================================================
// --- 4. MAIN PAGE (The Privacy Fortress) ---
// ============================================================================

export default function PrivacyPage() {
    const [mode, setMode] = useState<'human' | 'legal'>('human');
    const [activeSection, setActiveSection] = useState(privacyProtocols[0].id);
    const { scrollYProgress } = useScroll();
    const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 });
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
        
        // Replaces destructive synchronous scroll layout thrashing with an optimized Intersection Observer
        const observer = new IntersectionObserver(
            (entries) => {
                const intersectingEntry = entries.find(entry => entry.isIntersecting);
                if (intersectingEntry) {
                    setActiveSection(intersectingEntry.target.id);
                }
            },
            {
                root: null,
                rootMargin: '-30% 0px -70% 0px', // Triggers state change precisely when the section reaches the upper view
                threshold: 0
            }
        );

        privacyProtocols.forEach((protocol) => {
            const el = document.getElementById(protocol.id);
            if (el) observer.observe(el);
        });

        return () => observer.disconnect();
    }, []);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100 selection:bg-green-500/30">
            
            <motion.div 
                className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-green-400 to-cyan-500 origin-left z-50 will-change-transform" 
                style={{ scaleX }} 
            />

            <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
                {isMounted && (
                    <Canvas 
                        camera={{ position: [0, 0, 15], fov: 45 }}
                        dpr={[1, 1.5]} // Caps pixel ratio to prevent GPU overload on high-DPI retina screens
                        gl={{ powerPreference: "high-performance", antialias: false, alpha: false }}
                        performance={{ min: 0.5 }} // Allows dynamic frame downscaling under heavy load
                    >
                        <Suspense fallback={null}>
                            <PrivacyBackground />
                        </Suspense>
                    </Canvas>
                )}
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
            </div>

            <section className="relative z-10 pt-40 pb-24 px-4 text-center">
                <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }} 
                    animate={{ opacity: 1, scale: 1 }} 
                    transition={{ duration: 0.8 }}
                    className="will-change-transform"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-green-500/20 bg-green-900/10 backdrop-blur-md mb-8">
                        <Lock size={14} className="text-green-400" aria-hidden="true" />
                        <span className="text-xs font-bold uppercase tracking-widest text-green-200/80">Encrypted Vault</span>
                    </div>
                    <h1 className="text-5xl md:text-7xl font-black text-white mb-6 tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        PRIVACY <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-cyan-500">POLICY</span>
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed">
                        At <strong className="text-white">airdeliver</strong>, privacy isn&apos;t just a checkbox. It&apos;s the foundation of our autonomous infrastructure.
                    </p>
                </motion.div>
            </section>

            <section className="relative z-10 container mx-auto px-4 max-w-7xl pb-32">
                
                <div className="sticky top-24 z-30 mb-16 flex justify-center">
                    <ToggleSwitch mode={mode} setMode={setMode} />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                    
                    <aside className="hidden lg:block lg:col-span-4 xl:col-span-3">
                        <nav className="sticky top-48 p-6 rounded-[30px] bg-white/5 backdrop-blur-xl border border-white/10 overflow-hidden" aria-label="Privacy Protocols Navigation">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500/50 to-transparent" />
                            
                            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-6 pl-2">Protocols</h2>
                            <div className="space-y-2">
                                {privacyProtocols.map((protocol) => (
                                    <NavItem 
                                        key={protocol.id} 
                                        id={protocol.id} 
                                        title={protocol.title} 
                                        active={activeSection === protocol.id} 
                                    />
                                ))}
                            </div>

                            <div className="mt-8 pt-6 border-t border-white/5">
                                <div className="flex items-center gap-3 p-4 rounded-2xl bg-green-950/30 border border-green-500/20">
                                    <CheckCircle2 className="text-green-400" size={24} aria-hidden="true" />
                                    <div>
                                        <p className="text-xs text-green-200 font-bold">GDPR Compliant</p>
                                        <p className="text-[10px] text-green-400/70">Audited Annually</p>
                                    </div>
                                </div>
                            </div>
                        </nav>
                    </aside>

                    <main className="col-span-1 lg:col-span-8 xl:col-span-9">
                        <div className="space-y-4">
                            {privacyProtocols.map((protocol) => (
                                <ProtocolCard key={protocol.id} data={protocol} mode={mode} />
                            ))}
                        </div>

                        <div className="mt-20 text-center pt-12 border-t border-white/10">
                            <p className="text-gray-500 text-sm mb-4">
                                Need deeper access? Contact our Data Protection Officer at <a href="mailto:privacy@airdeliver.com" className="text-green-400 hover:underline focus:outline-none focus:ring-2 focus:ring-green-400 rounded-sm">privacy@airdeliver.com</a>
                            </p>
                            <p className="text-[10px] text-gray-700 uppercase tracking-widest">
                                Protocol Version 6.0 | Last Encrypted Update: Jun 2026
                            </p>
                        </div>
                    </main>

                </div>
            </section>
        </div>
    );
}
