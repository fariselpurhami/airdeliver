//** apps/web/components/ai/AIChatOverlay.tsx **//

'use client';

import { useRouter } from 'next/navigation';
import { ProductDetailsCard } from '../products/ProductDetailsCard';
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence, useAnimation } from 'framer-motion';
import { 
    Bot, User, CornerDownRight, ShoppingCart, Cpu, X, 
    ChevronLeft, ChevronRight, Save, ChevronDown, ChevronUp, Trash2, Undo2, AlertCircle, 
    ShoppingBag, ShieldOff, Loader2, Wind, Navigation, Zap, 
    Activity, Signal, BrainCircuit, Lock, Star, Sparkles, Mic, Camera, Image as ImageIcon, MapPin, Clock, Eye, ShieldCheck
} from 'lucide-react';
import { useAIOrderingStore, Message } from '../../hooks/useAIOrderingStore';
import Image from 'next/image';
import useEmblaCarousel from 'embla-carousel-react';
import { loadStripe, StripeElementsOptions, Stripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import AIPaymentForm  from './AIPaymentForm';
import { useSession } from "next-auth/react";
import { useShallow } from 'zustand/react/shallow';
import { AIVoiceOverlay } from './AIVoiceOverlay';
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
const DEFAULT_PLACEHOLDER = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC";

const getAbsoluteImageUrl = (relativePath: string | undefined): string => {
    if (!relativePath) return DEFAULT_PLACEHOLDER;
    if (relativePath.startsWith('http') || relativePath.startsWith('data:')) return relativePath;

    const apiBase = process.env.NEXT_PUBLIC_API_URL
        ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')
        : 'http://localhost:8000';
    
    const cleanPath = relativePath.startsWith('/') ? relativePath : `/${relativePath}`;
    if (cleanPath.includes('default.jpeg')) return DEFAULT_PLACEHOLDER;

    return `${apiBase}${cleanPath}`;
};

const useTextToSpeech = (messages: any[]) => {
    useEffect(() => {
        const lastMessage = messages[messages.length - 1];

        if (lastMessage && lastMessage.sender === 'ai' && lastMessage.contentType !== 'typing') {
            const textToSpeak = typeof lastMessage.content === 'string' ? lastMessage.content :
                                lastMessage.intro_message || "Here are the results."; 

            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(textToSpeak);
            utterance.lang = 'en-US'; 
            utterance.rate = 1.1; 
            utterance.pitch = 1.0;

            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => v.name.includes("Google US English") || v.name.includes("Samantha"));
            if (preferredVoice) utterance.voice = preferredVoice;

            window.speechSynthesis.speak(utterance);
        }
        
        // Cleanup to prevent memory leaks/orphaned audio
        return () => window.speechSynthesis.cancel();
    }, [messages.length]); 
};

const HolographicFlightDeck = React.memo(({ data }: { data: any }) => {
    if (!data) return null;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{ willChange: 'transform, opacity' }}
            className="w-full bg-[#050B14] border border-cyan-500/30 rounded-2xl overflow-hidden relative mt-2 shadow-[0_0_30px_rgba(6,182,212,0.15)] transform-gpu"
        >
            <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.05)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none" />
         
            <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/10 to-transparent w-[50%] skew-x-12 pointer-events-none"
                animate={{ left: ['-100%', '200%'] }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                style={{ willChange: 'left' }}
            />

            <div className="p-5 relative z-10">
                <div className="flex justify-between items-start mb-6 border-b border-white/10 pb-4">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            <span className="text-xs font-bold text-cyan-400 tracking-[0.2em] uppercase">Live Uplink</span>
                        </div>
                        <h3 className="text-lg font-black text-white font-mono">{data.mission_id}</h3>
                    </div>
                    <div className="text-right">
                        <span className="block text-[10px] text-gray-500 uppercase tracking-widest">Drone ID</span>
                        <span className="font-mono text-cyan-200">{data.drone_id}</span>
                    </div>
                </div>

                <div className="h-32 w-full relative mb-6 mx-auto flex items-center justify-center">
                    <svg className="w-full h-full absolute inset-0 overflow-visible">
                        <motion.path
                            d="M 20,60 Q 150,10 280,60"
                            fill="none"
                            stroke="rgba(6, 182, 212, 0.3)"
                            strokeWidth="2"
                            strokeDasharray="5 5"
                        />
                         <motion.path
                            d="M 20,60 Q 150,10 280,60"
                            fill="none"
                            stroke="#06b6d4"
                            strokeWidth="2"
                            initial={{ pathLength: 0 }}
                            animate={{ pathLength: 1 }}
                            transition={{ duration: 2, ease: "easeInOut" }}
                        />
                        <circle cx="20" cy="60" r="4" fill="#06b6d4" />
                        <text x="20" y="80" fill="gray" fontSize="10" textAnchor="middle">HQ</text>
                        <motion.g
                            initial={{ offsetDistance: "0%" }}
                            animate={{ offsetDistance: "100%" }}
                            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                            style={{ offsetPath: 'path("M 20,60 Q 150,10 280,60")' }}
                        >
                            <circle cx="0" cy="0" r="6" fill="#06b6d4" className="drop-shadow-[0_0_10px_rgba(6,182,212,1)]" />
                        </motion.g>
                        <circle cx="280" cy="60" r="4" fill="#ef4444" />
                        <circle cx="280" cy="60" r="8" fill="none" stroke="#ef4444" strokeOpacity="0.5" className="animate-ping" />
                        <text x="280" y="80" fill="gray" fontSize="10" textAnchor="middle">YOU</text>
                    </svg>
                </div>

                <div className="grid grid-cols-3 gap-2">
                    <div className="bg-white/5 rounded-xl p-3 flex flex-col items-center border border-white/5">
                        <Clock size={16} className="text-cyan-400 mb-2" />
                        <span className="text-[10px] text-gray-500 uppercase">ETA</span>
                        <span className="text-sm font-bold text-white">{data.estimated_arrival_mins} min</span>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 flex flex-col items-center border border-white/5">
                        <Navigation size={16} className="text-purple-400 mb-2" />
                        <span className="text-[10px] text-gray-500 uppercase">Dist</span>
                        <span className="text-sm font-bold text-white">{data.distance_km} km</span>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 flex flex-col items-center border border-white/5">
                        <Wind size={16} className="text-green-400 mb-2" />
                        <span className="text-[10px] text-gray-500 uppercase">Weather</span>
                        <span className="text-[10px] font-bold text-white text-center leading-tight">{data.weather_condition}</span>
                    </div>
                </div>
            </div>

            <div className="bg-cyan-950/30 p-2 text-center border-t border-cyan-500/20">
                <span className="text-[10px] font-mono text-cyan-300 animate-pulse">
                    &gt;&gt; SYSTEM STATUS: {data.status} &lt;&lt;
                </span>
            </div>
        </motion.div>
    );
});
HolographicFlightDeck.displayName = 'HolographicFlightDeck';

