
//** apps/web/components/ai/AIChatOverlay.tsx **//

'use client';

import { ProductDetailsCard } from '../products/ProductDetailsCard';
import { Eye } from 'lucide-react';
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Bot, User, CornerDownRight, ShoppingCart, Cpu, X, 
    ChevronLeft, ChevronRight, Save, Trash2, Undo2, AlertCircle, 
    ShoppingBag, ShieldOff, Loader2, Wind, Navigation, Zap, 
    Activity, Signal, BrainCircuit, Lock, Star, Sparkles, Mic, Camera, Image as ImageIcon, MapPin, Clock
} from 'lucide-react';
import { useAIOrderingStore, Message } from '../../hooks/useAIOrderingStore';
import Image from 'next/image';
import useEmblaCarousel from 'embla-carousel-react';
import { loadStripe, StripeElementsOptions, Stripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { AIPaymentForm } from './AIPaymentForm';
import { useSession } from "next-auth/react";
import { useShallow } from 'zustand/react/shallow';
import { AIVoiceOverlay } from './AIVoiceOverlay';

const DEFAULT_PLACEHOLDER = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC";
const getAbsoluteImageUrl = (relativePath: string | undefined): string => {
    
    if (!relativePath) {
        return DEFAULT_PLACEHOLDER;
    }

    if (relativePath.startsWith('http') || relativePath.startsWith('data:')) {
        return relativePath;
    }

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
    }, [messages.length]); 
};

const HolographicFlightDeck = React.memo(({ data }: { data: any }) => {
    if (!data) return null;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full bg-[#050B14] border border-cyan-500/30 rounded-2xl overflow-hidden relative mt-2 shadow-[0_0_30px_rgba(6,182,212,0.15)]"
        >
            
            <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.05)_1px,transparent_1px)] bg-[size:20px_20px]" />

         
            <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/10 to-transparent w-[50%] skew-x-12"
                animate={{ left: ['-100%', '200%'] }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
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

                {/* Tactical Map Visualization (SVG) */}
                <div className="h-32 w-full relative mb-6 mx-auto flex items-center justify-center">
                    <svg className="w-full h-full absolute inset-0 overflow-visible">
                        {/* Flight Path Line */}
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

                        {/* Origin Point */}
                        <circle cx="20" cy="60" r="4" fill="#06b6d4" />
                        <text x="20" y="80" fill="gray" fontSize="10" textAnchor="middle">HQ</text>

                        {/* Drone Icon Moving */}
                        <motion.g
                            initial={{ offsetDistance: "0%" }}
                            animate={{ offsetDistance: "100%" }}
                            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                            style={{ offsetPath: 'path("M 20,60 Q 150,10 280,60")' }}
                        >
                            <circle cx="0" cy="0" r="6" fill="#06b6d4" className="drop-shadow-[0_0_10px_rgba(6,182,212,1)]" />
                        </motion.g>

                        {/* Destination Point */}
                        <circle cx="280" cy="60" r="4" fill="#ef4444" />
                        <circle cx="280" cy="60" r="8" fill="none" stroke="#ef4444" strokeOpacity="0.5" className="animate-ping" />
                        <text x="280" y="80" fill="gray" fontSize="10" textAnchor="middle">YOU</text>
                    </svg>
                </div>

                {/* Flight Stats Grid */}
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

            {/* Footer Status */}
            <div className="bg-cyan-950/30 p-2 text-center border-t border-cyan-500/20">
                <span className="text-[10px] font-mono text-cyan-300 animate-pulse">
                    &gt;&gt; SYSTEM STATUS: {data.status} &lt;&lt;
                </span>
            </div>
        </motion.div>
    );
});
HolographicFlightDeck.displayName = 'HolographicFlightDeck';

// ============================================================================
// --- 1. VISUAL COMPONENTS (High-Fidelity UI) ---
// ============================================================================

