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
    Activity, BrainCircuit, Lock, Star, Sparkles, Mic, Camera, Image as ImageIcon, MapPin, Clock, Eye, ShieldCheck
} from 'lucide-react';
import { useAIOrderingStore, Message } from '../../hooks/useAIOrderingStore';
import Image from 'next/image';
import useEmblaCarousel from 'embla-carousel-react';
import { loadStripe, StripeElementsOptions, Stripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import AIPaymentForm from './AIPaymentForm';
import ShippingAddressForm from '@/components/checkout/ShippingAddressForm';
import PayPalApproval from '@/components/checkout/PayPalApproval';
import { useSession } from "next-auth/react";
import { useShallow } from 'zustand/react/shallow';
import { AIVoiceOverlay } from './AIVoiceOverlay';
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock';
import { CatalogPrice, listedCatalogPrice } from './CatalogPrice';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- ENTERPRISE CONTRACT DEFINITIONS ---
export interface AIProduct {
    id: number | string;
    name: string;
    price?: number | string | null;
    price_status?: string;
    image?: string;
    image_url?: string;
    rating?: number;
    stock_level?: string;
    quantity?: number;
    product_id?: number;
    brand?: string;
    reviews_count?: string | number;
}

export interface ExtendedMessage {
    id: number | string;
    sender: 'ai' | 'user' | 'system';
    contentType: 'text' | 'image_user_upload' | 'error' | 'info' | 'success_text' | 'confirmation_prompt' | 'product_carousel' | 'proactive_suggestion' | 'recovery_prompt' | 'cart_preview' | 'typing' | 'payment_intent' | 'ORDER_CANCELLED';
    content: string | { items: AIProduct[]; total: number };
    imageUrl?: string;
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

const DEFAULT_PLACEHOLDER = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC";
const ZOMBIE_CONNECTION_THRESHOLD_MS = 60_000;
const SIMULATED_AUTH_DELAY_MS = 500;

const getAbsoluteImageUrl = (relativePath: string | undefined): string => {
    if (!relativePath) return DEFAULT_PLACEHOLDER;
    const trimmed = relativePath.trim();
    if (trimmed.startsWith('data:image/')) return trimmed;
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
        try {
            const parsed = new URL(trimmed);
            if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
                return parsed.toString();
            }
        } catch {
            return DEFAULT_PLACEHOLDER;
        }
        return DEFAULT_PLACEHOLDER;
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL
        ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')
        : 'http://localhost:8000';

    const cleanPath = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
    if (cleanPath.includes('default.jpeg')) return DEFAULT_PLACEHOLDER;

    return `${apiBase}${cleanPath}`;
};

const extractBrandAndTitle = (product: AIProduct): { brand: string; title: string } => {
    if (product.brand && product.brand.trim().length > 0) {
        return { brand: product.brand.trim().toUpperCase(), title: product.name };
    }
    const knownLuxuryTokens = [
        'GUCCI', 'PRADA', 'DIOR', 'HERMES', 'HERMÈS', 'BALENCIAGA', 'SAINT LAURENT',
        'LOUIS VUITTON', 'BOTTEGA VENETA', 'CARTIER', 'ROLEX', 'CHANEL', 'FENDI',
        'BURBERRY', 'VERSACE', 'GIVENCHY', 'VALENTINO', 'LOEWE', 'CELINE', 'APPLE', 'SONY', 'NIKE'
    ];
    const upperName = (product.name || '').trim().toUpperCase();
    for (const brand of knownLuxuryTokens) {
        if (upperName.startsWith(`${brand} `)) {
            const remaining = product.name.trim().slice(brand.length).trim();
            return {
                brand,
                title: remaining.length > 0 ? remaining : product.name
            };
        }
    }
    const words = (product.name || '').trim().split(/\s+/);
    if (words.length > 2) {
        return {
            brand: words[0]?.toUpperCase() ?? '',
            title: product.name
        };
    }
    return {
        brand: (product.stock_level || 'AIRDELIVER SELECT').toUpperCase(),
        title: product.name
    };
};

// Custom 4-point sparkle icon matching the screenshot's "" star
const FourPointSparkle = React.memo(({ className = "w-3.5 h-3.5 text-white/50" }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
        <path d="M12 2C12.7 7.5 16.5 11.3 22 12C16.5 12.7 12.7 16.5 12 22C11.3 16.5 7.5 12.7 2 12C7.5 11.3 11.3 7.5 12 2Z" />
    </svg>
));
FourPointSparkle.displayName = 'FourPointSparkle';

// Custom bookmark-star badge icon matching the top-right product card action button in the screenshot
const BookmarkStarIcon = React.memo(() => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M6 3C4.89543 3 4 3.89543 4 5V21L12 17.5L20 21V5C20 3.89543 19.1046 3 18 3H6ZM12 7.2L13.09 9.41L15.53 9.76L13.76 11.48L14.18 13.91L12 12.77L9.82 13.91L10.24 11.48L8.47 9.76L10.91 9.41L12 7.2Z" />
    </svg>
));
BookmarkStarIcon.displayName = 'BookmarkStarIcon';

// Custom sleek paper-plane Send icon matching the bottom-right glowing blue icon in the screenshot
const SendPlaneIcon = React.memo(({ size = 20 }: { size?: number }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
    >
        <path d="M4 4L20 12L4 20L7.5 12L4 4Z" />
        <path d="M7.5 12H14" />
    </svg>
));
SendPlaneIcon.displayName = 'SendPlaneIcon';