const DroneTelemetryWidget = React.memo(() => {
    const [stats, setStats] = useState({ speed: 45, alt: 120, bat: 98, stab: 100 });

    useEffect(() => {
        const interval = setInterval(() => {
            setStats(prev => ({
                speed: Math.max(40, Math.min(60, prev.speed + (Math.random() - 0.5) * 5)),
                alt: Math.max(115, Math.min(125, prev.alt + (Math.random() - 0.5) * 2)),
                bat: Math.max(90, prev.bat - 0.01),
                stab: Math.min(100, Math.max(98, prev.stab + (Math.random() - 0.5)))
            }));
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const TelemetryItem = ({ icon: Icon, label, value, unit, color }: any) => (
        <div className="flex flex-col items-start p-2 rounded-xl bg-white/5 border border-white/5 relative overflow-hidden group">
            <div className={`absolute top-0 right-0 p-1.5 opacity-20 group-hover:opacity-100 transition-opacity duration-500 ${color}`}>
                <Icon size={14} />
            </div>
            <span className="text-[9px] text-gray-500 uppercase tracking-wider font-bold mb-0.5">{label}</span>
            <div className="flex items-baseline gap-0.5">
                <span className="text-sm font-mono font-bold text-white tracking-tight">{value.toFixed(1)}</span>
                <span className="text-[8px] text-gray-400">{unit}</span>
            </div>
            <div className="w-full h-0.5 bg-gray-800 mt-1.5 rounded-full overflow-hidden">
                <motion.div 
                    className={`h-full ${color.replace('text-', 'bg-')}`} 
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, (value / (label === 'PWR' ? 100 : 60)) * 100)}%` }}
                    transition={{ duration: 0.5 }}
                    style={{ willChange: 'width' }}
                />
            </div>
        </div>
    );

    return (
        <div className="grid grid-cols-4 gap-2 w-full mt-2">
            <TelemetryItem icon={Wind} label="SPD" value={stats.speed} unit="km/h" color="text-cyan-400" />
            <TelemetryItem icon={Navigation} label="ALT" value={stats.alt} unit="m" color="text-purple-400" />
            <TelemetryItem icon={Zap} label="PWR" value={stats.bat} unit="%" color="text-green-400" />
            <TelemetryItem icon={Activity} label="STAB" value={stats.stab} unit="%" color="text-blue-400" />
        </div>
    );
});
DroneTelemetryWidget.displayName = 'DroneTelemetryWidget';

const CarouselProductCard = React.memo(({ product, onSelect, onViewDetails, totalItems }: { product: any, onSelect: (product: any, elementId: string) => void, onViewDetails: (product: any) => void, totalItems: number }) => {
    const slideWidthClass = "flex-none w-[280px] snap-center";
    const rawImagePath = product.image_url || product.image;
    const imageUrl = useMemo(() => getAbsoluteImageUrl(rawImagePath), [rawImagePath]);
    const elementId = `product-carousel-img-${product.id}`;

    const handleSelect = useCallback(() => {
        onSelect({ ...product, image: rawImagePath }, elementId);
    }, [product, rawImagePath, elementId, onSelect]);

    return (
        <div className={`embla__slide ${slideWidthClass} px-2 py-4`}>
            <motion.div
                className="flex flex-col p-0 bg-gradient-to-br from-[#0F172A] to-[#020617] backdrop-blur-3xl rounded-[32px] border border-white/10 h-full text-left shadow-2xl relative group overflow-hidden transform-gpu"
                whileHover={{ 
                    scale: 1.02,
                    border: "1px solid rgba(6, 182, 212, 0.5)",
                    boxShadow: "0 20px 50px -12px rgba(6, 182, 212, 0.25)" 
                }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 200, damping: 25 }}
                style={{ willChange: 'transform, opacity' }}
            >
                <motion.button
                    onClick={(e) => { e.stopPropagation(); onViewDetails(product); }}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    whileHover={{ scale: 1.1, backgroundColor: "rgba(6, 182, 212, 1)", color: "#000" }}
                    className="absolute top-4 right-2 z-50 p-2.5 rounded-full bg-black/40 border border-white/10 text-white backdrop-blur-md opacity-60 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-500 shadow-[0_0_20px_rgba(0,0,0,0.5)] transform-gpu"
                    title="Inspect Hologram"
                >
                    <Eye size={18} strokeWidth={2.5} />
                </motion.button>
                
                <div className="relative h-48 w-full flex items-center justify-center bg-gradient-to-b from-white/5 to-transparent p-4 overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                    <Image
                        id={elementId}
                        src={imageUrl}
                        alt={product.name}
                        width={250}
                        height={250}
                        loading="lazy"
                        decoding="async"
                        className="w-auto h-full object-contain drop-shadow-[0_10px_20px_rgba(0,0,0,0.5)] group-hover:scale-110 group-hover:-rotate-2 transition-transform duration-500 cubic-bezier(0.34, 1.56, 0.64, 1) transform-gpu"
                    />
                </div>

                <div className="p-5 flex flex-col flex-grow relative z-10">
                  
                    <div className="flex justify-between items-start mb-2">
                         <h4 className="text-lg font-medium text-white leading-tight tracking-[-0.01em] break-words" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>{product.name}</h4>
                    </div>
                   
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        {product.rating ? (
                          <div className="flex items-center gap-1 text-amber-300">
                            <Star className="h-3.5 w-3.5 shrink-0 fill-current" />
                            <span className="text-[11px] font-medium tracking-[0.08em] text-white/60 sm:text-xs">
                              ({product.rating}/5.0)
                           </span>
                         </div>
                       ) : null}

                       <span className="text-[10px] font-mono text-white/45 sm:text-[11px]">
                         ID: {product.id}
                       </span>
                     </div>

                     <div className="shrink-0 text-[13px] font-normal leading-none text-white/95 tabular-nums sm:text-sm">
                       ${(Number(product.price) || 0).toFixed(2)}
                     </div>
                   </div>
             
                   {product.stock_level ? (

                    <div className="mt-4">
                      <div className="inline-flex items-center rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-200 sm:text-sm">
                    {product.stock_level}
                 </div>
               </div>
             ) : null}

                    <div className="mt-auto pt-4 border-t border-white/5">
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.96 }}
                            onClick={handleSelect}
                            className="w-full relative overflow-hidden rounded-full bg-white text-black font-medium px-4 py-3 flex items-center justify-center gap-2 group/btn shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all duration-300 transform-gpu"
                        >
                            <span className="relative z-10 flex items-center gap-2 text-[11px] font-medium tracking-[0.14em] uppercase">
                                <ShoppingBag size={15} strokeWidth={1.75} absoluteStrokeWidth />
                                Add To Cart
                            </span>
                            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300 transform-gpu" />
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
});
CarouselProductCard.displayName = 'CarouselProductCard';

const ProductCarousel = React.memo(({ products, onViewDetails, onSelect }: { products: any[], onSelect: (product: any, elementId: string) => void, onViewDetails: (product: any) => void }) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'start', containScroll: 'trimSnaps', dragFree: false });
    
    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);
    
    const canScroll = products.length > 1;

    return (
        <div className="relative my-6 px-0 group/carousel w-full overflow-visible">
            <div className="overflow-hidden p-2 -mx-4" ref={emblaRef}>
                <div className="flex gap-2 pl-4 pr-8 snap-x snap-mandatory">
                    {products.map((p, i) => (
                        <CarouselProductCard 
                            key={p.id || i} 
                            product={p} 
                            onSelect={onSelect} 
                            onViewDetails={onViewDetails} 
                            totalItems={products.length} 
                        />
                    ))}
                </div>
            </div>
            {canScroll && (
                <>
                    <button onClick={scrollPrev} className="hidden sm:flex absolute top-1/2 -translate-y-1/2 left-0 p-3 bg-black/50 backdrop-blur-xl border border-white/10 rounded-full z-20 hover:bg-cyan-500 hover:text-black hover:border-cyan-400 transition-all opacity-0 group-hover/carousel:opacity-100 -translate-x-2 group-hover/carousel:translate-x-2 duration-300 shadow-xl transform-gpu"><ChevronLeft size={20}/></button>
                    <button onClick={scrollNext} className="hidden sm:flex absolute top-1/2 -translate-y-1/2 right-0 p-3 bg-black/50 backdrop-blur-xl border border-white/10 rounded-full z-20 hover:bg-cyan-500 hover:text-black hover:border-cyan-400 transition-all opacity-0 group-hover/carousel:opacity-100 translate-x-2 group-hover/carousel:translate-x-0 duration-300 shadow-xl transform-gpu"><ChevronRight size={20}/></button>
                </>
            )}
        </div>
    );
});
ProductCarousel.displayName = 'ProductCarousel';

const AIReasoning = React.memo(({ text }: { text: string }) => (
    <motion.div
        initial={{ opacity: 0, height: 0, scale: 0.95 }}
        animate={{ opacity: 1, height: 'auto', scale: 1 }}
        style={{ willChange: 'transform, opacity, height' }}
        className="flex items-start gap-3 p-4 mt-4 bg-[#0A1116] border border-cyan-900/50 rounded-2xl max-w-lg relative overflow-hidden transform-gpu"
    >
        <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500" />
        <div className="absolute -right-4 -top-4 w-16 h-16 bg-cyan-500/10 blur-xl rounded-full pointer-events-none" />
        <div>
            <span className="block text-[10px] font-black text-cyan-300 tracking-widest mb-1">airdeliverOS</span>
            <p className="text-sm text-cyan-100/80 font-sans leading-relaxed">{text}</p>
        </div>
    </motion.div>
));
AIReasoning.displayName = 'AIReasoning';

const ExpandableUserMessage = React.memo(({ text }: { text: string }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // تحديد ما إذا كان النص طويلاً ويحتاج إلى طي
    const needsExpansion = text.length > 250 || text.split('\n').length > 4;

    if (!needsExpansion) {
        return <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-normal">{text}</p>;
    }

    return (
        <div className="flex flex-col w-full">
            <motion.div
                initial={false}
                animate={{ height: isExpanded ? 'auto' : '71px' }} // 90px تكفي لإظهار حوالي 3 إلى 4 سطور
                className="overflow-hidden relative transform-gpu"
                style={{ willChange: 'height' }}
            >
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-normal">
                    {text}
                </p>
               
            </motion.div>

            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-0.5 flex items-center justify-center p-1 hover:bg-white/10 rounded-full transition-colors self-end text-cyan-400 group"
                title={isExpanded ? "إخفاء التفاصيل" : "عرض المزيد"}
            >
                {isExpanded ? (
                    <ChevronUp size={18} className="group-hover:-translate-y-0.5 transition-transform" />
                ) : (
                    <ChevronDown size={18} className="group-hover:translate-y-0.5 transition-transform animate-bounce" />
                )}
            </button>
        </div>
    );
});
ExpandableUserMessage.displayName = 'ExpandableUserMessage';

const ChatMessage = React.memo(({ message, onSend, onViewDetails, isActiveAction, onNavigateToAuth, onProductSelect, onConfirmOrder, onClearCart, onRestore, onSave, onCancel }: any) => {
    const isAI = message.sender === 'ai';

    const renderContent = () => {
        switch (message.contentType) {
            case 'image_user_upload':
                const hasCaption = message.content && message.content.trim().length > 0 && 
                                  !message.content.includes("Analyzing") && 
                                  !message.content.includes("Processing");
                const hasImg = !!message.imageUrl;

                return (
                    <div className="flex flex-col w-full min-w-[300px] max-w-[350px]">
                        {hasImg && (
                            <div className={`relative w-full aspect-[4/3] flex-none overflow-hidden shadow-2xl ${hasCaption ? 'rounded-t-[32px] border-b-0' : 'rounded-[32px]'}`}>
                                <Image
                                    src={message.imageUrl}
                                    alt="Uploaded"
                                    fill
                                    loading="lazy"
                                    decoding="async"
                                    className="object-cover" 
                                />
                            </div>
                        )}
                        {hasCaption && (
                             <div className="bg-zinc-900/95 backdrop-blur-xl px-5 py-4 rounded-b-[32px] border border-white/10 text-gray-100 text-[15px] leading-relaxed shadow-lg relative -mt-[1px]">
                                {message.content}
                             </div>
                        )}
                    </div>
                );
            case 'text':
            case 'error':
            case 'info':
            case 'success_text':
                
                if (!isAI && message.contentType === 'text') {
                    return <ExpandableUserMessage text={message.content} />;
                }
                return (
                 // 👇 نقلنا مسافات الأسطر (space-y-3) للـ div الأب هنا
                    <div className={`text-[13px] leading-normal text-white/90 font-normal break-words w-full space-y-2 ${message.contentType === 'error' ? 'bg-red-950/20 p-2 rounded' : ''}`}>
                        <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                // تم إزالة className من هنا نهائياً بناءً على تحديث المكتبة الجديد
                            components={{
                                p: ({ node, ...props }) => (
                                    <p className="mb-3 last:mb-0 text-left whitespace-pre-wrap leading-normal" {...props} />
                                ),
                                strong: ({ node, ...props }) => (
                                    <strong className="font-bold text-white" {...props} />
                                ),
                                ul: ({ node, ...props }) => (
                                    <ul className="list-disc list-inside space-y-1.5 mb-3 mt-1.5 last:mb-0" {...props} />
                                ),
                                li: ({ node, ...props }) => (
                                    <li className="pl-0 leading-normal" {...props} />
                                ),
                            }}
                        >
                            {message.content}
                        </ReactMarkdown>
                    </div>
                );
            case 'FLIGHT_MANIFEST':
                return (
                    <div className="w-full -ml-2">
                         <p className="whitespace-pre-line mb-2 text-sm px-2 leading-relaxed text-white font-medium">
                             {message.content}
                         </p>
                         <HolographicFlightDeck data={message.flight_data} />
                    </div>
                );
            case 'confirmation_prompt':
                if (!isActiveAction) return null;
                return (
                    <div>
                        <p className="whitespace-pre-wrap mb-4 text-sm leading-relaxed text-white/90 font-normal">{message.content}</p>
                        {isActiveAction && (
                            <div className="flex flex-wrap gap-3">
                                {(message.options as string[])?.map((option: string) => {
                                // تحديد إذا كان هذا هو زر التأكيد لتمييزه
                                    const isConfirm = option === 'Confirm Order';
                                
                                // التصميم الافتراضي لباقي الأزرار
                                    let buttonStyle = "bg-white/5 text-cyan-200 border-white/10 hover:bg-cyan-500 hover:text-black";
                                
                                // التصميم الفخم المخصص لزر Confirm Order
                                    if (isConfirm) {
                                        buttonStyle = "bg-gradient-to-r from-cyan-400 to-cyan-500 text-[#020617] border-transparent shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_35px_rgba(6,182,212,0.6)]";
                                    } 
                                    else if (option === 'Switch to PayPal') {
                                        buttonStyle = "bg-[#003087] text-white border-transparent hover:bg-[#003087]/80"; 
                                    }
                                    else if (option === 'Retry Payment') {
                                        buttonStyle = "bg-green-600 text-white hover:bg-green-500 border-transparent shadow-[0_0_15px_rgba(22,163,74,0.3)]";
                                    }

                                    return (
                                        <motion.button
                                            key={option}
                                            whileHover={{ scale: 1.05 }}
                                            whileTap={{ scale: 0.95 }}
                                            onClick={() => {
                                                if (option === 'Confirm Order') onConfirmOrder(); 
                                                else if (option === 'Clear Cart') onClearCart();
                                                else if (option === 'Sign In') onNavigateToAuth('SIGNIN');
                                                else if (option === 'Sign Up') onNavigateToAuth('SIGNUP');
                                                else if (option === 'Switch to PayPal') onSend("I want to use PayPal");
                                                else if (option === 'Retry Payment') onConfirmOrder(); 
                                                else if (option === 'Save for Later') onSave();
                                                else onSend(option);
                                            }}
                                        // جعلنا الزر rounded-full وضفنا flex لترتيب الأيقونة مع النص
                                            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-full border transition-all duration-300 transform-gpu ${buttonStyle}`}
                                        >
                                        {/* إضافة أيقونة جمالية لزر التأكيد فقط */}
                                            {isConfirm && <Zap size={16} strokeWidth={2.5} />}
                                        
                                        {/* تنسيق الخط ليصبح أكثر أناقة */}
                                            <span className={`text-xs uppercase tracking-[0.15em] ${isConfirm ? 'font-black' : 'font-bold'}`}>
                                                {option}
                                            </span>
                                        </motion.button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                );
            case 'product_carousel':
            case 'proactive_suggestion':
                return (
                    <div className="w-full -ml-2">
                        <p className="whitespace-pre-wrap mb-2 text-sm px-2 leading-relaxed text-white/90 font-normal">{message.content}</p>
                        <ProductCarousel products={message.products || []} onSelect={onProductSelect} onViewDetails={onViewDetails} />
                        {(message.reason || message.ai_notes) && (
                            <div className="px-2">
                                <AIReasoning text={message.reason || message.ai_notes} />
                            </div>
                        )}
                    </div>
                );
            case 'recovery_prompt':
               if (!isActiveAction) return null;
               return (
                  <div className="flex items-center justify-center w-full py-4">
                     <motion.div 
                         initial={{ scale: 0.9, opacity: 0, y: 10 }}
                         animate={{ scale: 1, opacity: 1, y: 0 }}
                         style={{ willChange: 'transform, opacity' }}
                         className="flex items-center gap-2 p-2 bg-white/[0.04] backdrop-blur-3xl border border-white/10 rounded-[55px] shadow-2xl transform-gpu"
                     >
                         {[
                             { icon: Undo2, label: "UNDO", action: onRestore, textColor: "text-white", hoverBg: "hover:bg-cyan-500/10" },
                             { icon: Save, label: "SAVE", action: onSave, textColor: "text-white", hoverBg: "hover:bg-purple-500/10" },
                             { icon: X, label: "CANCEL", action: onCancel, textColor: "text-white", hoverBg: "hover:bg-red-500/10" }
                         ].map((btn, idx) => (
                             <motion.button 
                                 key={idx}
                                 whileHover={{ scale: 1.05 }}
                                 whileTap={{ scale: 0.95 }}
                                 onClick={btn.action} 
                                 className={`flex flex-col items-center justify-center min-w-[60px] h-[60px] gap-2 rounded-full transition-all duration-300 transform-gpu ${btn.hoverBg} group`}
                             >
                                 <btn.icon size={17} strokeWidth={2.5} className="text-white opacity-80 group-hover:opacity-100" />
                                 <span className={`text-[8px] font-black uppercase tracking-widest ${btn.textColor}`}>
                                     {btn.label}
                                 </span>
                             </motion.button>
                         ))}
                      </motion.div>
                  </div>
                );
            default: return null;
        }
    };

    const contentNode = renderContent();

    if (['cart_preview', 'typing', 'payment_intent', 'ORDER_CANCELLED', 'system'].includes(message.contentType)) return null;
    if (!contentNode) return null;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            style={{ willChange: 'transform, opacity' }}
            className={`flex items-end gap-2 w-full mb-4 transform-gpu ${isAI ? 'justify-start' : 'justify-end'}`}
        >
            <div className={`w-fit max-w-[98%] px-4 py-3 ${
                isAI 
                    ? 'rounded-[32px] rounded-bl-none bg-[#050B14]/80 backdrop-blur-xl border border-white/5 text-gray-100 shadow-xl shadow-black/20 transform-gpu' 
                    : 'rounded-[32px] rounded-br-none bg-white/5 border border-white/10 text-white backdrop-blur-sm transform-gpu'
            }`}>
                {contentNode}
            </div>
        </motion.div>
    );
}, (prevProps, nextProps) => {
    // Explicit prop comparison for maximum list rendering performance
    return prevProps.message.id === nextProps.message.id && 
           prevProps.message.content === nextProps.message.content;
           prevProps.isActiveAction === nextProps.isActiveAction;
});
ChatMessage.displayName = 'ChatMessage';