const DroneTelemetryWidget = React.memo(() => {
    // Simulated live telemetry for architectural realism
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

// --- ARCHITECTURAL UPGRADE: Enhanced Product Card ---
const CarouselProductCard = React.memo(({ product, onSelect, onViewDetails, totalItems }: { product: any, onSelect: (product: any, elementId: string) => void, onViewDetails: (product: any) => void, totalItems: number }) => {
    const confirmOrder = useAIOrderingStore(state => state.confirmCurrentOrder);
    // Made cards significantly larger for better UX (85% width on mobile, 55% on desktop)
    const slideWidthClass = totalItems === 1 
    ? "flex-[0_0_100%] sm:flex-[0_0_auto] sm:w-[300px] md:w-[350px]" 
    : "flex-[0_0_85%] sm:flex-[0_0_60%] md:flex-[0_0_49%]";
    
    const rawImagePath = product.image_url || product.image;
    const imageUrl = useMemo(() => getAbsoluteImageUrl(rawImagePath), [rawImagePath]);
    const elementId = `product-carousel-img-${product.id}`;

    const handleSelect = useCallback(() => {
        const normalizedProduct = { ...product, image: rawImagePath };
        onSelect(normalizedProduct, elementId);
    }, [product, rawImagePath, elementId, onSelect]);

    return (
        <div className={`embla__slide ${slideWidthClass} px-4 py-4`}>
            <motion.div
                className="flex flex-col p-0 bg-gradient-to-br from-[#0F172A] to-[#020617] backdrop-blur-3xl rounded-[32px] border border-white/10 h-full text-left shadow-2xl relative group overflow-hidden"
                whileHover={{ 
                    scale: 1.02,
                    border: "1px solid rgba(6, 182, 212, 0.5)",
                    boxShadow: "0 20px 50px -12px rgba(6, 182, 212, 0.25)" 
                }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            >
	        <motion.button
                    onClick={(e) => { e.stopPropagation(); onViewDetails(product); }}
                    initial={{ opacity: 0, y: -10 }}
		    animate={{ opacity: 1, y: 0 }}
                    whileHover={{ scale: 1.1, backgroundColor: "rgba(6, 182, 212, 1)", color: "#000" }}
                    className="absolute top-4 right-2 z-50 p-2.5 rounded-full bg-black/40 border border-white/10 text-white backdrop-blur-md opacity-60 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-500 shadow-[0_0_20px_rgba(0,0,0,0.5)]"
                    title="Inspect Hologram"
                >
                    <Eye size={18} strokeWidth={2.5} />
                </motion.button>
                {/* Image Section with Atmospheric Glow */}
                <div className="relative h-56 w-full flex items-center justify-center bg-gradient-to-b from-white/5 to-transparent p-6 overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                    <Image
                        id={elementId}
                        src={imageUrl}
                        alt={product.name}
                        width={250}
                        height={250}
                        className="w-auto h-full object-contain drop-shadow-[0_10px_20px_rgba(0,0,0,0.5)] group-hover:scale-110 group-hover:-rotate-2 transition-transform duration-500 cubic-bezier(0.34, 1.56, 0.64, 1)"
                    />
                    
                    {/* Floating Price Tag */}
                    
                </div>

                {/* Content Section */}
                <div className="p-6 flex flex-col flex-grow relative z-10">
		    <div className="absolute -top-4 right-3 z-20 flex items-center gap-1">
                       <span className="text-cyan-300 font-bold font-mono text-lg">${(Number(product.price) || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-start mb-2">
                         <h4 className="text-xl font-bold text-white leading-snug tracking-tight line-clamp-2" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>{product.name}</h4>
                    </div>
                   
                    <div className="flex items-center gap-2 mb-6">
                         {product.rating && (
                            <div className="flex items-center gap-1 bg-yellow-500/10 border border-yellow-500/20 px-2 py-0.5 rounded-md">
                                <Star size={12} className="text-yellow-400 fill-yellow-400" />
                                <span className="text-xs font-bold text-yellow-200">{product.rating}</span>
                            </div>
                        )}
                        <span className="text-xs text-gray-500 font-mono">ID: {product.id}</span>
                    </div>

                    <div className="mt-auto pt-4 border-t border-white/5">
                        <motion.button
                 
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.96 }}
			    onClick={handleSelect}

                            className="w-full relative overflow-hidden rounded-full bg-white text-black font-bold px-4.5 py-4 flex items-center justify-center gap-2 group/btn shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all duration-300"
                        >
                            <span className="relative z-10 flex items-center gap-2 tracking-wide text-xs">
                                <ShoppingBag size={16} strokeWidth={2.5} />
                                ADD TO CART
                            </span>
                            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
});
CarouselProductCard.displayName = 'CarouselProductCard';

const ProductCarousel = React.memo(({ products, onViewDetails, onSelect }: { products: any[], onSelect: (product: any, elementId: string) => void }) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'center', containScroll: 'trimSnaps' });
    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);
    const totalItems = products.length;
    const canScroll = totalItems > 1;

    return (
        <div className="relative my-6 px-1 group/carousel w-full">
            <div className="overflow-hidden p-2 -m-2" ref={emblaRef}>
                <div className="flex gap-4 pl-4 pr-12 md:px-4">
                    {products.map((p, i) => <CarouselProductCard key={p.id || i} product={p} onSelect={onSelect} onViewDetails={onViewDetails} totalItems={totalItems} />)}
                </div>
            </div>
            {canScroll && (
                <>
                    <button onClick={scrollPrev} className="absolute top-1/2 -translate-y-1/2 left-0 p-3 bg-black/50 backdrop-blur-xl border border-white/10 rounded-full z-20 hover:bg-cyan-500 hover:text-black hover:border-cyan-400 transition-all opacity-0 group-hover/carousel:opacity-100 -translate-x-2 group-hover/carousel:translate-x-2 duration-300 shadow-xl"><ChevronLeft size={20}/></button>
                    <button onClick={scrollNext} className="absolute top-1/2 -translate-y-1/2 right-0 p-3 bg-black/50 backdrop-blur-xl border border-white/10 rounded-full z-20 hover:bg-cyan-500 hover:text-black hover:border-cyan-400 transition-all opacity-0 group-hover/carousel:opacity-100 translate-x-2 group-hover/carousel:translate-x-0 duration-300 shadow-xl"><ChevronRight size={20}/></button>
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
        className="flex items-start gap-3 p-4 mt-4 bg-[#0A1116] border border-cyan-900/50 rounded-2xl max-w-lg relative overflow-hidden"
    >
        <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500" />
        <div className="absolute -right-4 -top-4 w-16 h-16 bg-cyan-500/10 blur-xl rounded-full" />
        <div>
            <span className="block text-[10px] font-black text-cyan-300 tracking-widest mb-1">vision by air</span>
            <p className="text-sm text-cyan-100/80 font-sans leading-relaxed">{text}</p>
        </div>
    </motion.div>
));
AIReasoning.displayName = 'AIReasoning';

// --- ARCHITECTURAL UPGRADE: Refined Message Design ---
const ChatMessage = React.memo(({ message, onSend, onViewDetails, onProductSelect, onConfirmOrder, onClearCart, onRestore, onSave, onCancel }: any) => {
    const isAI = message.sender === 'ai';

    const renderContent = () => {
        switch (message.contentType) {
	    case 'image_user_upload':
                const hasCaption = message.content && message.content.trim().length > 0 && 
                                  !message.content.includes("Analyzing") && 
                                  !message.content.includes("Processing");
                const hasImg = !!message.imageUrl;

                return (
                    // 1. العرض: بنسمح للفقاعة توصل لـ 450px عشان الصورة تاخد راحتها
                    <div className="flex flex-col w-full min-w-[300px] max-w-[350px] sm:max-w-[450px]">
                        
                        {/* 2. صندوق الصورة: */}
                        {/* aspect-[4/3]: بيخلي البوكس ياخد نسبة الكاميرا الطبيعية (زي يوتيوب القديم) وده بيبين تفاصيل أكتر */}
                        {/* h-auto: الطول بيظبط نفسه حسب العرض */}
                        {hasImg && (
                            <div className={`relative w-full aspect-[4/3] flex-none overflow-hidden shadow-2xl ${hasCaption ? 'rounded-t-[32px] border-b-0' : 'rounded-[32px]'}`}>
                                <Image
                                    src={message.imageUrl}
                                    alt="Uploaded"
                                    fill
                                    // 3. object-contain: الصورة كاملة بدون قص
                                    // شيلنا p-2 عشان الصورة تلمس الحواف وتبان أكبر
                                    className="object-cover" 
                                />
                            </div>
                        )}

                        {/* 3. صندوق النص */}
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
                return <p className={`whitespace-pre-wrap text-[15px] md:text-base leading-7 text-white font-medium ${message.contentType === 'error' ? 'bg-red-950/20 p-2 rounded' : ''}`}>{message.content}</p>;
	    case 'FLIGHT_MANIFEST': // New Case
                return (
                    <div className="w-full -ml-2 sm:ml-0">
                         <p className="whitespace-pre-wrap mb-2 text-[15px] px-2 leading-7 text-white font-medium">
                             {message.content}
                         </p>
                         <HolographicFlightDeck data={message.flight_data} />
                    </div>
                );
            case 'confirmation_prompt':
                return (
                    <div>
                        <p className="whitespace-pre-wrap mb-5 text-[15px] leading-7">{message.content}</p>
                        <div className="flex flex-wrap gap-3">
                            {(message.options as string[])?.map((option: string) => {
                                const isPrimary = option === 'Confirm Order' || option === 'Retry Payment' || option === 'Switch to PayPal';
                                
                                // Dynamic Styling based on intent
                                let buttonStyle = "bg-white/5 text-cyan-200 border-white/10 hover:bg-cyan-500 hover:text-black";
                                if (option === 'Switch to PayPal') buttonStyle = "bg-[#003087] text-white border-transparent hover:bg-[#003087]/80"; // PayPal Blue
                                if (option === 'Retry Payment') buttonStyle = "bg-green-600 text-white hover:bg-green-500";

                                return (
                                    <motion.button
                                        key={option}
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        // ✅ الكود الجديد (توجيه صامت للأوامر)
                                        onClick={() => {
                                            // 1. Confirm Order -> Silent Action
                                            if (option === 'Confirm Order') {
                                                onConfirmOrder(); 
                                            }
                                            // 2. Clear Cart -> Silent Action
                                            else if (option === 'Clear Cart') {
                                                onClearCart();
                                            }
                                            // 3. باقي الأزرار
                                            else if (option === 'Switch to PayPal') {
                                                onSend("I want to use PayPal");
                                            }
                                            else if (option === 'Retry Payment') onConfirmOrder(); 
                                            else if (option === 'Save for Later') onSave();
                                            
                                            // 4. أي شيء آخر يُرسل كنص عادي
                                            else {
                                                onSend(option);
                                            }
                                        }}
                                        className={`text-xs font-bold uppercase tracking-widest px-6 py-3 rounded-xl border transition-all duration-300 ${buttonStyle}`}
                                    >
                                        {option}
                                    </motion.button>
                                );
                            })}
                        </div>
                    </div>
                );
            case 'product_carousel':
            case 'proactive_suggestion':
                return (
                    <div className="w-full -ml-2 sm:ml-0">
                        <p className="whitespace-pre-wrap mb-2 text-[15px] px-2 leading-7">{message.content}</p>
                        <ProductCarousel products={message.products || []} onSelect={onProductSelect} onViewDetails={onViewDetails} />
                        {(message.reason || message.ai_notes) && (
                            <div className="px-2">
                                <AIReasoning text={message.reason || message.ai_notes} />
                            </div>
                        )}
                    </div>
                );
            case 'recovery_prompt':
               return (
                  <div className="flex items-center justify-center w-full py-6">
            {/* شريط الأوامر العائم بتصميم Glassmorphism أبيض شفاف */}
                     <motion.div 
                         initial={{ scale: 0.9, opacity: 0, y: 10 }}
                         animate={{ scale: 1, opacity: 1, y: 0 }}
                         className="flex items-center gap-4 p-3 bg-white/[0.04] backdrop-blur-3xl border border-white/10 rounded-[55px] shadow-2xl"
                     >
                         {[
                             { 
                                 icon: Undo2, 
                                 label: "UNDO", 
                                 action: onRestore, 
                                 textColor: "text-white", 
                                 hoverBg: "hover:bg-cyan-500/10" 
                             },
                             { 
                                 icon: Save, 
                                 label: "SAVE", 
                                 action: onSave, 
                                 textColor: "text-white", 
                                 hoverBg: "hover:bg-purple-500/10" 
                             },
                             { 
                                 icon: X, 
                                 label: "CANCEL", 
                                 action: onCancel, 
                                 textColor: "text-white", 
                                 hoverBg: "hover:bg-red-500/10" 
                             }
                         ].map((btn, idx) => (
                             <motion.button 
                                 key={idx}
                                 whileHover={{ scale: 1.05 }}
                                 whileTap={{ scale: 0.95 }}
                                 onClick={btn.action} 
                                 className={`flex flex-col items-center justify-center min-w-[80px] h-[80px] gap-2 rounded-[55px] transition-all duration-300 ${btn.hoverBg} group`}
                    >
                        {/* الأيقونة بيضاء كما طلبت */}
                                 <btn.icon size={22} strokeWidth={2.5} className="text-white opacity-80 group-hover:opacity-100" />
                        
                        {/* الكلمة باللون الأصلي الخاص بها */}
                                 <span className={`text-[9px] font-black uppercase tracking-widest ${btn.textColor}`}>
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
    // --- VISUAL DESIGN: Distinct AI vs User styles ---
    if (!contentNode) return null;
    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className={`flex items-end gap-3 w-full mb-6 ${isAI ? 'justify-start' : 'justify-end'}`}
        >
            
            <div className={`w-auto max-w-[90%] md:max-w-3xl px-6 py-5 ${
                isAI 
                    ? 'rounded-[32px] rounded-bl-none bg-[#050B14]/80 backdrop-blur-xl border border-white/5 text-gray-100 shadow-xl shadow-black/20' 
                    : 'rounded-[32px] rounded-br-none bg-white/5 border border-white/10 text-white backdrop-blur-sm'
            }`}>
		{contentNode}
            </div>
        </motion.div>
    );
});
ChatMessage.displayName = 'ChatMessage';

const AIChatSidebar = React.memo(({ messages, glowingProductId, onRemoveItem }: {
    messages: Message[],
    glowingProductId: number | null,
    onRemoveItem: (productId: number) => void
    onConfirmOrder: () => void
}) => {
   
    const { cart, aiNote } = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
        const lastAINoteMessage = [...messages].reverse().find(m => m.sender === 'ai' && (m.ai_notes || m.reason));
        return {
            cart: lastCartMessage ? lastCartMessage.content : { items: [], total: 0 },
            aiNote: lastAINoteMessage ? (lastAINoteMessage.ai_notes || lastAINoteMessage.reason) : null
        };
    }, [messages]);

    return (
        <div className="hidden lg:flex w-[350px] xl:w-[400px] flex-shrink-0 backdrop-blur-3xl bg-black/60 border-l border-white/5 flex-col overflow-hidden relative z-20">
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.05] pointer-events-none" />
            
            <div className="flex-grow p-6 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-cyan-500/20 scrollbar-track-transparent relative z-10">
                <div className="flex items-center justify-between mb-8">
                    <h3 className="text-sm font-bold uppercase text-white tracking-widest flex items-center gap-2">
                    </h3>
                </div>

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
                                className="flex justify-between items-center p-3 rounded-2xl border transition-colors group relative overflow-hidden"
                            >
                                {item.product_id === glowingProductId && (
                                    <motion.div layoutId="glow" className="absolute inset-0 bg-cyan-500/5" transition={{ duration: 0.3 }} />
                                )}
                                <div className="flex items-center gap-3 flex-1 min-w-0 relative z-10">
                                    <div className="w-12 h-12 rounded-xl bg-black/40 border border-white/10 flex items-center justify-center overflow-hidden">
                                         <ShoppingBag size={16} className="text-gray-500" />
                                    </div>
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-gray-100 text-sm font-bold truncate tracking-tight" title={item.name}>
                                            {item.name}
                                        </span>
                                        <span className="text-[10px] text-gray-400 font-mono mt-0.5">QTY: {item.quantity}</span>
                                    </div>
                                </div>
                                <div className="flex flex-col items-end gap-1 relative z-10">
                                    <span className="font-bold text-cyan-300 font-mono text-sm">
                                        ${(item.price * item.quantity).toFixed(2)}
                                    </span>
                                    <motion.button
                                        onClick={() => onRemoveItem(item.product_id)}
                                        className="text-white hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all duration-200"
                                        title="Jettison Item"
                                    >
                                        <X size={14} />
                                    </motion.button>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>

            <div className="flex-shrink-0 p-6 border-t border-white/10 bg-[#050B14] space-y-6 relative z-20">
                
                <div>
                    <h3 className="text-[10px] font-bold text-gray-500 tracking-widest mb-3 flex items-center gap-2">
                        <Signal size={12} /> airaero X
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

    // 🆕 2. دالة التمدد التلقائي
    const handleAutoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const target = e.target;
        setValue(target.value);

        // تصفير الارتفاع لحساب الحجم الجديد بدقة
        target.style.height = 'auto';
        // تعيين الارتفاع الجديد بناءً على المحتوى (بحد أقصى 150px مثلاً)
        target.style.height = `${Math.min(target.scrollHeight, 150)}px`;
    };

    // --- 🎤 VOICE MODULE (Web Speech API) ---
    const toggleVoice = () => {
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
        recognition.lang = 'en-US'; // Or dynamic based on user

        recognition.onstart = () => setIsListening(true);
        recognition.onend = () => setIsListening(false);
        recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            setValue(transcript);
            // Optional: Auto-send on voice end
            // onSend(transcript); 
        };
        recognition.start();
    };

    const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onloadend = () => {
            const fullDataUrl = reader.result as string;
            const base64Raw = fullDataUrl.split(',')[1];
            // 💎 بدلاً من الإرسال الفوري، نضعها في الانتظار (Preview)
            setPendingImage({ url: fullDataUrl, base64: base64Raw });
        };
        reader.readAsDataURL(file);
        e.target.value = ''; // Reset input
    };

    // --- 🚀 HYBRID SEND (Image + Text) ---
    const handleTriggerSend = () => {
        if (isSendButtonDisabled) return;
        if (pendingImage) {
            // 💎 إرسال الصورة + النص (كـ Caption)
            onSendImage(pendingImage.url, pendingImage.base64, value);
            setPendingImage(null); // تنظيف المعاينة
            setValue('');
        } else if (value.trim()) {
            // إرسال نص فقط
            onSend(value);
            setValue('');
        }
	if (textareaRef.current) {
	    textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = '56px'; // ارجع للارتفاع الأصلي
        }
    };

    const isInputLocked = isTyping || isProcessing;
    const isSendButtonDisabled = isInputLocked || (!value.trim() && !pendingImage);

    return (
      <div className="p-6 border-t border-white/5 flex-shrink-0 bg-[#020617]/50 backdrop-blur-md relative z-20">
         <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={handleImageSelect} />

        {/* 💎 IMAGE PREVIEW AREA (The Architectural Upgrade) */}
        <AnimatePresence>
            {pendingImage && (
                <motion.div 
                    initial={{ opacity: 0, y: 10, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                    exit={{ opacity: 0, y: 10, height: 0 }}
                    className="absolute -top-24 left-6 z-30"
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
          
          {/* 📸 Vision Trigger */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-3 rounded-full bg-white/5 text-white hover:bg-cyan-500/20 transition-all border border-white/5 hover:border-cyan-500/50"
            title="Upload Visual Data"
          >
            <Camera size={20} />
          </button>

          {/* 🎤 Voice Trigger */}
          <button
            type="button"
            onClick={() => useAIOrderingStore.getState().setVoiceMode(true)}
            className="p-3 rounded-full bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500 hover:text-white transition-all border border-cyan-500/20 group"
            title="Talk to order with air"
          >
            <Mic size={20} className="group-hover:scale-110 transition-transform" />
          </button>

          {/* Text Input */}
          <div className="relative flex-grow">
            <textarea
                ref={textareaRef}
                value={value}
                onChange={handleAutoResize}
                rows={1}
                onKeyDown={(e) => {
                    // إرسال عند الضغط على Enter (بدون Shift)
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault(); // منع سطر جديد
                        if (!isSendButtonDisabled) handleTriggerSend();
                    }
                }}
                placeholder={isListening ? 'Listening...' : isInputLocked ? 'Thinking...' : 'Ask order with air...'}
                disabled={isInputLocked}
                className="w-full bg-gray-800 border border-gray-800 rounded-[28px] py-[14px] pr-16 pl-6 text-gray-100 placeh     older-gray-400 focus:bg-gray-800 focus:border-none focus:outline-none transition-all duration-300 font-medium shadow-lg resize-none overflow-hidden no-scrollbar min-h-[52px] leading-relaxed"
		style={{
                    // نظهر السكرول فقط لو الكلام زاد عن 150 بيكسل
                    overflowY: textareaRef.current && textareaRef.current.scrollHeight > 150 ? 'auto' : 'hidden'
                }}
            />
             <button
                disabled={isSendButtonDisabled}
                onClick={handleTriggerSend}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-transparent disabled:text-gray-500 text-white transition-all"
            >
                {isInputLocked ? <Loader2 size={18} className="animate-spin" /> : <CornerDownRight size={18} />}
            </button>
          </div>
        </div>
      </div>
    );
  }
);

// --- ARCHITECTURAL UPGRADE: Physics-Based Animation (1000x smoother) ---
const FlyToCartAnimator = React.memo(() => {
  const flyQueue = useAIOrderingStore((state) => state.flyQueue);
  const removeFlyItem = useAIOrderingStore((state) => state.removeFlyItem);

  const getStartPosition = (startElementId: string) => {
    if (!startElementId) return { x: window.innerWidth / 2, y: window.innerHeight / 2, width: 0, height: 0 };
    const el = document.getElementById(startElementId);
    if (el) return el.getBoundingClientRect();
    return { x: window.innerWidth / 2, y: window.innerHeight / 2, width: 100, height: 100 };
  };

  const getEndPosition = () => {
    const el = document.getElementById('order-summary-cart-icon');
    if (el) {
      const rect = el.getBoundingClientRect();
      return { top: rect.top, left: rect.left };
    }
    return { top: 50, left: window.innerWidth - 50 };
  };

  const endPos = getEndPosition();

  return (
    <AnimatePresence>
      {flyQueue.map((item) => {
          const startRect = getStartPosition(item.startElementId);
          const imageSource = getAbsoluteImageUrl(item.image);
          if (!startRect || startRect.width === 0) return null;

          // Using "spring" physics instead of "ease" for organic, super-smooth movement
          return (
            <motion.div
              key={item.animationId} 
              className="fixed z-[9999] rounded-full overflow-hidden border-2 border-cyan-400 shadow-[0_0_30px_rgba(6,182,212,0.8)]"
              style={{ 
                  position: 'fixed',
                  top: 0,
                  left: 0,
                  pointerEvents: 'none'
              }}
              initial={{ 
                  x: startRect.left, 
                  y: startRect.top, 
                  width: startRect.width, 
                  height: startRect.height, 
                  opacity: 1,
                  scale: 1 
              }}
              animate={{ 
                  x: endPos.left - 10, // Slight offset to hit icon center
                  y: endPos.top - 10, 
                  width: 30, 
                  height: 30, 
                  opacity: 0,
                  scale: 0.5,
                  rotate: 360
              }}
              transition={{ 
                  type: "spring", 
                  stiffness: 55, 
                  damping: 15,
                  mass: 0.8
              }}
              onAnimationComplete={() => removeFlyItem(item.animationId)}
            >
              <Image src={imageSource} alt="product" width={100} height={100} className="w-full h-full object-cover" priority />
            </motion.div>
          );
      })}
    </AnimatePresence>
  );
});
FlyToCartAnimator.displayName = 'FlyToCartAnimator';

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
    
    const [detailProduct, setDetailProduct] = useState<any | null>(null);
    const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '';
    const stripePromise: Promise<Stripe | null> | null = useMemo(() => {
        if (STRIPE_PUBLISHABLE_KEY) {
            return loadStripe(STRIPE_PUBLISHABLE_KEY);
        }
        return null;
    }, [STRIPE_PUBLISHABLE_KEY]);
    
    const [stripeObj, setStripeObj] = useState<Stripe | null>(null);
    const [isStripeError, setIsStripeError] = useState(false);
    const [isAnimationComplete, setIsAnimationComplete] = useState(false);

    useEffect(() => {
        if (stripePromise) {
            stripePromise
                .then((stripe) => {
                    setStripeObj(stripe);
                    setIsStripeError(false);
                })
                .catch((err) => {
                    console.error("Stripe Load Error:", err);
                    setIsStripeError(true);
                });
        } else {
            setIsStripeError(true);
        }
    }, [stripePromise]);
    
    const messages = useAIOrderingStore(state => state.messages);
    const isLoading = useAIOrderingStore(state => state.isLoading);
    const isProcessing = useAIOrderingStore(state => state.isProcessing);
    const paymentDetails = useAIOrderingStore(state => state.paymentDetails);
    const glowingProductId = useAIOrderingStore(state => state.glowingProductId);
    const socketStatus = useAIOrderingStore(state => state.socketStatus);
    const actions = useAIOrderingStore(
        useShallow((state) => ({
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

    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cartItems = lastCartMessage?.content?.items || [];

    useEffect(() => {
        if (status === 'authenticated' && currentAccessToken && !isConnectedRef.current) {
            isConnectedRef.current = true; 
            actions.connectSocket(currentAccessToken);
        } else if (status === 'unauthenticated') {
             isConnectedRef.current = false;
             actions.disconnectSocket();
        }
    }, [status, currentAccessToken, actions]);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [messages, isLoading]);

    useEffect(() => {
        if (!paymentDetails) {
            setIsAnimationComplete(false);
        }
    }, [paymentDetails]);

    const hasTriggeredRecoveryRef = useRef(false);

    useEffect(() => {
        hasTriggeredRecoveryRef.current = false;
    }, [cartItems, paymentDetails?.orderId]);

    const handleClose = useCallback(() => {
        if (paymentDetails && !isProcessing) {
            if (hasTriggeredRecoveryRef.current) {
                // نعم حذرناه، وهو أصر على الخروج مرة أخرى -> إذن نغلق النافذة بصمت
                onClose();
            } else {
                // لا، هذه أول مرة يحاول يخرج -> نظهر رسالة التحذير (Pause)
                actions.initiateCheckoutRecovery();
                // ونسجل أننا حذرناه
                hasTriggeredRecoveryRef.current = true;
            }

        } else if (!paymentDetails) {
            // الحالة الثانية: وضع الشات العادي -> إغلاق مباشر
            onClose();
        }
    }, [paymentDetails, isProcessing, onClose, actions]);
    
    const handlePaymentSuccess = useCallback(() => {
        actions.setOverlayVisible(false);
        onClose();
        actions.resetChat();
    }, [onClose, actions.setOverlayVisible, actions.resetChat]);

    const handleSendMessage = useCallback((text: string) => {
        if (status === 'authenticated' && socketStatus === 'connected') {
            actions.sendMessage(text, false);
        } else if (status === 'authenticated' && socketStatus !== 'connected') {
            actions.addSocketAIMessage({
                type: 'error',
                content: "Establishing uplink to Autonomous Engine... standby.",
            });
        } else {
             useAIOrderingStore.setState(state => ({
                messages: [...state.messages, { id: Date.now(), sender: 'user', contentType: 'text', content: text }],
                isLoading: true
            }));
            setTimeout(() => {
                actions.addSocketAIMessage({
                    type: 'confirmation_prompt',
                    content: "Access to Autonomous Commerce is personalized. Identify yourself to proceed.",
                    options: ["Sign In", "Create Account"],
                });
            }, 500);
        }
    }, [status, socketStatus, actions.sendMessage, actions.addSocketAIMessage]);

    const handleProductSelect = useCallback((product: any, elementId: string) => {
        if (status === 'authenticated' && socketStatus === 'connected') {
            actions.addProductById(product, elementId);
        } else if (status === 'authenticated') {
             actions.addSocketAIMessage({ type: 'error', content: "Engine warming up..." });
        } else {
             actions.addSocketAIMessage({ type: 'error', content: "Authentication required for cart operations." });
        }
    }, [status, socketStatus, actions.addProductById, actions.addSocketAIMessage]);
        
            const stripeAppearance = useMemo(() => ({
                theme: 'night',
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
                const stripeGateway = paymentDetails?.gateways.find(g => g.provider === 'stripe');
                if (!stripeGateway?.clientSecret) return undefined;

                return {
                    clientSecret: stripeGateway.clientSecret,
                    appearance: stripeAppearance, 
                };
            }, [paymentDetails, stripeAppearance]);

    const isPaymentMode = !!paymentDetails; 
    const isKeyMissing = !STRIPE_PUBLISHABLE_KEY;
    const isReadyToRender = stripeObj && stripeOptions && !isStripeError;

    return (
        <AnimatePresence>
	    <AIVoiceOverlay />
            {isOpen && (
                <motion.div
		    key="chat-window"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={handleClose}
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden"
		            style={{ colorScheme: 'dark' }}
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
                                className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4"
				onClick={() => setDetailProduct(null)}
                            >
                                <div onClick={(e) => e.stopPropagation()} className="w-full max-w-7xl h-[93vh]">
                                    <ProductDetailsCard
                                        product={detailProduct}
                                        onClose={() => setDetailProduct(null)}
                                    />
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: 30 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }}
                        exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.3 } }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full max-w-7xl h-[93vh] flex flex-col bg-[#020617]/40 backdrop-blur-3xl border border-white/10 rounded-[73px] shadow-[0_0_100px_rgba(6,182,212,0.1)] overflow-hidden relative"
                    >
                       
                        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-cyan-500/5 blur-[120px] pointer-events-none rounded-full" />
                        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/5 blur-[120px] pointer-events-none rounded-full" />

                        <header className="px-8 py-6 flex items-center flex-shrink-0 relative z-10">
                            <button
                                onClick={handleClose} 
                                className="ml-auto p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all duration-300"
                            >
                                <X size={20} />
                            </button>
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
                                        className="w-full h-full flex items-center justify-center overflow-y-auto relative z-20"
					                    style={{ isolation: 'isolate' }}
                                    >
                                        {isReadyToRender && isAnimationComplete ? (
                                            <Elements 
					        key={`${stripeOptions?.clientSecret}-loaded`} 
						stripe={stripeObj} 
						options={stripeOptions}
					    >
                                                <AIPaymentForm
                                                    orderId={paymentDetails!.orderId}
                                                    total={paymentDetails!.total}
                                                    items={cartItems}
                                                    onPaymentSuccess={handlePaymentSuccess}
                                                />
                                            </Elements>
                                        ) : (
                                            <div className="flex flex-col items-center gap-6">
                                                {isStripeError || isKeyMissing ? (
                                                     <PaymentFatalError keyMissing={isKeyMissing} />
                                                ) : (
                                                    <div className="flex flex-col items-center gap-4">
                                                        <div className="relative">
                                                            <div className="w-20 h-20 rounded-full border-2 border-cyan-900 border-t-cyan-400 animate-spin" />
                                                            <div className="absolute inset-0 flex items-center justify-center">
                                                                <Lock size={24} className="text-cyan-400" />
                                                            </div>
                                                        </div>
                                                        <p className="text-cyan-200 font-mono text-sm tracking-[0.2em] animate-pulse">ENCRYPTING UPLINK...</p>
                                                    </div>
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
                                        className="flex-grow flex flex-col relative z-10 w-full"
        
                            >
                                        <div className="flex-grow px-4 lg:px-12 py-8 space-y-8 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent">
                                            <AnimatePresence initial={false}> 
                                                {messages.map((msg) => (
                                                    <ChatMessage
                                                        key={msg.id}
                                                        message={msg}
                                                        onSend={handleSendMessage}
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
				    onConfirmOrder={actions.confirmCurrentOrder}
                                 />
                            )}
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

