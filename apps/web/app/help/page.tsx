'use client';

import React, { useState, Suspense, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Point, Points } from '@react-three/drei';
import { Bot, Mail, Phone, ChevronDown, Search } from 'lucide-react';
import { Input } from '@/components/ui/input'; // Assuming shadcn/ui
import * as THREE from 'three';

// --- Dummy Data for FAQ ---
const faqItems = [
    {
        question: "How fast is the delivery?",
        answer: "Our standard autonomous delivery is completed in under 30 minutes within city limits. Express Drone Mode can reduce this to as little as 10 minutes, depending on flight conditions and distance."
    },
    {
        question: "How do I track my order?",
        answer: "You can track your order in real-time through the 'Tracking' section of your profile. Our interface provides a live 3D map of your drone's flight path, estimated time of arrival, and current status."
    },
    {
        question: "What is 'AI Optimization'?",
        answer: "Our AI Core analyzes your cart, delivery location, and real-time network data to select the most efficient drone and flight path. This ensures maximum speed while minimizing energy consumption for a more sustainable delivery."
    },
];

// --- 3D Background Component ---
const NeuralLinesBackground = () => {
    const linesRef = useRef<THREE.Group>(null!);
    useFrame((state, delta) => {
        if (linesRef.current) {
            linesRef.current.rotation.y += delta * 0.05;
        }
    });
    return (
        <group ref={linesRef}>
            {Array.from({ length: 100 }).map((_, i) => (
                <mesh key={i}>
                    <ringGeometry args={[i * 0.1, i * 0.1 + 0.01, 64]} />
                    <meshBasicMaterial color="#00E6FF" transparent opacity={0.1} />
                </mesh>
            ))}
        </group>
    );
};

// --- Helper Component: Interactive Contact Card ---
const ContactCard = ({ icon, title, text, delay }: { icon: React.ReactNode, title: string, text: string, delay: number }) => (
    <motion.div
        variants={{ hidden: { opacity: 0, y: 50 }, visible: { opacity: 1, y: 0 } }}
        transition={{ duration: 0.7, delay }}
        whileHover={{ y: -10, scale: 1.03, transition: { type: 'spring', stiffness: 300 } }}
        className="relative p-8 bg-black/30 backdrop-blur-xl border border-white/10 rounded-2xl text-center cursor-pointer overflow-hidden"
    >
        <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="flex justify-center mb-4 text-cyan-400">{icon}</div>
        <h3 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>{title}</h3>
        <p className="text-gray-400">{text}</p>
    </motion.div>
);

// --- Helper Component: FAQ Accordion Item ---
const FaqItem = ({ item, isOpen, onToggle }: { item: any, isOpen: boolean, onToggle: () => void }) => (
    <motion.div layout className="bg-white/5 border border-white/10 rounded-lg overflow-hidden">
        <motion.header layout className="flex justify-between items-center p-6 cursor-pointer" onClick={onToggle}>
            <h4 className="font-semibold text-white">{item.question}</h4>
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
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                >
                    <div className="px-6 pb-6 text-gray-400 leading-relaxed" style={{ fontFamily: "'Inter', sans-serif" }}>
                        <p>{item.answer}</p>
                    </div>
                </motion.section>
            )}
        </AnimatePresence>
    </motion.div>
);

// --- Main Help Center Page ---
export default function HelpPage() {
    const [expandedFaq, setExpandedFaq] = useState<number | null>(0);

    return (
        <div className="min-h-screen w-full bg-black text-white" style={{ fontFamily: "'Neue Montreal', sans-serif" }}>
            {/* 1. HERO SECTION */}
            <section className="relative h-[80vh] w-full flex items-center justify-center text-center overflow-hidden">
                <div className="absolute inset-0 z-0 opacity-40">
                    <Canvas camera={{ position: [0, 0, 5], fov: 75 }}>
                        <Suspense fallback={null}>
                            <NeuralLinesBackground />
                            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                        </Suspense>
                    </Canvas>
                </div>
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="z-10 px-4"
                >
                    <h1 className="text-5xl md:text-7xl font-black text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Need Assistance?
                    </h1>
                    <p className="mt-4 text-lg text-gray-300 max-w-2xl mx-auto">
                        Our intelligent system and human team are available 24/7 to support your journey.
                    </p>
                    <motion.button
                        whileHover={{ scale: 1.05, boxShadow: "0 0 25px rgba(0, 230, 255, 0.5)" }}
                        whileTap={{ scale: 0.95 }}
                        className="mt-8 glowing-button rounded-full px-8 py-4 text-lg font-bold"
                    >
                        Start Live AI Chat
                    </motion.button>
                </motion.div>
            </section>

            {/* 2. SMART CONTACT OPTIONS */}
            <section className="py-24 px-4 container mx-auto">
                <motion.div
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, amount: 0.2 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto"
                >
                    <ContactCard icon={<Bot size={32} />} title="AI Chat Assistant" text="Get instant answers from our intelligent support system." delay={0} />
                    <ContactCard icon={<Mail size={32} />} title="Email Support" text="Send a detailed inquiry to our human support specialists." delay={0.1} />
                    <ContactCard icon={<Phone size={32} />} title="Human Callback" text="Request a scheduled call with a member of our team." delay={0.2} />
                </motion.div>
            </section>

            {/* 3. KNOWLEDGE BASE / FAQ */}
            <section className="py-24 px-4 bg-black bg-grid-white/[0.05]">
                <div className="container mx-auto max-w-4xl text-center">
                    <h2 className="text-4xl md:text-5xl font-bold text-white mb-12" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                        Knowledge Base
                    </h2>
                    <div className="relative mb-8">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
                        <Input
                            type="text"
                            placeholder="Search our knowledge base with AI..."
                            className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-full text-white placeholder-gray-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
                        />
                    </div>
                    <motion.div layout className="space-y-4 text-left">
                        {faqItems.map((item, index) => (
                            <FaqItem
                                key={index}
                                item={item}
                                isOpen={expandedFaq === index}
                                onToggle={() => setExpandedFaq(expandedFaq === index ? null : index)}
                            />
                        ))}
                    </motion.div>
                </div>
            </section>
            
            {/* FOOTER */}
            <footer className="py-20 px-4 text-center border-t border-white/10">
                <p className="text-gray-400">airdeliver © 2025 – Intelligent Support, Powered by AI.</p>
            </footer>
        </div>
    );
}
