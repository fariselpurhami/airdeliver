//** apps/web/components/ai/AIChatOverlay.tsx **//

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, CornerDownRight, ShoppingCart, Cpu, Clock, X, ChevronLeft, ChevronRight, Save, Trash2, Undo2, AlertCircle, ShoppingBag } from 'lucide-react';
import { useAIOrderingStore, Message } from '@/hooks/useAIOrderingStore';
import Image from 'next/image';
import useEmblaCarousel from 'embla-carousel-react';
import { loadStripe, StripeElementsOptions } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { AIPaymentForm } from './AIPaymentForm';
import { useSession } from "next-auth/react";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '');

const getAbsoluteImageUrl = (relativePath: string | undefined): string => {
    if (!relativePath || relativePath.startsWith('http')) {
        return relativePath || '/images/default.jpeg';
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL
        ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')
        : 'http://localhost:8000';

    const normalizedPath = relativePath.startsWith('/') ? relativePath : `/${relativePath}`;

    return `${apiBase}${normalizedPath}`;
};

const CarouselProductCard = React.memo(({ product, onSelect, totalItems }: { product: any, onSelect: (product: any, elementId: string) => void, totalItems: number }) => {
    const mdWidthClass = totalItems === 2 ? "md:flex-[0_0_50%]" : "md:flex-[0_0_40%]";
    const slideWidthClass = `flex-[0_0_65%] sm:flex-[0_0_50%] ${mdWidthClass}`;
    
    const rawImagePath = product.image_url || product.image;
    const imageUrl = getAbsoluteImageUrl(rawImagePath);
    const elementId = `product-carousel-img-${product.id}`;

    const handleSelect = useCallback(() => {
        const normalizedProduct = {
            ...product,
            image: rawImagePath
        };
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

const ChatMessage = React.memo(({ message, onSend, onProductSelect, onConfirmOrder, onClearCart, onRestore, onSave, onCancel }: {
    message: Message,
    onSend: (text: string) => void,
    onProductSelect: (product: any, elementId: string) => void,
    onConfirmOrder: () => void,
    onClearCart: () => void,
    onRestore: () => void,
    onSave: () => void,
    onCancel: () => void
}) => {
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
                                            if (option === 'Confirm Order') {
                                                onConfirmOrder();
                                            } else if (option === 'Clear Cart') {
                                                onClearCart();
                                            } else {
                                                onSend(option);
                                            }
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
                            <motion.button
                                whileHover={{ scale: 1.03 }}
                                onClick={onRestore}
                                className="flex flex-col items-center justify-center gap-1.5 text-xs font-bold bg-cyan-500/20 text-cyan-300 py-3 px-1 rounded-lg border border-cyan-500/50 hover:bg-cyan-500/30 transition-all h-full w-full text-center"
                            >
                                <Undo2 size={20} />
                                <span className="whitespace-nowrap">Restore Checkout</span>
                            </motion.button>

                            <motion.button
                                whileHover={{ scale: 1.03 }}
                                onClick={onSave}
                                className="flex flex-col items-center justify-center gap-1.5 text-xs font-bold bg-purple-500/20 text-purple-300 py-3 px-1 rounded-lg border border-purple-500/50 hover:bg-purple-500/30 transition-all h-full w-full text-center"
                            >
                                <Save size={20} />
                                <span className="whitespace-nowrap">Save for Later</span>
                            </motion.button>

                            <motion.button
                                whileHover={{ scale: 1.03 }}
                                onClick={onCancel}
                                className="flex flex-col items-center justify-center gap-1.5 text-xs font-bold bg-red-500/20 text-red-300 py-3 px-1 rounded-lg border border-red-500/50 hover:bg-red-500/30 transition-all h-full w-full text-center"
                            >
                                <Trash2 size={20} />
                                <span className="whitespace-nowrap">Cancel Order</span>
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
    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cart = lastCartMessage ? lastCartMessage.content : { items: [], total: 0 };

    const lastAINoteMessage = [...messages].reverse().find(m => m.sender === 'ai' && (m.ai_notes || m.reason));
    const aiNote = lastAINoteMessage ? (lastAINoteMessage.ai_notes || lastAINoteMessage.reason) : "AI reasoning will appear here.";

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
                            transition={{
                                duration: 3,
                                repeat: Infinity,
                                ease: "easeInOut"
                            }}
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
    if (el) {
      return el.getBoundingClientRect();
    }
    return { x: window.innerWidth / 2, y: window.innerHeight / 2, width: 100, height: 100 };
  };

  const getEndPosition = () => {
    const el = document.getElementById('order-summary-cart-icon');
    if (el) {
      const rect = el.getBoundingClientRect();
      return {
        top: rect.top + rect.height / 2,
        left: rect.left + rect.width / 2,
      };
    }
    return { top: 100, left: window.innerWidth - 100 };
  };

  const endPos = getEndPosition();

  return (
    <AnimatePresence>
      {flyQueue.map((item) => {
          const startRect = getStartPosition(item.startElementId);
          const imageSource = getAbsoluteImageUrl(item.image || item.image_url);

          if (!startRect || startRect.width === 0) return null;

          return (
            <motion.div
              key={item.animationId} 
              className="fixed z-[9999] rounded-lg overflow-hidden border border-cyan-500/50"
              initial={{
                top: startRect.top,
                left: startRect.left,
                width: startRect.width,
                height: startRect.height,
                opacity: 1,
                rotate: 0,
              }}
              animate={{
                top: endPos.top,
                left: endPos.left,
                width: 20,
                height: 20,
                opacity: 0.5,
                rotate: 720,
                filter: 'blur(4px)',
                scale: 0.2,
              }}
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

export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {

    const {
        messages, isLoading, sendMessage, addProductById,
        paymentDetails, setOverlayVisible, glowingProductId,
        flyToCartItem, resetChat, removeProductById,
        initiateCheckoutRecovery, isProcessing,
        confirmCurrentOrder, clearCart,
        restoreCheckout, saveForLater, hardCancelOrder
    } = useAIOrderingStore();

    const socket = useAIOrderingStore((state) => state.socket);
    const connectSocket = useAIOrderingStore((state) => state.connectSocket);
    const disconnectSocket = useAIOrderingStore((state) => state.disconnectSocket);

    const { data: session, status } = useSession();

    useEffect(() => {
        if (isOpen && status === 'authenticated' && !socket && session?.accessToken) {
            connectSocket(session.accessToken);
        }

        return () => {
            if (!isOpen) {
                disconnectSocket();
            }
        };
    }, [isOpen, status, session, connectSocket, disconnectSocket, socket]);


    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [messages, isLoading]);

    const handleClose = () => {
        if (paymentDetails && !isProcessing) {
            initiateCheckoutRecovery();
        } else if (!paymentDetails) {
            onClose();
        }
    };

    const handleChatCancel = () => {
        hardCancelOrder('changed_mind');
    };

    const handlePaymentSuccess = () => {
        setOverlayVisible(false);
        onClose();
        resetChat();
    };

    const handleSendMessage = useCallback((text: string) => {
        if (status === 'authenticated' && socket) {
            sendMessage(text, false);
        } else if (status === 'authenticated' && !socket) {
            useAIOrderingStore.getState().addSocketAIMessage({
                type: 'error',
                content: "Autonomous Engine connection is not yet ready. Please wait a moment and try again.",
            });
        } else {
            const userMessage: Message = {
                id: Date.now(),
                sender: 'user',
                contentType: 'text',
                content: text,
            };
            useAIOrderingStore.setState((state) => ({
                messages: [...state.messages, userMessage],
                isLoading: true,
            }));

            setTimeout(() => {
                useAIOrderingStore.getState().addSocketAIMessage({
                    type: 'confirmation_prompt',
                    content: "Access to Autonomous Commerce is personalized. Sign in to unlock instant AI ordering.",
                    options: ["Sign In", "Create Account"],
                });
            }, 500);
        }
    }, [sendMessage, status, socket]);

    const handleProductSelect = useCallback((product: any, elementId: string) => {
        if (status === 'authenticated' && socket) {
            addProductById(product, elementId);
        } else if (status === 'authenticated' && !socket) {
            useAIOrderingStore.getState().addSocketAIMessage({
                type: 'error',
                content: "Autonomous Engine connection is not yet ready. Please wait a moment and try again.",
            });
        } else {
             useAIOrderingStore.getState().addSocketAIMessage({
                type: 'error',
                content: "Please sign in to add items.",
            });
        }
    }, [addProductById, status, socket]);

    const stripeOptions: StripeElementsOptions | undefined = paymentDetails?.gateways.find(g => g.provider === 'stripe' && g.clientSecret)
        ? {
            clientSecret: paymentDetails.gateways.find(g => g.provider === 'stripe')!.clientSecret,
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
          }
        : undefined;

    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cart = lastCartMessage ? lastCartMessage.content : { items: [], total: 0 };

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
                                    transition={{
                                        duration: 3,
                                        repeat: Infinity,
                                        ease: "easeInOut"
                                    }}
                                >
                                    {paymentDetails ? 'Secure Checkout' : 'Order with air'}
                                </motion.span>
                            </h3>
                            <button
                                onClick={handleClose}
                                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </header>

                        <div className="flex-grow flex overflow-hidden relative">
                            <AnimatePresence>
                                {paymentDetails && stripeOptions ? (
                                    <motion.div
                                        key="payment"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0, transition: { duration: 0.1 } }}
                                        className="w-full h-full flex items-center justify-center overflow-y-auto"
                                        style={{ position: 'absolute', top: 0, left: 0 }}
                                    >
                                        <Elements
                                            key={stripeOptions.clientSecret}
                                            stripe={stripePromise}
                                            options={stripeOptions}
                                        >
                                            <AIPaymentForm
                                                orderId={paymentDetails.orderId}
                                                total={paymentDetails.total}
                                                items={cart.items}
                                                onPaymentSuccess={handlePaymentSuccess}
                                            />
                                        </Elements>
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="chat"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0, transition: { duration: 0.1 } }}
                                        className="w-full lg:w-2/3 flex flex-col"
                                    >
                                        <div className="flex-grow p-6 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
                                            <AnimatePresence>
                                                {messages.map((msg) => (
                                                    <ChatMessage
                                                        key={msg.id}
                                                        message={msg}
                                                        onSend={handleSendMessage}
                                                        onProductSelect={handleProductSelect}
                                                        onConfirmOrder={confirmCurrentOrder}
                                                        onClearCart={clearCart}
                                                        onRestore={restoreCheckout}
                                                        onSave={saveForLater}
                                                        onCancel={handleChatCancel}
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
                            {!(paymentDetails && stripeOptions) && (
                                 <AIChatSidebar
                                    messages={messages}
                                    glowingProductId={glowingProductId}
                                    onRemoveItem={removeProductById}
                                 />
                            )}
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
