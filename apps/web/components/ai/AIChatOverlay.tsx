// apps/web/components/ai/AIChatOverlay.tsx

'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, CornerDownRight, ShoppingCart, Cpu, Clock, X, ChevronLeft, ChevronRight, Save, Trash2, Undo2, AlertCircle, ShoppingBag, ShieldOff, Loader2 } from 'lucide-react';
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
                className="flex flex-col p-5 bg-black/80 backdrop-blur-md rounded-2xl border border-cyan-500/20 h-full text-left shadow-lg shadow-cyan-900/10 group relative"
                whileHover={{ 
                    scale: 1.02, 
                    zIndex: 50,
                    borderColor: "rgba(6, 182, 212, 0.5)",
                    boxShadow: "0 0 20px rgba(6, 182, 212, 0.15)"
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
                <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl" />
                <div className="relative z-10 flex-grow flex flex-col">
                    <div className="relative h-32 mb-4 w-full flex items-center justify-center bg-white/5 rounded-xl p-2 group-hover:bg-white/10 transition-colors">
                        <Image
                            id={elementId}
                            src={imageUrl}
                            alt={product.name}
                            width={150}
                            height={150}
                            className="w-full h-full object-contain drop-shadow-xl group-hover:scale-110 transition-transform duration-500 ease-out"
                        />
                    </div>
                    <h4 className="text-base font-bold text-white mb-1 line-clamp-1">{product.name}</h4>
                    <div className="flex items-end gap-2 mb-3">
                        <span className="text-xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-400">
                            ${product.price.toFixed(2)}
                        </span>
                        {product.rating && (
                            <span className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                                ⭐ {product.rating} <span className="text-gray-600">|</span> {product.stock_status || 'In Stock'}
                            </span>
                        )}
                    </div>
                    <div className="mt-auto">
                        <motion.button
                            onClick={handleSelect}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.95 }}
                            className="w-full relative group/btn overflow-hidden rounded-xl bg-cyan-950/30 border border-cyan-500/30 p-[1px]"
                        >
                            <div className="relative px-4 py-3 bg-black/50 backdrop-blur-xl rounded-[10px] flex items-center justify-center gap-2 transition-all duration-300 group-hover/btn:bg-cyan-500 group-hover/btn:text-black">
                                <ShoppingBag size={18} className="text-cyan-400 group-hover/btn:text-black transition-colors" />
                                <span className="font-bold text-sm text-cyan-100 group-hover/btn:text-black">Add to Cart</span>
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
        <div className="relative my-4 px-1">
            <div className="overflow-hidden" ref={emblaRef}>
                <div className="flex -ml-3">
                    {products.map((p, i) => <CarouselProductCard key={p.id || i} product={p} onSelect={onSelect} totalItems={totalItems} />)}
                </div>
            </div>
            {canScroll && (
                <>
                    <button onClick={scrollPrev} className="absolute top-1/2 -translate-y-1/2 -left-2 p-1.5 bg-black/50 backdrop-blur border border-white/10 rounded-full z-10 hover:bg-cyan-500 hover:text-black transition-all"><ChevronLeft size={18}/></button>
                    <button onClick={scrollNext} className="absolute top-1/2 -translate-y-1/2 -right-2 p-1.5 bg-black/50 backdrop-blur border border-white/10 rounded-full z-10 hover:bg-cyan-500 hover:text-black transition-all"><ChevronRight size={18}/></button>
                </>
            )}
        </div>
    );
});
ProductCarousel.displayName = 'ProductCarousel';

