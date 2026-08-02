//** apps/web/components/ai/AIVoiceOverlay.tsx **//

'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';

// --- 🌊 MATH ENGINE: Generative Organic Waves ---
const generateOrganicPath = (points: number, radius: number, audioLevel: number, offset: number) => {
    let d = "";
    const angleStep = (Math.PI * 2) / points;

    for (let i = 0; i <= points; i++) {
        const angle = i * angleStep;
        
        const wave1 = Math.sin(angle * 6 + offset) * (20 * audioLevel); 
        const wave2 = Math.cos(angle * 3 - offset) * (15 * audioLevel); 
        
        const r = radius + wave1 + wave2;
        
        const x = 300 + Math.cos(angle) * r; 
        const y = 300 + Math.sin(angle) * r;

        if (i === 0) d += `M ${x} ${y}`;
        else d += ` L ${x} ${y}`;
    }
    d += " Z"; 
    return d;
};

// --- 🧬 COMPONENT: The Living Hologram ---
const HolographicBlob = ({ audioLevel }: { audioLevel: number }) => {
    const [time, setTime] = useState(0);

    useEffect(() => {
        let frameId: number;
        const animate = () => {
            setTime(t => t + 0.02); 
            frameId = requestAnimationFrame(animate);
        };
        animate();
        return () => cancelAnimationFrame(frameId);
    }, []);

    const path1 = useMemo(() => generateOrganicPath(100, 90, audioLevel, time), [audioLevel, time]);
    const path2 = useMemo(() => generateOrganicPath(100, 95, audioLevel * 0.8, time + 2), [audioLevel, time]);
    const path3 = useMemo(() => generateOrganicPath(100, 85, audioLevel * 1.2, time - 1), [audioLevel, time]);

    return (
        <div className="relative w-full h-full flex items-center justify-center pointer-events-none scale-75 origin-bottom">
             <svg width="600" height="600" viewBox="0 0 600 600" className="absolute w-[160%] h-[160%] opacity-90">
                <defs>
                    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.8" />
                    </linearGradient>
                    <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
                    </linearGradient>
                    <linearGradient id="grad3" x1="100%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#ec4899" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#d946ef" stopOpacity="0" />
                    </linearGradient>
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>

                <motion.path 
                    d={path1} 
                    fill="none" 
                    stroke="url(#grad1)" 
                    strokeWidth="2"
                    filter="url(#glow)"
                />

                <motion.path 
                    d={path2} 
                    fill="none" 
                    stroke="url(#grad2)" 
                    strokeWidth="1.5"
                    className="mix-blend-screen"
                />

                <motion.path 
                    d={path3} 
                    fill="none" 
                    stroke="url(#grad3)" 
                    strokeWidth="1.5"
                    className="mix-blend-screen"
                />
            </svg>
            
            <motion.div 
                className="absolute w-24 h-24 rounded-full blur-lg bg-cyan-500/20"
                animate={{ 
                    scale: [1, 1.3, 1], 
                    opacity: [0.4, 0.7, 0.4] 
                }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
        </div>
    );
};

export const AIVoiceOverlay = () => {
    // --- STATE & HOOKS ---
    const { isVoiceMode, setVoiceMode, addSocketAIMessage } = useAIOrderingStore();
    const [status, setStatus] = useState<'listening' | 'processing' | 'speaking'>('listening');
    const [aiResponse, setAiResponse] = useState('');
    const [audioLevel, setAudioLevel] = useState(1); 

    // --- REFS ---
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const audioQueueRef = useRef<ArrayBuffer[]>([]);
    const isPlayingRef = useRef(false);
    const animationFrameRef = useRef<number>();

    // --- AUDIO QUEUE PROCESSOR ---
    const processAudioQueue = async () => {
        if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
        isPlayingRef.current = true;
        const chunk = audioQueueRef.current.shift();
        if (chunk && audioContextRef.current) {
            try {
                const audioBuffer = await audioContextRef.current.decodeAudioData(chunk);
                const source = audioContextRef.current.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContextRef.current.destination);
                if (analyserRef.current) source.connect(analyserRef.current);
                source.start(0);
                setStatus('speaking');
                source.onended = () => {
                    isPlayingRef.current = false;
                    if (audioQueueRef.current.length === 0) setStatus('listening');
                    else processAudioQueue(); 
                };
            } catch (e) {
                isPlayingRef.current = false;
                processAudioQueue();
            }
        }
    };

    // --- INITIALIZATION (Mic + WebSocket) ---
    useEffect(() => {
        if (!isVoiceMode) return;
        let localStream: MediaStream | null = null;
        
        const initVoiceSession = async () => {
            try {
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                    alert("المايكروفون غير مدعوم في هذا المتصفح. تأكد من تشغيل الموقع عبر HTTPS أو Localhost، ومنح الصلاحية للموقع.");
                    setVoiceMode(false);
                    return;
                }
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                // دعم متصفحات مختلفة
                const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
                const ctx = new AudioContextClass();
                audioContextRef.current = ctx;
                
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 256;
                analyser.smoothingTimeConstant = 0.8; 
                analyserRef.current = analyser;
                
                const source = ctx.createMediaStreamSource(localStream);
                source.connect(analyser);

                const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ordering/voice-stream?ticket=DEMO`; 
                const ws = new WebSocket(wsUrl);
                ws.binaryType = 'arraybuffer';
                wsRef.current = ws;

                const mediaRecorder = new MediaRecorder(localStream, { mimeType: 'audio/webm' });
                mediaRecorderRef.current = mediaRecorder;
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) ws.send(e.data);
                };
                mediaRecorder.start(250); 

                ws.onmessage = async (event) => {
                    if (event.data instanceof ArrayBuffer) {
                        audioQueueRef.current.push(event.data);
                        processAudioQueue();
                    } else if (typeof event.data === 'string') {
                        const data = JSON.parse(event.data);
                        if (data.type === 'text_stream') setAiResponse(data.text);
                        
                        if (data.type === 'control') {
                            addSocketAIMessage({ id: Date.now(), sender: 'user', contentType: 'text', content: data.payload.query, status: 'sent' });
                        }
                        if (data.type === 'product_carousel' || (data.products && data.products.length > 0)) {
                            addSocketAIMessage(data); 
                        }
                    }
                };

                const updateVisuals = () => {
                    if (analyser) {
                        const dataArray = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(dataArray);
                        
                        const relevantFreqs = dataArray.slice(10, 80);
                        const average = relevantFreqs.reduce((a, b) => a + b) / relevantFreqs.length;
                        
                        const scale = 1 + Math.log(1 + average / 40); 
                        setAudioLevel(Math.max(1, scale));
                    }
                    animationFrameRef.current = requestAnimationFrame(updateVisuals);
                };
                updateVisuals();
            } catch (err) {
                console.error("Voice Error:", err);
                setVoiceMode(false);
            }
        };
        initVoiceSession();

        return () => {
            if (localStream) localStream.getTracks().forEach(track => track.stop());
            if (wsRef.current) wsRef.current.close();
            if (audioContextRef.current) audioContextRef.current.close();
            if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        };
    }, [isVoiceMode]);

    if (!isVoiceMode) return null;

    return (
        <AnimatePresence>
            {/* Light Backdrop */}
            <motion.div
                key="voice-backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 z-[100] bg-slate-950/10"
                onClick={() => setVoiceMode(false)}
            />

            {/* THE BOTTOM FLOATING DOCK */}
            <motion.div
                key="voice-card"
                initial={{ opacity: 0, y: 100 }} 
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 100 }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                className="absolute bottom-0 left-0 w-full z-[101] flex flex-col pointer-events-none pt-8"
            >
                <div className="absolute inset-0 w-full h-full bg-gradient-to-t from-slate-950/95 via-slate-950/70 to-slate-950/20 backdrop-blur-md rounded-t-3xl border-t border-white/5 pointer-events-none" />

                {/* Header (Status & Close) */}
                <div className="relative w-full px-6 flex justify-between items-center mb-2 z-50 pointer-events-auto">
                    <div className="flex items-center gap-2 bg-white/5 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 shadow-lg">
                        <div className={`w-1.5 h-1.5 rounded-full ${status === 'speaking' ? 'bg-green-500' : 'bg-cyan-500'} animate-pulse`} />
                        <span className="text-[10px] font-mono text-cyan-400/90 tracking-widest uppercase">
                            {status === 'listening' ? "I'm listening..." : status === 'processing' ? 'Thinking' : 'Speaking'}
                        </span>
                    </div>
                    
                    <button 
                        onClick={() => setVoiceMode(false)}
                        className="p-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 text-gray-400 hover:bg-white/15 hover:text-white hover:border-white/20 hover:scale-105 transition-all duration-300 shadow-lg"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Hologram Container */}
                <div className="relative w-full h-[180px] flex items-center justify-center overflow-visible pointer-events-auto">
                    
                    <HolographicBlob audioLevel={audioLevel} />

                    {/* Live Transcription Text */}
                    <div className="absolute inset-0 flex items-center justify-center text-center z-50 px-8 pb-4">
                        <AnimatePresence mode="wait">
                            <motion.p 
                                key={aiResponse || "default-text"}
                                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                                exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                                className={`text-xl font-medium leading-relaxed max-w-[300px] drop-shadow-2xl ${
                                    status === 'listening' 
                                    ? 'text-white/40 italic font-light' 
                                    : 'text-transparent bg-clip-text bg-gradient-to-r from-cyan-50 via-white to-purple-100'
                                }`}
                            >
                                {status === 'Listening' ? "" : aiResponse}
                            </motion.p>
                        </AnimatePresence>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};