const AIChatSidebar = React.memo(({ messages, glowingProductId, onRemoveItem, isMobileOpen, onCloseMobile }: {
    messages: Message[],
    glowingProductId: number | null,
    onRemoveItem: (productId: number) => void,
    isMobileOpen: boolean,
    onCloseMobile: () => void
}) => {
    const cart = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
        return lastCartMessage ? lastCartMessage.content : { items: [], total: 0 };
    }, [messages]);

    return (
        <>
            <AnimatePresence>
                {isMobileOpen && (
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onCloseMobile}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm z-[100] transform-gpu"
                        style={{ willChange: 'opacity' }}
                    />
                )}
            </AnimatePresence>

            <div className={`
                absolute top-0 right-0 bottom-0 z-[110] w-[calc(100%+1px)] md:w-[460px] transform transition-transform duration-500 cubic-bezier(0.34, 1.56, 0.64, 1)
                backdrop-blur-3xl bg-[#050B14]/95 border-l-0 md:border-l border-white/10 flex-col overflow-hidden will-change-transform
                ${isMobileOpen ? 'translate-x-0' : 'translate-x-full'}
                ${!isMobileOpen ? 'hidden' : 'flex'}
            `}>
                <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.05] pointer-events-none" />
                
                <div className="flex justify-between items-center p-5 border-b border-white/10 bg-black/20">
                    <span className="text-sm font-bold uppercase text-white tracking-widest flex items-center gap-2">
                        <ShoppingBag size={16} strokeWidth={2.5} />
                    </span>
                    <button onClick={onCloseMobile} className="p-2 rounded-full bg-white/5 text-white hover:bg-red-500/80 transition-colors">
                        <X size={18} />
                    </button>
                </div>

                <div className="flex-grow p-6 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-cyan-500/20 scrollbar-track-transparent relative z-10">
                    <div className="space-y-4 flex-grow">
                        <AnimatePresence>
                            {cart.items.length === 0 ? (
                                <motion.div 
                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                    className="flex flex-col items-center justify-center h-48 text-gray-600 gap-3 border border-dashed border-white/5 rounded-3xl bg-white/[0.02]"
                                >
                                    <ShoppingCart size={32} className="opacity-30" />
                                    <p className="text-xs uppercase tracking-widest font-mono">Empty | Cart</p>
                                </motion.div>
                            ) : cart.items.map((item: any, index: number) => (
                                <motion.div
                                    key={item.product_id || index}
                                    layout
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{
                                        opacity: 1,
                                        x: 0,
                                        backgroundColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.15)" : "rgba(255, 255, 255, 0.03)",
                                        borderColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.5)" : "rgba(255, 255, 255, 0.05)",
                                    }}
                                    exit={{ opacity: 0, x: 20 }}
                                    style={{ willChange: 'transform, opacity, background-color, border-color' }}
                                    className="flex justify-between items-start p-3 rounded-2xl border transition-colors group relative overflow-hidden transform-gpu"
                                >
                                    {item.product_id === glowingProductId && (
                                        <motion.div layoutId="glow" className="absolute inset-0 bg-cyan-500/5 pointer-events-none" transition={{ duration: 0.3 }} />
                                    )}
                                    <div className="flex items-center gap-3 flex-1 min-w-0 relative z-10">
                                        <div className="w-12 h-12 rounded-xl bg-black/40 border border-white/10 flex items-center justify-center overflow-hidden">
                                            <ShoppingBag size={16} className="text-gray-500" />
                                        </div>
                                        <div className="flex flex-col min-w-0">
                                            <span className="text-gray-100 text-sm font-bold leading-snug tracking-tight break-words" title={item.name}>
                                                {item.name}
                                            </span>
                                            <span className="text-[10px] text-gray-400 font-mono mt-0.5">QTY: {item.quantity}</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end gap-1 relative z-10">
                                        <span className="font-bold text-cyan-300 font-mono text-sm">
                                            ${(item.price * item.quantity).toFixed(2)}
                                        </span>
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation(); // 🛡️ بيمنع تداخل اللمس مع العناصر اللي خلف الزرار على الموبايل
                                                onRemoveItem(item.product_id || item.id); // 🛡️ حماية مزدوجة لو الـ ID جاي بأي صيغة
                                            }}
    // 🛡️ نقلنا الـ hover للديسكتوب فقط باستخدام md: وأضفنا active: للموبايل علشان يستجيب بلمسة واحدة
                                            className="p-1.5 rounded-lg bg-red-500/10 text-red-400 active:bg-red-500 active:text-white md:hover:bg-red-500 md:hover:text-white transition-all duration-200"
                                            title="Jettison Item"
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </div>

                <div className="flex-shrink-0 p-6 border-t border-white/10 bg-[#050B14] space-y-6 relative z-20">
                    <div>
                        <h3 className="text-[10px] font-bold text-gray-500 tracking-widest mb-3 flex items-center gap-2">
                            <Signal size={12} /> airdeliver X
                        </h3>
                        <DroneTelemetryWidget />
                    </div>
                    <div className="w-full h-[1px] bg-white/10" />
                    <div className="flex justify-between items-end">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Total</span>
                            <span className="text-[10px] text-gray-600">Including Service Fees</span>
                        </div>
                        <span className="text-3xl font-bold text-white font-mono tracking-tighter">
                            ${Number(cart.total || 0).toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>
        </>
    );
});
AIChatSidebar.displayName = 'AIChatSidebar';