const AIReasoning = React.memo(({ text }: { text: string }) => (
    <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 p-2 mt-3 bg-cyan-900/10 border border-cyan-400/20 rounded-lg max-w-md mx-auto"
    >
        <Cpu size={16} className="text-cyan-400 flex-shrink-0 glowing-icon"/>
        <p className="text-xs text-cyan-300/80 italic">{text}</p>
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
                return <p className={`whitespace-pre-wrap text-base ${message.contentType === 'error' ? 'text-red-400' : ''} ${message.contentType === 'success_text' ? 'text-cyan-300' : ''}`}>{message.content}</p>;
            case 'confirmation_prompt':
                return (
                    <div>
                        <p className="whitespace-pre-wrap mb-3 text-base">{message.content}</p>
                        <div className="flex flex-wrap gap-2">
                            {(message.options as string[])?.map((option: string) => {
                                const isConfirm = option === 'Confirm Order';
                                const buttonStyle = isConfirm
                                    ? "bg-purple-500/20 text-purple-300 border-purple-500/50 hover:bg-purple-500/30"
                                    : "bg-cyan-500/20 text-cyan-300 border-cyan-500/50 hover:bg-cyan-500/30";
                                return (
                                    <motion.button
                                        key={option}
                                        whileHover={{ scale: 1.05 }}
                                        onClick={() => {
                                            if (option === 'Confirm Order') onConfirmOrder();
                                            else if (option === 'Clear Cart') onClearCart();
                                            else onSend(option);
                                        }}
                                        className={`text-sm px-3 py-1.5 rounded-lg border ${buttonStyle} transition-all`}
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
                    <div>
                        <p className="whitespace-pre-wrap mb-2 text-base">{message.content}</p>
                        <ProductCarousel products={message.products || []} onSelect={onProductSelect} />
                        {message.reason && <AIReasoning text={message.reason} />}
                        {message.ai_notes && !message.reason && <AIReasoning text={message.ai_notes} />}
                    </div>
                );
            case 'recovery_prompt':
                return (
                    <div className="flex flex-col gap-3 w-full">
                        <div className="flex items-center gap-2 text-amber-400 mb-1">
                            <AlertCircle size={18} />
                            <span className="font-bold text-base">Order Paused</span>
                        </div>
                        <p className="whitespace-pre-wrap text-base text-gray-200 mb-1">{message.content}</p>
                        <div className="grid grid-cols-3 gap-2 w-full mt-2">
                            <motion.button whileHover={{ scale: 1.03 }} onClick={onRestore} className="flex flex-col items-center justify-center gap-1.5 text-xs font-bold bg-cyan-500/20 text-cyan-300 py-3 px-1 rounded-lg border border-cyan-500/50 hover:bg-cyan-500/30 transition-all h-full w-full text-center">
                                <Undo2 size={20} /> <span className="whitespace-nowrap">Restore Checkout</span>
                            </motion.button>
                            <motion.button whileHover={{ scale: 1.03 }} onClick={onSave} className="flex flex-col items-center justify-center gap-1.5 text-xs font-bold bg-purple-500/20 text-purple-300 py-3 px-1 rounded-lg border border-purple-500/50 hover:bg-purple-500/30 transition-all h-full w-full text-center">
                                <Save size={20} /> <span className="whitespace-nowrap">Save for Later</span>
                            </motion.button>
                            <motion.button whileHover={{ scale: 1.03 }} onClick={onCancel} className="flex flex-col items-center justify-center gap-1.5 text-xs font-bold bg-red-500/20 text-red-300 py-3 px-1 rounded-lg border border-red-500/50 hover:bg-red-500/30 transition-all h-full w-full text-center">
                                <Trash2 size={20} /> <span className="whitespace-nowrap">Cancel Order</span>
                            </motion.button>
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
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex items-start gap-3 w-full ${isAI ? 'justify-start' : 'justify-end'}`}
        >
            {isAI && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/50">
                    <Bot size={16} className="text-cyan-400" />
                </div>
            )}
            <div className={`w-auto max-w-lg px-3 py-2 rounded-xl ${isAI ? 'bg-black/20 border border-cyan-400/30 text-gray-200' : 'bg-gradient-to-r from-blue-600 to-violet-600 text-white'}`}>
                <MessageContent />
            </div>
            {!isAI && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-500/20 flex items-center justify-center border border-gray-500/50">
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
            aiNote: lastAINoteMessage ? (lastAINoteMessage.ai_notes || lastAINoteMessage.reason) : "AI reasoning will appear here."
        };
    }, [messages]);

    return (
        <div className="hidden lg:flex w-1/3 bg-black/20 border-l border-cyan-400/30 rounded-r-2xl flex-col overflow-hidden">
            <div className="flex-grow p-6 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
                <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                    <ShoppingCart size={18} id="order-summary-cart-icon" /> Order Summary
                </h3>
                <div className="space-y-2 flex-grow">
                    <AnimatePresence>
                        {cart.items.length === 0 ? <p className="text-sm text-gray-500 italic">Your cart is empty.</p> : cart.items.map((item: any, index: number) => (
                            <motion.div
                                key={item.product_id || index}
                                layout
                                initial={{ opacity: 0, x: -20 }}
                                animate={{
                                    opacity: 1,
                                    x: 0,
                                    backgroundColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.2)" : "rgba(255, 255, 255, 0.05)",
                                    borderColor: item.product_id === glowingProductId ? "rgba(6, 182, 212, 0.5)" : "rgba(255, 255, 255, 0.1)",
                                }}
                                transition={{ duration: 0.8, ease: "easeInOut" }}
                                exit={{ opacity: 0, x: 20 }}
                                className="flex justify-between items-center text-sm p-3 rounded-lg border"
                            >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                    <motion.button
                                        onClick={() => onRemoveItem(item.product_id)}
                                        className="p-0.5 rounded-full text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all flex-shrink-0"
                                        whileHover={{ scale: 1.2, rotate: 90 }}
                                        whileTap={{ scale: 0.9 }}
                                        title={`Remove ${item.name}`}
                                    >
                                        <X size={14} />
                                    </motion.button>
                                    <span className="text-gray-300 truncate" title={item.name}>
                                        {item.name} (x{item.quantity})
                                    </span>
                                </div>
                                <span className="font-bold text-white flex-shrink-0 ml-2">
                                    ${(item.price * item.quantity).toFixed(2)}
                                </span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>
            <div className="flex-shrink-0 p-6 border-t border-cyan-400/30 bg-black/30 backdrop-blur-sm space-y-5">
                <div>
                    <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                        <Clock size={18} /> Details
                    </h3>
                    <div className="text-sm space-y-2 text-gray-400">
                        <div className="flex justify-between"><span>Estimated Delivery:</span><span className="text-white font-semibold">12 Mins</span></div>
                        <div className="flex justify-between"><span>Delivery Fee:</span><span className="text-white font-semibold">Free</span></div>
                    </div>
                </div>
                <div className="w-full h-[1px] bg-cyan-400/20" />
                <div>
                    <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                        <motion.div
                            animate={{
                                filter: [
                                    'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4))',
                                    'drop-shadow(0 0 8px rgba(0, 198, 255, 0.8))',
                                    'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4))'
                                ]
                            }}
                            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                        >
                            <Cpu size={18} className="text-cyan-400"/>
                        </motion.div>
                        AI Notes
                    </h3>
                    <p className="text-sm text-gray-400 italic">{aiNote}</p>
                </div>
                <div className="w-full h-[1px] bg-cyan-400/20" />
                <div className="flex justify-between items-center font-bold pt-2">
                    <span className="text-white text-base">Total</span>
                    <span className="text-base text-white">${cart.total.toFixed(2)}</span>
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
      <form onSubmit={handleSubmit} className="p-4 border-t border-cyan-400/30 flex-shrink-0">
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={isDisabled ? 'AI is processing your request...' : 'Ask AI to order anything...'}
            disabled={isDisabled}
            className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-full py-3 pr-14 pl-5 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none transition-all"
          />
          <button
            type="submit"
            disabled={isDisabled}
            onClick={(e) => e.stopPropagation()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-gray-600 transition-colors"
          >
            <CornerDownRight size={20} className="text-black" />
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
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        className="flex items-center gap-3"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/50">
        <Bot size={16} className="text-cyan-400" />
      </div>
      <div className="flex items-center gap-1.5 px-4 py-3 bg-black/20 rounded-lg">
        <motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ duration: 0.8, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ duration: 0.8, delay: 0.1, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ duration: 0.8, delay: 0.2, repeat: Infinity, ease: 'easeInOut' }} />
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
              className="fixed z-[9999] rounded-lg overflow-hidden border border-cyan-500/50"
              initial={{ top: startRect.top, left: startRect.left, width: startRect.width, height: startRect.height, opacity: 1, rotate: 0 }}
              animate={{ top: endPos.top, left: endPos.left, width: 20, height: 20, opacity: 0.5, rotate: 720, filter: 'blur(4px)', scale: 0.2 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }} 
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
    <div className="w-full h-full flex flex-col items-center justify-center p-10 text-center bg-black/50 rounded-2xl">
        <ShieldOff size={48} className="text-red-400 mb-4" />
        <h3 className="text-xl font-bold text-white mb-2">Secure Checkout Unavailable</h3>
        {keyMissing ? (
            <p className="text-gray-400">
                The Stripe Public Key is missing from the environment variables. Please check NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY configuration.
            </p>
        ) : (
            <p className="text-gray-400">
                A critical error occurred while loading the payment processor.
            </p>
        )}
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
    
    const [isStripePromiseResolved, setIsStripePromiseResolved] = useState(false);

    useEffect(() => {
        if (stripePromise) {
            stripePromise.then(() => setIsStripePromiseResolved(true));
        } else {
             setIsStripePromiseResolved(true);
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
                content: "Connecting to Autonomous Engine... please wait.",
            });
        } else {
         
             useAIOrderingStore.setState(state => ({
                messages: [...state.messages, { id: Date.now(), sender: 'user', contentType: 'text', content: text }],
                isLoading: true
            }));
            setTimeout(() => {
                actions.addSocketAIMessage({
                    type: 'confirmation_prompt',
                    content: "Access to Autonomous Commerce is personalized. Sign in to unlock instant AI ordering.",
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
             actions.addSocketAIMessage({ type: 'error', content: "Please sign in to add items." });
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
                  borderRadius: '6px',
                }
            },
        };
    }, [paymentDetails]);

    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cartItems = lastCartMessage?.content?.items || [];
    
    const isPaymentMode = !!paymentDetails; 
    const isKeyMissing = !STRIPE_PUBLISHABLE_KEY;

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={handleClose}
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-lg flex justify-center items-center p-4"
                >
                  
                    <FlyToCartAnimator /> 

                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 50 }}
                        animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }}
                        exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.2, ease: "easeOut" } }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full max-w-7xl h-[95vh] max-h-[1000px] flex flex-col bg-black/50 backdrop-blur-2xl border border-cyan-400/30 rounded-2xl shadow-2xl shadow-cyan-500/20 overflow-hidden"
                    >
                        <header className="p-4 border-b border-cyan-400/30 flex justify-between items-center flex-shrink-0">
                            <h3 className="font-normal text-base text-white normal-case" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                <motion.span
                                    className="text-transparent bg-clip-text bg-gradient-to-br from-cyan-400 to-purple-600"
                                    animate={{
                                        filter: [
                                            'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4))',
                                            'drop-shadow(0 0 8px rgba(0, 198, 255, 0.8))',
                                            'drop-shadow(0 0 2px rgba(0, 198, 255, 0.4))'
                                        ]
                                    }}
                                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                                >
                                    {paymentDetails ? 'Secure Checkout' : 'order with air'}
                                </motion.span>
                            </h3>
                            <button onClick={handleClose} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </header>

                        <div className="flex-grow flex overflow-hidden relative">
                            <AnimatePresence mode="wait">
                                {isPaymentMode ? (
                                    <motion.div
                                        key="payment"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0, transition: { duration: 0.1 } }}
                                        className="w-full h-full flex items-center justify-center overflow-y-auto"
                                        style={{ position: 'absolute', top: 0, left: 0, zIndex: 20 }}
                                    >
                                        {stripeOptions && isStripePromiseResolved ? (
                                            <Elements key={stripeOptions.clientSecret} stripe={stripePromise} options={stripeOptions}>
                                                <AIPaymentForm
                                                    orderId={paymentDetails!.orderId}
                                                    total={paymentDetails!.total}
                                                    items={cartItems}
                                                    onPaymentSuccess={handlePaymentSuccess}
                                                />
                                            </Elements>
                                        ) : (
                                            <div className="flex flex-col items-center gap-4">
                                                 <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
                                                 <p className="text-cyan-300 font-mono text-sm">Initializing Secure Gateway...</p>
                                                 {isKeyMissing && <PaymentFatalError keyMissing={true} />}
                                            </div>
                                        )}
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="chat"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0, transition: { duration: 0.1 } }}
                                        className="w-full lg:w-2/3 flex flex-col relative z-10"
                                    >
                                        <div className="flex-grow p-6 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
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
