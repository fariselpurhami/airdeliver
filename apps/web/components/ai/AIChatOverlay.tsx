//** apps/web/components/ai/AIChatOverlay.tsx **//

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, CornerDownRight, ShoppingCart, Cpu, Clock, X, ChevronLeft, ChevronRight } from 'lucide-react';
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

    // 1. تحديد جذر API بشكل صريح (مثال: http://localhost:8000)
    //    هذا يضمن أننا نضرب البورت 8000 بشكل صحيح.
    const apiBase = process.env.NEXT_PUBLIC_API_URL 
        ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '') 
        : 'http://localhost:8000';
    
    // 2. ضمان أن المسار النسبي يبدأ بـ / لربطه بشكل صحيح.
    const normalizedPath = relativePath.startsWith('/') ? relativePath : `/${relativePath}`;
    
    // 3. التحقق من أن المسار يبدو معقولاً قبل الإرجاع (مثلاً: /static/...)
    // ملاحظة: إذا كان product.image_url يحتوي بالفعل على /apps/images/، فهذا خطأ في البيانات الخلفية.
    // نفترض أن الخادم يخدم الصور من مسار /static/ كما هو مُعد في main.py.
    
    // الحل: يجب أن تكون النتيجة http://localhost:8000/static/images/wallet.jpg
    // إذا كانت قاعدة البيانات تُرجع المسار الصحيح (e.g., /static/images/wallet.jpg)، فهذا الكود سيجمعه بشكل صحيح:
    return `${apiBase}${normalizedPath}`;
};


const CarouselProductCard = ({ product, onSelect, totalItems }: { product: any, onSelect: (product: any) => void, totalItems: number }) => {

    const mdWidthClass = totalItems === 2 ? "md:flex-[0_0_50%]" : "md:flex-[0_0_40%]";
    const slideWidthClass = `flex-[0_0_65%] sm:flex-[0_0_50%] ${mdWidthClass}`;

    const imageUrl = getAbsoluteImageUrl(product.image_url);

    return (
        <div className={`embla__slide ${slideWidthClass} px-2`}>
            <motion.div
                className="flex flex-col  p-4 bg-black/90 rounded-lg border border-cyan-400/20 h-full text-left"
                whileHover={{ scale: 1.03, z: 10 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            >
                <Image src={imageUrl} alt={product.name} width={120} height={120} className="w-full h-24 object-contain mb-3 rounded-md"/>
                <h4 className="text-sm font-bold text-white">{product.name}</h4>
                <p className="text-lg font-bold text-white mb-2">${product.price.toFixed(2)}</p>
                <div className="text-xs text-gray-400 flex items-center gap-2 mb-2">
                    <span>⭐ {product.rating || '4.5'} ({product.reviews || '1.2'}k)</span> | <span className="text-green-400">{product.stock_status || 'In Stock'}</span>
                </div>
                <div className="text-xs text-gray-400 flex items-center gap-2 mt-auto">
                    <span>🚀 {product.delivery_eta || '15 Min'} Delivery</span>
                </div>
                <motion.button
                    onClick={() => onSelect(product)}
                    whileHover={{ scale: 1.05 }}
                    className="w-full mt-3 text-sm bg-cyan-500/30 text-cyan-200 py-2 rounded-lg border border-cyan-500/50"
                >
                    Add to Cart
                </motion.button>
            </motion.div>
        </div>
    );
};

const ProductCarousel = ({ products, onSelect }: { products: any[], onSelect: (product: any) => void }) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'start' });
    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);
    const totalItems = products.length;
    const canScroll = totalItems > 2;

    return (
        <div className="relative my-4">
            <div className="overflow-hidden" ref={emblaRef}>
                <div className="flex">
                    {products.map((p, i) => <CarouselProductCard key={p.id || i} product={p} onSelect={onSelect} totalItems={totalItems} />)}
                </div>
            </div>
            {canScroll && (
                <>
                    <button onClick={scrollPrev} className="absolute top-1/2 -translate-y-1/2 -left-3 p-1 bg-white/10 rounded-full z-10 hover:bg-white/20"><ChevronLeft size={16}/></button>
                    <button onClick={scrollNext} className="absolute top-1/2 -translate-y-1/2 -right-3 p-1 bg-white/10 rounded-full z-10 hover:bg-white/20"><ChevronRight size={16}/></button>
                </>
            )}
        </div>
    );
};

