//** apps/web/components/ai/AIChatOverlay.tsx **//

'use client';

import { useRouter } from 'next/navigation'; //[cite: 1]
import { ProductDetailsCard } from '../products/ProductDetailsCard'; //[cite: 1]
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'; //[cite: 1]
import { motion, AnimatePresence, useAnimation } from 'framer-motion'; //[cite: 1]
import { 
    Bot, User, CornerDownRight, ShoppingCart, Cpu, X, 
    ChevronLeft, ChevronRight, Save, ChevronDown, ChevronUp, Trash2, Undo2, AlertCircle, 
    ShoppingBag, ShieldOff, Loader2, Wind, Navigation, Zap, 
    Activity, Signal, BrainCircuit, Lock, Star, Sparkles, Mic, Camera, Image as ImageIcon, MapPin, Clock, Eye, ShieldCheck
} from 'lucide-react'; //[cite: 1]
import { useAIOrderingStore, Message } from '../../hooks/useAIOrderingStore'; //[cite: 1]
import Image from 'next/image'; //[cite: 1]
import useEmblaCarousel from 'embla-carousel-react'; //[cite: 1]
import { loadStripe, StripeElementsOptions, Stripe } from '@stripe/stripe-js'; //[cite: 1]
import { Elements } from '@stripe/react-stripe-js'; //[cite: 1]
import AIPaymentForm from './AIPaymentForm'; //[cite: 1]
import { useSession } from "next-auth/react"; //[cite: 1]
import { useShallow } from 'zustand/react/shallow'; //[cite: 1]
import { AIVoiceOverlay } from './AIVoiceOverlay'; //[cite: 1]
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock'; //[cite: 1]
import ReactMarkdown from 'react-markdown'; //[cite: 1]
import remarkGfm from 'remark-gfm'; //[cite: 1]

// --- ENTERPRISE CONTRACT DEFINITIONS ---
export interface AIProduct {
    id: number | string;
    name: string;
    price: number | string;
    image?: string;
    image_url?: string;
    rating?: number;
    stock_level?: string;
    quantity?: number;
    product_id?: number;
}

export interface FlightData {
    mission_id: string;
    drone_id: string;
    estimated_arrival_mins: number;
    distance_km: number;
    weather_condition: string;
    status: string;
}

export interface ExtendedMessage extends Omit<Message, 'content'> {
    id: number | string;
    sender: 'ai' | 'user' | 'system';
    contentType: 'text' | 'image_user_upload' | 'error' | 'info' | 'success_text' | 'FLIGHT_MANIFEST' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'recovery_prompt' | 'cart_preview' | 'typing' | 'payment_intent' | 'ORDER_CANCELLED';
    content: string | { items: AIProduct[]; total: number };
    imageUrl?: string;
    flight_data?: FlightData;
    options?: string[];
    products?: AIProduct[];
    reason?: string;
    ai_notes?: string;
    timestamp?: number;
    intro_message?: string;
}

declare global {
    interface Window {
        webkitSpeechRecognition: any;
    }
}

const DEFAULT_PLACEHOLDER = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"; //[cite: 1]
const ZOMBIE_CONNECTION_THRESHOLD_MS = 60_000; //[cite: 1]
const SIMULATED_AUTH_DELAY_MS = 500; //[cite: 1]

const getAbsoluteImageUrl = (relativePath: string | undefined): string => { //[cite: 1]
    if (!relativePath) return DEFAULT_PLACEHOLDER; //[cite: 1]
    if (relativePath.startsWith('http') || relativePath.startsWith('data:')) return relativePath; //[cite: 1]

    const apiBase = process.env.NEXT_PUBLIC_API_URL //[cite: 1]
        ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '') //[cite: 1]
        : 'http://localhost:8000'; //[cite: 1]
    
    const cleanPath = relativePath.startsWith('/') ? relativePath : `/${relativePath}`; //[cite: 1]
    if (cleanPath.includes('default.jpeg')) return DEFAULT_PLACEHOLDER; //[cite: 1]

    return `${apiBase}${cleanPath}`; //[cite: 1]
};

