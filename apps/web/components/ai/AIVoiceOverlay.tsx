//** apps/web/components/ai/AIVoiceOverlay.tsx **//

'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mic, Zap, BrainCircuit, Sparkles, Activity } from 'lucide-react';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';

// --- 🌌 Sub-Component: Particle Field Background ---
const ParticleField = () => {
    const particles = useMemo(() => {
        return Array.from({ length: 40 }).map((_, i) => ({
            id: i,
            x: Math.random() * 100,
            y: Math.random() * 100,
            size: Math.random() * 3 + 1,
            duration: Math.random() * 10 + 10,
            delay: Math.random() * 5
        }));
    }, []);

    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
            {particles.map((p) => (
                <motion.div
                    key={p.id}
                    initial={{ opacity: 0, x: `${p.x}%`, y: `${p.y}%` }}
                    animate={{ 
                        opacity: [0, 0.4, 0], 
                        y: [`${p.y}%`, `${p.y - 20}%`],
                        x: [`${p.x}%`, `${p.x + (Math.random() > 0.5 ? 10 : -10)}%`]
                    }}
                    transition={{ 
                        duration: p.duration, 
                        repeat: Infinity, 
                        delay: p.delay, 
                        ease: "linear" 
                    }}
                    className="absolute rounded-full bg-white blur-[1px]"
                    style={{ width: p.size, height: p.size }}
                />
            ))}
        </div>
    );
};

