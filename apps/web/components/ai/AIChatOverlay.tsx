//** apps/web/components/ai/AIChatOverlay.tsx **//

'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Bot, User, CornerDownRight, ShoppingCart, Cpu, Clock, X, 
    ChevronLeft, ChevronRight, Save, Trash2, Undo2, AlertCircle, 
    ShoppingBag, ShieldOff, Loader2, Wind, Navigation, Zap, 
    Activity, Signal, Gauge, Battery, BrainCircuit 
} from 'lucide-react';
import { useAIOrderingStore, Message } from '../../hooks/useAIOrderingStore';
import Image from 'next/image';
import useEmblaCarousel from 'embla-carousel-react';
import { loadStripe, StripeElementsOptions, Stripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { AIPaymentForm } from './AIPaymentForm';
import { useSession } from "next-auth/react";
import { useShallow } from 'zustand/react/shallow';

const getAbsoluteImageUrl = (relativePath: string | undefined): string => {
    if (!relativePath || relativePath.startsWith('http')) {
        return relativePath || '/images/default.jpeg';
    }
    const apiBase = process.env.NEXT_PUBLIC_API_URL
        ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')
        : 'http://localhost:8000';
    return `${apiBase}${relativePath.startsWith('/') ? relativePath : `/${relativePath}`}`;
};

// ============================================================================
// --- 1. VISUAL COMPONENTS (The "Art" of the Interface) ---
// ============================================================================

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
            <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold mb-1">{label}</span>
            <div className="flex items-baseline gap-1">
                <span className="text-lg font-mono font-bold text-white tracking-tight">{value.toFixed(1)}</span>
                <span className="text-[9px] text-gray-400">{unit}</span>
            </div>
            <div className="w-full h-0.5 bg-gray-800 mt-2 rounded-full overflow-hidden">
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
        <div className="grid grid-cols-2 gap-2 w-full mt-2">
            <TelemetryItem icon={Wind} label="SPD" value={stats.speed} unit="km/h" color="text-cyan-400" />
            <TelemetryItem icon={Navigation} label="ALT" value={stats.alt} unit="m" color="text-purple-400" />
            <TelemetryItem icon={Zap} label="PWR" value={stats.bat} unit="%" color="text-green-400" />
            <TelemetryItem icon={Activity} label="STAB" value={stats.stab} unit="%" color="text-blue-400" />
        </div>
    );
});
DroneTelemetryWidget.displayName = 'DroneTelemetryWidget';