const ChatInput = React.memo(
  ({ onSend, onSendImage, isTyping, isProcessing }: { 
      onSend: (text: string) => void; 
      onSendImage: (base64: string, raw: string, caption?: string) => void;
      isTyping: boolean; 
      isProcessing: boolean 
  }) => {
    const [value, setValue] = useState('');
    const [pendingImage, setPendingImage] = useState<{ url: string; base64: string } | null>(null);
    const [isListening, setIsListening] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Optimized auto-resize pushing heavy DOM reads to next frame to avoid main thread blocking
    const handleAutoResize = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setValue(e.target.value);
        requestAnimationFrame(() => {
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
                textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
            }
        });
    }, []);

    const toggleVoice = useCallback(() => {
        if (!('webkitSpeechRecognition' in window)) {
            alert("Voice module not supported in this browser sector.");
            return;
        }
        
        if (isListening) {
            setIsListening(false);
            return;
        }

        const recognition = new (window as any).webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => setIsListening(true);
        recognition.onend = () => setIsListening(false);
        recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            setValue(transcript);
        };
        recognition.start();
    }, [isListening]);

    const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onloadend = () => {
            const fullDataUrl = reader.result as string;
            const base64Raw = fullDataUrl.split(',')[1];
            setPendingImage({ url: fullDataUrl, base64: base64Raw });
        };
        reader.readAsDataURL(file);
        e.target.value = ''; 
    }, []);

    const handleTriggerSend = useCallback(() => {
        if (isTyping || isProcessing || (!value.trim() && !pendingImage)) return;
        if (pendingImage) {
            onSendImage(pendingImage.url, pendingImage.base64, value);
            setPendingImage(null); 
            setValue('');
        } else if (value.trim()) {
            onSend(value);
            setValue('');
        }
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = '56px'; 
        }
    }, [isTyping, isProcessing, pendingImage, value, onSendImage, onSend]);

    const isInputLocked = isTyping || isProcessing;
    const isSendButtonDisabled = isInputLocked || (!value.trim() && !pendingImage);
    const hasInput = value.length > 0 || pendingImage !== null;
    return (
      <div className="p-6 border-t border-white/5 flex-shrink-0 bg-[#020617]/50 backdrop-blur-md relative z-20">
         <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={handleImageSelect} />

        <AnimatePresence>
            {pendingImage && (
                <motion.div 
                    initial={{ opacity: 0, y: 10, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                    exit={{ opacity: 0, y: 10, height: 0 }}
                    style={{ willChange: 'transform, opacity, height' }}
                    className="absolute -top-24 left-6 z-30 transform-gpu"
                >
                    <div className="relative group">
                        <div className="w-20 h-20 rounded-xl overflow-hidden border border-cyan-500/50 shadow-lg bg-black/50 backdrop-blur-md">
                            <Image src={pendingImage.url} alt="Preview" width={80} height={80} className="object-cover w-full h-full" />
                        </div>
                        <button 
                            onClick={() => setPendingImage(null)}
                            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 shadow-md hover:scale-110 transition-transform"
                        >
                            <X size={12} />
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>

        <div className="relative group max-w-4xl mx-auto flex items-center gap-2">
          <AnimatePresence>
              {!hasInput && (
                  <motion.div
                      initial={{ width: 0, opacity: 0, scale: 0.8 }}
                      animate={{ width: 'auto', opacity: 1, scale: 1 }}
                      exit={{ width: 0, opacity: 0, scale: 0.5 }}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                      className="flex items-center gap-2 overflow-hidden flex-shrink-0 origin-left"
                      style={{ willChange: 'width, opacity, transform' }}
                  >
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="p-3 rounded-full bg-white/5 text-white hover:bg-cyan-500/20 transition-all border border-white/5 hover:border-cyan-500/50"
                      title="Upload Visual Data"
                    >
                      <Camera size={20} />
                    </button>

                    <button
                      type="button"
                      onClick={() => useAIOrderingStore.getState().setVoiceMode(true)}
                      className="p-3 rounded-full bg-white/5 text-white hover:bg-cyan-500/20 transition-all border border-white/5 hover:border-cyan-500/50 group"
                      title="Talk to order with air"
                    >
                      <Mic size={20} className="group-hover:scale-110 transition-transform" />
                    </button>
                </motion.div>
             )}
         </AnimatePresence>
         <div className="relative flex-grow min-w-0">
           <textarea
               ref={textareaRef}
               value={value}
               onChange={handleAutoResize}
               rows={1}
               onFocus={() => {
                   // تأخير 300 ملي ثانية لانتظار أنيميشن الكيبورد حتى يكتمل
                   setTimeout(() => {
                       if (textareaRef.current) {
                           // إجبار المتصفح على رفع الشاشة لتوضيح مربع الكتابة
                           textareaRef.current.scrollIntoView({
                               behavior: 'smooth',
                               block: 'center'
                           });
                       }
                   }, 300);
               }}
               onKeyDown={(e) => {
                   if (e.key === 'Enter' && !e.shiftKey) {
                       e.preventDefault(); 
                       if (!isSendButtonDisabled) handleTriggerSend();
                   }
               }}
               placeholder={isListening ? 'Listening...' : isInputLocked ? 'Thinking...' : 'Ask order with air...'}
               disabled={isInputLocked}
               className="w-full bg-gray-800 border border-gray-800 rounded-[28px] py-[14px] pr-16 pl-6 text-gray-100 placeholder-gray-400 focus:bg-gray-800  placeholder:whitespace-nowrap focus:border-none focus:outline-none transition-all duration-300 font-medium shadow-lg resize-none overflow-hidden no-scrollbar min-h-[52px] leading-relaxed"
               style={{ overflowY: textareaRef.current && textareaRef.current.scrollHeight > 150 ? 'auto' : 'hidden' }}
           />
            <button
                disabled={isSendButtonDisabled}
                onClick={handleTriggerSend}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full  bg-cyan-600 hover:bg-cyan-500 disabled:bg-transparent disabled:text-gray-500 text-white transition-all"
            >
                {isInputLocked ? <Loader2 size={18} className="animate-spin" /> : <CornerDownRight size={18} />}
            </button>
          </div>
        </div>
      </div>
    );
});
ChatInput.displayName = 'ChatInput';

const FlyToCartAnimator = React.memo(() => {
  const flyQueue = useAIOrderingStore(useShallow(state => state.flyQueue)); //
  const removeFlyItem = useAIOrderingStore(state => state.removeFlyItem); //[cite: 1]

  return (
    <AnimatePresence>
      {flyQueue.map((item) => { //[cite: 1]
          const startEl = document.getElementById(item.startElementId); //[cite: 1]
          const endEl = document.getElementById('order-summary-cart-icon'); //[cite: 1]
          
          if (!startEl) return null; //[cite: 1]
          const startRect = startEl.getBoundingClientRect(); //[cite: 1]
          const endPos = endEl ? endEl.getBoundingClientRect() : { top: 50, left: window.innerWidth - 50 }; //[cite: 1]

          const imageSource = getAbsoluteImageUrl(item.image); //[cite: 1]
          
          // 🚀 تحسين الأداء: حساب نسبة التصغير بدلاً من تحريك الأبعاد الثابتة
          const TARGET_SIZE = 10;
          const targetScale = TARGET_SIZE / Math.max(startRect.width, 1);
          
          // 🎢 إضافة الإثارة: حساب نقطة المنتصف لعمل حركة على شكل قوس (Arc)
          const midY = Math.min(startRect.top, endPos.top) - 80; // يقفز لأعلى بمقدار 80 بكسل قبل النزول للسلة

          return (
            <motion.div
              key={item.animationId} //[cite: 1]
              className="fixed z-[9999] rounded-full overflow-hidden border-2 border-cyan-400 shadow-[0_0_30px_rgba(6,182,212,0.8)] transform-gpu" //[cite: 1]
              style={{ 
                  position: 'fixed', //[cite: 1]
                  top: 0, //[cite: 1]
                  left: 0, //[cite: 1]
                  pointerEvents: 'none', //[cite: 1]
                  // 🚀 تثبيت العرض والطول لمنع إعادة حساب التخطيط (Layout Thrashing)
                  width: startRect.width, 
                  height: startRect.height, 
                  // 🚀 إزالة width و height من willChange ليكون الأداء خفيفاً جداً
                  willChange: 'transform, opacity' 
              }}
              initial={{ 
                  x: startRect.left, //[cite: 1]
                  y: startRect.top, //[cite: 1]
                  opacity: 1, //[cite: 1]
                  scale: 0.6, //[cite: 1]
                  rotate: 0
              }}
              animate={{ 
                  // 🎢 استخدام Keyframes لصناعة القوس والتأثير البصري
                  x: [startRect.left, endPos.left - 10], 
                  y: [startRect.top, midY, endPos.top - 10], 
                  opacity: [1, 1, 0], // يظل ظاهراً حتى يصل للسلة ثم يختفي
                  scale: [0.6, 0.75, targetScale], // تأثير "Pop": يكبر قليلاً عند الضغط ثم يصغر وهو في طريقه للسلة
                  rotate: [0, -20, 360] // يميل قليلاً للخلف ثم يدور بسرعة
              }}
              transition={{ 
                  duration: 0.7, // توقيت مثالي لا هو بطيء ولا سريع مزعج
                  ease: "easeInOut",
                  times: [0, 0.3, 1] // توقيت التحكم في مسار الحركة (Keyframes)
              }}
              onAnimationComplete={() => removeFlyItem(item.animationId)} //[cite: 1]
            >
              <Image src={imageSource} alt="product" width={100} height={100} priority className="w-full h-full object-cover" /> {/*[cite: 1] */}
            </motion.div>
          );
      })}
    </AnimatePresence>
  );
});
FlyToCartAnimator.displayName = 'FlyToCartAnimator'; //[cite: 1]

const PaymentFatalError = React.memo(({ keyMissing }: { keyMissing: boolean }) => (
    <div className="w-full h-full flex flex-col items-center justify-center p-10 text-center bg-black/40 backdrop-blur-xl rounded-[30px] border border-red-500/20">
        <div className="p-4 bg-red-500/10 rounded-full mb-4 animate-pulse">
            <ShieldOff size={48} className="text-red-400" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2 tracking-wide font-mono">SECURE GATEWAY OFFLINE</h3>
        <p className="text-gray-400 max-w-md text-sm leading-relaxed">
            {keyMissing 
                ? "Configuration Error: Stripe Public Key missing. System cannot initiate secure tunnel." 
                : "Critical Protocol Failure: Unable to load payment processor module."}
        </p>
    </div>
));
PaymentFatalError.displayName = 'PaymentFatalError';

// ============================================================================
// --- MAIN COMPONENT ---
// ============================================================================

export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    const router = useRouter();   
    const [detailProduct, setDetailProduct] = useState<any | null>(null);
    const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
    
    useBodyScrollLock({ locked: isOpen });
    const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '';
    const stripePromise: Promise<Stripe | null> | null = useMemo(() => {
        return STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : null;
    }, [STRIPE_PUBLISHABLE_KEY]);
    
    const [stripeObj, setStripeObj] = useState<Stripe | null>(null);
    const [isStripeError, setIsStripeError] = useState(false);
    const [isAnimationComplete, setIsAnimationComplete] = useState(false);

    useEffect(() => {
        if (stripePromise) {
            stripePromise
                .then(stripe => { setStripeObj(stripe); setIsStripeError(false); })
                .catch(err => { console.error("Stripe Load Error:", err); setIsStripeError(true); });
        } else {
            setIsStripeError(true);
        }
    }, [stripePromise]);
    
    // Explicit useShallow selection prevents whole-tree re-renders on arbitrary store changes
    const messages = useAIOrderingStore(useShallow(state => state.messages));
    const isLoading = useAIOrderingStore(state => state.isLoading);
    const isProcessing = useAIOrderingStore(state => state.isProcessing);
    const paymentDetails = useAIOrderingStore(useShallow(state => state.paymentDetails));
    const glowingProductId = useAIOrderingStore(state => state.glowingProductId);
    const socketStatus = useAIOrderingStore(state => state.socketStatus);
    
    const actions = useAIOrderingStore(
        useShallow(state => ({
            sendMessage: state.sendMessage,
            sendImage: state.sendImage,
            addProductById: state.addProductById,
            setOverlayVisible: state.setOverlayVisible,
            resetChat: state.resetChat,
            removeProductById: state.removeProductById,
            initiateCheckoutRecovery: state.initiateCheckoutRecovery,
            confirmCurrentOrder: state.confirmCurrentOrder,
            clearCart: state.clearCart,
            restoreCheckout: state.restoreCheckout,
            saveForLater: state.saveForLater,
            hardCancelOrder: state.hardCancelOrder,
            addSocketAIMessage: state.addSocketAIMessage,
            connectSocket: state.connectSocket,
            disconnectSocket: state.disconnectSocket
        }))
    );

    const { data: session, status } = useSession();
    const chatEndRef = useRef<HTMLDivElement>(null);
    const currentAccessToken = session?.accessToken;
    const isConnectedRef = useRef(false);

    // Derived cart state highly optimized using useMemo
    const cartItems = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
        return lastCartMessage?.content?.items || [];
    }, [messages]);
    
    const cartControls = useAnimation();
    const prevCartCountRef = useRef(cartItems.length);

    useEffect(() => {
        if (cartItems.length > prevCartCountRef.current) {
            cartControls.start({
                scale: [1, 1.25, 0.9, 1.1, 1],
                rotate: [0, -12, 12, -6, 6, 0],
                transition: { duration: 0.5, ease: "easeInOut" }
            });
        }
        prevCartCountRef.current = cartItems.length;
    }, [cartItems.length, cartControls]);

    const activeActionId = useMemo(() => {
        const lastActionable = [...messages].reverse().find(m =>
            ['confirmation_prompt', 'recovery_prompt'].includes(m.contentType)
        );
        return lastActionable?.id;
    }, [messages]);

    useEffect(() => {
        if (status === 'authenticated' && currentAccessToken && !isConnectedRef.current) {
            isConnectedRef.current = true; 
            actions.connectSocket(currentAccessToken);
        } else if (status === 'unauthenticated') {
            isConnectedRef.current = false;
            actions.disconnectSocket();
        }
        return () => { isConnectedRef.current = false; };
    }, [status, currentAccessToken, actions]);

    // Defer scrolling layout thrash to next animation frame
    useEffect(() => {
        const scrollContainer = chatEndRef.current?.parentElement;
        if (!scrollContainer) return;

        let rafId: number;
        let timeoutId: NodeJS.Timeout;

        const performScroll = () => {
            rafId = requestAnimationFrame(() => {
                const targetTop = scrollContainer.scrollHeight + 150;
            
                if (scrollContainer.scrollTop !== targetTop) {
                    scrollContainer.scrollTo({
                        top: targetTop,
                        behavior: 'smooth'
                   });
                }
            });
        };

        performScroll();
        timeoutId = setTimeout(performScroll, 400);

        return () => {
            cancelAnimationFrame(rafId);
            clearTimeout(timeoutId);
        };
    }, [messages, isLoading, activeActionId]);
    
    useEffect(() => {
        if (!paymentDetails) setIsAnimationComplete(false);
    }, [paymentDetails]);

    const hasTriggeredRecoveryRef = useRef(false);
    useEffect(() => {
        hasTriggeredRecoveryRef.current = false;
    }, [cartItems.length, paymentDetails]);

    const handleClose = useCallback(() => {
        if (paymentDetails && !isProcessing) {
            if (hasTriggeredRecoveryRef.current) {
                onClose();
            } else {
                actions.initiateCheckoutRecovery();
                hasTriggeredRecoveryRef.current = true;
            }
        } else if (!paymentDetails) {
            onClose();
        }
    }, [paymentDetails, isProcessing, onClose, actions]);
    
    const handlePaymentSuccess = useCallback(() => {
        actions.setOverlayVisible(false);
        onClose();
        actions.resetChat();
    }, [onClose, actions]);
    
    const handleSendMessage = useCallback((rawText: string) => {
        const text = rawText.trim();
        if (!text) return;

        if (status !== 'authenticated') {
            useAIOrderingStore.setState(state => ({
                messages: [...state.messages, { id: Date.now(), sender: 'user', contentType: 'text', content: text }],
                isLoading: true
            }));
            setTimeout(() => {
                actions.addSocketAIMessage({
                    type: 'confirmation_prompt',
                    content: "Hey there! Ready to experience smart shopping? Let's get you set up in seconds.",
                    options: ["Sign In", "Sign Up"],
                });
                useAIOrderingStore.setState({ isLoading: false });
            }, 500);
            return;
        }
        actions.sendMessage(text, false);
    }, [status, actions]);

    const handleProductSelect = useCallback((product: any, elementId: string) => {
    if (status === 'authenticated') {
        // 1. لو الاتصال مقطوع، إديله التوكن عشان يعمل ريستارت للسيرفر بسرعة
        if (socketStatus !== 'connected' && currentAccessToken) {
            actions.connectSocket(currentAccessToken);
        }
        
        // 2. إرمي أمر الإضافة للـ Store.. 
        // الـ Store هيشغل الـ Thinking، هيحفظ الأمر في الـ Queue، ولما السيرفر يصحى هيبعته لوحده![cite: 5]
        actions.addProductById(product, elementId);
        
    } else {
        useAIOrderingStore.setState({ isLoading: true }); // تشغيل الـ Thinking لحظياً
        
        setTimeout(() => {
            actions.addSocketAIMessage({
                type: 'confirmation_prompt',
                content: "Let's get you set up in seconds.",
                options: ["Sign In", "Sign Up"],
            });
            useAIOrderingStore.setState({ isLoading: false }); // قفل الـ Thinking وإظهار الأزرار
        }, 500);
    }
}, [status, socketStatus, actions, currentAccessToken]);

    const stripeAppearance = useMemo(() => ({
        theme: 'night' as const,
        labels: 'floating' as const,
        variables: {
            colorPrimary: '#06b6d4', 
            colorBackground: '#0F172A', 
            colorText: '#ffffff',
            colorDanger: '#ef4444',
            fontFamily: 'system-ui, sans-serif',
            spacingUnit: '4px',
            borderRadius: '16px',
            colorIcon: '#ffffff', 
        },
        rules: {
            '.Input': { backgroundColor: '#1E293B', border: '1px solid #334155' },
            '.Input:focus': { border: '1px solid #06b6d4', boxShadow: '0 0 0 1px #06b6d4' },
            '.Tab': { backgroundColor: '#1E293B', color: '#ffffff' }, 
            '.Tab--selected': { backgroundColor: '#06b6d4', color: '#000000' },
        }
    }), []);

    const stripeOptions = useMemo<StripeElementsOptions | undefined>(() => {
        // بنقرأ الـ client_secret مباشرة زي ما الباك إند بيبعته بالظبط
        const clientSecret = paymentDetails?.client_secret;
        
        if (!clientSecret) return undefined;
        
        return { clientSecret: clientSecret, appearance: stripeAppearance };
    }, [paymentDetails, stripeAppearance]);

    const isPaymentMode = !!paymentDetails; 
    const isKeyMissing = !STRIPE_PUBLISHABLE_KEY;
    const isReadyToRender = stripeObj && stripeOptions && !isStripeError;
    
    const handleNavigateToAuth = useCallback((mode: 'SIGNIN' | 'SIGNUP') => {
        actions.setOverlayVisible(false);
        onClose();
        router.push(`/auth?mode=${mode}`);
    }, [actions, onClose, router]);

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    key="chat-window"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={handleClose}
                    style={{ colorScheme: 'dark', willChange: 'opacity', fontFamily: "'Montserrat', sans-serif" }}
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden transform-gpu"
                >
                   
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" />
                    <FlyToCartAnimator /> 
                    
                    <AnimatePresence>
                        {detailProduct && (
                            <motion.div
                                initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
                                animate={{ opacity: 1, backdropFilter: "blur(16px)" }}
                                exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
                                transition={{ duration: 0.3, ease: "easeOut" }}
                                style={{ willChange: 'opacity, backdrop-filter' }}
                                className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4 sm:p-4 transform-gpu"
                                onClick={() => setDetailProduct(null)}
                            >
                                <div onClick={(e) => e.stopPropagation()} className="w-full h-full max-w-[460px] max-h-[1050px] md:max-h-[90vh]">
                                    <ProductDetailsCard product={detailProduct} onClose={() => setDetailProduct(null)} />
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: 30 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }}
                        exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.3 } }}
                        onClick={(e) => e.stopPropagation()}
                        style={{ willChange: 'transform, opacity' }}
                        className="w-full h-full max-w-[460px] max-h-[1050px] md:max-h-[90vh] flex flex-col bg-[#020617]/55 backdrop-blur-3xl border border-white/10 rounded-[73px] shadow-[0_0_100px_rgba(6,182,212,0.1)] overflow-hidden relative transform-gpu"
                    >
                        <div className="absolute inset-[-1px] z-[120] rounded-[73px] overflow-hidden pointer-events-none [&>*]:pointer-events-auto">
                            <AIVoiceOverlay />
                        </div>
                       
                        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-cyan-500/5 blur-[120px] pointer-events-none rounded-full backface-hidden" />
                        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/5 blur-[120px] pointer-events-none rounded-full backface-hidden" />

                        <header className="px-8 py-6 flex items-center flex-shrink-0 relative z-10">
			    <div className="flex items-center gap-3">
                                <div className="w-11 h-11 rounded-full bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-300">
                                    <Bot size={18} />
                                </div>
                                <div>
                                    <h2 className="text-[11px] text-gray-400 flex items-center gap-1 mt-1">
                                       <Cpu size={12} className="text-cyan-500" />
                                       Real-time shopping
                                    </h2>
                                    <p className="text-[11px] text-gray-400 flex items-center gap-1 mt-1">
                                        <ShieldCheck size={12} className="text-cyan-500" />
                                        Secured
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 ml-auto">
                                {!isPaymentMode && (
                                    <div className="flex-shrink-0">
                                        <motion.button
                                            id="order-summary-cart-icon" 
                                            animate={cartControls}
                                            onClick={() => setIsMobileSidebarOpen(true)}
                                            className="p-3 rounded-full bg-cyan-600/20 border border-cyan-500/50 text-cyan-400 hover:bg-cyan-600/40 transition-all flex items-center justify-center relative"
                                        >
                                            <ShoppingBag size={18} />
                                            {cartItems.length > 0 && (
                                                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                                                    {cartItems.length}
                                                </span>
                                            )}
                                            </motion.button>
                                    </div>
                                )}

                                <button
                                    onClick={handleClose} 
                                    className="p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all duration-300"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                          </header>

                        <div className="flex-grow flex overflow-hidden relative z-10">
                            <AnimatePresence mode="wait">
                                {isPaymentMode ? (
                                    <motion.div
                                        key="payment"
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -20, transition: { duration: 0.2 } }}
                                        onAnimationComplete={() => setIsAnimationComplete(true)}
                                        style={{ isolation: 'isolate', willChange: 'transform, opacity' }}
                                        className="w-full h-full flex flex-col relative z-20 transform-gpu"
                                    >
                                        {isReadyToRender && isAnimationComplete ? (
                                            (() => {
                                        // 1. الفحص المعماري الصارم: التأكد من وجود البيانات في الهيكلة الجديدة
                                                const hasValidData = Boolean(
                                                    stripeOptions?.clientSecret &&
                                                    paymentDetails?.order_data &&
                                                    typeof paymentDetails.order_data.total === 'number'
                                                );

                                        // 2. Fallback: عرض رسالة خطأ آمنة لو البيانات ناقصة
                                                if (!hasValidData) {
                                                    return (
                                                        <div className="flex flex-col items-center justify-center h-full p-6 text-center">
                                                           <div className="p-4 bg-red-500/10 rounded-full mb-4">
                                                               <AlertCircle size={48} className="text-red-400" />
                                                           </div>
                                                           <h3 className="text-xl font-bold text-white mb-2 tracking-wide font-mono">DATA CONTRACT BREACH</h3>
                                                           <p className="text-gray-400 max-w-md text-sm leading-relaxed">
                                                               Incomplete payment payload received from server. Missing order total or items.
                                                           </p>
                                                       </div>
                                                    );
                                                }

                                          // 3. Success: تمرير الداتا الموثوقة للفورم عبر الـ DTO الجديد
                                                return (
                                                    <Elements 
                                                        key={`${stripeOptions?.clientSecret}-loaded`} 
                                                        stripe={stripeObj} 
                                                        options={stripeOptions}
                                                    >
                                                        <AIPaymentForm
                                                            orderId={paymentDetails.order_data.order_id}
                                                            total={paymentDetails.order_data.total}
                                                            items={paymentDetails.order_data.items}
                                                            onPaymentSuccess={handlePaymentSuccess}
                                                            clientSecret={stripeOptions.clientSecret}
                                                        />
                                                    </Elements>
                                                );
                                            })()
                                        ) : (
                                            <div className="absolute inset-0 flex flex-col items-center justify-center w-full h-full z-50">
                                                {isStripeError || isKeyMissing ? (
                                                     <PaymentFatalError keyMissing={isKeyMissing} />
                                                ) : (
                                                    <Loader2 size={26} className="text-cyan-500 animate-spin" />
                                                )}
                                            </div>
                                        )}
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="chat"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0, transition: { duration: 0.1 } }}
                                        style={{ willChange: 'opacity' }}
                                        className="flex-grow flex flex-col relative z-10 w-full transform-gpu"
                                    >
                                        <div className="flex-grow px-4 lg:px-12 py-8 space-y-8 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent">
                                            <AnimatePresence initial={false}> 
                                                {messages.map((msg) => (
                                                    <ChatMessage
                                                        key={msg.id}
                                                        message={msg}
                                                        isActiveAction={msg.id === activeActionId}
                                                        onSend={handleSendMessage}
                                                        onNavigateToAuth={handleNavigateToAuth}
                                                        onProductSelect={handleProductSelect}
                                                        onViewDetails={setDetailProduct}
                                                        onConfirmOrder={actions.confirmCurrentOrder}
                                                        onClearCart={actions.clearCart}
                                                        onRestore={actions.restoreCheckout}
                                                        onSave={actions.saveForLater}
                                                        onCancel={actions.hardCancelOrder}
                                                    />
                                                ))}
                                            </AnimatePresence>
                                            <div ref={chatEndRef} />
                                        </div>
                                        <ChatInput onSend={handleSendMessage} onSendImage={actions.sendImage} isTyping={isLoading} isProcessing={isProcessing} />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                                 
                            {!(isPaymentMode) && (
                                 <AIChatSidebar
                                     messages={messages}
                                     glowingProductId={glowingProductId}
                                     onRemoveItem={actions.removeProductById}
                                     isMobileOpen={isMobileSidebarOpen}
                                     onCloseMobile={() => setIsMobileSidebarOpen(false)}
                                 />
                            )}
                       </div>
                   </motion.div>
               </motion.div>
           )}
       </AnimatePresence>
   );
}
