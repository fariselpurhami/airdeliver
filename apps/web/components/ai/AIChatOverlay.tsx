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

const CarouselProductCard = ({ product, onSelect }: { product: any, onSelect: (productName: string) => void }) => (
    <div className="embla__slide flex-[0_0_50%] md:flex-[0_0_40%]">
        <div className="flex flex-col p-4 bg-white/5 rounded-lg border border-cyan-400/20 h-full text-left">
            <Image src={product.image || '/images/default.jpeg'} alt={product.name} width={120} height={120} className="w-full h-24 object-contain mb-3 rounded-md"/>
            <h4 className="text-sm font-bold text-white">{product.name}</h4>
            <p className="text-lg font-bold text-white mb-2">${product.price.toFixed(2)}</p>
            <div className="text-xs text-gray-400 flex items-center gap-2 mb-2">
                <span>⭐ {product.rating || '4.5'} ({product.reviews || '1.2'}k)</span> | <span className="text-green-400">{product.stock_status || 'In Stock'}</span>
            </div>
            <div className="text-xs text-gray-400 flex items-center gap-2 mt-auto">
                <span>🚀 {product.delivery_eta || '15 Min'} Delivery</span>
            </div>
           
            <motion.button 
                onClick={() => onSelect(`__ADD_BY_ID__:${product.id}`)} 
                className="w-full mt-3 text-sm bg-cyan-500/30 text-cyan-200 py-2 rounded-lg border border-cyan-500/50"
            >
                Add to Cart
            </motion.button>
            
        </div>
    </div>
);

const ProductCarousel = ({ products, onSelect }: { products: any[], onSelect: (productName: string) => void }) => {
    const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, align: 'start' });
    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);

    return (
        <div className="relative my-4 -mx-4">
            <div className="overflow-hidden" ref={emblaRef}>
                <div className="flex space-x-4 ml-4">
                    {products.map((p, i) => <CarouselProductCard key={p.id || i} product={p} onSelect={onSelect} />)}
                </div>
            </div>
            <button onClick={scrollPrev} className="absolute top-1/2 -translate-y-1/2 -left-3 p-1 bg-white/10 rounded-full z-10 hover:bg-white/20"><ChevronLeft size={16}/></button>
            <button onClick={scrollNext} className="absolute top-1/2 -translate-y-1/2 -right-3 p-1 bg-white/10 rounded-full z-10 hover:bg-white/20"><ChevronRight size={16}/></button>
        </div>
    );
};

const AIReasoning = ({ text }: { text: string }) => (
    <motion.div 
        initial={{ opacity: 0, y: 10 }} 
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 p-2 mt-3 bg-cyan-900/10 border border-cyan-400/20 rounded-lg"
    >
        <Cpu size={16} className="text-cyan-400 flex-shrink-0"/>
        <p className="text-xs text-cyan-300/80 italic">{text}</p>
    </motion.div>
);

const ChatMessage = React.memo(({ message, onSend }: { message: Message, onSend: (text: string) => void }) => {
    const isAI = message.sender === 'ai';

    const MessageContent = () => {
        switch (message.contentType) {
            case 'text':
            case 'error':
                return <p className={`whitespace-pre-wrap text-base ${message.contentType === 'error' ? 'text-red-400' : ''}`}>{message.content}</p>;
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
                        <p className="whitespace-pre-wrap mb-2 test-base">{message.content}</p>
                        <ProductCarousel products={message.products || []} onSelect={onSend} />
                        {message.reason && <AIReasoning text={message.reason} />}
                        {message.ai_notes && <AIReasoning text={message.ai_notes} />}
                    </div>
                );
            default: return null;
        }
    };

    if (['cart_preview', 'typing', 'payment_intent'].includes(message.contentType)) return null;

    return (
        <motion.div layout initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`flex items-start gap-3 w-full ${isAI ? 'justify-start' : 'justify-end'}`}>
            {isAI && <Bot size={24} className="flex-shrink-0 mt-1 text-cyan-400 glowing-icon" />}
            <div className={`w-auto max-w-lg p-4 rounded-xl ${isAI ? 'bg-black/20 border border-cyan-400/30 text-gray-200' : 'bg-gradient-to-r from-blue-600 to-violet-600 text-white'}`}>
                <MessageContent />
            </div>
            {!isAI && <User size={24} className="flex-shrink-0 mt-1 text-gray-300" />}
        </motion.div>
    );
});
ChatMessage.displayName = 'ChatMessage';