const CarouselProductCard = React.memo(({ product, onSelect, totalItems }: { product: any, onSelect: (product: any, elementId: string) => void, totalItems: number }) => {
    const mdWidthClass = totalItems === 2 ? "md:flex-[0_0_50%]" : "md:flex-[0_0_40%]";
    const slideWidthClass = `flex-[0_0_65%] sm:flex-[0_0_50%] ${mdWidthClass}`;
    
    const rawImagePath = product.image_url || product.image;
    const imageUrl = useMemo(() => getAbsoluteImageUrl(rawImagePath), [rawImagePath]);
    const elementId = `product-carousel-img-${product.id}`;

    const handleSelect = useCallback(() => {
        const normalizedProduct = { ...product, image: rawImagePath };
        onSelect(normalizedProduct, elementId);
    }, [product, rawImagePath, elementId, onSelect]);

    return (
        <div className={`embla__slide ${slideWidthClass} px-3 py-2`}>
            <motion.div
                className="flex flex-col p-5 bg-black/40 backdrop-blur-xl rounded-[24px] border border-white/10 h-full text-left shadow-lg relative group overflow-hidden"
                whileHover={{ 
                    scale: 1.02, 
                    zIndex: 50,
                    borderColor: "rgba(0, 198, 255, 0.4)",
                    boxShadow: "0 0 30px rgba(0, 198, 255, 0.1)"
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                
                <div className="relative z-10 flex-grow flex flex-col">
                    <div className="relative h-32 mb-4 w-full flex items-center justify-center bg-gradient-to-b from-white/5 to-transparent rounded-2xl p-4 group-hover:from-cyan-500/10 transition-colors duration-500">
                        <Image
                            id={elementId}
                            src={imageUrl}
                            alt={product.name}
                            width={150}
                            height={150}
                            className="w-full h-full object-contain drop-shadow-2xl group-hover:scale-110 group-hover:-rotate-3 transition-transform duration-500 ease-out"
                        />
                    </div>
                    <h4 className="text-base font-bold text-white mb-1 line-clamp-1" style={{ fontFamily: "'Montserrat', sans-serif" }}>{product.name}</h4>
                    <div className="flex items-end gap-2 mb-4">
                        <span className="text-xl font-bold text-cyan-400 font-mono">
                            ${product.price.toFixed(2)}
                        </span>
                        {product.rating && (
                            <span className="text-[10px] text-gray-500 mb-1 flex items-center gap-1 bg-white/5 px-2 py-0.5 rounded-full">
                                <span className="text-yellow-400">★</span> {product.rating}
                            </span>
                        )}
                    </div>
                    <div className="mt-auto">
                        <motion.button
                            onClick={handleSelect}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.95 }}
                            className="w-full relative overflow-hidden rounded-xl bg-cyan-500/10 border border-cyan-500/30 p-[1px] group/btn"
                        >
                            <div className="relative px-4 py-3 rounded-[10px] flex items-center justify-center gap-2 transition-all duration-300 group-hover/btn:bg-cyan-500 group-hover/btn:text-black">
                                <ShoppingBag size={16} className="text-cyan-400 group-hover/btn:text-black transition-colors" />
                                <span className="font-bold text-xs uppercase tracking-wider text-cyan-100 group-hover/btn:text-black">Add to Cart</span>
                            </div>
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
});
CarouselProductCard.displayName = 'CarouselProductCard';

const ProductCarousel = React.memo(({ products, onSelect }: { products: any[], onSelect: (product: any, elementId: string) => void }) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'start' });
    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);
    const totalItems = products.length;
    const canScroll = totalItems > 2;

    return (
        <div className="relative my-4 px-1 group/carousel">
            <div className="overflow-hidden" ref={emblaRef}>
                <div className="flex -ml-3">
                    {products.map((p, i) => <CarouselProductCard key={p.id || i} product={p} onSelect={onSelect} totalItems={totalItems} />)}
                </div>
            </div>
            {canScroll && (
                <>
                    <button onClick={scrollPrev} className="absolute top-1/2 -translate-y-1/2 -left-4 p-2 bg-black/80 backdrop-blur-md border border-white/10 rounded-full z-10 hover:bg-cyan-500 hover:text-black transition-all opacity-0 group-hover/carousel:opacity-100 translate-x-2 group-hover/carousel:translate-x-0 duration-300"><ChevronLeft size={18}/></button>
                    <button onClick={scrollNext} className="absolute top-1/2 -translate-y-1/2 -right-4 p-2 bg-black/80 backdrop-blur-md border border-white/10 rounded-full z-10 hover:bg-cyan-500 hover:text-black transition-all opacity-0 group-hover/carousel:opacity-100 -translate-x-2 group-hover/carousel:translate-x-0 duration-300"><ChevronRight size={18}/></button>
                </>
            )}
        </div>
    );
});
ProductCarousel.displayName = 'ProductCarousel';

const AIReasoning = React.memo(({ text }: { text: string }) => (
    <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        className="flex items-start gap-3 p-3 mt-3 bg-gradient-to-r from-cyan-900/10 to-transparent border-l-2 border-cyan-500 rounded-r-lg max-w-lg"
    >
        <Cpu size={16} className="text-cyan-400 flex-shrink-0 mt-0.5 animate-pulse"/>
        <p className="text-xs text-cyan-200/90 font-mono leading-relaxed">{text}</p>
    </motion.div>
));
AIReasoning.displayName = 'AIReasoning';

