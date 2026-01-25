'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Mic, Zap, BrainCircuit, Activity } from 'lucide-react';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';

export const AIVoiceOverlay = () => {
    // ... (كل الـ Hooks والمنطق يظل كما هو تماماً بدون تغيير) ...
    const { isVoiceMode, setVoiceMode, addSocketAIMessage } = useAIOrderingStore();
    const [status, setStatus] = useState<'listening' | 'processing' | 'speaking'>('listening');
    const [aiResponse, setAiResponse] = useState('');
    const [audioLevel, setAudioLevel] = useState(1); 

    const wsRef = useRef<WebSocket | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const audioQueueRef = useRef<ArrayBuffer[]>([]);
    const isPlayingRef = useRef(false);
    const animationFrameRef = useRef<number>();
    
    // Theme Colors
    const statusColors = {
        listening: { bg: 'bg-cyan-500', glow: 'shadow-cyan-500/50', text: 'text-cyan-400', hex: '#06b6d4' },
        processing: { bg: 'bg-fuchsia-600', glow: 'shadow-fuchsia-500/50', text: 'text-fuchsia-400', hex: '#c026d3' },
        speaking: { bg: 'bg-emerald-500', glow: 'shadow-emerald-500/50', text: 'text-emerald-400', hex: '#10b981' }
    };
    const currentTheme = statusColors[status];

    // ... (نفس دالة processAudioQueue) ...
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
                console.error("Decode Error", e);
                isPlayingRef.current = false;
                processAudioQueue();
            }
        }
    };

    // ... (نفس دالة useEffect) ...
    useEffect(() => {
        if (!isVoiceMode) return;
        let localStream: MediaStream | null = null;
        const initVoiceSession = async () => {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
                const ctx = new AudioContextClass();
                audioContextRef.current = ctx;
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 256;
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

                ws.onopen = () => console.log('🌐 Socket Connected');
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
                    }
                };
                ws.onclose = () => console.log("🔌 Socket Closed");

                const updateVisuals = () => {
                    if (analyser) {
                        const dataArray = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(dataArray);
                        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                        const scale = 1 + (average / 255) * 1.5; 
                        setAudioLevel(scale);
                    }
                    animationFrameRef.current = requestAnimationFrame(updateVisuals);
                };
                updateVisuals();
            } catch (err) {
                console.error("❌ Failed to initialize voice:", err);
                alert("Please allow microphone access to use Voice Mode.");
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

    // 🔥🔥🔥 التغيير الشامل في التصميم (Matching AIChatOverlay) 🔥🔥🔥
    return (
        <AnimatePresence>
            {/* 1. الخلفية الشفافة (Backdrop) التي تغطي الشاشة بالكامل */}
            <motion.div
                key="voice-overlay-backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-md flex items-center justify-center p-4 md:p-8"
                onClick={() => setVoiceMode(false)} // اغلاق عند الضغط في الخارج
            >
                {/* 2. الكارت الرئيسي (Main Card) - نفس أبعاد وتصميم الشات */}
                <motion.div
                    key="voice-overlay-card"
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    transition={{ duration: 0.3, type: "spring", damping: 25, stiffness: 300 }}
                    onClick={(e) => e.stopPropagation()} // منع الاغلاق عند الضغط داخل الكارت
                    // 👇 هذه الكلاسات تجعله مطابق للصورة (أسود، حواف دائرية كبيرة، بوردر خفيف)
                    className="relative w-full max-w-7xl h-[93vh] flex flex-col bg-[#020617]/90 border border-white/10 rounded-[73px] overflow-hidden shadow-2xl flex flex-col items-center justify-center"
                >
                    {/* 🟢 زر الإغلاق (Top Right) */}
                    <div className="absolute top-6 right-6 z-50">
                        <button 
                            onClick={() => setVoiceMode(false)}
                            className="p-3 rounded-full bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-all border border-white/5"
                        >
                            <X size={24} />
                        </button>
                    </div>

                    {/* 🟢 محتوى الكارت (Center Content) */}
                    <div className="flex flex-col items-center justify-center gap-12 w-full max-w-3xl px-6 relative z-10">
                        
                        {/* الخلفية الجمالية داخل الكارت */}
                        <div className={`absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-${currentTheme.bg.split('-')[1]}-900 via-transparent to-transparent pointer-events-none blur-3xl`} />

                        {/* 🧠 The Living Core (بحجم متوسط يناسب الكارت الكبير) */}
                        <div className="relative flex items-center justify-center scale-125"> 
                            {/* Orbitals */}
                            <motion.div 
                                animate={{ rotate: 360 }}
                                transition={{ repeat: Infinity, duration: 10, ease: "linear" }}
                                className={`absolute w-64 h-64 rounded-full border border-white/5 border-t-${currentTheme.bg.split('-')[1]}-500/30 border-r-transparent`}
                            />
                            <motion.div 
                                animate={{ rotate: -360 }}
                                transition={{ repeat: Infinity, duration: 15, ease: "linear" }}
                                className="absolute w-52 h-52 rounded-full border border-white/5 border-b-white/20 border-l-transparent"
                            />

                            {/* 🔥 REACTIVE ORB */}
                            <motion.div
                                layoutId="core-orb-card"
                                animate={{ 
                                    scale: audioLevel, 
                                    boxShadow: status === 'speaking' 
                                        ? `0 0 ${50 * audioLevel}px ${currentTheme.hex}88` 
                                        : `0 0 30px ${currentTheme.hex}33`
                                }}
                                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                className={`relative w-32 h-32 rounded-full ${currentTheme.bg} flex items-center justify-center backdrop-blur-md bg-opacity-90 z-10 transition-colors duration-300`}
                            >
                                <motion.div key={status} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                    {status === 'listening' && <Mic size={40 * (audioLevel * 0.8)} className="text-white drop-shadow-md" />}
                                    {status === 'processing' && <BrainCircuit size={40} className="text-white drop-shadow-md animate-pulse" />}
                                    {status === 'speaking' && <Activity size={40 * (audioLevel * 0.8)} className="text-white drop-shadow-md" />}
                                </motion.div>
                                <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-white/40 to-transparent opacity-50" />
                            </motion.div>
                        </div>

                        {/* 📝 Typography */}
                        <div className="text-center space-y-6 w-full relative z-20 mt-8">
                            {/* Status Badge */}
                            <motion.div layout className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-md ${currentTheme.text}`}>
                                <div className={`w-2 h-2 rounded-full ${currentTheme.bg} animate-pulse`} />
                                <span className="text-xs font-mono uppercase tracking-[0.2em] font-bold">
                                    {status === 'listening' ? 'Listening' : status === 'processing' ? 'Thinking' : 'Speaking'}
                                </span>
                            </motion.div>

                            {/* AI Text Response */}
                            <div className="min-h-[100px] flex items-center justify-center">
                                <AnimatePresence mode="wait">
                                    <motion.p 
                                        key={status === 'listening' ? 'listen-txt' : aiResponse}
                                        initial={{ opacity: 0, y: 10, filter: 'blur(8px)' }}
                                        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                                        exit={{ opacity: 0, y: -10, filter: 'blur(8px)' }}
                                        transition={{ duration: 0.4 }}
                                        className={`text-3xl md:text-5xl font-medium leading-tight max-w-4xl ${status === 'listening' ? 'text-white/30 font-light' : 'text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-100 to-gray-400'}`}
                                    >
                                        {status === 'listening' ? "I'm listening..." : aiResponse}
                                    </motion.p>
                                </AnimatePresence>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};