export const CarouselProductCard = React.memo(({ product, onSelect, onViewDetails }: {
    product: AIProduct;
    onSelect: (product: AIProduct, elementId: string) => void;
    onViewDetails: (product: AIProduct) => void;
    totalItems: number;
}) => {
    const rawImagePath = product.image_url || product.image;
    const imageUrl = useMemo(() => getAbsoluteImageUrl(rawImagePath), [rawImagePath]);
    const elementId = `product-carousel-img-${product.id}`;
    const { brand, title } = useMemo(() => extractBrandAndTitle(product), [product]);
    const displayRating = product.rating ? Number(product.rating).toFixed(1) : '4.8';
    const displayReviews = product.reviews_count ? `${product.reviews_count} reviews` : '1.2k reviews';

    const handleSelect = useCallback(() => {
        onSelect({ ...product, image: rawImagePath }, elementId);
    }, [product, rawImagePath, elementId, onSelect]);

    return (
        <div className="embla__slide flex-none w-[262px] sm:w-[274px] snap-start px-2.5 py-3">
            <motion.div
                className="relative flex flex-col h-full rounded-[32px] p-3.5 bg-white/[0.06] backdrop-blur-[24px] border border-white/[0.08] shadow-[0_16px_40px_-10px_rgba(0,0,0,0.6),inset_0_1px_1px_rgba(255,255,255,0.15)] group overflow-hidden transform-gpu"
                whileHover={{
                    scale: 1.02,
                    backgroundColor: "rgba(255, 255, 255, 0.09)"
                }}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                style={{ willChange: 'transform, opacity, background-color' }}
            >
                <div 
                    className="relative w-full aspect-square rounded-[24px] bg-gradient-to-b from-white/[0.05] to-transparent flex items-center justify-center p-4 overflow-hidden mb-3 cursor-pointer"
                    onClick={(e) => {
                        e.stopPropagation();
                        onViewDetails(product);
                    }}
                >
                    <button
                        type="button"
                        aria-label={`Inspect ${product.name}`}
                        className="absolute top-2.5 end-2.5 z-30 w-8 h-8 rounded-full bg-black/40 backdrop-blur-md text-white/90 hover:text-white flex items-center justify-center transition-colors shadow-sm"
                    >
                        <BookmarkStarIcon />
                    </button>
                    <Image
                        id={elementId}
                        src={imageUrl}
                        alt={product.name}
                        width={200}
                        height={200}
                        loading="lazy"
                        decoding="async"
                        className="w-auto h-full max-h-[140px] object-contain drop-shadow-[0_14px_22px_rgba(0,0,0,0.22)] group-hover:scale-105 transition-transform duration-500 ease-out transform-gpu"
                    />
                 </div>

                    {/* Bottom Dark Obsidian Details Surface */}
                 <div className="flex flex-col flex-grow px-1">
                    <span className="text-[11px] font-semibold text-white/50 tracking-wider uppercase mb-1 truncate">
                        {brand}
                    </span>
                    
                    <h4 
                        className="text-[15px] font-semibold text-white/95 leading-tight tracking-tight line-clamp-2 mb-3"
                        title={product.name}
                    >
                        {title}
                    </h4>

                    <div className="mt-auto flex items-center justify-between">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-white/40 font-medium">PRICE</span>
                            <span className="text-[17px] font-bold text-white tracking-tight leading-none">
                                <CatalogPrice product={product} />
                            </span>
                        </div>

                        <motion.button
                            type="button"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={handleSelect}
                            disabled={listedCatalogPrice(product) === null}
                            title={listedCatalogPrice(product) === null ? 'Inspect product details to verify price before adding' : 'Add to cart'}
                            className="disabled:opacity-40 disabled:cursor-not-allowed h-9 px-4 rounded-full bg-white text-black flex items-center justify-center gap-1.5 shadow-[0_4px_12px_rgba(255,255,255,0.15)] hover:shadow-[0_4px_16px_rgba(255,255,255,0.25)] transition-shadow"
                        >
                            <ShoppingBag size={14} strokeWidth={2.5} />
                            <span className="text-[12px] font-bold tracking-wide">ADD</span>
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
});
CarouselProductCard.displayName = 'CarouselProductCard';

const ProductCarousel = React.memo(({ products, onViewDetails, onSelect }: {
    products: AIProduct[];
    onSelect: (product: AIProduct, elementId: string) => void;
    onViewDetails: (product: AIProduct) => void;
}) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({
        loop: false,
        align: 'start',
        containScroll: 'trimSnaps',
        
        dragFree: false
    });

    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);

    const canScroll = products.length > 1;

    return (
        <div className="relative my-3 -mx-6 group/carousel w-[calc(100%+3rem)] overflow-visible">
            {/* Ambient radial glow behind the active product card */}
            <div className="absolute inset-x-10 top-1/2 -translate-y-1/2 h-56 bg-sky-500/10 blur-[70px] rounded-full pointer-events-none" />

            <div className="overflow-hidden py-2" ref={emblaRef}>
                <div className="flex items-stretch px-2 snap-x snap-mandatory">
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
                    <button
                        type="button"
                        onClick={scrollPrev}
                        aria-label="Previous product"
                        className="hidden sm:flex absolute top-1/2 -translate-y-1/2 start-3 p-2.5 bg-white/[0.08] backdrop-blur-2xl rounded-full z-20 text-white/80 hover:bg-white/[0.18] hover:text-white transition-all opacity-0 group-hover/carousel:opacity-100 duration-300 shadow-xl transform-gpu"
                    >
                        <ChevronLeft size={18} />
                    </button>
                    <button
                        type="button"
                        onClick={scrollNext}
                        aria-label="Next product"
                        className="hidden sm:flex absolute top-1/2 -translate-y-1/2 end-3 p-2.5 bg-white/[0.08] backdrop-blur-2xl rounded-full z-20 text-white/80 hover:bg-white/[0.18] hover:text-white transition-all opacity-0 group-hover/carousel:opacity-100 duration-300 shadow-xl transform-gpu"
                    >
                        <ChevronRight size={18} />
                    </button>
                </>
            )}
        </div>
    );
});
ProductCarousel.displayName = 'ProductCarousel';

const AIReasoning = React.memo(({ text }: { text: string }) => (
    <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ willChange: 'transform, opacity' }}
        className="flex flex-col gap-1.5 my-2 max-w-lg relative transform-gpu"
    >
        <div className="flex items-center gap-1.5 text-[12px] font-medium text-white/50 tracking-wide">
            <FourPointSparkle className="w-3.5 h-3.5 text-white/50" />
            <span>airdeliverOS Insight</span>
        </div>
        <p className="text-[14px] text-white/85 font-normal leading-[1.55]">{text}</p>
        <div className="my-5 w-full h-px bg-gradient-to-r from-transparent via-white to-transparent" />
    </motion.div>
));
AIReasoning.displayName = 'AIReasoning';