const ChatMessage = React.memo(({ message, onSend, onProductSelect, onConfirmOrder, onClearCart, onRestore, onSave, onCancel }: any) => {
    const isAI = message.sender === 'ai';

    const MessageContent = () => {
        switch (message.contentType) {
            case 'text':
            case 'error':
            case 'success_text':
                return <p className={`whitespace-pre-wrap text-sm md:text-base leading-relaxed ${message.contentType === 'error' ? 'text-red-400 font-mono' : ''} ${message.contentType === 'success_text' ? 'text-cyan-300' : ''}`}>{message.content}</p>;
            case 'confirmation_prompt':
                return (
                    <div>
                        <p className="whitespace-pre-wrap mb-4 text-sm md:text-base">{message.content}</p>
                        <div className="flex flex-wrap gap-2">
                            {(message.options as string[])?.map((option: string) => {
                                const isConfirm = option === 'Confirm Order';
                                const buttonStyle = isConfirm
                                    ? "bg-purple-600/20 text-purple-300 border-purple-500/50 hover:bg-purple-500 hover:text-white"
                                    : "bg-cyan-500/10 text-cyan-300 border-cyan-500/30 hover:bg-cyan-500 hover:text-black";
                                return (
                                    <motion.button
                                        key={option}
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        onClick={() => {
                                            if (option === 'Confirm Order') onConfirmOrder();
                                            else if (option === 'Clear Cart') onClearCart();
                                            else onSend(option);
                                        }}
                                        className={`text-xs font-bold uppercase tracking-wider px-4 py-2 rounded-full border ${buttonStyle} transition-all duration-300`}
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
                    <div className="w-full">
                        <p className="whitespace-pre-wrap mb-2 text-sm md:text-base">{message.content}</p>
                        <ProductCarousel products={message.products || []} onSelect={onProductSelect} />
                        {(message.reason || message.ai_notes) && (
                            <AIReasoning text={message.reason || message.ai_notes} />
                        )}
                    </div>
                );
            case 'recovery_prompt':
                return (
                    <div className="flex flex-col gap-3 w-full p-2">
                        <div className="flex items-center gap-2 text-amber-400 mb-1">
                            <AlertCircle size={18} />
                            <span className="font-bold text-sm uppercase tracking-wide">Session Interrupted</span>
                        </div>
                        <p className="whitespace-pre-wrap text-sm text-gray-300 mb-2">{message.content}</p>
                        <div className="grid grid-cols-3 gap-2 w-full">
                            {[
                                { icon: Undo2, label: "Resume", color: "cyan", action: onRestore },
                                { icon: Save, label: "Save", color: "purple", action: onSave },
                                { icon: Trash2, label: "Discard", color: "red", action: onCancel }
                            ].map((btn, idx) => (
                                <motion.button 
                                    key={idx}
                                    whileHover={{ scale: 1.03, y: -2 }}
                                    onClick={btn.action} 
                                    className={`flex flex-col items-center justify-center gap-2 p-3 rounded-xl border bg-${btn.color}-500/10 border-${btn.color}-500/30 text-${btn.color}-400 hover:bg-${btn.color}-500/20 transition-all`}
                                >
                                    <btn.icon size={18} /> 
                                    <span className="text-[10px] font-bold uppercase">{btn.label}</span>
                                </motion.button>
                            ))}
                        </div>
                    </div>
                );
            default: return null;
        }
    };

    if (['cart_preview', 'typing', 'payment_intent', 'ORDER_CANCELLED'].includes(message.contentType)) return null;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className={`flex items-start gap-4 w-full ${isAI ? 'justify-start' : 'justify-end'}`}
        >
            {isAI && (
                <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-cyan-950/50 flex items-center justify-center border border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]">
                    <Bot size={16} className="text-cyan-400" />
                </div>
            )}
            <div className={`w-auto max-w-[85%] md:max-w-xl px-5 py-4 rounded-[24px] ${
                isAI 
                    ? 'bg-black/40 backdrop-blur-md border border-white/5 text-gray-100 shadow-lg' 
                    : 'bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-xl shadow-purple-900/20'
            } ${isAI ? 'rounded-tl-none' : 'rounded-tr-none'}`}>
                <MessageContent />
            </div>
            {!isAI && (
                <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gray-800/50 flex items-center justify-center border border-gray-700">
                    <User size={16} className="text-gray-400" />
                </div>
            )}
        </motion.div>
    );
});
ChatMessage.displayName = 'ChatMessage';

const AIChatSidebar = React.memo(({ messages, glowingProductId, onRemoveItem }: {
    messages: Message[],
    glowingProductId: number | null,
    onRemoveItem: (productId: number) => void
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
        <div className="hidden lg:flex w-[35%] bg-black/40 backdrop-blur-2xl border-l border-white/5 flex-col overflow-hidden relative">
            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" />
            
            <div className="flex-grow p-6 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-cyan-500/20 scrollbar-track-transparent relative z-10">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                        <ShoppingBag size={14} className="text-cyan-400" id="order-summary-cart-icon" /> 
                        Manifest
                    </h3>
                    <div className="px-2 py-0.5 rounded bg-cyan-900/30 border border-cyan-500/20 text-[10px] text-cyan-400 font-mono">
                        LIVE
                    </div>
                </div>

                <div className="space-y-3 flex-grow">
                    <AnimatePresence>
                        {cart.items.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-40 text-gray-600 gap-2 border border-dashed border-white/5 rounded-2xl">
                                <ShoppingCart size={24} className="opacity-50" />
                                <p className="text-xs uppercase tracking-wide">Cart / Empty</p>
                            </div>
                        ) : cart.items.map((item: any, index: number) => (
                            <motion.div
                                key={item.product_id || index}
                                layout
                                initial={{ opacity: 0, x: -20 }}
                                animate={{
                                    opacity: 1,
                                    x: 0,
                                    backgroundColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.1)" : "rgba(255, 255, 255, 0.02)",
                                    borderColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.4)" : "rgba(255, 255, 255, 0.05)",
                                }}
                                exit={{ opacity: 0, x: 20 }}
                                className="flex justify-between items-center p-3 rounded-xl border transition-colors group"
                            >
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-10 h-10 rounded-lg bg-black/50 border border-white/10 flex items-center justify-center overflow-hidden">
                                       
                                         <ShoppingBag size={14} className="text-gray-500" />
                                    </div>
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-gray-200 text-sm font-medium truncate" title={item.name}>
                                            {item.name}
                                        </span>
                                        <span className="text-xs text-gray-500 font-mono">Qty: {item.quantity}</span>
                                    </div>
                                </div>
                                <div className="flex flex-col items-end gap-1">
                                    <span className="font-bold text-cyan-300 font-mono text-sm">
                                        ${(item.price * item.quantity).toFixed(2)}
                                    </span>
                                    <motion.button
                                        onClick={() => onRemoveItem(item.product_id)}
                                        className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                        title="Jettison Item"
                                    >
                                        <X size={12} />
                                    </motion.button>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>

            <div className="flex-shrink-0 p-6 border-t border-white/10 bg-black/60 backdrop-blur-xl space-y-5 relative z-20">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-1 bg-cyan-500/20 rounded-full" />
                
                <div>
                    <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                        <Signal size={12} /> Flight Telemetry
                    </h3>
                    <DroneTelemetryWidget />
                </div>

                <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />

                {aiNote && (
                    <div className="bg-cyan-900/10 border border-cyan-500/10 p-3 rounded-xl">
                        <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest mb-1 flex items-center gap-2">
                            <BrainCircuit size={12} /> Optimization Node
                        </h3>
                        <p className="text-xs text-cyan-100/70 italic leading-relaxed">{aiNote}</p>
                    </div>
                )}

                <div className="flex justify-between items-end pt-2">
                    <div className="flex flex-col">
                        <span className="text-[10px] text-gray-500 uppercase tracking-widest">Total Price</span>
                        <span className="text-xs text-gray-400">Inclusive of Premium Charges</span>
                    </div>
                    <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-cyan-200 font-mono tracking-tight">
                        ${cart.total.toFixed(2)}
                    </span>
                </div>
            </div>
        </div>
    );
});
AIChatSidebar.displayName = 'AIChatSidebar';

const ChatInput = React.memo(
  ({ onSend, isTyping, isProcessing }: { onSend: (text: string) => void; isTyping: boolean; isProcessing: boolean }) => {
    const [value, setValue] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);
    const wasTypingRef = useRef<boolean>(isTyping);

    useEffect(() => {
      if (wasTypingRef.current === true && isTyping === false) {
        inputRef.current?.focus();
      }
      wasTypingRef.current = isTyping;
    }, [isTyping]);

    const isDisabled = isTyping || isProcessing;

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      if (value.trim() && !isDisabled) {
        onSend(value);
        setValue('');
      }
    };

    return (
      <form onSubmit={handleSubmit} className="p-5 border-t border-white/5 flex-shrink-0 bg-black/20 backdrop-blur-md relative z-20">
        <div className="relative group">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={isDisabled ? 'Systems processing...' : 'Ask order with air...'}
            disabled={isDisabled}
            className="w-full bg-black/40 backdrop-blur-xl border border-white/10 rounded-full py-4 pr-14 pl-6 text-white placeholder-gray-600 focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/50 focus:outline-none transition-all duration-300 font-medium"
          />
          <button
            type="submit"
            disabled={isDisabled}
            onClick={(e) => e.stopPropagation()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-500 text-white shadow-lg transition-all hover:scale-105 active:scale-95"
          >
            {isDisabled ? <Loader2 size={18} className="animate-spin" /> : <CornerDownRight size={18} />}
          </button>
        </div>
      </form>
    );
  }
);
ChatInput.displayName = 'ChatInput';

const TypingIndicator = React.memo(() => (
    <motion.div
        layout
        initial={{ opacity: 0, y: 10, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0 }}
        className="flex items-center gap-3"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-cyan-950/50 flex items-center justify-center border border-cyan-500/30">
        <Bot size={16} className="text-cyan-400" />
      </div>
      <div className="flex items-center gap-1.5 px-4 py-3 bg-black/40 border border-white/5 rounded-[18px] rounded-tl-none">
        <span className="text-xs text-cyan-500 font-mono mr-2 animate-pulse">COMPUTING</span>
        <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, repeat: Infinity }} />
        <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, delay: 0.2, repeat: Infinity }} />
        <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, delay: 0.4, repeat: Infinity }} />
      </div>
    </motion.div>
));
TypingIndicator.displayName = 'TypingIndicator';

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
      return { top: rect.top + rect.height / 2, left: rect.left + rect.width / 2 };
    }
    return { top: 100, left: window.innerWidth - 100 };
  };

  const endPos = getEndPosition();

  return (
    <AnimatePresence>
      {flyQueue.map((item) => {
          const startRect = getStartPosition(item.startElementId);
          const imageSource = getAbsoluteImageUrl(item.image);
          if (!startRect || startRect.width === 0) return null;

          return (
            <motion.div
              key={item.animationId} 
              className="fixed z-[9999] rounded-xl overflow-hidden border border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.5)]"
              initial={{ top: startRect.top, left: startRect.left, width: startRect.width, height: startRect.height, opacity: 1, rotate: 0 }}
              animate={{ top: endPos.top, left: endPos.left, width: 20, height: 20, opacity: 0.5, rotate: 360, scale: 0.1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} 
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

export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    
    const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '';
    const stripePromise: Promise<Stripe | null> | null = useMemo(() => {
        if (STRIPE_PUBLISHABLE_KEY) {
            return loadStripe(STRIPE_PUBLISHABLE_KEY);
        }
        return null;
    }, [STRIPE_PUBLISHABLE_KEY]);
    
    const [stripeObj, setStripeObj] = useState<Stripe | null>(null);
    const [isStripeError, setIsStripeError] = useState(false);

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

    useEffect(() => {
        if (isOpen && status === 'authenticated' && session?.accessToken) {
            actions.connectSocket(session.accessToken);
        }
        return () => {
            if (!isOpen) actions.disconnectSocket();
        };
    }, [isOpen, status, session, actions.connectSocket, actions.disconnectSocket]);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [messages, isLoading]);

    const handleClose = useCallback(() => {
        if (paymentDetails && !isProcessing) {
            actions.initiateCheckoutRecovery();
        } else if (!paymentDetails) {
            onClose();
        }
    }, [paymentDetails, isProcessing, onClose, actions.initiateCheckoutRecovery]);
    
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

    const stripeOptions = useMemo<StripeElementsOptions | undefined>(() => {
        const stripeGateway = paymentDetails?.gateways.find(g => g.provider === 'stripe');
        if (!stripeGateway?.clientSecret) return undefined;
        
        return {
            clientSecret: stripeGateway.clientSecret,
            appearance: {
                theme: 'night',
                labels: 'floating',
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
                    '.Input:focus': { border: '1px solid #06b6d4', boxShadow: '0 0 0 1px #06b6d4' }
                }
            },
        };
    }, [paymentDetails]);

    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cartItems = lastCartMessage?.content?.items || [];
    
    const isPaymentMode = !!paymentDetails; 
    const isKeyMissing = !STRIPE_PUBLISHABLE_KEY;
    const isReadyToRender = stripeObj && stripeOptions && !isStripeError;

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={handleClose}
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden"
                >
                   
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" />
                    <FlyToCartAnimator /> 

                    <motion.div
                        initial={{ scale: 0.95, opacity: 0, y: 30 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }}
                        exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.3 } }}
                        onClick={(e) => e.stopPropagation()}
                       
                        className="w-full max-w-7xl h-[95vh] max-h-[1100px] flex flex-col bg-black/60 backdrop-blur-3xl border border-white/10 rounded-[40px] shadow-[0_0_50px_rgba(0,198,255,0.15)] overflow-hidden relative"
                    >
                       
                        <div className="absolute top-0 left-0 w-32 h-32 bg-cyan-500/5 blur-[60px] pointer-events-none" />
                        <div className="absolute bottom-0 right-0 w-32 h-32 bg-purple-500/5 blur-[60px] pointer-events-none" />

                        <header className="px-8 py-5 border-b border-white/5 flex justify-between items-center flex-shrink-0 relative z-10 bg-black/20">
                            <h3 className="font-bold text-xl normal-case tracking-tight" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                <motion.span
                                    className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-purple-400"
                                    animate={{
                                        textShadow: [
                                            '0 0 10px rgba(6,182,212,0)',
                                            '0 0 20px rgba(6,182,212,0.3)',
                                            '0 0 10px rgba(6,182,212,0)'
                                        ]
                                    }}
                                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                                >
                                    {paymentDetails ? 'secure_checkout' : 'order with air'}
                                </motion.span>
                                <span className="ml-2 text-[10px] text-cyan-500/50 font-mono align-top">BETA v5.0</span>
                            </h3>
                            <button 
                                onClick={handleClose} 
                                className="p-2.5 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/30 transition-all duration-300"
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
                                        className="w-full h-full flex items-center justify-center overflow-y-auto relative z-20"
                                    >
                                        {isReadyToRender ? (
                                            <Elements key={stripeOptions.clientSecret} stripe={stripeObj} options={stripeOptions}>
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
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="relative">
                                                            <div className="w-16 h-16 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin" />
                                                            <div className="absolute inset-0 flex items-center justify-center">
                                                                <Lock size={20} className="text-cyan-400" />
                                                            </div>
                                                        </div>
                                                        <p className="text-cyan-200 font-mono text-sm tracking-widest animate-pulse">ENCRYPTING CONNECTION...</p>
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
                                        className="w-full lg:w-[65%] flex flex-col relative z-10"
                                    >
                                        <div className="flex-grow px-6 py-6 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent">
                                            <AnimatePresence initial={false}> 
                                                {messages.map((msg) => (
                                                    <ChatMessage
                                                        key={msg.id}
                                                        message={msg}
                                                        onSend={handleSendMessage}
                                                        onProductSelect={handleProductSelect}
                                                        onConfirmOrder={actions.confirmCurrentOrder}
                                                        onClearCart={actions.clearCart}
                                                        onRestore={actions.restoreCheckout}
                                                        onSave={actions.saveForLater}
                                                        onCancel={actions.hardCancelOrder}
                                                    />
                                                ))}
                                            </AnimatePresence>
                                            {isLoading && <TypingIndicator />}
                                            <div ref={chatEndRef} />
                                        </div>
                                        <ChatInput onSend={handleSendMessage} isTyping={isLoading} isProcessing={isProcessing} />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                            
                           
                            {!(isPaymentMode) && (
                                 <AIChatSidebar
                                    messages={messages}
                                    glowingProductId={glowingProductId}
                                    onRemoveItem={actions.removeProductById}
                                 />
                            )}
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