const HolographicFlightDeck = React.memo(({ data }: { data: FlightData }) => {
    if (!data) return null; //[cite: 1]

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }} //[cite: 1]
            animate={{ opacity: 1, scale: 1 }} //[cite: 1]
            style={{ willChange: 'transform, opacity' }} //[cite: 1]
            className="w-full bg-[#050B14] border border-cyan-500/30 rounded-2xl overflow-hidden relative mt-2 shadow-[0_0_30px_rgba(6,182,212,0.15)] transform-gpu" //[cite: 1]
        >
            <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.05)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none" /> 
         
            <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/10 to-transparent w-[50%] skew-x-12 pointer-events-none" //[cite: 1]
                animate={{ left: ['-100%', '200%'] }} //[cite: 1]
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }} //[cite: 1]
                style={{ willChange: 'left' }} //[cite: 1]
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
                            d="M 20,60 Q 150,10 280,60" //[cite: 1]
                            fill="none" //[cite: 1]
                            stroke="rgba(6, 182, 212, 0.3)" //[cite: 1]
                            strokeWidth="2" //[cite: 1]
                            strokeDasharray="5 5" //[cite: 1]
                        />
                         <motion.path
                            d="M 20,60 Q 150,10 280,60" //[cite: 1]
                            fill="none" //[cite: 1]
                            stroke="#06b6d4" //[cite: 1]
                            strokeWidth="2" //[cite: 1]
                            initial={{ pathLength: 0 }} //[cite: 1]
                            animate={{ pathLength: 1 }} //[cite: 1]
                            transition={{ duration: 2, ease: "easeInOut" }} //[cite: 1]
                        />
                        <circle cx="20" cy="60" r="4" fill="#06b6d4" /> 
                        <text x="20" y="80" fill="gray" fontSize="10" textAnchor="middle">HQ</text> 
                        <motion.g
                            initial={{ offsetDistance: "0%" }} //[cite: 1]
                            animate={{ offsetDistance: "100%" }} //[cite: 1]
                            transition={{ duration: 10, repeat: Infinity, ease: "linear" }} //[cite: 1]
                            style={{ offsetPath: 'path("M 20,60 Q 150,10 280,60")' }} //[cite: 1]
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
    const [stats, setStats] = useState({ speed: 45, alt: 120, bat: 98, stab: 100 }); //[cite: 1]

    useEffect(() => {
        const interval = setInterval(() => { //[cite: 1]
            setStats(prev => ({ //[cite: 1]
                speed: Math.max(40, Math.min(60, prev.speed + (Math.random() - 0.5) * 5)), //[cite: 1]
                alt: Math.max(115, Math.min(125, prev.alt + (Math.random() - 0.5) * 2)), //[cite: 1]
                bat: Math.max(90, prev.bat - 0.01), //[cite: 1]
                stab: Math.min(100, Math.max(98, prev.stab + (Math.random() - 0.5))) //[cite: 1]
            })); //[cite: 1]
        }, 1000); //[cite: 1]
        return () => clearInterval(interval); //[cite: 1]
    }, []);

    const TelemetryItem = ({ icon: Icon, label, value, unit, color }: { icon: any, label: string, value: number, unit: string, color: string }) => (
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
                    initial={{ width: 0 }} //[cite: 1]
                    animate={{ width: `${Math.min(100, (value / (label === 'PWR' ? 100 : 60)) * 100)}%` }} //[cite: 1]
                    transition={{ duration: 0.5 }} //[cite: 1]
                    style={{ willChange: 'width' }} //[cite: 1]
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

const CarouselProductCard = React.memo(({ product, onSelect, onViewDetails, totalItems }: { product: AIProduct, onSelect: (product: AIProduct, elementId: string) => void, onViewDetails: (product: AIProduct) => void, totalItems: number }) => {
    const slideWidthClass = "flex-none w-[280px] snap-center"; //[cite: 1]
    const rawImagePath = product.image_url || product.image; //[cite: 1]
    const imageUrl = useMemo(() => getAbsoluteImageUrl(rawImagePath), [rawImagePath]); //[cite: 1]
    const elementId = `product-carousel-img-${product.id}`; //[cite: 1]

    const handleSelect = useCallback(() => {
        onSelect({ ...product, image: rawImagePath }, elementId); //[cite: 1]
    }, [product, rawImagePath, elementId, onSelect]);

    return (
        <div className={`embla__slide ${slideWidthClass} px-2 py-4`}> 
            <motion.div
                className="flex flex-col p-0 bg-gradient-to-br from-[#0F172A] to-[#020617] backdrop-blur-3xl rounded-[32px] border border-white/10 h-full text-left shadow-2xl relative group overflow-hidden transform-gpu" //[cite: 1]
                whileHover={{ 
                    scale: 1.02, //[cite: 1]
                    border: "1px solid rgba(6, 182, 212, 0.5)", //[cite: 1]
                    boxShadow: "0 20px 50px -12px rgba(6, 182, 212, 0.25)"  //[cite: 1]
                }}
                initial={{ opacity: 0, y: 20 }} //[cite: 1]
                animate={{ opacity: 1, y: 0 }} //[cite: 1]
                transition={{ type: 'spring', stiffness: 200, damping: 25 }} //[cite: 1]
                style={{ willChange: 'transform, opacity' }} //[cite: 1]
            >
                <motion.button
                    onClick={(e) => { e.stopPropagation(); onViewDetails(product); }} //[cite: 1]
                    initial={{ opacity: 0, y: -10 }} //[cite: 1]
                    animate={{ opacity: 1, y: 0 }} //[cite: 1]
                    whileHover={{ scale: 1.1, backgroundColor: "rgba(6, 182, 212, 1)", color: "#000" }} //[cite: 1]
                    className="absolute top-4 right-2 z-50 p-2.5 rounded-full bg-black/40 border border-white/10 text-white backdrop-blur-md opacity-60 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-500 shadow-[0_0_20px_rgba(0,0,0,0.5)] transform-gpu" //[cite: 1]
                    title="Inspect Hologram" //[cite: 1]
                >
                    <Eye size={18} strokeWidth={2.5} /> 
                </motion.button>
                
                <div className="relative h-48 w-full flex items-center justify-center bg-gradient-to-b from-white/5 to-transparent p-4 overflow-hidden"> 
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" /> 
                    <Image
                        id={elementId} //[cite: 1]
                        src={imageUrl} //[cite: 1]
                        alt={product.name} //[cite: 1]
                        width={250} //[cite: 1]
                        height={250} //[cite: 1]
                        loading="lazy" //[cite: 1]
                        decoding="async" //[cite: 1]
                        className="w-auto h-full object-contain drop-shadow-[0_10px_20px_rgba(0,0,0,0.5)] group-hover:scale-110 group-hover:-rotate-2 transition-transform duration-500 cubic-bezier(0.34, 1.56, 0.64, 1) transform-gpu" //[cite: 1]
                    />
                </div>

                <div className="p-5 flex flex-col flex-grow relative z-10"> 
                  
                    <div className="flex justify-between items-start mb-2"> 
                         <h4 className="text-lg font-medium text-white leading-tight tracking-[-0.01em] break-words" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>{product.name}</h4> 
                    </div>
                   
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-2"> 
                      <div className="flex min-w-0 items-center gap-2"> 
                        {product.rating ? ( //[cite: 1]
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
             
                   {product.stock_level ? ( //[cite: 1]

                    <div className="mt-4"> 
                      <div className="inline-flex items-center rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-200 sm:text-sm"> 
                    {product.stock_level} 
                 </div>
               </div>
             ) : null}

                    <div className="mt-auto pt-4 border-t border-white/5"> 
                        <motion.button
                            whileHover={{ scale: 1.02 }} //[cite: 1]
                            whileTap={{ scale: 0.96 }} //[cite: 1]
                            onClick={handleSelect} //[cite: 1]
                            className="w-full relative overflow-hidden rounded-full bg-white text-black font-medium px-4 py-3 flex items-center justify-center gap-2 group/btn shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all duration-300 transform-gpu" //[cite: 1]
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

const ProductCarousel = React.memo(({ products, onViewDetails, onSelect }: { products: AIProduct[], onSelect: (product: AIProduct, elementId: string) => void, onViewDetails: (product: AIProduct) => void }) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'start', containScroll: 'trimSnaps', dragFree: false }); //[cite: 1]
    
    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]); //[cite: 1]
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]); //[cite: 1]
    
    const canScroll = products.length > 1; //[cite: 1]

    return (
        <div className="relative my-6 px-0 group/carousel w-full overflow-visible"> 
            <div className="overflow-hidden p-2 -mx-4" ref={emblaRef}> 
                <div className="flex gap-2 pl-4 pr-8 snap-x snap-mandatory"> 
                    {products.map((p, i) => (
                        <CarouselProductCard 
                            key={p.id || i} //[cite: 1]
                            product={p} //[cite: 1]
                            onSelect={onSelect} //[cite: 1]
                            onViewDetails={onViewDetails} //[cite: 1]
                            totalItems={products.length} //[cite: 1]
                        />
                    ))}
                </div>
            </div>
            {canScroll && ( //[cite: 1]
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
        initial={{ opacity: 0, height: 0, scale: 0.95 }} //[cite: 1]
        animate={{ opacity: 1, height: 'auto', scale: 1 }} //[cite: 1]
        style={{ willChange: 'transform, opacity, height' }} //[cite: 1]
        className="flex items-start gap-3 p-4 mt-4 bg-[#0A1116] border border-cyan-900/50 rounded-2xl max-w-lg relative overflow-hidden transform-gpu" //[cite: 1]
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
    const [isExpanded, setIsExpanded] = useState(false); //[cite: 1]

    const needsExpansion = text.length > 250 || text.split('\n').length > 4; //[cite: 1]

    if (!needsExpansion) { //[cite: 1]
        return <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-normal">{text}</p>; //[cite: 1]
    }

    return (
        <div className="flex flex-col w-full"> 
            <motion.div
                initial={false} //[cite: 1]
                animate={{ height: isExpanded ? 'auto' : '71px' }}  //[cite: 1]
                className="overflow-hidden relative transform-gpu" //[cite: 1]
                style={{ willChange: 'height' }} //[cite: 1]
            >
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-normal"> 
                    {text}
                </p>
               
            </motion.div>

            <button
                onClick={() => setIsExpanded(!isExpanded)} //[cite: 1]
                className="mt-0.5 flex items-center justify-center p-1 hover:bg-white/10 rounded-full transition-colors self-end text-cyan-400 group" //[cite: 1]
                title={isExpanded ? "Hide Details" : "Show More"}
            >
                {isExpanded ? ( //[cite: 1]
                    <ChevronUp size={18} className="group-hover:-translate-y-0.5 transition-transform" /> 
                ) : (
                    <ChevronDown size={18} className="group-hover:translate-y-0.5 transition-transform animate-bounce" /> 
                )}
            </button>
        </div>
    );
});
ExpandableUserMessage.displayName = 'ExpandableUserMessage';

const ChatMessage = React.memo(({ message, onSend, onViewDetails, isActiveAction, onNavigateToAuth, onProductSelect, onConfirmOrder, onClearCart, onRestore, onSave, onCancel }: { 
    message: ExtendedMessage, 
    onSend: (t: string) => void, 
    onViewDetails: (p: AIProduct) => void, 
    isActiveAction: boolean, 
    onNavigateToAuth: (mode: 'SIGNIN'|'SIGNUP') => void, 
    onProductSelect: (p: AIProduct, id: string) => void,
    onConfirmOrder: () => void,
    onClearCart: () => void,
    onRestore: () => void,
    onSave: () => void,
    onCancel: () => void
}) => {
    const isAI = message.sender === 'ai'; //[cite: 1]

    const renderContent = () => {
        switch (message.contentType) { //[cite: 1]
            case 'image_user_upload':
                const hasCaption = typeof message.content === 'string' && message.content.trim().length > 0 &&  //[cite: 1]
                                  !message.content.includes("Analyzing") &&  //[cite: 1]
                                  !message.content.includes("Processing"); //[cite: 1]
                const hasImg = !!message.imageUrl; //[cite: 1]

                return (
                    <div className="flex flex-col gap-2 items-end w-full"> 
                        {hasImg && ( //[cite: 1]
                            <div className="relative w-[100px] sm:w-[140px] aspect-[4/3] flex-none overflow-hidden shadow-sm rounded-xl border border-white/10 bg-black/20"> 
                               
                                <Image
                                    src={message.imageUrl!} //[cite: 1]
                                    alt="Uploaded" //[cite: 1]
                                    fill //[cite: 1]
                                    loading="lazy" //[cite: 1]
                                    decoding="async" //[cite: 1]
                                    className="object-contain" //[cite: 1]
                                />
                            </div>
                        )}
                        {hasCaption && ( //[cite: 1]
                             <div className="px-4 py-3 rounded-[32px] rounded-br-none bg-zinc-900 text-gray-100 text-[14px] leading-relaxed break-words max-w-[90%] shadow-md"> 
                                {typeof message.content === 'string' ? message.content : ''}
                             </div>
                        )}
                    </div>
                );
            case 'text':
            case 'error':
            case 'info':
            case 'success_text':
                
                if (!isAI && message.contentType === 'text') { //[cite: 1]
                    return <ExpandableUserMessage text={typeof message.content === 'string' ? message.content : ''} />; //[cite: 1]
                }
                return (
                    <div className={`text-[12px] leading-relaxed text-white/90 font-normal break-words w-full space-y-2 ${message.contentType === 'error' ? 'bg-red-950/20 p-2 rounded' : ''}`}> 
                        <ReactMarkdown 
                            remarkPlugins={[remarkGfm]} //[cite: 1]
                            components={{
                                p: ({ node, ...props }) => ( //[cite: 1]
                                    <p className="mb-3 last:mb-0 text-left whitespace-pre-wrap leading-normal" {...props} /> //[cite: 1]
                                ),
                                strong: ({ node, ...props }) => ( //[cite: 1]
                                    <strong className="font-bold text-white" {...props} /> //[cite: 1]
                                ),
                                ul: ({ node, ...props }) => ( //[cite: 1]
                                    <ul className="list-disc list-inside space-y-1.5 mb-3 mt-1.5 last:mb-0" {...props} /> //[cite: 1]
                                ),
                                li: ({ node, ...props }) => ( //[cite: 1]
                                    <li className="pl-0 leading-normal" {...props} /> //[cite: 1]
                                ),
                            }}
                        >
                            {typeof message.content === 'string' ? message.content : ''}
                        </ReactMarkdown>
                    </div>
                );
            case 'FLIGHT_MANIFEST':
                return (
                    <div className="w-full -ml-2"> 
                         <p className="whitespace-pre-line mb-2 text-sm px-2 leading-relaxed text-white font-medium"> 
                             {typeof message.content === 'string' ? message.content : ''}
                         </p>
                         {message.flight_data && <HolographicFlightDeck data={message.flight_data} />}
                    </div>
                );
            case 'confirmation_prompt':
                if (!isActiveAction) return null; //[cite: 1]
                return (
                    <div>
                        <p className="whitespace-pre-wrap mb-4 text-[12px] leading-relaxed text-white/90 font-normal">{typeof message.content === 'string' ? message.content : ''}</p> 
                        {isActiveAction && ( //[cite: 1]
                            <div className="flex flex-wrap gap-3"> 
                                {message.options?.map((option: string) => { //[cite: 1]
                                    const isConfirm = option === 'Confirm Order'; //[cite: 1]
                                
                                    let buttonStyle = "bg-white/5 text-cyan-200 border-white/10 hover:bg-cyan-500 hover:text-black"; //[cite: 1]
                                
                                    if (isConfirm) { //[cite: 1]
                                        buttonStyle = "bg-gradient-to-r from-cyan-400 to-cyan-500 text-[#020617] border-transparent shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_35px_rgba(6,182,212,0.6)]"; //[cite: 1]
                                    } 
                                    else if (option === 'Switch to PayPal') { //[cite: 1]
                                        buttonStyle = "bg-[#003087] text-white border-transparent hover:bg-[#003087]/80";  //[cite: 1]
                                    }
                                    else if (option === 'Retry Payment') { //[cite: 1]
                                        buttonStyle = "bg-green-600 text-white hover:bg-green-500 border-transparent shadow-[0_0_15px_rgba(22,163,74,0.3)]"; //[cite: 1]
                                    }

                                    return (
                                        <motion.button
                                            key={option} //[cite: 1]
                                            whileHover={{ scale: 1.05 }} //[cite: 1]
                                            whileTap={{ scale: 0.95 }} //[cite: 1]
                                            onClick={() => { //[cite: 1]
                                                if (option === 'Confirm Order') onConfirmOrder();  //[cite: 1]
                                                else if (option === 'Clear Cart') onClearCart(); //[cite: 1]
                                                else if (option === 'Sign In') onNavigateToAuth('SIGNIN'); //[cite: 1]
                                                else if (option === 'Sign Up') onNavigateToAuth('SIGNUP'); //[cite: 1]
                                                else if (option === 'Switch to PayPal') onSend("I want to use PayPal"); //[cite: 1]
                                                else if (option === 'Retry Payment') onConfirmOrder();  //[cite: 1]
                                                else if (option === 'Save for Later') onSave(); //[cite: 1]
                                                else onSend(option); //[cite: 1]
                                            }}
                                            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-full border transition-all duration-300 transform-gpu ${buttonStyle}`} //[cite: 1]
                                        >
                                            {isConfirm && <Zap size={16} strokeWidth={2.5} />} 
                                        
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
                        <p className="whitespace-pre-wrap mb-2 text-[12px] px-2 leading-relaxed text-white/90 font-normal">{typeof message.content === 'string' ? message.content : ''}</p> 
                        

<ProductCarousel products={message.products || []} onSelect={onProductSelect} onViewDetails={onViewDetails} /> 
                        {(message.reason || message.ai_notes) && ( //[cite: 1]
                            <div className="px-2"> 
                                <AIReasoning text={(message.reason || message.ai_notes) as string} /> 
                            </div>
                        )}
                    </div>
                );
            case 'recovery_prompt':
               if (!isActiveAction) return null; //[cite: 1]
               return (
                  <div className="flex items-center justify-center w-full py-4"> 
                     <motion.div 
                         initial={{ scale: 0.9, opacity: 0, y: 10 }} //[cite: 1]
                         animate={{ scale: 1, opacity: 1, y: 0 }} //[cite: 1]
                         style={{ willChange: 'transform, opacity' }} //[cite: 1]
                         className="flex items-center gap-2 p-2 bg-white/[0.04] backdrop-blur-3xl border border-white/10 rounded-[55px] shadow-2xl transform-gpu" //[cite: 1]
                     >
                         {[
                             { icon: Undo2, label: "UNDO", action: onRestore, textColor: "text-white", hoverBg: "hover:bg-cyan-500/10" }, //[cite: 1]
                             { icon: Save, label: "SAVE", action: onSave, textColor: "text-white", hoverBg: "hover:bg-purple-500/10" }, //[cite: 1]
                             { icon: X, label: "CANCEL", action: onCancel, textColor: "text-white", hoverBg: "hover:bg-red-500/10" } //[cite: 1]
                         ].map((btn, idx) => ( //[cite: 1]
                             <motion.button 
                                 key={idx} //[cite: 1]
                                 whileHover={{ scale: 1.05 }} //[cite: 1]
                                 whileTap={{ scale: 0.95 }} //[cite: 1]
                                 onClick={btn.action}  //[cite: 1]
                                 className={`flex flex-col items-center justify-center min-w-[60px] h-[60px] gap-2 rounded-full transition-all duration-300 transform-gpu ${btn.hoverBg} group`} //[cite: 1]
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
            default: return null; //[cite: 1]
        }
    };

    const contentNode = renderContent(); //[cite: 1]

    if (['cart_preview', 'typing', 'payment_intent', 'ORDER_CANCELLED', 'system'].includes(message.contentType)) return null; //[cite: 1]
    if (!contentNode) return null; //[cite: 1]

    return (
        <motion.div
            layout //[cite: 1]
            initial={{ opacity: 0, y: 20, scale: 0.98 }} //[cite: 1]
            animate={{ opacity: 1, y: 0, scale: 1 }} //[cite: 1]
            style={{ willChange: 'transform, opacity' }} //[cite: 1]
            className={`flex items-end gap-2 w-full mb-4 transform-gpu ${isAI ? 'justify-start' : 'justify-end'}`} //[cite: 1]
        >
            <div className={`w-fit max-w-[98%] ${ //[cite: 1]
                message.contentType === 'image_user_upload'  //[cite: 1]
                    ? ''  //[cite: 1]
                    : `px-4 py-3 ${isAI  //[cite: 1]
                        ? 'rounded-[32px] rounded-bl-none bg-[#050B14]/80 backdrop-blur-xl border border-white/5 text-gray-100 shadow-xl shadow-black/20'   //[cite: 1]
                        : 'w-fit max-w-[90%] px-4 py-4 rounded-[32px] rounded-br-none bg-zinc-900 text-gray-100 text-[14px] leading-relaxed break-words shadow-md'}` //[cite: 1]
            } transform-gpu`}> 
                {contentNode} 
            </div>
        </motion.div>
    );

}, (prevProps, nextProps) => {
    return prevProps.message.id === nextProps.message.id &&  //[cite: 1]
           prevProps.message.content === nextProps.message.content && //[cite: 1]
           prevProps.isActiveAction === nextProps.isActiveAction; //[cite: 1]
});
ChatMessage.displayName = 'ChatMessage';

const AIChatSidebar = React.memo(({ messages, glowingProductId, onRemoveItem, isMobileOpen, onCloseMobile }: {
    messages: ExtendedMessage[],
    glowingProductId: number | null,
    onRemoveItem: (productId: number) => void,
    isMobileOpen: boolean,
    onCloseMobile: () => void
}) => {
    const cart = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview'); //[cite: 1]
        return (lastCartMessage?.content as { items: AIProduct[]; total: number }) || { items: [], total: 0 }; //[cite: 1]
    }, [messages]);

    return (
        <>
            <AnimatePresence>
                {isMobileOpen && ( //[cite: 1]
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} //[cite: 1]
                        onClick={onCloseMobile} //[cite: 1]
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm z-[100] transform-gpu" //[cite: 1]
                        style={{ willChange: 'opacity' }} //[cite: 1]
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
                            {cart.items.length === 0 ? ( //[cite: 1]
                                <motion.div 
                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} //[cite: 1]
                                    className="flex flex-col items-center justify-center h-48 text-gray-600 gap-3 border border-dashed border-white/5 rounded-3xl bg-white/[0.02]" //[cite: 1]
                                >
                                    <ShoppingCart size={32} className="opacity-30" /> 
                                    <p className="text-xs uppercase tracking-widest font-mono">Empty | Cart</p> 
                                </motion.div>
                            ) : cart.items.map((item: AIProduct, index: number) => ( //[cite: 1]
                                <motion.div
                                    key={item.product_id || index} //[cite: 1]
                                    layout //[cite: 1]
                                    initial={{ opacity: 0, x: -20 }} //[cite: 1]
                                    animate={{
                                        opacity: 1, //[cite: 1]
                                        x: 0, //[cite: 1]
                                        backgroundColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.15)" : "rgba(255, 255, 255, 0.03)", //[cite: 1]
                                        borderColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.5)" : "rgba(255, 255, 255, 0.05)", //[cite: 1]
                                    }}
                                    exit={{ opacity: 0, x: 20 }} //[cite: 1]
                                    style={{ willChange: 'transform, opacity, background-color, border-color' }} //[cite: 1]
                                    className="flex justify-between items-start p-3 rounded-2xl border transition-colors group relative overflow-hidden transform-gpu" //[cite: 1]
                                >
                                    {item.product_id === glowingProductId && ( //[cite: 1]
                                        <motion.div layoutId="glow" className="absolute inset-0 bg-cyan-500/5 pointer-events-none" transition={{ duration: 0.3 }} /> //[cite: 1]
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
                                            ${(Number(item.price) * (item.quantity || 1)).toFixed(2)} 
                                        </span>
                                        <button
                                            type="button" //[cite: 1]
                                            onClick={(e) => { //[cite: 1]
                                                e.stopPropagation();  //[cite: 1]
                                                onRemoveItem(Number(item.product_id || item.id));  //[cite: 1]
                                            }}
                                            className="p-1.5 rounded-lg bg-red-500/10 text-red-400 active:bg-red-500 active:text-white md:hover:bg-red-500 md:hover:text-white transition-all duration-200" //[cite: 1]
                                            title="Jettison Item" //[cite: 1]
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
    const [value, setValue] = useState(''); //[cite: 1]
    const [pendingImage, setPendingImage] = useState<{ url: string; base64: string } | null>(null); //[cite: 1]
    const [isListening, setIsListening] = useState(false); //[cite: 1]
    const fileInputRef = useRef<HTMLInputElement>(null); //[cite: 1]
    const textareaRef = useRef<HTMLTextAreaElement>(null); //[cite: 1]

    const handleAutoResize = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setValue(e.target.value); //[cite: 1]
        requestAnimationFrame(() => { //[cite: 1]
            if (textareaRef.current) { //[cite: 1]
                textareaRef.current.style.height = 'auto'; //[cite: 1]
                textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`; //[cite: 1]
            }
        });
    }, []);

    const toggleVoice = useCallback(() => {
        if (!('webkitSpeechRecognition' in window)) { //[cite: 1]
            alert("Voice module not supported in this browser sector."); //[cite: 1]
            return; //[cite: 1]
        }
        
        if (isListening) { //[cite: 1]
            setIsListening(false); //[cite: 1]
            return; //[cite: 1]
        }

        const recognition = new window.webkitSpeechRecognition(); //[cite: 1]
        recognition.continuous = false; //[cite: 1]
        recognition.interimResults = false; //[cite: 1]
        recognition.lang = 'en-US'; //[cite: 1]

        recognition.onstart = () => setIsListening(true); //[cite: 1]
        recognition.onend = () => setIsListening(false); //[cite: 1]
        recognition.onresult = (event: any) => { //[cite: 1]
            const transcript = event.results[0][0].transcript; //[cite: 1]
            setValue(transcript); //[cite: 1]
        };
        recognition.start(); //[cite: 1]
    }, [isListening]);

    const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]; //[cite: 1]
        if (!file) return; //[cite: 1]

        const reader = new FileReader(); //[cite: 1]
        reader.onloadend = () => { //[cite: 1]
            const fullDataUrl = reader.result as string; //[cite: 1]
            const base64Raw = fullDataUrl.split(',')[1]; //[cite: 1]
            setPendingImage({ url: fullDataUrl, base64: base64Raw }); //[cite: 1]
        };
        reader.readAsDataURL(file); //[cite: 1]
        e.target.value = '';  //[cite: 1]
    }, []);

    const handleTriggerSend = useCallback(() => {
        if (isTyping || isProcessing || (!value.trim() && !pendingImage)) return; //[cite: 1]
        if (pendingImage) { //[cite: 1]
            onSendImage(pendingImage.url, pendingImage.base64, value); //[cite: 1]
            setPendingImage(null);  //[cite: 1]
            setValue(''); //[cite: 1]
        } else if (value.trim()) { //[cite: 1]
            onSend(value); //[cite: 1]
            setValue(''); //[cite: 1]
        }
        if (textareaRef.current) { //[cite: 1]
            textareaRef.current.style.height = 'auto'; //[cite: 1]
            textareaRef.current.style.height = '56px';  //[cite: 1]
        }
    }, [isTyping, isProcessing, pendingImage, value, onSendImage, onSend]);

    const isInputLocked = isTyping || isProcessing; //[cite: 1]
    const isSendButtonDisabled = isInputLocked || (!value.trim() && !pendingImage); //[cite: 1]
    const hasInput = value.length > 0 || pendingImage !== null; //[cite: 1]
    return (
      <div className="p-6 border-t border-white/5 flex-shrink-0 bg-[#020617]/50 backdrop-blur-md relative z-20"> 
         <input type="file" ref={fileInputRef} accept="image/*" className="hidden" onChange={handleImageSelect} /> 

        <AnimatePresence>
            {pendingImage && ( //[cite: 1]
                <motion.div 
                    initial={{ opacity: 0, y: 10, height: 0 }} //[cite: 1]
                    animate={{ opacity: 1, y: 0, height: 'auto' }} //[cite: 1]
                    exit={{ opacity: 0, y: 10, height: 0 }} //[cite: 1]
                    style={{ willChange: 'transform, opacity, height' }} //[cite: 1]
                    className="absolute -top-18 left-6 z-30 transform-gpu" //[cite: 1]
                >
                    <div className="relative group"> 
                        <div className="w-20 h-20 rounded-xl overflow-hidden border border-cyan-500/50 shadow-lg bg-black/50 backdrop-blur-md"> 
                            <Image src={pendingImage.url} alt="Preview" width={80} height={80} className="object-cover w-full h-full" /> 
                        </div>
                        <button 
                            onClick={() => setPendingImage(null)} //[cite: 1]
                            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 shadow-md hover:scale-110 transition-transform" //[cite: 1]
                        >
                            <X size={12} /> 
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>

        <div className="relative group max-w-4xl mx-auto flex items-center gap-2"> 
          <AnimatePresence>
              {!hasInput && ( //[cite: 1]
                  <motion.div
                      initial={{ width: 0, opacity: 0, scale: 0.8 }} //[cite: 1]
                      animate={{ width: 'auto', opacity: 1, scale: 1 }} //[cite: 1]
                      exit={{ width: 0, opacity: 0, scale: 0.5 }} //[cite: 1]
                      transition={{ type: "spring", stiffness: 400, damping: 25 }} //[cite: 1]
                      className="flex items-center gap-2 overflow-hidden flex-shrink-0 origin-left" //[cite: 1]
                      style={{ willChange: 'width, opacity, transform' }} //[cite: 1]
                  >
                    <button
                      type="button" //[cite: 1]
                      onClick={() => fileInputRef.current?.click()} //[cite: 1]
                      className="p-3 rounded-full bg-white/5 text-white hover:bg-cyan-500/20 transition-all border border-white/5 hover:border-cyan-500/50" //[cite: 1]
                      title="Upload Visual Data" //[cite: 1]
                    >
                      <Camera size={20} /> 
                    </button>

                    <button
                      type="button" //[cite: 1]
                      onClick={() => useAIOrderingStore.getState().setVoiceMode(true)} //[cite: 1]
                      className="p-3 rounded-full bg-white/5 text-white hover:bg-cyan-500/20 transition-all border border-white/5 hover:border-cyan-500/50 group" //[cite: 1]
                      title="Talk to order with air" //[cite: 1]
                    >
                      <Mic size={20} className="group-hover:scale-110 transition-transform" /> 
                    </button>
                </motion.div>
             )}
         </AnimatePresence>
         <div className="relative flex-grow min-w-0"> 
           <textarea
               ref={textareaRef} //[cite: 1]
               value={value} //[cite: 1]
               onChange={handleAutoResize} //[cite: 1]
               rows={1} //[cite: 1]
               onFocus={() => { //[cite: 1]
                   setTimeout(() => { //[cite: 1]
                       if (textareaRef.current) { //[cite: 1]
                           textareaRef.current.scrollIntoView({ //[cite: 1]
                               behavior: 'smooth', //[cite: 1]
                               block: 'center' //[cite: 1]
                           });
                       }
                   }, 300); //[cite: 1]
               }}
               onKeyDown={(e) => { //[cite: 1]
                   if (e.key === 'Enter' && !e.shiftKey) { //[cite: 1]
                       e.preventDefault();  //[cite: 1]
                       if (!isSendButtonDisabled) handleTriggerSend(); //[cite: 1]
                   }
               }}
               placeholder={isListening ? 'Listening...' : isInputLocked ? 'Thinking...' : 'Ask order with air...'} //[cite: 1]
               disabled={isInputLocked} //[cite: 1]
               className="w-full bg-gray-800 border border-gray-800 rounded-[28px] py-[14px] pr-16 pl-6 text-gray-100 placeholder-gray-400 focus:bg-gray-800  placeholder:whitespace-nowrap focus:border-none focus:outline-none transition-all duration-300 font-medium shadow-lg resize-none overflow-hidden no-scrollbar min-h-[52px] leading-relaxed" //[cite: 1]
               style={{ overflowY: textareaRef.current && textareaRef.current.scrollHeight > 150 ? 'auto' : 'hidden' }} //[cite: 1]
           />
            <button
                disabled={isSendButtonDisabled} //[cite: 1]
                onClick={handleTriggerSend} //[cite: 1]
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full  bg-cyan-600 hover:bg-cyan-500 disabled:bg-transparent disabled:text-gray-500 text-white transition-all" //[cite: 1]
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
  const flyQueue = useAIOrderingStore(useShallow(state => state.flyQueue)); //[cite: 1]
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
          
          const TARGET_SIZE = 10; //[cite: 1]
          const targetScale = TARGET_SIZE / Math.max(startRect.width, 1); //[cite: 1]
          
          const midY = Math.min(startRect.top, endPos.top) - 80;  //[cite: 1]

          return (
            <motion.div
              key={item.animationId} //[cite: 1]
              className="fixed z-[9999] rounded-full overflow-hidden border-2 border-cyan-400 shadow-[0_0_30px_rgba(6,182,212,0.8)] transform-gpu" //[cite: 1]
              style={{ 
                  position: 'fixed', //[cite: 1]
                  top: 0, //[cite: 1]
                  left: 0, //[cite: 1]
                  pointerEvents: 'none', //[cite: 1]
                  width: startRect.width,  //[cite: 1]
                  height: startRect.height,  //[cite: 1]
                  willChange: 'transform, opacity'  //[cite: 1]
              }}
              initial={{ 
                  x: startRect.left, //[cite: 1]
                  y: startRect.top, //[cite: 1]
                  opacity: 1, //[cite: 1]
                  scale: 0.6, //[cite: 1]
                  rotate: 0 //[cite: 1]
              }}
              animate={{ 
                  x: [startRect.left, endPos.left - 10],  //[cite: 1]
                  y: [startRect.top, midY, endPos.top - 10],  //[cite: 1]
                  opacity: [1, 1, 0], //[cite: 1]
                  scale: [0.6, 0.75, targetScale], //[cite: 1]
                  rotate: [0, -20, 360] //[cite: 1]
              }}
              transition={{ 
                  duration: 0.7, //[cite: 1]
                  ease: "easeInOut", //[cite: 1]
                  times: [0, 0.3, 1] //[cite: 1]
              }}
              onAnimationComplete={() => removeFlyItem(item.animationId)} //[cite: 1]
            >
              <Image src={imageSource} alt="product" width={100} height={100} priority className="w-full h-full object-cover" /> 
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
            {keyMissing  //[cite: 1]
                ? "Configuration Error: Stripe Public Key missing. System cannot initiate secure tunnel."  //[cite: 1]
                : "Critical Protocol Failure: Unable to load payment processor module."} 
        </p>
    </div>
));
PaymentFatalError.displayName = 'PaymentFatalError';

// ============================================================================
// --- MAIN COMPONENT ---
// ============================================================================

export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    const router = useRouter();    //[cite: 1]
    const [detailProduct, setDetailProduct] = useState<AIProduct | null>(null); //[cite: 1]
    const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false); //[cite: 1]
    
    useBodyScrollLock({ locked: isOpen }); //[cite: 1]
    const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || ''; //[cite: 1]
    const stripePromise: Promise<Stripe | null> | null = useMemo(() => { //[cite: 1]
        return STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : null; //[cite: 1]
    }, [STRIPE_PUBLISHABLE_KEY]); //[cite: 1]
    
    const [stripeObj, setStripeObj] = useState<Stripe | null>(null); //[cite: 1]
    const [isStripeError, setIsStripeError] = useState(false); //[cite: 1]
    const [isAnimationComplete, setIsAnimationComplete] = useState(false); //[cite: 1]

    useEffect(() => {
        if (stripePromise) { //[cite: 1]
            stripePromise //[cite: 1]
                .then(stripe => { setStripeObj(stripe); setIsStripeError(false); }) //[cite: 1]
                .catch(err => { console.error("Stripe Load Error:", err); setIsStripeError(true); }); //[cite: 1]
        } else {
            setIsStripeError(true); //[cite: 1]
        }
    }, [stripePromise]);
    
    const messages = useAIOrderingStore(useShallow(state => state.messages)) as ExtendedMessage[]; //[cite: 1]
    const isLoading = useAIOrderingStore(state => state.isLoading); //[cite: 1]
    const isProcessing = useAIOrderingStore(state => state.isProcessing); //[cite: 1]
    const paymentDetails = useAIOrderingStore(useShallow(state => state.paymentDetails)); //[cite: 1]
    const glowingProductId = useAIOrderingStore(state => state.glowingProductId); //[cite: 1]
    const socketStatus = useAIOrderingStore(state => state.socketStatus); //[cite: 1]
    
    const actions = useAIOrderingStore( //[cite: 1]
        useShallow(state => ({ //[cite: 1]
            sendMessage: state.sendMessage, //[cite: 1]
            sendImage: state.sendImage, //[cite: 1]
            addProductById: state.addProductById, //[cite: 1]
            setOverlayVisible: state.setOverlayVisible, //[cite: 1]
            resetChat: state.resetChat, //[cite: 1]
            removeProductById: state.removeProductById, //[cite: 1]
            initiateCheckoutRecovery: state.initiateCheckoutRecovery, //[cite: 1]
            confirmCurrentOrder: state.confirmCurrentOrder, //[cite: 1]
            clearCart: state.clearCart, //[cite: 1]
            restoreCheckout: state.restoreCheckout, //[cite: 1]
            saveForLater: state.saveForLater, //[cite: 1]
            hardCancelOrder: state.hardCancelOrder, //[cite: 1]
            addSocketAIMessage: state.addSocketAIMessage, //[cite: 1]
            connectSocket: state.connectSocket, //[cite: 1]
            disconnectSocket: state.disconnectSocket //[cite: 1]
        }))
    );

    const { data: session, status } = useSession(); //[cite: 1]
    const chatEndRef = useRef<HTMLDivElement>(null); //[cite: 1]
    const currentAccessToken = (session as any)?.accessToken; //[cite: 1]
    const isConnectedRef = useRef(false); //[cite: 1]

    const cartItems = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview'); //[cite: 1]
        return (lastCartMessage?.content as { items: AIProduct[] })?.items || []; //[cite: 1]
    }, [messages]);
    
    const cartControls = useAnimation(); //[cite: 1]
    const prevCartCountRef = useRef(cartItems.length); //[cite: 1]

    useEffect(() => {
        if (cartItems.length > prevCartCountRef.current) { //[cite: 1]
            cartControls.start({ //[cite: 1]
                scale: [1, 1.25, 0.9, 1.1, 1], //[cite: 1]
                rotate: [0, -12, 12, -6, 6, 0], //[cite: 1]
                transition: { duration: 0.5, ease: "easeInOut" } //[cite: 1]
            });
        }
        prevCartCountRef.current = cartItems.length; //[cite: 1]
    }, [cartItems.length, cartControls]);

    const activeActionId = useMemo(() => {
        const lastActionable = [...messages].reverse().find(m => //[cite: 1]
            ['confirmation_prompt', 'recovery_prompt'].includes(m.contentType) //[cite: 1]
        );
        return lastActionable?.id; //[cite: 1]
    }, [messages]);

    useEffect(() => {
        if (status === 'authenticated' && currentAccessToken && !isConnectedRef.current) { //[cite: 1]
            isConnectedRef.current = true;  //[cite: 1]
            actions.connectSocket(currentAccessToken); //[cite: 1]
        } else if (status === 'unauthenticated') { //[cite: 1]
            isConnectedRef.current = false; //[cite: 1]
            actions.disconnectSocket(); //[cite: 1]
        }
        return () => { 
            isConnectedRef.current = false;  //[cite: 1]
            actions.disconnectSocket();  //[cite: 1]
        };
    }, [status, currentAccessToken, actions]);

    useEffect(() => {
        const scrollContainer = chatEndRef.current?.parentElement; //[cite: 1]
        if (!scrollContainer) return; //[cite: 1]

        let rafId: number; //[cite: 1]
        let timeoutId: NodeJS.Timeout; //[cite: 1]

        const performScroll = () => { //[cite: 1]
            rafId = requestAnimationFrame(() => { //[cite: 1]
                const targetTop = scrollContainer.scrollHeight + 150; //[cite: 1]
            
                if (scrollContainer.scrollTop !== targetTop) { //[cite: 1]
                    scrollContainer.scrollTo({ //[cite: 1]
                        top: targetTop, //[cite: 1]
                        behavior: 'smooth' //[cite: 1]
                   });
                }
            });
        };

        performScroll(); //[cite: 1]
        timeoutId = setTimeout(performScroll, 400); //[cite: 1]

        return () => {
            cancelAnimationFrame(rafId); //[cite: 1]
            clearTimeout(timeoutId); //[cite: 1]
        };
    }, [messages, isLoading, activeActionId]);
    
    useEffect(() => {
        if (!paymentDetails) setIsAnimationComplete(false); //[cite: 1]
    }, [paymentDetails]);

    const hasTriggeredRecoveryRef = useRef(false); //[cite: 1]
    useEffect(() => {
        hasTriggeredRecoveryRef.current = false; //[cite: 1]
    }, [cartItems.length, paymentDetails]);

    const handleClose = useCallback(() => {
        if (paymentDetails && !isProcessing) { //[cite: 1]
            if (hasTriggeredRecoveryRef.current) { //[cite: 1]
                onClose(); //[cite: 1]
            } else {
                actions.initiateCheckoutRecovery(); //[cite: 1]
                hasTriggeredRecoveryRef.current = true; //[cite: 1]
            }
        } else if (!paymentDetails) { //[cite: 1]
            onClose(); //[cite: 1]
        }
    }, [paymentDetails, isProcessing, onClose, actions]);
    
    const handlePaymentSuccess = useCallback(() => {
        actions.setOverlayVisible(false); //[cite: 1]
        onClose(); //[cite: 1]
        actions.resetChat(); //[cite: 1]
    }, [onClose, actions]);
    
    const handleSendMessage = useCallback((rawText: string) => {
        const text = rawText.trim(); //[cite: 1]
        if (!text) return; //[cite: 1]

        if (status !== 'authenticated') { //[cite: 1]
            useAIOrderingStore.setState(state => ({ //[cite: 1]
                messages: [...state.messages, { id: Date.now(), sender: 'user', contentType: 'text', content: text }], //[cite: 1]
                isLoading: true //[cite: 1]
            }));
            setTimeout(() => { //[cite: 1]
                actions.addSocketAIMessage({ //[cite: 1]
                    type: 'confirmation_prompt', //[cite: 1]
                    content: "Hey there! Ready to experience smart shopping? Let's get you set up in seconds.", //[cite: 1]
                    options: ["Sign In", "Sign Up"], //[cite: 1]
                });
                useAIOrderingStore.setState({ isLoading: false }); //[cite: 1]
            }, 500); //[cite: 1]
            return; //[cite: 1]
        }
        actions.sendMessage(text, false); //[cite: 1]
    }, [status, actions]);

    const handleProductSelect = useCallback((product: AIProduct, elementId: string): void => {
        if (status !== 'authenticated') { //[cite: 1]
            useAIOrderingStore.setState({ isLoading: true }); //[cite: 1]
          
            window.setTimeout(() => { //[cite: 1]
                actions.addSocketAIMessage({ //[cite: 1]
                    type: 'confirmation_prompt', //[cite: 1]
                    content: 'Sign in to secure your selection.', //[cite: 1]
                    options: ['Sign In', 'Sign Up'], //[cite: 1]
                });
                useAIOrderingStore.setState({ isLoading: false }); //[cite: 1]
            }, SIMULATED_AUTH_DELAY_MS); //[cite: 1]
          
            return; //[cite: 1]
        }

        const { messages } = useAIOrderingStore.getState(); //[cite: 1]
        const lastMessage = messages[messages.length - 1] as ExtendedMessage; //[cite: 1]
        const lastActiveTime = lastMessage?.timestamp ?? 0; //[cite: 1]

        const isZombieConnection = (Date.now() - lastActiveTime) > ZOMBIE_CONNECTION_THRESHOLD_MS; //[cite: 1]

        if (socketStatus !== 'connected' || isZombieConnection) { //[cite: 1]
            if (!currentAccessToken) { //[cite: 1]
                actions.addSocketAIMessage({ //[cite: 1]
                    type: 'error', //[cite: 1]
                    content: 'Session token missing. Cannot reconnect.', //[cite: 1]
                });
                return;  //[cite: 1]
            }

            useAIOrderingStore.setState({ isLoading: true }); //[cite: 1]
            actions.disconnectSocket(); //[cite: 1]
            actions.connectSocket(currentAccessToken); //[cite: 1]
        }
        
        actions.addProductById(product, elementId); //[cite: 1]
    }, [status, socketStatus, currentAccessToken, actions]);

    const stripeAppearance = useMemo(() => ({
        theme: 'night' as const, //[cite: 1]
        labels: 'floating' as const, //[cite: 1]
        variables: {
            colorPrimary: '#06b6d4',  //[cite: 1]
            colorBackground: '#0F172A',  //[cite: 1]
            colorText: '#ffffff', //[cite: 1]
            colorDanger: '#ef4444', //[cite: 1]
            fontFamily: 'system-ui, sans-serif', //[cite: 1]
            spacingUnit: '4px', //[cite: 1]
            borderRadius: '16px', //[cite: 1]
            colorIcon: '#ffffff',  //[cite: 1]
        },
        rules: {
            '.Input': { backgroundColor: '#1E293B', border: '1px solid #334155' }, //[cite: 1]
            '.Input:focus': { border: '1px solid #06b6d4', boxShadow: '0 0 0 1px #06b6d4' }, //[cite: 1]
            '.Tab': { backgroundColor: '#1E293B', color: '#ffffff' },  //[cite: 1]
            '.Tab--selected': { backgroundColor: '#06b6d4', color: '#000000' }, //[cite: 1]
        }
    }), []);

    const stripeOptions = useMemo<StripeElementsOptions | undefined>(() => {
        const clientSecret = paymentDetails?.client_secret; //[cite: 1]
        if (!clientSecret) return undefined; //[cite: 1]
        return { clientSecret: clientSecret, appearance: stripeAppearance }; //[cite: 1]
    }, [paymentDetails, stripeAppearance]);

    const isPaymentMode = !!paymentDetails;  //[cite: 1]
    const isKeyMissing = !STRIPE_PUBLISHABLE_KEY; //[cite: 1]
    const isReadyToRender = stripeObj && stripeOptions && !isStripeError; //[cite: 1]
    
    const handleNavigateToAuth = useCallback((mode: 'SIGNIN' | 'SIGNUP') => {
        actions.setOverlayVisible(false); //[cite: 1]
        onClose(); //[cite: 1]
        router.push(`/auth?mode=${mode}`); //[cite: 1]
    }, [actions, onClose, router]);

    return (
        <AnimatePresence>
            {isOpen && ( //[cite: 1]
                <motion.div
                    key="chat-window" //[cite: 1]
                    initial={{ opacity: 0 }} //[cite: 1]
                    animate={{ opacity: 1 }} //[cite: 1]
                    exit={{ opacity: 0 }} //[cite: 1]
                    onClick={handleClose} //[cite: 1]
                    style={{ colorScheme: 'dark', willChange: 'opacity', fontFamily: "'Montserrat', sans-serif" }} //[cite: 1]
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden transform-gpu" //[cite: 1]
                >
                   
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" /> 
                    <FlyToCartAnimator /> 
                    
                    <AnimatePresence>
                        {detailProduct && ( //[cite: 1]
                            <motion.div
                                initial={{ opacity: 0, backdropFilter: "blur(0px)" }} //[cite: 1]
                                animate={{ opacity: 1, backdropFilter: "blur(16px)" }} //[cite: 1]
                                exit={{ opacity: 0, backdropFilter: "blur(0px)" }} //[cite: 1]
                                transition={{ duration: 0.3, ease: "easeOut" }} //[cite: 1]
                                style={{ willChange: 'opacity, backdrop-filter' }} //[cite: 1]
                                className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4 sm:p-4 transform-gpu" //[cite: 1]
                                onClick={() => setDetailProduct(null)} //[cite: 1]
                            >
                                <div onClick={(e) => e.stopPropagation()} className="w-full h-full max-w-[460px] max-h-[1050px] md:max-h-[90vh]"> 
                                    <ProductDetailsCard product={detailProduct} onClose={() => setDetailProduct(null)} /> 
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: 30 }} //[cite: 1]
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }} //[cite: 1]
                        exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.3 } }} //[cite: 1]
                        onClick={(e) => e.stopPropagation()} //[cite: 1]
                        style={{ willChange: 'transform, opacity' }} //[cite: 1]
                        className="w-full h-full max-w-[460px] max-h-[1050px] md:max-h-[90vh] flex flex-col bg-[#020617]/55 backdrop-blur-3xl border border-white/10 rounded-[73px] shadow-[0_0_100px_rgba(6,182,212,0.1)] overflow-hidden relative transform-gpu" //[cite: 1]
                    >
                        <div className="absolute inset-[-1px] z-[120] rounded-[73px] overflow-hidden pointer-events-none"> 
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
                                {!isPaymentMode && ( //[cite: 1]
                                    <div className="flex-shrink-0"> 
                                        <motion.button
                                            id="order-summary-cart-icon"  //[cite: 1]
                                            animate={cartControls} //[cite: 1]
                                            onClick={() => setIsMobileSidebarOpen(true)} //[cite: 1]
                                            className="p-3 rounded-full bg-cyan-600/20 border border-cyan-500/50 text-cyan-400 hover:bg-cyan-600/40 transition-all flex items-center justify-center relative" //[cite: 1]
                                        >
                                            <ShoppingBag size={18} /> 
                                            {cartItems.length > 0 && ( //[cite: 1]
                                                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center"> 
                                                    {cartItems.length} 
                                                </span>
                                            )}
                                            </motion.button>
                                    </div>
                                )}

                                <button
                                    onClick={handleClose}  //[cite: 1]
                                    className="p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all duration-300" //[cite: 1]
                                >
                                    <X size={18} /> 
                                </button>
                            </div>
                          </header>

                        <div className="flex-grow flex overflow-hidden relative z-10"> 
                            <AnimatePresence mode="wait"> 
                                {isPaymentMode ? ( //[cite: 1]
                                    <motion.div
                                        key="payment" //[cite: 1]
                                        initial={{ opacity: 0, x: 20 }} //[cite: 1]
                                        animate={{ opacity: 1, x: 0 }} //[cite: 1]
                                        exit={{ opacity: 0, x: -20, transition: { duration: 0.2 } }} //[cite: 1]
                                        onAnimationComplete={() => setIsAnimationComplete(true)} //[cite: 1]
                                        style={{ isolation: 'isolate', willChange: 'transform, opacity' }} //[cite: 1]
                                        className="w-full h-full flex flex-col relative z-20 transform-gpu" //[cite: 1]
                                    >
                                        {isReadyToRender && isAnimationComplete ? ( //[cite: 1]
                                            (() => {
                                                const hasValidData = Boolean( //[cite: 1]
                                                    stripeOptions?.clientSecret && //[cite: 1]
                                                    paymentDetails?.order_data && //[cite: 1]
                                                    typeof paymentDetails.order_data.total === 'number' //[cite: 1]
                                                );

                                                if (!hasValidData) { //[cite: 1]
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

                                                return (
                                                    <Elements 
                                                        key={`${stripeOptions.clientSecret}-loaded`}  //[cite: 1]
                                                        stripe={stripeObj}  //[cite: 1]
                                                        options={stripeOptions} //[cite: 1]
                                                    >
                                                        <AIPaymentForm
                                                            orderId={paymentDetails.order_data.order_id} //[cite: 1]
                                                            total={paymentDetails.order_data.total} //[cite: 1]
                                                            items={paymentDetails.order_data.items} //[cite: 1]
                                                            onPaymentSuccess={handlePaymentSuccess} //[cite: 1]
                                                            clientSecret={stripeOptions.clientSecret} //[cite: 1]
                                                        />
                                                    </Elements>
                                                );
                                            })()
                                        ) : (
                                            <div className="absolute inset-0 flex flex-col items-center justify-center w-full h-full z-50"> 
                                                {isStripeError || isKeyMissing ? ( //[cite: 1]
                                                     <PaymentFatalError keyMissing={isKeyMissing} /> //[cite: 1]
                                                ) : (
                                                    <Loader2 size={26} className="text-cyan-500 animate-spin" /> //[cite: 1]
                                                )}
                                            </div>
                                        )}
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="chat" //[cite: 1]
                                        initial={{ opacity: 0 }} //[cite: 1]
                                        animate={{ opacity: 1 }} //[cite: 1]
                                        exit={{ opacity: 0, transition: { duration: 0.1 } }} //[cite: 1]
                                        style={{ willChange: 'opacity' }} //[cite: 1]
                                        className="flex-grow flex flex-col relative z-10 w-full transform-gpu" //[cite: 1]
                                    >
                                        <div className="flex-grow px-4 lg:px-12 py-8 space-y-8 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent"> 
                                            <AnimatePresence initial={false}>  
                                                {messages.map((msg) => ( //[cite: 1]
                                                    <ChatMessage
                                                        key={msg.id} //[cite: 1]
                                                        message={msg} //[cite: 1]
                                                        isActiveAction={msg.id === activeActionId} //[cite: 1]
                                                        onSend={handleSendMessage} //[cite: 1]
                                                        onNavigateToAuth={handleNavigateToAuth} //[cite: 1]
                                                        onProductSelect={handleProductSelect} //[cite: 1]
                                                        onViewDetails={setDetailProduct} //[cite: 1]
                                                        onConfirmOrder={actions.confirmCurrentOrder} //[cite: 1]
                                                        onClearCart={actions.clearCart} //[cite: 1]
                                                        onRestore={actions.restoreCheckout} //[cite: 1]
                                                        onSave={actions.saveForLater} //[cite: 1]
                                                        onCancel={actions.hardCancelOrder} //[cite: 1]
                                                    />
                                                ))}
                                            </AnimatePresence>
                                            <div ref={chatEndRef} /> 
                                        </div>
                                        <ChatInput onSend={handleSendMessage} onSendImage={actions.sendImage} isTyping={isLoading} isProcessing={isProcessing} /> 
                                    </motion.div>
                                )}
                            </AnimatePresence>
                                 
                            {!(isPaymentMode) && ( //[cite: 1]
                                 <AIChatSidebar
                                     messages={messages} //[cite: 1]
                                     glowingProductId={glowingProductId} //[cite: 1]
                                     onRemoveItem={actions.removeProductById} //[cite: 1]
                                     isMobileOpen={isMobileSidebarOpen} //[cite: 1]
                                     onCloseMobile={() => setIsMobileSidebarOpen(false)} //[cite: 1]
                                 />
                            )}
                       </div>
                   </motion.div>
               </motion.div>
           )}
       </AnimatePresence>
   );
}