const ExpandableUserMessage = React.memo(({ text }: { text: string }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const needsExpansion = text.length > 250 || text.split('\n').length > 4;

    if (!needsExpansion) {
        return <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-white/95 font-normal">{text}</p>;
    }

    return (
        <div className="flex flex-col w-full">
            <motion.div
                initial={false}
                animate={{ height: isExpanded ? 'auto' : '71px' }}
                className="overflow-hidden relative transform-gpu"
                style={{ willChange: 'height' }}
            >
                <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-white/95 font-normal">
                    {text}
                </p>
            </motion.div>

            <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-1 flex items-center justify-center p-1 hover:bg-white/10 rounded-full transition-colors self-end text-sky-300 group"
                title={isExpanded ? "Hide Details" : "Show More"}
                aria-label={isExpanded ? "Hide Details" : "Show More"}
            >
                {isExpanded ? (
                    <ChevronUp size={16} className="group-hover:-translate-y-0.5 transition-transform" />
                ) : (
                    <ChevronDown size={16} className="group-hover:translate-y-0.5 transition-transform animate-bounce" />
                )}
            </button>
        </div>
    );
});
ExpandableUserMessage.displayName = 'ExpandableUserMessage';

const ChatMessage = React.memo(({ message, onSend, onViewDetails, isActiveAction, onNavigateToAuth, onProductSelect, onConfirmOrder, onClearCart, onRestore, onSave, onCancel }: {
    message: ExtendedMessage;
    onSend: (t: string) => void;
    onViewDetails: (p: AIProduct) => void;
    isActiveAction: boolean;
    onNavigateToAuth: (mode: 'SIGNIN' | 'SIGNUP') => void;
    onProductSelect: (p: AIProduct, id: string) => void;
    onConfirmOrder: () => void;
    onClearCart: () => void;
    onRestore: () => void;
    onSave: () => void;
    onCancel: () => void;
}) => {
    const isAI = message.sender === 'ai';

    const renderContent = () => {
        switch (message.contentType) {
            case 'image_user_upload': {
                const hasCaption = typeof message.content === 'string' && message.content.trim().length > 0 &&
                    !message.content.includes("Analyzing") &&
                    !message.content.includes("Processing");
                const hasImg = !!message.imageUrl;

                return (
                    <div className="flex flex-col gap-2 items-end w-full">
                        {hasImg && (
                            <div className="relative w-[110px] sm:w-[140px] aspect-[4/3] flex-none overflow-hidden shadow-lg rounded-2xl bg-white/[0.06] backdrop-blur-xl">
                                <Image
                                    src={message.imageUrl!}
                                    alt="Uploaded"
                                    fill
                                    loading="lazy"
                                    decoding="async"
                                    className="object-contain"
                                />
                            </div>
                        )}
                        {hasCaption && (
                            <div className="px-4 py-3 rounded-[24px] rounded-br-sm bg-white/[0.09] backdrop-blur-2xl text-white/95 text-[14px] leading-relaxed break-words max-w-[90%] shadow-lg">
                                {typeof message.content === 'string' ? message.content : ''}
                            </div>
                        )}
                    </div>
                );
            }
            case 'text':
            case 'error':
            case 'info':
            case 'success_text': {
                if (!isAI && message.contentType === 'text') {
                    return <ExpandableUserMessage text={typeof message.content === 'string' ? message.content : ''} />;
                }
                return (
                    <div className={`w-full space-y-1.5 ${message.contentType === 'error' ? 'bg-rose-950/30 p-3 rounded-2xl text-rose-200' : ''}`}>
                        
                        <div className="text-[14px] leading-[1.55] text-white/85 font-normal break-words">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    p: ({ node, ...props }) => (
                                        <p className="mb-2.5 last:mb-0 text-start whitespace-pre-wrap leading-[1.55]" {...props} />
                                    ),
                                    strong: ({ node, ...props }) => (
                                        <strong className="font-semibold text-white" {...props} />
                                    ),
                                    ul: ({ node, ...props }) => (
                                        <ul className="list-disc list-inside space-y-1.5 mb-2.5 mt-1.5 last:mb-0" {...props} />
                                    ),
                                    li: ({ node, ...props }) => (
                                        <li className="ps-0 leading-[1.55]" {...props} />
                                    ),
                                }}
                            >
                                {typeof message.content === 'string' ? message.content : ''}
                            </ReactMarkdown>
                        </div>
                    </div>
                );
            }
            case 'confirmation_prompt':
                if (!isActiveAction) return null;
                return (
                    <div className="w-full">
                        
                        <p className="whitespace-pre-wrap mb-4 text-[14px] leading-[1.55] text-white/85 font-normal">
                            {typeof message.content === 'string' ? message.content : ''}
                        </p>
                        {isActiveAction && (
                            <div className="flex flex-wrap gap-2.5">
                                {message.options?.map((option: string) => {
                                    const isConfirm = option === 'Confirm Order';

                                    let buttonStyle = "bg-white/[0.08] text-white/90 hover:bg-white/[0.16] shadow-[inset_0_1px_1px_rgba(255,255,255,0.18)]";

                                    if (isConfirm) {
                                        buttonStyle = "bg-gradient-to-r from-sky-400 to-cyan-400 text-[#05070E] shadow-[0_0_25px_rgba(56,189,248,0.35)] hover:shadow-[0_0_35px_rgba(56,189,248,0.55)]";
                                    } else if (option === 'Switch to PayPal') {
                                        buttonStyle = "bg-[#003087] text-white hover:bg-[#003087]/85";
                                    } else if (option === 'Retry Payment') {
                                        buttonStyle = "bg-emerald-600 text-white hover:bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)]";
                                    }

                                    return (
                                        <motion.button
                                            type="button"
                                            key={option}
                                            whileHover={{ scale: 1.03 }}
                                            whileTap={{ scale: 0.96 }}
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
                                            className={`flex items-center justify-center gap-2 px-5 py-2.5 rounded-full backdrop-blur-2xl transition-all duration-300 transform-gpu ${buttonStyle}`}
                                        >
                                            {isConfirm && <Zap size={15} strokeWidth={2.5} />}
                                            <span className={`text-[11px] uppercase tracking-[0.14em] ${isConfirm ? 'font-bold' : 'font-semibold'}`}>
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
            case 'proactive_suggestion': {
                const insightText = (typeof message.content === 'string' && message.content.trim().length > 0)
                    ? message.content
                    : ((message.reason || message.ai_notes) || '');
                const secondaryReasoning = (typeof message.content === 'string' && message.content.trim().length > 0 && (message.reason || message.ai_notes))
                    ? (message.reason || message.ai_notes)
                    : undefined;

                return (
                    <div className="w-full">
                        {insightText && (
                            <div className="mb-3">
                               
                                <p className="whitespace-pre-wrap text-[14px] leading-[1.55] text-white/85 font-normal">
                                    {insightText}
                                </p>
                            </div>
                        )}

                        

<ProductCarousel
                            products={message.products || []}
                            onSelect={onProductSelect}
                            onViewDetails={onViewDetails}
                        />

                        {secondaryReasoning && (
                            <AIReasoning text={secondaryReasoning} />
                        )}
                    </div>
                );
            }
            case 'recovery_prompt':
                if (!isActiveAction) return null;
                return (
                    <div className="flex items-center justify-center w-full py-3">
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0, y: 10 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            style={{ willChange: 'transform, opacity' }}
                            className="flex items-center gap-2 p-2 bg-white/[0.06] backdrop-blur-3xl rounded-full shadow-[0_20px_50px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.15)] transform-gpu"
                        >
                            {[
                                { icon: Undo2, label: "UNDO", action: onRestore, textColor: "text-white", hoverBg: "hover:bg-sky-500/15" },
                                { icon: Save, label: "SAVE", action: onSave, textColor: "text-white", hoverBg: "hover:bg-indigo-500/15" },
                                { icon: X, label: "CANCEL", action: onCancel, textColor: "text-white", hoverBg: "hover:bg-rose-500/15" }
                            ].map((btn, idx) => (
                                <motion.button
                                    type="button"
                                    key={idx}
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                    onClick={btn.action}
                                    className={`flex flex-col items-center justify-center min-w-[60px] h-[60px] gap-1.5 rounded-full transition-all duration-300 transform-gpu ${btn.hoverBg} group`}
                                >
                                    <btn.icon size={17} strokeWidth={2.2} className="text-white opacity-80 group-hover:opacity-100" />
                                    <span className={`text-[8px] font-bold uppercase tracking-widest ${btn.textColor}`}>
                                        {btn.label}
                                    </span>
                                </motion.button>
                            ))}
                        </motion.div>
                    </div>
                );
            default:
                return null;
        }
    };

    const contentNode = renderContent();

    if (['cart_preview', 'typing', 'payment_intent', 'ORDER_CANCELLED', 'ORDER_CONFIRMED', 'system'].includes(message.contentType)) return null;
    if (!contentNode) return null;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ willChange: 'transform, opacity' }}
            className={`flex items-end gap-2 w-full mb-4 transform-gpu ${isAI ? 'justify-start' : 'justify-end'}`}
        >
            <div
                className={`${
                    message.contentType === 'image_user_upload'
                        ? 'w-full'
                        : isAI
                            ? 'w-full text-white/90'
                            : 'w-fit max-w-[88%] px-4 py-3 rounded-[24px] rounded-br-sm bg-white/[0.09] backdrop-blur-2xl text-white/95 text-[14px] leading-relaxed break-words shadow-[0_10px_30px_rgba(0,0,0,0.35),inset_0_1px_1px_rgba(255,255,255,0.14)]'
                } transform-gpu`}
            >
                {contentNode}
            </div>
        </motion.div>
    );
}, (prevProps, nextProps) => {
    return prevProps.message.id === nextProps.message.id &&
           prevProps.message.content === nextProps.message.content &&
           prevProps.isActiveAction === nextProps.isActiveAction;
});
ChatMessage.displayName = 'ChatMessage';

const AIChatSidebar = React.memo(({ messages, glowingProductId, onRemoveItem, isMobileOpen, onCloseMobile }: {
    messages: ExtendedMessage[];
    glowingProductId: number | null;
    onRemoveItem: (productId: number) => void;
    isMobileOpen: boolean;
    onCloseMobile: () => void;
}) => {
    const cart = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
        return (lastCartMessage?.content as { items: AIProduct[]; total: number }) || { items: [], total: 0 };
    }, [messages]);

    return (
        <>
            <AnimatePresence>
                {isMobileOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onCloseMobile}
                        className="absolute inset-0 bg-black/60 backdrop-blur-md z-[100] transform-gpu"
                        style={{ willChange: 'opacity' }}
                    />
                )}
            </AnimatePresence>

            <div className={`
                absolute top-0 end-0 bottom-0 z-[110] w-full md:w-[460px] transform transition-transform duration-500 cubic-bezier(0.34, 1.56, 0.64, 1)
                backdrop-blur-3xl bg-[#060913]/95 flex-col overflow-hidden will-change-transform
                ${isMobileOpen ? 'translate-x-0' : 'translate-x-full'}
                ${!isMobileOpen ? 'hidden' : 'flex'}
            `}>
                <div className="flex justify-between items-center px-6 py-5 bg-white/[0.02]">
                    <span className="text-xs font-semibold uppercase text-white/90 tracking-[0.18em] flex items-center gap-2">
                        <ShoppingBag size={16} strokeWidth={2} />
                        <span>Bag Summary</span>
                    </span>
                    <button
                        type="button"
                        onClick={onCloseMobile}
                        aria-label="Close bag summary"
                        className="w-10 h-10 rounded-full bg-white/[0.08] text-white/80 hover:bg-white/[0.15] hover:text-white flex items-center justify-center transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="flex-grow p-6 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-sky-500/20 scrollbar-track-transparent relative z-10">
                    <div className="space-y-3.5 flex-grow">
                        <AnimatePresence>
                            {cart.items.length === 0 ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex flex-col items-center justify-center h-48 text-white/35 gap-3 rounded-3xl bg-white/[0.03]"
                                >
                                    <ShoppingCart size={30} className="opacity-40" />
                                    <p className="text-xs uppercase tracking-widest font-mono">Empty | Bag</p>
                                </motion.div>
                            ) : cart.items.map((item: AIProduct, index: number) => (
                                <motion.div
                                    key={item.product_id || index}
                                    layout
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{
                                        opacity: 1,
                                        x: 0,
                                        backgroundColor: item.product_id === glowingProductId ? "rgba(56, 189, 248, 0.14)" : "rgba(255, 255, 255, 0.04)",
                                    }}
                                    exit={{ opacity: 0, x: 20 }}
                                    style={{ willChange: 'transform, opacity, background-color' }}
                                    className="flex justify-between items-start p-3.5 rounded-2xl transition-colors group relative overflow-hidden transform-gpu shadow-[inset_0_1px_1px_rgba(255,255,255,0.08)]"
                                >
                                    {item.product_id === glowingProductId && (
                                        <motion.div layoutId="glow" className="absolute inset-0 bg-sky-400/5 pointer-events-none" transition={{ duration: 0.3 }} />
                                    )}
                                    <div className="flex items-center gap-3 flex-1 min-w-0 relative z-10">
                                        <div className="w-12 h-12 rounded-xl bg-white/[0.06] flex items-center justify-center overflow-hidden">
                                            <ShoppingBag size={16} className="text-white/50" />
                                        </div>
                                        <div className="flex flex-col min-w-0">
                                            <span className="text-white/95 text-sm font-semibold leading-snug tracking-tight break-words" title={item.name}>
                                                {item.name}
                                            </span>
                                            <span className="text-[10px] text-white/45 font-mono mt-0.5">QTY: {item.quantity}</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end gap-1.5 relative z-10">
                                        <span className="font-semibold text-sky-300 font-mono text-sm">
                                            ${(Number(item.price) * (item.quantity || 1)).toFixed(2)}
                                        </span>
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onRemoveItem(Number(item.product_id || item.id));
                                            }}
                                            className="p-1.5 rounded-full bg-rose-500/15 text-rose-300 active:bg-rose-500 active:text-white md:hover:bg-rose-500 md:hover:text-white transition-all duration-200"
                                            title="Remove Item"
                                            aria-label={`Remove ${item.name}`}
                                        >
                                            <X size={13} />
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </div>

                <div className="flex-shrink-0 p-6 bg-[#050811]/90 space-y-5 relative z-20">
                  
                    <div className="flex justify-between items-end">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-white/50 uppercase tracking-widest font-semibold">Total</span>
                            <span className="text-[10px] text-white/35">Including Service Fees</span>
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
        isProcessing: boolean;
    }) => {
        const [value, setValue] = useState('');
        const [pendingImage, setPendingImage] = useState<{ url: string; base64: string } | null>(null);
        const [isListening, setIsListening] = useState(false);
        const [isDragOver, setIsDragOver] = useState(false);
        const fileInputRef = useRef<HTMLInputElement>(null);
        const textareaRef = useRef<HTMLTextAreaElement>(null);
        const focusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

        useEffect(() => {
            return () => {
                if (focusTimerRef.current) clearTimeout(focusTimerRef.current);
            };
        }, []);

        const handleAutoResize = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
            setValue(e.target.value);
            requestAnimationFrame(() => {
                if (textareaRef.current) {
                    textareaRef.current.style.height = 'auto';
                    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
                }
            });
        }, []);

        const processSelectedFile = useCallback((file: File | undefined) => {
            if (!file || !file.type.startsWith('image/')) return;
            const reader = new FileReader();
            reader.onloadend = () => {
                const fullDataUrl = reader.result as string;
                const base64Raw = fullDataUrl.split(',')[1];
                if (base64Raw) {
                    setPendingImage({ url: fullDataUrl, base64: base64Raw });
                }
            };
            reader.readAsDataURL(file);
        }, []);

        const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
            processSelectedFile(e.target.files?.[0]);
            e.target.value = '';
        }, [processSelectedFile]);

        const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
            e.preventDefault();
            setIsDragOver(false);
            processSelectedFile(e.dataTransfer.files?.[0]);
        }, [processSelectedFile]);

        const handleVoiceActivate = useCallback(() => {
            const storeState = useAIOrderingStore.getState();
            if (typeof storeState.setVoiceMode === 'function') {
                storeState.setVoiceMode(true);
                return;
            }
            if (!('webkitSpeechRecognition' in window)) {
                return;
            }
            if (isListening) {
                setIsListening(false);
                return;
            }
            const recognition = new window.webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            recognition.onstart = () => setIsListening(true);
            recognition.onend = () => setIsListening(false);
            recognition.onresult = (event: any) => {
                const transcript = event.results?.[0]?.[0]?.transcript;
                if (transcript) setValue(transcript);
            };
            recognition.start();
        }, [isListening]);

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
            }
        }, [isTyping, isProcessing, pendingImage, value, onSendImage, onSend]);

        const isInputLocked = isTyping || isProcessing;
        const isSendButtonDisabled = isInputLocked || (!value.trim() && !pendingImage);

        return (
            <div
                onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                className="px-5 pb-6 pt-2 flex-shrink-0 relative z-20"
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    accept="image/*"
                    className="hidden"
                    onChange={handleImageSelect}
                />

                <AnimatePresence>
                    {pendingImage && (
                        <motion.div
                            initial={{ opacity: 0, y: 10, height: 0 }}
                            animate={{ opacity: 1, y: 0, height: 'auto' }}
                            exit={{ opacity: 0, y: 10, height: 0 }}
                            style={{ willChange: 'transform, opacity, height' }}
                            className="absolute -top-20 start-7 z-30 transform-gpu"
                        >
                            <div className="relative group">
                                <div className="w-16 h-16 rounded-2xl overflow-hidden shadow-[0_10px_25px_rgba(0,0,0,0.6),0_0_15px_rgba(56,189,248,0.3)] bg-black/60 backdrop-blur-md">
                                    <Image src={pendingImage.url} alt="Preview" width={64} height={64} className="object-cover w-full h-full" />
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setPendingImage(null)}
                                    aria-label="Remove attached image"
                                    className="absolute -top-1.5 -end-1.5 bg-rose-500 text-white rounded-full p-1 shadow-md hover:scale-110 transition-transform"
                                >
                                    <X size={11} />
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Luminous Floating Capsule Input Bar matching screenshot */}
                <div
                    className={`relative w-[340px] mx-auto rounded-full p-[1.5px] transition-all duration-300 ${
                        isDragOver
                            ? 'bg-gradient-to-r from-sky-400 via-cyan-300 to-indigo-400 shadow-[0_0_40px_rgba(56,189,248,0.45)]'
                            : 'bg-gradient-to-r from-[#38BDF8]/45 via-white/25 to-[#818CF8]/45 shadow-[0_0_32px_rgba(56,189,248,0.22),0_12px_32px_rgba(0,0,0,0.65)]'
                    }`}
                >
                    <div className="flex items-center gap-1.5 bg-[#0E131F]/95 backdrop-blur-2xl rounded-full ps-1.5 pe-2 py-1">
                        {/* Left Circular Camera Button */}
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            aria-label="Upload or scan image"
                            title="Upload Visual Data"
                            className="w-9 h-9 rounded-full bg-white/[0.08] hover:bg-white/[0.15] text-white/75 hover:text-white flex items-center justify-center transition-all flex-shrink-0 shadow-[inset_0_1px_1px_rgba(255,255,255,0.12)]"
                        >
                            <Camera size={17} strokeWidth={1.8} />
                        </button>

                        {/* Center Auto-Resizing Input */}
                        <div className="relative flex-grow min-w-0 flex items-center">
                            <textarea
                                ref={textareaRef}
                                value={value}
                                onChange={handleAutoResize}
                                rows={1}
                                onFocus={() => {
                                    if (focusTimerRef.current) clearTimeout(focusTimerRef.current);
                                    focusTimerRef.current = setTimeout(() => {
                                        if (textareaRef.current) {
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
                                placeholder={
                                    isListening
                                        ? 'Listening...'
                                        : isInputLocked
                                            ? 'Thinking...'
                                            : 'Ask, drop image, or speak...'
                                }
                                disabled={isInputLocked}
                                className="w-full bg-transparent py-1.5 px-1 text-[13px] text-white/95 placeholder-white/40 placeholder:whitespace-nowrap focus:outline-none transition-all duration-200 font-normal resize-none overflow-hidden no-scrollbar max-h-[120px] leading-snug"
                                style={{ overflowY: textareaRef.current && textareaRef.current.scrollHeight > 120 ? 'auto' : 'hidden' }}
                            />
                        </div>

                        {/* Right Inline Microphone Button */}
                        <button
                            type="button"
                            onClick={handleVoiceActivate}
                            aria-label="Speak to order"
                            title="Talk to order with air"
                            className="w-9 h-9 rounded-full text-white/60 hover:text-white hover:bg-white/[0.08] flex items-center justify-center transition-all flex-shrink-0"
                        >
                            <Mic size={18} strokeWidth={1.8} />
                        </button>

                        {/* Far-Right Glowing Sky-Blue Send Plane Button */}
                        <button
                            type="button"
                            disabled={isSendButtonDisabled}
                            onClick={handleTriggerSend}
                            aria-label="Send message"
                            className="w-8 h-8 rounded-full flex items-center justify-center text-[#38BDF8] hover:text-[#7DD3FC] disabled:text-[#38BDF8]/35 transition-all flex-shrink-0 drop-shadow-[0_0_8px_rgba(56,189,248,0.45)]"
                        >
                            {isInputLocked ? (
                                <Loader2 size={17} className="animate-spin text-[#38BDF8]" />
                            ) : (
                                <SendPlaneIcon size={18} />
                            )}
                        </button>
                    </div>
                </div>
            </div>
        );
    }
);
ChatInput.displayName = 'ChatInput';

const FlyToCartAnimator = React.memo(() => {
    const flyQueue = useAIOrderingStore(useShallow(state => state.flyQueue));
    const removeFlyItem = useAIOrderingStore(state => state.removeFlyItem);

    return (
        <AnimatePresence>
            {flyQueue.map((item) => {
                const startEl = document.getElementById(item.startElementId);
                const endEl = document.getElementById('order-summary-cart-icon');

                if (!startEl) return null;
                const startRect = startEl.getBoundingClientRect();
                const endPos = endEl ? endEl.getBoundingClientRect() : { top: 50, left: window.innerWidth - 50 };

                const imageSource = getAbsoluteImageUrl(item.image);

                const TARGET_SIZE = 10;
                const targetScale = TARGET_SIZE / Math.max(startRect.width, 1);

                const midY = Math.min(startRect.top, endPos.top) - 80;

                return (
                    <motion.div
                        key={item.animationId}
                        className="fixed z-[9999] rounded-full overflow-hidden shadow-[0_0_30px_rgba(56,189,248,0.85)] transform-gpu"
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            pointerEvents: 'none',
                            width: startRect.width,
                            height: startRect.height,
                            willChange: 'transform, opacity'
                        }}
                        initial={{
                            x: startRect.left,
                            y: startRect.top,
                            opacity: 1,
                            scale: 0.6,
                            rotate: 0
                        }}
                        animate={{
                            x: [startRect.left, endPos.left - 10],
                            y: [startRect.top, midY, endPos.top - 10],
                            opacity: [1, 1, 0],
                            scale: [0.6, 0.75, targetScale],
                            rotate: [0, -20, 360]
                        }}
                        transition={{
                            duration: 0.7,
                            ease: "easeInOut",
                            times: [0, 0.3, 1]
                        }}
                        onAnimationComplete={() => removeFlyItem(item.animationId)}
                    >
                        <Image src={imageSource} alt="product" width={100} height={100} priority className="w-full h-full object-cover" />
                    </motion.div>
                );
            })}
        </AnimatePresence>
    );
});
FlyToCartAnimator.displayName = 'FlyToCartAnimator';

const PaymentFatalError = React.memo(({ keyMissing }: { keyMissing: boolean }) => (
    <div className="w-full h-full flex flex-col items-center justify-center p-10 text-center bg-black/40 backdrop-blur-2xl rounded-[30px]">
        <div className="p-4 bg-rose-500/10 rounded-full mb-4 animate-pulse">
            <ShieldOff size={48} className="text-rose-400" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2 tracking-wide font-mono">SECURE GATEWAY OFFLINE</h3>
        <p className="text-white/55 max-w-md text-sm leading-relaxed">
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

export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const router = useRouter();
    const [detailProduct, setDetailProduct] = useState<AIProduct | null>(null);
    const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
    const timersRef = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

    const registerTimeout = useCallback((fn: () => void, delayMs: number) => {
        const id = setTimeout(() => {
            timersRef.current.delete(id);
            fn();
        }, delayMs);
        timersRef.current.add(id);
        return id;
    }, []);

    useEffect(() => {
        const activeTimers = timersRef.current;
        return () => {
            activeTimers.forEach(id => clearTimeout(id));
            activeTimers.clear();
        };
    }, []);

    useBodyScrollLock({ locked: isOpen });
    const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '';
    const stripePromise: Promise<Stripe | null> | null = useMemo(() => {
        return STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : null;
    }, [STRIPE_PUBLISHABLE_KEY]);

    const [stripeObj, setStripeObj] = useState<Stripe | null>(null);
    const [isStripeError, setIsStripeError] = useState(false);
    const [isAnimationComplete, setIsAnimationComplete] = useState(false);

    useEffect(() => {
        let isMounted = true;
        if (stripePromise) {
            stripePromise
                .then(stripe => {
                    if (isMounted) {
                        setStripeObj(stripe);
                        setIsStripeError(false);
                    }
                })
                .catch(err => {
                    console.error("Stripe Load Error:", err);
                    if (isMounted) setIsStripeError(true);
                });
        } else {
            setIsStripeError(true);
        }
        return () => {
            isMounted = false;
        };
    }, [stripePromise]);

    const messages = useAIOrderingStore(useShallow(state => state.messages)) as ExtendedMessage[];
    const isLoading = useAIOrderingStore(state => state.isLoading);
    const isProcessing = useAIOrderingStore(state => state.isProcessing);
    const isShippingStep = useAIOrderingStore(state => state.isShippingStep);
    const shippingAddress = useAIOrderingStore(state => state.shippingAddress);
    const submitShippingAddress = useAIOrderingStore(state => state.submitShippingAddress);
    const cancelShipping = useAIOrderingStore(state => state.cancelShipping);
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
    const currentAccessToken = (session as any)?.accessToken;
    const isConnectedRef = useRef(false);

    const cartItems = useMemo(() => {
        const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
        return (lastCartMessage?.content as { items: AIProduct[] })?.items || [];
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
        return () => {
            isConnectedRef.current = false;
            actions.disconnectSocket();
        };
    }, [status, currentAccessToken, actions]);

    useEffect(() => {
        const scrollContainer = chatEndRef.current?.parentElement;
        if (!scrollContainer) return;

        let rafId: number;
        let timeoutId: ReturnType<typeof setTimeout>;

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
            registerTimeout(() => {
                actions.addSocketAIMessage({
                    type: 'confirmation_prompt',
                    content: "Hey there! Ready to experience smart shopping? Let's get you set up in seconds.",
                    options: ["Sign In", "Sign Up"],
                });
                useAIOrderingStore.setState({ isLoading: false });
            }, SIMULATED_AUTH_DELAY_MS);
            return;
        }
        actions.sendMessage(text, false);
    }, [status, actions, registerTimeout]);

    const handleProductSelect = useCallback((product: AIProduct, elementId: string): void => {
        if (status !== 'authenticated') {
            useAIOrderingStore.setState({ isLoading: true });

            registerTimeout(() => {
                actions.addSocketAIMessage({
                    type: 'confirmation_prompt',
                    content: 'Sign in to secure your selection.',
                    options: ['Sign In', 'Sign Up'],
                });
                useAIOrderingStore.setState({ isLoading: false });
            }, SIMULATED_AUTH_DELAY_MS);

            return;
        }

        const { messages: currentMessages } = useAIOrderingStore.getState();
        const lastMessage = currentMessages[currentMessages.length - 1] as ExtendedMessage | undefined;
        const lastActiveTime = lastMessage?.timestamp ?? 0;

        const isZombieConnection = (Date.now() - lastActiveTime) > ZOMBIE_CONNECTION_THRESHOLD_MS;

        if (socketStatus !== 'connected' || isZombieConnection) {
            if (!currentAccessToken) {
                actions.addSocketAIMessage({
                    type: 'error',
                    content: 'Session token missing. Cannot reconnect.',
                });
                return;
            }

            useAIOrderingStore.setState({ isLoading: true });
            actions.disconnectSocket();
            actions.connectSocket(currentAccessToken);
        }

        actions.addProductById({ ...product, id: product.id as number }, elementId);
    }, [status, socketStatus, currentAccessToken, actions, registerTimeout]);

    const stripeAppearance = useMemo(() => ({
        theme: 'night' as const,
        labels: 'floating' as const,
        variables: {
            colorPrimary: '#38BDF8',
            colorBackground: '#0A0E17',
            colorText: '#ffffff',
            colorDanger: '#f43f5e',
            fontFamily: 'system-ui, sans-serif',
            spacingUnit: '4px',
            borderRadius: '16px',
            colorIcon: '#ffffff',
        },
        rules: {
            '.Input': { backgroundColor: '#111827', border: 'none' },
            '.Input:focus': { boxShadow: '0 0 0 1px #38BDF8' },
            '.Tab': { backgroundColor: '#111827', color: '#ffffff' },
            '.Tab--selected': { backgroundColor: '#38BDF8', color: '#000000' },
        }
    }), []);

    const stripeOptions = useMemo<StripeElementsOptions | undefined>(() => {
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
        router.push(`/login?mode=${mode}`);
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
                    style={{
                        colorScheme: 'dark',
                        willChange: 'opacity',
                        fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Plus Jakarta Sans', 'Inter', sans-serif"
                    }}
                    className="fixed inset-0 z-50 bg-[#04070F]/95 backdrop-blur-3xl flex justify-center items-center p-0 sm:p-4 overflow-hidden transform-gpu"
                >
                    <FlyToCartAnimator />

                    <AnimatePresence>
                        {detailProduct && (
                            <motion.div
                                initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
                                animate={{ opacity: 1, backdropFilter: "blur(16px)" }}
                                exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
                                transition={{ duration: 0.3, ease: "easeOut" }}
                                style={{ willChange: 'opacity, backdrop-filter' }}
                                className="fixed inset-0 z-[100] bg-black/65 flex items-center justify-center p-4 transform-gpu"
                                onClick={() => setDetailProduct(null)}
                            >
                                <div onClick={(e) => e.stopPropagation()} className="w-full h-full max-w-[460px] max-h-[1050px] md:max-h-[90vh]">
                                    <ProductDetailsCard product={detailProduct} onClose={() => setDetailProduct(null)} />
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Borderless Swim-Free Main Surface */}
                    <motion.div
                        initial={{ scale: 0.97, opacity: 0, y: 20 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } }}
                        exit={{ scale: 0.97, opacity: 0, y: 20, transition: { duration: 0.25 } }}
                        onClick={(e) => e.stopPropagation()}
                        style={{ willChange: 'transform, opacity' }}
                        className="w-full h-full max-w-[460px] max-h-full md:max-h-[92vh] flex flex-col bg-transparent overflow-hidden relative transform-gpu"
                    >
                        <div className="absolute inset-0 z-[120] overflow-hidden pointer-events-none">
                            <AIVoiceOverlay />
                        </div>

                        {/* Atmospheric Multi-Point Radial Glows matching the screenshot */}
                        <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-[380px] h-[260px] bg-[#38BDF8]/15 blur-[95px] pointer-events-none rounded-full" />
                        <div className="absolute top-16 end-0 w-[260px] h-[260px] bg-indigo-500/12 blur-[100px] pointer-events-none rounded-full" />
                        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[360px] h-[180px] bg-[#38BDF8]/10 blur-[90px] pointer-events-none rounded-full" />

                        {/* Header: Left "airdeliverOS • Secured" Frosted Pill + Right Twin Glass Circle Buttons */}
                        <header className="px-6 pt-6 pb-3 flex items-center justify-between flex-shrink-0 relative z-10">
                            <div className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/[0.08] backdrop-blur-2xl shadow-[0_8px_30px_rgba(0,0,0,0.35),inset_0_1px_1px_rgba(255,255,255,0.16)]">
                                <span className="w-2 h-2 rounded-full bg-[#7DD3FC] shadow-[0_0_8px_#7DD3FC]" />
                                <span className="text-[13px] font-medium text-white/95 tracking-tight">Order with Air</span>
                                
                            </div>

                            <div className="flex items-center gap-2.5 ms-auto">
                                {!isPaymentMode && (
                                    <div className="flex-shrink-0">
                                        <motion.button
                                            type="button"
                                            id="order-summary-cart-icon"
                                            animate={cartControls}
                                            onClick={() => setIsMobileSidebarOpen(true)}
                                            aria-label="Open shopping bag"
                                            className="w-11 h-11 rounded-full bg-white/[0.08] backdrop-blur-2xl text-white/85 hover:bg-white/[0.15] hover:text-white transition-all flex items-center justify-center relative shadow-[0_8px_24px_rgba(0,0,0,0.35),inset_0_1px_1px_rgba(255,255,255,0.16)]"
                                        >
                                            <ShoppingBag size={18} strokeWidth={1.8} />
                                            {cartItems.length > 0 && (
                                                <span className="absolute -top-0.5 -end-0.5 bg-[#475569] text-white text-[10px] font-semibold w-4 h-4 rounded-full flex items-center justify-center shadow-md">
                                                    {cartItems.length}
                                                </span>
                                            )}
                                        </motion.button>
                                    </div>
                                )}

                                <button
                                    type="button"
                                    onClick={handleClose}
                                    aria-label="Close overlay"
                                    className="w-11 h-11 rounded-full bg-white/[0.08] backdrop-blur-2xl text-white/85 hover:bg-white/[0.15] hover:text-white transition-all duration-300 flex items-center justify-center shadow-[0_8px_24px_rgba(0,0,0,0.35),inset_0_1px_1px_rgba(255,255,255,0.16)]"
                                >
                                    <X size={18} strokeWidth={1.8} />
                                </button>
                            </div>
                        </header>

                        {/* Main Content Area */}
                        <div className="flex-grow flex overflow-hidden relative z-10">
                            <AnimatePresence mode="wait">
                                {isShippingStep ? (
                                    <ShippingAddressForm initialValue={shippingAddress} onSubmit={submitShippingAddress} onBack={cancelShipping} />
                                ) : paymentDetails?.gateway_provider === 'paypal' && paymentDetails.order_data ? (
                                    <PayPalApproval approvalUrl={paymentDetails.action_url || ''} orderId={paymentDetails.order_data.order_id} total={paymentDetails.order_data.total} currency={paymentDetails.order_data.currency} />
                                ) : isPaymentMode ? (
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
                                                const orderData = paymentDetails?.order_data;
                                                const hasValidData = Boolean(
                                                    stripeOptions?.clientSecret &&
                                                    orderData &&
                                                    typeof orderData.total === 'number'
                                                );

                                                if (!hasValidData) {
                                                    return (
                                                        <div className="flex flex-col items-center justify-center h-full p-6 text-center">
                                                            <div className="p-4 bg-rose-500/10 rounded-full mb-4">
                                                                <AlertCircle size={48} className="text-rose-400" />
                                                            </div>
                                                            <h3 className="text-xl font-bold text-white mb-2 tracking-wide font-mono">DATA CONTRACT BREACH</h3>
                                                            <p className="text-white/55 max-w-md text-sm leading-relaxed">
                                                                Incomplete payment payload received from server. Missing order total or items.
                                                            </p>
                                                        </div>
                                                    );
                                                }

                                                return (
                                                    <Elements
                                                        key={`${stripeOptions.clientSecret}-loaded`}
                                                        stripe={stripeObj}
                                                        options={stripeOptions}
                                                    >
                                                        <AIPaymentForm
                                                            orderId={orderData!.order_id}
                                                            total={orderData!.total}
                                                            items={orderData!.items}
                                                            onPaymentSuccess={handlePaymentSuccess}
                                                            clientSecret={stripeOptions.clientSecret}
                                                            currency={orderData!.currency}
                                                        />
                                                    </Elements>
                                                );
                                            })()
                                        ) : (
                                            <div className="absolute inset-0 flex flex-col items-center justify-center w-full h-full z-50">
                                                {isStripeError || isKeyMissing ? (
                                                    <PaymentFatalError keyMissing={isKeyMissing} />
                                                ) : (
                                                    <Loader2 size={26} className="text-sky-400 animate-spin" />
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
                                        <div className="flex-grow px-6 pt-4 pb-6 space-y-5 overflow-y-auto scrollbar-thin scrollbar-thumb-sky-500/10 scrollbar-track-transparent">
                                            {/* Hero Headline Section matching the screenshot */}
                                            <div className="pt-1 pb-2">
                                                <h1 className="text-[23px] sm:text-[25px] font-semibold text-white tracking-[-0.02em] leading-snug">
                                                    Don’t search. Just ask.
                                                </h1>
                                                <p className="text-[15px] sm:text-[20px] font-normal text-white/45 tracking-[-0.01em] leading-snug mt-0.5">
                                                    Powered by airdeliver, Turning intent into reality.
                                                </p>
                                            </div>

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
                                                        onCancel={() => actions.hardCancelOrder('changed_mind')}
                                                    />
                                                ))}
                                            </AnimatePresence>
                                            <div ref={chatEndRef} />
                                        </div>

                                        <ChatInput
                                            onSend={handleSendMessage}
                                            onSendImage={actions.sendImage}
                                            isTyping={isLoading}
                                            isProcessing={isProcessing}
                                        />
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {!isPaymentMode && (
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