const AIReasoning = ({ text }: { text: string }) => (
    <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 p-2 mt-3 bg-cyan-900/10 border border-cyan-400/20 rounded-lg max-w-md mx-auto"
    >
        <Cpu size={16} className="text-cyan-400 flex-shrink-0 glowing-icon"/>
        <p className="text-xs text-cyan-300/80 italic">{text}</p>
    </motion.div>
);

const ChatMessage = React.memo(({ message, onSend, onProductSelect }: { message: Message, onSend: (text: string) => void, onProductSelect: (product: any) => void }) => {
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
                            {(message.options as string[])?.map((option: string) => (
                                <motion.button key={option} whileHover={{ scale: 1.05 }} onClick={() => onSend(option)} className="text-sm bg-cyan-500/20 text-cyan-300 px-3 py-1.5 rounded-full border border-cyan-500/50">
                                    {option}
                                </motion.button>
                            ))}
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
                        {message.ai_notes && <AIReasoning text={message.ai_notes} />}
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
                    <ShoppingCart size={18} /> Order Summary
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
  ({ onSend, isTyping }: { onSend: (text: string) => void; isTyping: boolean }) => {
    const [value, setValue] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);
    const wasTypingRef = useRef<boolean>(isTyping);

    useEffect(() => {
      if (wasTypingRef.current === true && isTyping === false) {
        inputRef.current?.focus();
      }
      wasTypingRef.current = isTyping;
    }, [isTyping]);

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      if (value.trim() && !isTyping) {
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
            placeholder={isTyping ? 'AI is thinking...' : 'Ask AI to order anything...'}
            disabled={isTyping}
            className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-full py-3 pr-14 pl-5 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none transition-all"
          />
          <button
            type="submit"
            disabled={isTyping}
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


const TypingIndicator = () => (
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
        <motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -3, 0]} } transition={{ duration: 0.8, delay: 0.1, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ duration: 0.8, delay: 0.2, repeat: Infinity, ease: 'easeInOut' }} />
      </div>
    </motion.div>
);

const FlyingItemAnimator = ({ imageUrl }: { imageUrl: string }) => {
    const { flyToCartItem, setOverlayVisible } = useAIOrderingStore((state) => ({
        flyToCartItem: state.flyToCartItem,
        setOverlayVisible: state.setOverlayVisible,
    }));

    const onAnimationComplete = () => {
        useAIOrderingStore.setState({ flyToCartItem: null });
    };

    return (
        <motion.div
            className="absolute z-[999] p-1 bg-white/10 rounded-lg border border-cyan-400/50"
            style={{
                top: '50%',
                left: '30%',
                transform: 'translate(-50%, -50%)',
            }}
            initial={{
                opacity: 1,
                scale: 0.8,
                x: 0,
                y: 0,
            }}
            animate={{
                x: '100vh',
                y: '-30vh',
                opacity: 0,
                scale: 0.1,
            }}
            transition={{ duration: 0.8, ease: "easeIn" }}
            onAnimationComplete={onAnimationComplete}
        >
            <Image src={imageUrl} alt="Flying item" width={60} height={60} className="object-contain" />
        </motion.div>
    );
};


export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {

    const {
        messages, isLoading, sendMessage, addProductById,
        paymentDetails, setOverlayVisible, glowingProductId,
        flyToCartItem, resetChat, removeProductById,
        cancelPaymentIntent, isProcessing
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
            cancelPaymentIntent();
        } else if (!paymentDetails) {
            onClose();
        }
    };

    const handlePaymentSuccess = () => {
        setOverlayVisible(false);
        onClose();
        resetChat();
    };

    const handleSendMessage = useCallback((text: string) => {
        if (status === 'authenticated' && socket) {
            sendMessage(text);
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

    const handleProductSelect = useCallback((product: any) => {
        if (status === 'authenticated' && socket) {
            addProductById(product);
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
                    {flyToCartItem && <FlyingItemAnimator imageUrl={flyToCartItem} />}
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
                                                {messages.map((msg) => <ChatMessage key={msg.id} message={msg} onSend={handleSendMessage} onProductSelect={handleProductSelect} />)}
                                            </AnimatePresence>
                                            {isLoading && <TypingIndicator />}
                                            <div ref={chatEndRef} />
                                        </div>
                                        <ChatInput onSend={handleSendMessage} isTyping={isLoading || (messages.length > 0 && messages[messages.length - 1].contentType === 'success_text')} />
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
