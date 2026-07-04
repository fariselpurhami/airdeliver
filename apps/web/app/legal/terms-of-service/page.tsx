//** apps/web/app/legal/terms-of-service/page.tsx **//

'use client';

import React, { useState, Suspense, useRef, useEffect, memo } from 'react';
import { motion, AnimatePresence, useScroll, useSpring, useReducedMotion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import { 
    ShieldCheck, Cpu, Lock, Globe, Scale, FileText, 
    AlertTriangle, Zap, ChevronRight, CheckCircle2 
} from 'lucide-react';
import * as THREE from 'three';
import dynamic from 'next/dynamic';

// ============================================================================
// --- 1. DATA INFRASTRUCTURE (Expanded Protocols) ---
// ============================================================================

const legalSections = [
  {
    id: "data-integrity",
    icon: Lock,
    title: "1. Data & Privacy Integrity",
    humanText: "Your data is encrypted and locked away. We only use it to make your deliveries faster, never to sell to third parties.",
    legalText: "airdeliver employs military-grade end-to-end encryption (E2EE) for all user data transmission and storage. Personal Identifiable Information (PII) is strictly siloed and accessed solely by autonomous agents for logistical optimization. We expressly disclaim any right to sell, lease, or distribute user data to external entities without explicit, written consent."
  },
  {
    id: "autonomous-ops",
    icon: Cpu,
    title: "2. Autonomous Operations",
    humanText: "Our fleet flies itself. While our AI is incredibly smart, weather and physics still apply. Deliveries are fast, but safety comes first.",
    legalText: "The Service relies on Level 5 Autonomous Systems. While airdeliver maintains 99.9% uptime, operational continuity is contingent upon environmental variables, airspace regulations, and hardware integrity. Predictive delivery windows are algorithmic estimates and do not constitute a binding guarantee of arrival time in force majeure events."
  },
  {
    id: "user-conduct",
    icon: Globe,
    title: "3. User Responsibilities",
    humanText: "Don't order illegal stuff. Give us a safe place to land. Be a good human.",
    legalText: "The User warrants that all goods requested for transport comply with local, federal, and international laws. The User assumes full liability for ensuring the designated drop-off zone is clear of obstructions and safe for aerial drone approach. airdeliver reserves the right to terminate service immediately upon detection of illicit activity."
  },
  {
    id: "intellectual-property",
    icon: Scale,
    title: "4. Intellectual Property",
    humanText: "Our tech, our code, our drones. You can use the app, but please don't try to reverse-engineer our AI.",
    legalText: "All algorithms, neural network architectures, drone designs, and software interfaces associated with airdeliver are the exclusive intellectual property of airdeliver Systems Inc. Users are granted a limited, non-exclusive, non-transferable license to access the platform for personal use only. Reverse engineering is strictly prohibited."
  },
  {
    id: "payment-terms",
    icon: Zap,
    title: "5. Payment Protocols",
    humanText: "Payments are automatic and secure. Refunds are handled by our AI instantly if things go wrong.",
    legalText: "Transactions are processed via secure, tokenized payment gateways. Charges are applied automatically upon order dispatch. In the event of service failure attributed to airdeliver's infrastructure, our Automated Refund System (ARS) will instantly credit the User's account. All fees are subject to dynamic pricing based on network demand."
  },
  {
    id: "liability",
    icon: AlertTriangle,
    title: "6. Limitation of Liability",
    humanText: "We aren't liable if a bird hits the drone or if you drop your phone while ordering.",
    legalText: "To the maximum extent permitted by law, airdeliver shall not be liable for indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from (i) your access to or use of or inability to access or use the Service; (ii) any conduct or content of any third party on the Service."
  }
];

// ============================================================================
// --- 2. ARCHITECTURAL BACKGROUND (The Grid) ---
// ============================================================================

const TermsBackground = memo(() => {
    const groupRef = useRef<THREE.Group>(null!);
    const prefersReducedMotion = useReducedMotion();

    useFrame((state) => {
        if (groupRef.current && !prefersReducedMotion) {
            groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.02;
        }
    });

    return (
        <group ref={groupRef}>
            <fog attach="fog" args={['#000000', 30, 90]} />
            <ambientLight intensity={0.2} />
            <pointLight position={[10, 10, 10]} intensity={1.5} color="#00C6FF" />
            <Stars radius={120} depth={50} count={5000} factor={4} saturation={0} fade speed={prefersReducedMotion ? 0 : 1} />
        </group>
    );
});
TermsBackground.displayName = 'TermsBackground';

// Dynamically import Three.js content to prevent SSR hydration mismatch & isolate weight
const DynamicTermsBackground = dynamic(() => Promise.resolve(TermsBackground), { 
    ssr: false,
    loading: () => null
});

// ============================================================================
// --- 3. UI COMPONENTS (The Interface) ---
// ============================================================================

interface ModeToggleProps {
    mode: 'human' | 'legal';
    setMode: (m: 'human' | 'legal') => void;
}

const ModeToggle = memo(({ mode, setMode }: ModeToggleProps) => (
    <div 
        role="group"
        aria-label="Toggle language mode"
        className="flex items-center gap-4 bg-white/5 backdrop-blur-xl border border-white/10 p-2 rounded-full w-fit mx-auto sticky top-24 z-20 shadow-2xl"
    >
        <button 
            onClick={() => setMode('human')}
            aria-pressed={mode === 'human'}
            className={`relative px-6 py-3 rounded-full text-sm font-bold uppercase tracking-wider transition-all duration-300 ${mode === 'human' ? 'text-black' : 'text-gray-400 hover:text-white'}`}
        >
            {mode === 'human' && (
                <motion.div layoutId="mode-toggle" className="absolute inset-0 bg-cyan-400 rounded-full shadow-[0_0_20px_rgba(34,211,238,0.5)]" />
            )}
            <span className="relative z-10 flex items-center gap-2"><CheckCircle2 size={16} aria-hidden="true" /> Human Mode</span>
        </button>
        <button 
            onClick={() => setMode('legal')}
            aria-pressed={mode === 'legal'}
            className={`relative px-6 py-3 rounded-full text-sm font-bold uppercase tracking-wider transition-all duration-300 ${mode === 'legal' ? 'text-black' : 'text-gray-400 hover:text-white'}`}
        >
            {mode === 'legal' && (
                <motion.div layoutId="mode-toggle" className="absolute inset-0 bg-white rounded-full shadow-[0_0_20px_rgba(255,255,255,0.5)]" />
            )}
            <span className="relative z-10 flex items-center gap-2"><Scale size={16} aria-hidden="true" /> Legal Mode</span>
        </button>
    </div>
));
ModeToggle.displayName = 'ModeToggle';

interface NavigationLinkProps {
    id: string;
    title: string;
    active: boolean;
}

const NavigationLink = memo(({ id, title, active }: NavigationLinkProps) => (
    <a 
        href={`#${id}`}
        aria-current={active ? 'step' : undefined}
        className={`group flex items-center justify-between w-full p-4 rounded-2xl border transition-all duration-300 ${active ? 'bg-cyan-900/20 border-cyan-500/50 text-white' : 'bg-transparent border-transparent text-gray-500 hover:text-gray-300 hover:bg-white/5'}`}
    >
        <span className="text-sm font-medium truncate pr-4">{title}</span>
        <ChevronRight size={14} aria-hidden="true" className={`transform transition-transform ${active ? 'text-cyan-400 translate-x-0' : 'text-gray-700 -translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0'}`} />
    </a>
));
NavigationLink.displayName = 'NavigationLink';

interface LegalMonolithProps {
    section: typeof legalSections[0];
    mode: 'human' | 'legal';
}

const LegalMonolith = memo(({ section, mode }: LegalMonolithProps) => {
    return (
        <motion.div 
            id={section.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            className="group relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-[40px] p-8 md:p-12 mb-8 overflow-hidden transition-colors hover:border-cyan-500/30 will-change-transform"
        >
            <div className="absolute top-0 right-0 p-8 opacity-20 group-hover:opacity-40 transition-opacity pointer-events-none">
                <section.icon size={64} className="text-cyan-400" aria-hidden="true" />
            </div>

            <div className="relative z-10">
                <h3 className="text-2xl md:text-3xl font-bold text-white mb-6" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                    {section.title}
                </h3>
                
                <div className="relative min-h-[100px]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={mode}
                            initial={{ opacity: 0, x: mode === 'human' ? -20 : 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: mode === 'human' ? 20 : -20 }}
                            transition={{ duration: 0.3 }}
                            className="will-change-transform"
                        >
                            {mode === 'human' ? (
                                <div className="flex gap-4 items-start">
                                    <div className="w-1 h-full min-h-[3rem] bg-cyan-500/50 rounded-full" />
                                    <p className="text-lg text-cyan-100/80 font-medium leading-relaxed">
                                        &quot;{section.humanText}&quot;
                                    </p>
                                </div>
                            ) : (
                                <div className="bg-black/30 rounded-2xl p-6 border border-white/5 font-mono text-sm text-gray-400 leading-relaxed text-justify">
                                    {section.legalText}
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
});
LegalMonolith.displayName = 'LegalMonolith';

// ============================================================================
// --- 4. MAIN PAGE (The Assembly) ---
// ============================================================================

export default function TermsPage() {
    const [mode, setMode] = useState<'human' | 'legal'>('human');
    const [activeSection, setActiveSection] = useState(legalSections[0].id);
    const { scrollYProgress } = useScroll();
    const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 });

    useEffect(() => {
        // Obviates main thread blocking by migrating layout calculations to an async observer
        const observer = new IntersectionObserver(
            (entries) => {
                const intersectingEntry = entries.find(entry => entry.isIntersecting);
                if (intersectingEntry) {
                    setActiveSection(intersectingEntry.target.id);
                }
            },
            {
                root: null,
                rootMargin: '-20% 0px -80% 0px', // Triggers accurately when section crests the upper viewport
                threshold: 0
            }
        );

        legalSections.forEach((section) => {
            const el = document.getElementById(section.id);
            if (el) observer.observe(el);
        });

        return () => observer.disconnect();
    }, []);

    return (
        <div className="min-h-screen w-full bg-black text-gray-100 selection:bg-cyan-500/30">
            
            <motion.div 
                className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 to-purple-600 origin-left z-50 will-change-transform" 
                style={{ scaleX }} 
            />

            <div className="fixed inset-0 z-0 opacity-60 pointer-events-none">
                <Canvas 
                    camera={{ position: [0, 0, 15], fov: 45 }}
                    dpr={[1, 1.5]} // Restricts DPR scale multiplier to save GPU cycles on mobile/retina displays
                    gl={{ powerPreference: "high-performance", antialias: false, alpha: false }}
                    performance={{ min: 0.5 }}
                >
                    <Suspense fallback={null}>
                        <DynamicTermsBackground />
                    </Suspense>
                </Canvas>
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
            </div>

            <section className="relative z-10 pt-40 pb-20 px-4 text-center">
                <motion.div 
                    initial={{ opacity: 0, y: 30 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="will-change-transform"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-md mb-6">
                        <FileText size={14} className="text-cyan-400" aria-hidden="true" />
                        <span className="text-xs font-bold uppercase tracking-widest text-gray-300">System Protocols v2.4</span>
                    </div>
                    <h1 className="text-5xl md:text-7xl font-black text-white mb-6 tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        TERMS OF <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-600">SERVICE</span>
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto font-light">
                        The operational framework governing the relationship between human users and the airdeliver autonomous infrastructure.
                    </p>
                </motion.div>
            </section>

            <section className="relative z-10 container mx-auto px-4 max-w-7xl pb-32">
                
                <div className="sticky top-24 z-30 mb-16 flex justify-center">
                    <ModeToggle mode={mode} setMode={setMode} />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                    
                    <aside className="hidden lg:block lg:col-span-4 xl:col-span-3">
                        <nav className="sticky top-48 p-6 rounded-[30px] bg-white/5 backdrop-blur-xl border border-white/10" aria-label="Legal Sections Navigation">
                            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-6 pl-2">Navigation</h2>
                            <div className="space-y-2">
                                {legalSections.map((section) => (
                                    <NavigationLink 
                                        key={section.id} 
                                        id={section.id} 
                                        title={section.title} 
                                        active={activeSection === section.id} 
                                    />
                                ))}
                            </div>
                            <div className="mt-8 pt-6 border-t border-white/5">
                                <div className="flex items-center gap-3 p-4 rounded-xl bg-cyan-900/20 border border-cyan-500/20">
                                    <ShieldCheck className="text-cyan-400" size={24} aria-hidden="true" />
                                    <div>
                                        <p className="text-xs text-cyan-200 font-bold">Encrypted Connection</p>
                                        <p className="text-[10px] text-cyan-400/70">Verified by airdeliver Security</p>
                                    </div>
                                </div>
                            </div>
                        </nav>
                    </aside>

                    <main className="col-span-1 lg:col-span-8 xl:col-span-9">
                        <div className="space-y-2">
                            {legalSections.map((section) => (
                                <LegalMonolith key={section.id} section={section} mode={mode} />
                            ))}
                        </div>

                        <div className="mt-16 text-center border-t border-white/10 pt-12">
                            <p className="text-gray-500 text-sm mb-6">
                                By accessing the airdeliver network, you acknowledge these protocols.
                            </p>
                            <p className="text-xs text-gray-600 uppercase tracking-widest">
                                Last Updated: June 01, 2026
                            </p>
                        </div>
                    </main>

                </div>
            </section>
        </div>
    );
}
