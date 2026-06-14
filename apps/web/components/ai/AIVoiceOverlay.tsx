//** apps/web/components/ai/AIVoiceOverlay.tsx **//

'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useAIOrderingStore } from '../../hooks/useAIOrderingStore';

// --- 🌊 MATH ENGINE: Generative Organic Waves ---
// محرك رياضي لرسم خطوط منحنية طبيعية تتفاعل مع مستوى الصوت
const generateOrganicPath = (points: number, radius: number, audioLevel: number, offset: number) => {
    let d = "";
    const angleStep = (Math.PI * 2) / points;

    for (let i = 0; i <= points; i++) {
        const angle = i * angleStep;
        
        // دمج موجتين بترددات مختلفة لخلق العشوائية المنظمة
        const wave1 = Math.sin(angle * 6 + offset) * (20 * audioLevel); 
        const wave2 = Math.cos(angle * 3 - offset) * (15 * audioLevel); 
        
        const r = radius + wave1 + wave2;
        
        // مركز الـ SVG هو 300,300
        const x = 300 + Math.cos(angle) * r; 
        const y = 300 + Math.sin(angle) * r;

        if (i === 0) d += `M ${x} ${y}`;
        else d += ` L ${x} ${y}`;
    }
    d += " Z"; 
    return d;
};