export const AIVoiceOverlay = () => {
    const { isVoiceMode, setVoiceMode, addSocketAIMessage } = useAIOrderingStore();
    const [status, setStatus] = useState<'listening' | 'processing' | 'speaking'>('listening');
    const [aiResponse, setAiResponse] = useState('');
    
    // 🎚️ Audio Physics State (Real-time Volume)
    const [audioLevel, setAudioLevel] = useState(1); 

    // 🛠️ Refs for Hardware Control
    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const audioQueueRef = useRef<ArrayBuffer[]>([]);
    const isPlayingRef = useRef(false);
    const animationFrameRef = useRef<number>();

    // 🎨 Ultra-Modern Color Palette
    const statusColors = {
        listening: { bg: 'bg-cyan-500', glow: 'shadow-cyan-500/50', text: 'text-cyan-400', hex: '#06b6d4' },
        processing: { bg: 'bg-fuchsia-600', glow: 'shadow-fuchsia-500/50', text: 'text-fuchsia-400', hex: '#c026d3' },
        speaking: { bg: 'bg-emerald-500', glow: 'shadow-emerald-500/50', text: 'text-emerald-400', hex: '#10b981' }
    };
    const currentTheme = statusColors[status];

    // --- 🔊 HELPER: Play Audio Queue (Gapless Playback) ---
    const processAudioQueue = async () => {
        if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
        
        isPlayingRef.current = true;
        const chunk = audioQueueRef.current.shift();
        
        if (chunk && audioContextRef.current) {
            try {
                // Decode & Play
                const audioBuffer = await audioContextRef.current.decodeAudioData(chunk);
                const source = audioContextRef.current.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContextRef.current.destination);
                
                // Connect to Analyzer for Visuals (Make the Orb dance to AI voice)
                if (analyserRef.current) {
                    source.connect(analyserRef.current);
                }

                source.start(0);
                setStatus('speaking');

                source.onended = () => {
                    isPlayingRef.current = false;
                    if (audioQueueRef.current.length === 0) {
                        setStatus('listening');
                    } else {
                        processAudioQueue(); // Play next chunk
                    }
                };
            } catch (e) {
                console.error("Audio Decode Error", e);
                isPlayingRef.current = false;
                processAudioQueue();
            }
        }
    };

    // --- 🎙️ MAIN LOGIC ---
    useEffect(() => {
        if (!isVoiceMode) return;

        // 1. Initialize Audio Context (The Engine)
        const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
        const ctx = new AudioContextClass();
        audioContextRef.current = ctx;
        
        // Setup Analyzer (Visual Physics)
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;

        // 2. WebSocket Setup (Binary Mode)
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ordering/voice-stream?ticket=DEMO`;
        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer'; // 👈 CRITICAL: We expect raw bytes
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('🎙️ Binary Voice Link Active');
            startMicrophone(ws, ctx, analyser);
        };
        
        ws.onmessage = async (event) => {
            // A. Receive Audio Bytes (AI Voice)
            if (event.data instanceof ArrayBuffer) {
                audioQueueRef.current.push(event.data);
                processAudioQueue();
            } 
            // B. Receive Control Text (Metadata/Subtitles)
            else if (typeof event.data === 'string') {
                const data = JSON.parse(event.data);
                if (data.type === 'text_stream') {
                    setAiResponse(data.text);
                } else if (data.type === 'control' && data.payload.action === 'VOICE_SEARCH') {
                    addSocketAIMessage({
                        id: Date.now(),
                        sender: 'user',
                        contentType: 'text',
                        content: data.payload.query,
                        status: 'sent'
                    });
                }
            }
        };

        ws.onclose = () => stopMicrophone();

        // 3. Visualization Loop
        const updateVisuals = () => {
            if (analyserRef.current) {
                const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(dataArray);
                
                // Calculate Average Volume
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                // Normalize to 1.0 - 2.0 range for scaling
                const scale = 1 + (average / 255) * 1.5; 
                setAudioLevel(scale);
            }
            animationFrameRef.current = requestAnimationFrame(updateVisuals);
        };
        updateVisuals();

        return () => {
            stopMicrophone();
            ws.close();
            if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
            if (audioContextRef.current) audioContextRef.current.close();
        };
    }, [isVoiceMode]);

    // --- 🎤 Hardware Access ---
    const startMicrophone = async (ws: WebSocket, ctx: AudioContext, analyser: AnalyserNode) => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Connect Mic to Analyzer (So the orb moves when YOU speak)
            const source = ctx.createMediaStreamSource(stream);
            source.connect(analyser);

            // Setup Recorder (Send Chunks to Server)
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' }); // Chrome standard
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    // Send Binary Blob directly
                    ws.send(e.data); 
                }
            };

            // Slice every 250ms for low latency streaming
            mediaRecorder.start(250); 
        } catch (e) {
            console.error("Mic Access Denied", e);
            setVoiceMode(false);
        }
    };

    const stopMicrophone = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
    };

    if (!isVoiceMode) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
                animate={{ opacity: 1, backdropFilter: "blur(20px)" }}
                exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
                className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/90"
            >
                {/* 🌌 1. Cinematic Background */}
                <div className={`absolute inset-0 bg-gradient-to-b from-black via-gray-900 to-black opacity-80`} />
                <div className={`absolute inset-0 opacity-20 transition-colors duration-1000 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-${currentTheme.bg.split('-')[1]}-900 via-transparent to-transparent`} />
                <ParticleField />

                {/* 🧠 2. The Living Core (Orb) */}
                <div className="relative z-20 flex flex-col items-center gap-16 w-full max-w-4xl">
                    <div className="relative flex items-center justify-center">
                        {/* Orbitals */}
                        <motion.div 
                            animate={{ rotate: 360 }}
                            transition={{ repeat: Infinity, duration: 10, ease: "linear" }}
                            className={`absolute w-80 h-80 rounded-full border border-white/5 border-t-${currentTheme.bg.split('-')[1]}-500/30 border-r-transparent`}
                        />
                        <motion.div 
                            animate={{ rotate: -360 }}
                            transition={{ repeat: Infinity, duration: 15, ease: "linear" }}
                            className="absolute w-64 h-64 rounded-full border border-white/5 border-b-white/20 border-l-transparent"
                        />

                        {/* 🔥 THE REACTIVE ORB (Moves with Volume) */}
                        <motion.div
                            layoutId="core-orb"
                            animate={{ 
                                scale: audioLevel, // 👈 Driven by Real-time Physics
                                boxShadow: status === 'speaking' 
                                    ? `0 0 ${60 * audioLevel}px ${currentTheme.hex}88` 
                                    : `0 0 40px ${currentTheme.hex}33`
                            }}
                            transition={{ type: "spring", stiffness: 300, damping: 20 }}
                            className={`relative w-32 h-32 rounded-full ${currentTheme.bg} flex items-center justify-center backdrop-blur-md bg-opacity-90 z-10 transition-colors duration-300`}
                        >
                            <motion.div key={status} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                {status === 'listening' && <Mic size={40 * (audioLevel * 0.8)} className="text-white drop-shadow-md" />}
                                {status === 'processing' && <BrainCircuit size={40} className="text-white drop-shadow-md animate-pulse" />}
                                {status === 'speaking' && <Activity size={40 * (audioLevel * 0.8)} className="text-white drop-shadow-md" />}
                            </motion.div>
                            {/* Liquid Surface */}
                            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-white/40 to-transparent opacity-50" />
                        </motion.div>
                    </div>

                    {/* 📝 3. Cinematic Typography */}
                    <div className="text-center space-y-6 px-4 w-full min-h-[120px]">
                        <motion.div layout className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-md ${currentTheme.text}`}>
                            <div className={`w-2 h-2 rounded-full ${currentTheme.bg} animate-pulse`} />
                            <span className="text-xs font-mono uppercase tracking-[0.2em] font-bold">
                                {status === 'listening' ? 'Listening' : status === 'processing' ? 'Thinking' : 'Speaking'}
                            </span>
                        </motion.div>

                        <AnimatePresence mode="wait">
                            <motion.p 
                                key={status === 'listening' ? 'listen-txt' : aiResponse}
                                initial={{ opacity: 0, y: 10, filter: 'blur(10px)' }}
                                animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                                exit={{ opacity: 0, y: -10, filter: 'blur(10px)' }}
                                transition={{ duration: 0.5 }}
                                className={`text-3xl md:text-5xl font-medium leading-tight ${status === 'listening' ? 'text-white/40 font-light' : 'text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-100 to-gray-400'}`}
                            >
                                {status === 'listening' ? "I'm listening..." : aiResponse}
                            </motion.p>
                        </AnimatePresence>
                    </div>

                    {/* ❌ 4. Close Control */}
                    <motion.button 
                        whileHover={{ scale: 1.1, rotate: 90 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => setVoiceMode(false)}
                        className="mt-8 p-4 rounded-full bg-white/5 border border-white/10 text-white/50 hover:bg-red-500/20 hover:border-red-500 hover:text-white transition-all duration-300"
                    >
                        <X size={28} />
                    </motion.button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};
