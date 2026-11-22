//** apps/web/components/ai/AIVoiceOverlay.tsx **//

'use client';

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';

// --- CONFIGURATION CONSTANTS ---
const AUDIO_SAMPLE_RATE = 16000;
const BARGE_IN_THRESHOLD = 0.05;
const FFT_SIZE = 256;

// --- STRICT DOMAIN TYPES ---
type VoiceControlPayload = { action: 'VOICE_SEARCH'; query: string };

type VoiceStreamMessage = 
    | { type: 'text_stream'; text: string }
    | { type: 'control'; payload: VoiceControlPayload }
    | { type: 'product_carousel'; products: Record<string, unknown>[] }
    | { type: 'error'; message: string };

// --- MATH ENGINE: Generative Organic Waves ---
const generateOrganicPath = (points: number, radius: number, audioLevel: number, offset: number): string => {
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

// --- COMPONENT: The Living Hologram ---
const HolographicBlob = React.memo(({ audioLevel }: { audioLevel: number }) => {
    const [time, setTime] = useState<number>(0);

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
});
HolographicBlob.displayName = 'HolographicBlob';

// --- MAIN ORCHESTRATION COMPONENT ---
export const AIVoiceOverlay = React.memo(() => {
    // 1. Atomic State Subscriptions (Zero Render Thrashing)
    const isVoiceMode = useAIOrderingStore(state => state.isVoiceMode);
    const setVoiceMode = useAIOrderingStore(state => state.setVoiceMode);
    const addSocketAIMessage = useAIOrderingStore(state => state.addSocketAIMessage);
    const sendMessage = useAIOrderingStore(state => state.sendMessage);

    // 2. Local View State
    const [status, setStatus] = useState<'listening' | 'processing' | 'speaking'>('listening');
    const [aiResponse, setAiResponse] = useState<string>('');
    const [audioLevel, setAudioLevel] = useState<number>(1); 

    // 3. Mutable References (Lifecycles & Queues)
    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const audioQueueRef = useRef<ArrayBuffer[]>([]);
    const isPlayingRef = useRef<boolean>(false);
    const animationFrameRef = useRef<number>(undefined);

    // 4. Sequential Audio Decoder & Player
    const processAudioQueue = useCallback(async () => {
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
                    else void processAudioQueue(); 
                };
            } catch (error) {
                console.error("[VoiceOrchestrator] Audio Decode Error:", error);
                isPlayingRef.current = false;
                void processAudioQueue();
            }
        }
    }, []);

    // 5. Hardware & Transport Initialization
    useEffect(() => {
        if (!isVoiceMode) return;
        let localStream: MediaStream | null = null;
        let processor: ScriptProcessorNode | null = null;
        
        const initVoiceSession = async () => {
            try {
                if (!navigator.mediaDevices?.getUserMedia) {
                    console.error("[VoiceOrchestrator] Hardware Access Denied or Unsupported.");
                    setVoiceMode(false);
                    return;
                }

                // Request Microphone
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                // Initialize Cross-Browser Audio Context
                const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
                const ctx = new AudioContextClass({ sampleRate: AUDIO_SAMPLE_RATE });
                audioContextRef.current = ctx;
                
                // Holographic Audio Analyzer Setup
                const analyser = ctx.createAnalyser();
                analyser.fftSize = FFT_SIZE;
                analyser.smoothingTimeConstant = 0.8; 
                analyserRef.current = analyser;
                
                const source = ctx.createMediaStreamSource(localStream);
                source.connect(analyser);

                // Transport Layer Establishment
                const wsBase = process.env.NEXT_PUBLIC_WS_URL || `ws://${window.location.host}`;
                const httpBase = wsBase.replace('ws', 'http').replace('wss', 'https');

                // طلب التذكرة من الباك إند
                const ticketResponse = await fetch(`${httpBase}/api/v1/ordering/ticket`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // لو بتبعت Token حطه هنا
                        // 'Authorization': `Bearer ${session?.accessToken}` 
                    }
                });

                if (!ticketResponse.ok) {
                    console.error("[VoiceOrchestrator] Failed to acquire auth ticket.");
                    setVoiceMode(false);
                    return;
                }

                const { ticket } = await ticketResponse.json();
                const wsUrl = `${wsBase}/api/v1/ordering/voice-stream?ticket=${ticket}`;

                const ws = new WebSocket(wsUrl);
                ws.binaryType = 'arraybuffer';
                wsRef.current = ws;

                // Raw PCM Extraction (Fallback for typical Next.js lack of AudioWorklet serving)
                processor = ctx.createScriptProcessor(4096, 1, 1);
                source.connect(processor);
                processor.connect(ctx.destination);

                processor.onaudioprocess = (e: AudioProcessingEvent) => {
                    if (ws.readyState !== WebSocket.OPEN) return;
                    
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcmData = new Int16Array(inputData.length);
                    let volumeSum = 0;
                    
                    for (let i = 0; i < inputData.length; i++) {
                        const sample = inputData[i] ?? 0;
                        const s = Math.max(-1, Math.min(1, sample));
                        pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        volumeSum += Math.abs(sample);
                    }
                    
                    ws.send(pcmData.buffer);

                    // Voice Activity Detection (VAD) / Barge-in
                    if (isPlayingRef.current) {
                        const averageVolume = volumeSum / inputData.length;
                        if (averageVolume > BARGE_IN_THRESHOLD) { 
                            ws.send(JSON.stringify({ type: "INTERRUPT" }));
                            isPlayingRef.current = false;
                            audioQueueRef.current = [];
                            setStatus('listening');
                        }
                    }
                };

                // Network Ingress Parsing
                ws.onmessage = (event: MessageEvent) => {
                    // Binary Payload = Audio Chunk
                    if (event.data instanceof ArrayBuffer) {
                        audioQueueRef.current.push(event.data);
                        void processAudioQueue();
                        return;
                    } 
                    
                    // String Payload = Control or Text Stream
                    if (typeof event.data === 'string') {
                        try {
                            const data = JSON.parse(event.data) as VoiceStreamMessage;
                            
                            switch (data.type) {
                                case 'text_stream':
                                    setAiResponse(data.text);
                                    break;
                                    
                                case 'control':
                                    // THE BRIDGE: Dispatch to NLU Engine
                                    sendMessage(data.payload.query, true);
                                    break;
                                    
                                case 'product_carousel':
                                    if (data.products && data.products.length > 0) {
                                        addSocketAIMessage(data); 
                                    }
                                    break;
                                    
                                case 'error':
                                    console.warn("[VoiceOrchestrator] Upstream Engine Error:", data.message);
                                    break;
                            }
                        } catch (err) {
                            console.error("[VoiceOrchestrator] Unparsable JSON payload received:", err);
                        }
                    }
                };

                // Visual Render Loop
                const updateVisuals = () => {
                    if (analyser) {
                        const dataArray = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(dataArray);
                        const relevantFreqs = dataArray.slice(10, 80);
                        const average = relevantFreqs.reduce((a, b) => a + b, 0) / relevantFreqs.length;
                        const scale = 1 + Math.log(1 + average / 40); 
                        setAudioLevel(Math.max(1, scale));
                    }
                    animationFrameRef.current = requestAnimationFrame(updateVisuals);
                };
                updateVisuals();

            } catch (err) {
                console.error("[VoiceOrchestrator] Critical Initialization Failure:", err);
                setVoiceMode(false);
            }
        };

        void initVoiceSession();

        // 6. Deterministic Resource Teardown
        return () => {
            if (processor) processor.disconnect();
            if (localStream) localStream.getTracks().forEach(track => track.stop());
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close(1000, "Component Unmounted");
            }
            if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
                void audioContextRef.current.close();
            }
            if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
            
            audioQueueRef.current = [];
            isPlayingRef.current = false;
        };
    }, [isVoiceMode, setVoiceMode, sendMessage, addSocketAIMessage, processAudioQueue]);

    if (!isVoiceMode) return null;

    return (
        <AnimatePresence>
            {/* Backdrop */}
            <motion.div
                key="voice-backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 z-[100] bg-slate-950/10 pointer-events-none"
            />

            {/* Floating Dock */}
            <motion.div
                key="voice-card"
                initial={{ opacity: 0, y: 100 }} 
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 100 }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                className="absolute bottom-0 left-0 w-full z-[101] flex flex-col pointer-events-none pt-8"
            >
                <div className="absolute inset-0 w-full h-full bg-gradient-to-t from-slate-950/95 via-slate-950/70 to-slate-950/20 backdrop-blur-md rounded-t-3xl border-t border-white/5 pointer-events-none" />

                {/* Header (Status & Controls) */}
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
                        aria-label="Close Voice Interface"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Core Visualizer */}
                <div className="relative w-full h-[180px] flex items-center justify-center overflow-visible pointer-events-auto">
                    <HolographicBlob audioLevel={audioLevel} />

                    {/* Subtitle / Telemetry Layer */}
                    <div className="absolute inset-0 flex items-center justify-center text-center z-50 px-8 pb-4 pointer-events-none">
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
                                {status === 'listening' ? "" : aiResponse}
                            </motion.p>
                        </AnimatePresence>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
});
AIVoiceOverlay.displayName = 'AIVoiceOverlay';