// --- 🧬 COMPONENT: The Living Hologram (No Icons, Just Energy) ---
const HolographicBlob = ({ audioLevel }: { audioLevel: number }) => {
    const [time, setTime] = useState(0);

    // حلقة تحريك الزمن للموجات
    useEffect(() => {
        let frameId: number;
        const animate = () => {
            setTime(t => t + 0.02); 
            frameId = requestAnimationFrame(animate);
        };
        animate();
        return () => cancelAnimationFrame(frameId);
    }, []);

    // توليد 3 طبقات من الموجات بألوان وتوقيتات مختلفة
    const path1 = useMemo(() => generateOrganicPath(100, 90, audioLevel, time), [audioLevel, time]);
    const path2 = useMemo(() => generateOrganicPath(100, 95, audioLevel * 0.8, time + 2), [audioLevel, time]);
    const path3 = useMemo(() => generateOrganicPath(100, 85, audioLevel * 1.2, time - 1), [audioLevel, time]);

    return (
        <div className="relative w-full h-full flex items-center justify-center">
             <svg width="600" height="600" viewBox="0 0 600 600" className="absolute w-[160%] h-[160%] opacity-90 pointer-events-none">
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
                        <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>

                {/* الطبقة الأساسية (بنفسجي/أزرق) */}
                <motion.path 
                    d={path1} 
                    fill="none" 
                    stroke="url(#grad1)" 
                    strokeWidth="2"
                    filter="url(#glow)"
                />

                {/* الطبقة الثانوية (سماوي) - وضع الشاشة Screen Mode */}
                <motion.path 
                    d={path2} 
                    fill="none" 
                    stroke="url(#grad2)" 
                    strokeWidth="1.5"
                    className="mix-blend-screen"
                />

                {/* الطبقة الثالثة (وردي) - نبض الطاقة */}
                <motion.path 
                    d={path3} 
                    fill="none" 
                    stroke="url(#grad3)" 
                    strokeWidth="1.5"
                    className="mix-blend-screen"
                />
            </svg>
            
            {/* النواة المركزية (طاقة خالصة بدون أيقونة) */}
            <motion.div 
                className="absolute w-24 h-24 rounded-full blur-2xl bg-cyan-500/20"
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
                // 1. طلب المايكروفون أولاً
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                // 2. إعداد الـ AudioContext
                const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
                const ctx = new AudioContextClass();
                audioContextRef.current = ctx;
                
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 256;
                analyser.smoothingTimeConstant = 0.8; // نعومة الحركة
                analyserRef.current = analyser;
                
                const source = ctx.createMediaStreamSource(localStream);
                source.connect(analyser);

                // 3. الاتصال بالسيرفر
                const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ordering/voice-stream?ticket=DEMO`; 
                const ws = new WebSocket(wsUrl);
                ws.binaryType = 'arraybuffer';
                wsRef.current = ws;

                // 4. تسجيل وإرسال الصوت
                const mediaRecorder = new MediaRecorder(localStream, { mimeType: 'audio/webm' });
                mediaRecorderRef.current = mediaRecorder;
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) ws.send(e.data);
                };
                mediaRecorder.start(250); 

                // 5. استقبال الرسائل
                ws.onmessage = async (event) => {
                    if (event.data instanceof ArrayBuffer) {
                        audioQueueRef.current.push(event.data);
                        processAudioQueue();
                    } else if (typeof event.data === 'string') {
                        const data = JSON.parse(event.data);
                        if (data.type === 'text_stream') setAiResponse(data.text);
                        
                        // توجيه الأوامر والمنتجات للـ Store (عشان تظهر في الشات العادي)
                        if (data.type === 'control') {
                            addSocketAIMessage({ id: Date.now(), sender: 'user', contentType: 'text', content: data.payload.query, status: 'sent' });
                        }
                        if (data.type === 'product_carousel' || (data.products && data.products.length > 0)) {
                            addSocketAIMessage(data); 
                        }
                    }
                };

                // 6. حلقة التحديث البصري (Visualization Loop)
                const updateVisuals = () => {
                    if (analyser) {
                        const dataArray = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(dataArray);
                        
                        // التركيز على ترددات الصوت البشري
                        const relevantFreqs = dataArray.slice(10, 80);
                        const average = relevantFreqs.reduce((a, b) => a + b) / relevantFreqs.length;
                        
                        // معادلة لوغاريتمية لحساسية طبيعية
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

        // تنظيف الموارد عند الإغلاق
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
            {/* 1. Backdrop (خلفية ضبابية لكامل الشاشة الداخلية) */}
            <motion.div
                key="voice-backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 z-[100] bg-black/80 backdrop-blur-md"
                onClick={() => setVoiceMode(false)}
            />

            {/* 2. THE FLOATING CARD (متطابق بالمللي مع حاوية الموبايل) */}
            <motion.div
                key="voice-card"
                initial={{ opacity: 0, scale: 0.95 }} 
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                
                // التموضع والتصميم الجديد (absolute لتعبئة الشاشة الأب):
                className="absolute inset-0 z-[101] w-full h-full bg-[#020617]/95 backdrop-blur-3xl flex flex-col"
                
                // منع إغلاق الكارت عند الضغط بداخله
                onClick={(e) => e.stopPropagation()}
            >
                {/* A. Header (Status & Close) متطابق مع الـ AIChatOverlay */}
                <div className="absolute top-0 left-0 w-full px-8 py-6 flex justify-between items-start z-50">
                    <div className="flex items-center gap-2 mt-2">
                        <div className={`w-1.5 h-1.5 rounded-full ${status === 'speaking' ? 'bg-green-500' : 'bg-cyan-500'} animate-pulse`} />
                        <span className="text-[10px] font-mono text-cyan-500/80 tracking-widest uppercase">
                            {status === 'listening' ? 'Listening' : status === 'processing' ? 'Thinking' : 'Speaking'}
                        </span>
                    </div>
                    <button 
                        onClick={() => setVoiceMode(false)}
                        className="p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all duration-300"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* B. The Hologram Container (Energy Core) */}
                <div className="flex-1 relative flex items-center justify-center overflow-hidden">
                    {/* إضاءة خلفية خفيفة */}
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-900/5 to-transparent opacity-40 pointer-events-none" />
                    
                    {/* 🔥 THE ORGANIC HOLOGRAM (NO ICONS) */}
                    <HolographicBlob audioLevel={audioLevel} />
                </div>

                {/* C. Live Transcription Text */}
                <div className="p-8 pb-12 min-h-[140px] flex items-end justify-center text-center z-50">
                    <AnimatePresence mode="wait">
                        <motion.p 
                            key={aiResponse || "default-text"}
                            initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                            exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                            className={`text-2xl font-medium leading-relaxed max-w-[280px] ${
                                status === 'listening' 
                                ? 'text-white/30 italic font-light' 
                                : 'text-transparent bg-clip-text bg-gradient-to-r from-cyan-100 via-white to-purple-200 shadow-lg'
                            }`}
                        >
                            {status === 'listening' ? "I'm listening..." : aiResponse}
                        </motion.p>
                    </AnimatePresence>
                </div>

            </motion.div>
        </AnimatePresence>
    );
};
