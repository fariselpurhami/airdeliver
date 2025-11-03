'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, CornerDownRight, ShoppingCart, Cpu, Clock, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAIOrderingStore, Message } from '@/hooks/useAIOrderingStore';
import Image from 'next/image';
import useEmblaCarousel from 'embla-carousel-react';

const CarouselProductCard = ({ product, onSelect }: { product: any, onSelect: (productName: string) => void }) => (
    <div className="embla__slide flex-[0_0_50%] md:flex-[0_0_40%]">
        <div className="flex flex-col p-4 bg-white/5 rounded-lg border border-white/10 h-full text-left">
            <Image src={product.image || '/images/default.jpeg'} alt={product.name} width={120} height={120} className="w-full h-24 object-contain mb-3 rounded-md"/>
            <h4 className="text-sm font-bold text-white">{product.name}</h4>
            <p className="text-lg font-bold text-white mb-2">${product.price}</p>
            <div className="text-xs text-gray-400 flex items-center gap-2 mb-2">
                <span>⭐ {product.rating} ({product.reviews}k)</span> | <span className="text-green-400">{product.stock_status}</span>
            </div>
            <div className="text-xs text-gray-400 flex items-center gap-2 mt-auto">
                <span>🚀 {product.delivery_eta} Delivery</span>
            </div>
            <motion.button 
                onClick={() => onSelect(`buy ${product.name}`)} 
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
                    {products.map(p => <CarouselProductCard key={p.id} product={p} onSelect={onSelect} />)}
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
        className="flex items-center gap-2 p-2 mt-3 bg-gray-500/10 border border-gray-500/20 rounded-lg"
    >
        <Cpu size={16} className="text-gray-400 flex-shrink-0"/>
        <p className="text-xs text-gray-400 italic">{text}</p>
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
                    </div>
                );
            default: return null;
        }
    };

    if (['cart_preview', 'typing'].includes(message.contentType)) return null;

    return (
        <motion.div layout initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`flex items-start gap-3 w-full ${isAI ? 'justify-start' : 'justify-end'}`}>
            {isAI && <Bot size={24} className="flex-shrink-0 mt-1 text-cyan-400 glowing-icon" />}
            <div className={`w-auto max-w-lg p-4 rounded-xl ${isAI ? 'bg-black/20 border border-white/10 text-gray-200' : 'bg-gradient-to-r from-blue-600 to-violet-600 text-white'}`}>
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
    return (
        <div className="hidden lg:block w-1/3 bg-black/20 border-l border-white/10 p-6 rounded-r-2xl overflow-y-auto">
            <div className="sticky top-0 flex flex-col h-full">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><ShoppingCart size={18} /> Order Summary</h3>
                <div className="space-y-3 mb-6 flex-grow min-h-[120px]">
                    <AnimatePresence>
                        {cart.items.length === 0 ? <p className="text-sm text-gray-500">Your cart is empty.</p> : cart.items.map((item: any, index: number) => (
                            <motion.div key={index} layout initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="flex justify-between items-center text-sm">
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
                    <div className="w-full h-[1px] bg-white/10 my-6" />
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><Cpu size={18} /> AI Notes</h3>
                    <p className="text-sm text-gray-400 italic">"AI reasoning will appear here."</p>
                    <div className="w-full h-[1px] bg-white/10 my-6" />
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
        <form onSubmit={handleSubmit} className="p-4 border-t border-white/10 flex-shrink-0">
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
    const { messages, isLoading, sendMessage } = useAIOrderingStore();
    const chatEndRef = useRef<HTMLDivElement>(null);
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, isLoading]);
    
    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-center items-center p-4">
                   
                    <motion.div onClick={(e) => e.stopPropagation()} className="w-full max-w-7xl h-[95vh] max-h-[1000px] flex bg-black/50 border border-white/10 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
                        <div className="w-full lg:w-2/3 flex flex-col">
                            <header className="p-4 border-b border-white/10 flex justify-between items-center flex-shrink-0">
                                <div className="flex items-center space-x-3"><Bot className="text-cyan-400" size={24} /><h3 className="font-bold text-lg text-white">Order With AI</h3></div>
                                <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"><X size={20} /></button>
                            </header>
                            <div className="flex-grow p-6 space-y-6 overflow-y-auto">
                                <AnimatePresence>
                                    {messages.map((msg, index) => <ChatMessage key={index} message={msg} onSend={sendMessage} />)}
                                </AnimatePresence>
                                {isLoading && <TypingIndicator />}
                                <div ref={chatEndRef} />
                            </div>
                            <ChatInput onSend={sendMessage} isTyping={isLoading} />
                        </div>
                        <AIChatSidebar messages={messages} />
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