const AIChatSidebar = React.memo(({ messages }: { messages: Message[] }) => {
    const lastCartMessage = [...messages].reverse().find(m => m.contentType === 'cart_preview');
    const cart = lastCartMessage ? lastCartMessage.content : { items: [], total: 0 };
    
    const lastAINoteMessage = [...messages].reverse().find(m => m.sender === 'ai' && (m.ai_notes || m.reason));
    const aiNote = lastAINoteMessage ? (lastAINoteMessage.ai_notes || lastAINoteMessage.reason) : "AI reasoning will appear here.";

    return (
        <div className="hidden lg:block w-1/3 bg-black/20 border-l border-cyan-400/30 p-6 rounded-r-2xl overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
            <div className="sticky top-0 flex flex-col h-full">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><ShoppingCart size={18} /> Order Summary</h3>
                <div className="space-y-3 mb-6 flex-grow min-h-[120px]">
                    <AnimatePresence>
                        {cart.items.length === 0 ? <p className="text-sm text-gray-500">Your cart is empty.</p> : cart.items.map((item: any, index: number) => (
                            <motion.div key={item.product_id || index} layout initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="flex justify-between items-center text-sm">
                                <span className="text-gray-300">{item.name} (x{item.quantity})</span>
                                <span className="font-bold text-white">${(item.price * item.quantity).toFixed(2)}</span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
                <div className="mt-auto">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Clock size={18} /> Details</h3>
                    <div className="text-sm space-y-2 text-gray-400">
                        <div className="flex justify-between"><span>Estimated Delivery:</span><span className="text-white font-semibold">12 Mins</span></div>
                        <div className="flex justify-between"><span>Delivery Fee:</span><span className="text-white font-semibold">Free</span></div>
                    </div>
                    <div className="w-full h-[1px] bg-cyan-400/20 my-6" />
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Cpu size={18} /> AI Notes</h3>
                    <p className="text-sm text-gray-400 italic">{aiNote}</p>
                    <div className="w-full h-[1px] bg-cyan-400/20 my-6" />
                    <div className="flex justify-between items-center font-bold">
                        <span className="text-gray-300 text-lg">Total</span>
                        <span className="text-3xl text-white">${cart.total.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        </div>
    );
});
AIChatSidebar.displayName = 'AIChatSidebar';

const ChatInput = ({ onSend, isTyping }: { onSend: (text: string) => void; isTyping: boolean; }) => {
    const [value, setValue] = useState('');
    const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); if (value.trim() && !isTyping) { onSend(value); setValue(''); } };
    return (
        <form onSubmit={handleSubmit} className="p-4 border-t border-cyan-400/30 flex-shrink-0">
            <div className="relative">
                <input type="text" value={value} onChange={(e) => setValue(e.target.value)} placeholder={isTyping ? "AI is thinking..." : "Ask AI to order anything..."} disabled={isTyping} className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-full py-3 pr-14 pl-5 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none transition-all" />
                <button type="submit" disabled={isTyping} onClick={(e) => e.stopPropagation()} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-gray-600 transition-colors"><CornerDownRight size={20} className="text-black" /></button>
            </div>
        </form>
    );
};

const TypingIndicator = () => (
    <motion.div layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-2 self-start ml-12">
      <Bot size={24} className="flex-shrink-0 text-cyan-400 glowing-icon" /><div className="flex items-center gap-1"><motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.8, repeat: Infinity }} /><motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.8, delay: 0.1, repeat: Infinity }} /><motion.div className="w-2 h-2 bg-cyan-400 rounded-full" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.8, delay: 0.2, repeat: Infinity }} /></div>
    </motion.div>
);


export default function AIChatOverlay({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    
    const { messages, isLoading, sendMessage, paymentDetails, setOverlayVisible, addLocalAIMessage } = useAIOrderingStore();
    const { data: session, status } = useSession();
    const token = (session as any)?.accessToken;
    
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => { 
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' }); 
        }
    }, [messages, isLoading]);

    const handleClose = () => {
        setOverlayVisible(false); 
        onClose();
    };
    
    const handlePaymentSuccess = () => {
        setOverlayVisible(false); 
        onClose();
    };

    const handleSendMessage = useCallback((text: string) => {
        
        if (status === 'loading') {
             setTimeout(() => { 
                addLocalAIMessage(
                    "Authenticating... Please wait a moment.",
                    'error'
                );
            }, 300);
            return;
        }

        if (status === 'authenticated' && token) {
            sendMessage(text, token); 
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
                addLocalAIMessage(
                    "I'm sorry, I can only help you if you are logged in. Please log in to start your order.",
                    'error'
                );
            }, 500);
        }
    }, [sendMessage, token, status, addLocalAIMessage]);

    const stripeOptions: StripeElementsOptions = {
        clientSecret: paymentDetails?.clientSecret,
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
                    <motion.div 
                        initial={{ scale: 0.9, opacity: 0, y: 50 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 50 }}
                        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }} 
                        onClick={(e) => e.stopPropagation()} 
                        className="w-full max-w-7xl h-[95vh] max-h-[1000px] flex flex-col bg-black/50 backdrop-blur-2xl border border-cyan-400/30 rounded-2xl shadow-2xl shadow-cyan-500/20 overflow-hidden"
                    >
                        <header className="p-4 border-b border-cyan-400/30 flex justify-between items-center flex-shrink-0">
                            <h3 className="font-bold text-lg text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
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
                                    {paymentDetails ? 'Secure Checkout' : 'Order With AI'}
                                </motion.span>
                            </h3>
                            <button
                                onClick={handleClose}
                                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </header>
                   
                        <div className="flex-grow flex overflow-hidden">
                            <AnimatePresence mode="wait">
                                {paymentDetails && paymentDetails.clientSecret ? (
                                  
                                    <motion.div
                                        key="payment"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="w-full h-full flex items-center justify-center overflow-y-auto"
                                    >
                                        <Elements stripe={stripePromise} options={stripeOptions}>
                                            <AIPaymentForm 
                                                orderId={paymentDetails.orderId}
                                                total={paymentDetails.total}
                                                onPaymentSuccess={handlePaymentSuccess}
                                            />
                                        </Elements>
                                    </motion.div>
                                ) : (
                                    
                                    <motion.div 
                                        key="chat"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="w-full lg:w-2/3 flex flex-col"
                                    >
                                        <div className="flex-grow p-6 space-y-6 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
                                            <AnimatePresence>
                                             
                                                {messages.map((msg) => <ChatMessage key={msg.id} message={msg} onSend={handleSendMessage} />)}
                                            </AnimatePresence>
                                            {isLoading && <TypingIndicator />}
                                            <div ref={chatEndRef} />
                                        </div>
                                       
                                        <ChatInput onSend={handleSendMessage} isTyping={isLoading} />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                            
                           
                            {!(paymentDetails && paymentDetails.clientSecret) && (
                                 <AIChatSidebar messages={messages} />
                            )}
                        </div>

                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
