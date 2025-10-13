// file: apps/web/components/ai/Chatbot.tsx
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, X, Send, Bot, Cpu, User } from 'lucide-react';
import { useAISupportStore, type ChatMessage } from '@/hooks/useAISupportStore';

// --- Subcomponent: Explainability Chip ---
const ExplainabilityChip = ({ text }: { text: string }) => (
    <motion.div 
        initial={{ opacity: 0, y: 5 }} 
        animate={{ opacity: 1, y: 0 }} 
        className="flex items-center gap-2 self-start ml-10 -mt-2 mb-2 p-1.5 bg-gray-500/10 border border-gray-500/20 rounded-full"
    >
        <Cpu size={12} className="text-gray-400"/>
        <p className="text-xs text-gray-400 italic">{text}</p>
    </motion.div>
);

// --- Subcomponent: Message Bubble ---
const MessageBubble = ({ message }: { message: ChatMessage }) => {
    const isUser = message.sender === 'user';
    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex w-full items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            {!isUser && <Bot size={24} className="flex-shrink-0 mt-1 text-cyan-400" />}
            <div className={`max-w-xs px-3 py-2 rounded-xl text-sm ${isUser ? 'bg-blue-600 text-white rounded-br-none' : 'bg-white/10 text-gray-200 rounded-bl-none'}`}>
                <p>{message.data.text}</p>
            </div>
            {isUser && <User size={24} className="flex-shrink-0 mt-1 text-gray-300" />}
        </motion.div>
    );
};

// --- Main Chatbot Component ---
export default function Chatbot() {
    const { isOpen, setIsOpen, messages, sendMessage, isLoading } = useAISupportStore();
    const [input, setInput] = useState('');
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const handleSend = (e: React.FormEvent) => {
        e.preventDefault();
        sendMessage(input);
        setInput('');
    };

    return (
        <>
            <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 z-40 w-16 h-16 bg-gradient-to-tr from-blue-600 to-cyan-400 rounded-full shadow-lg shadow-black/50 flex justify-center items-center"
                aria-label="Open AI Support"
            >
                <MessageSquare size={32} className="text-white" />
            </motion.button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 50, scale: 0.9 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                        className="fixed bottom-24 right-6 z-50 w-[90vw] max-w-sm h-[60vh] max-h-[500px] bg-black/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl flex flex-col"
                    >
                        <header className="p-4 border-b border-white/10 flex justify-between items-center flex-shrink-0">
                            <div className="flex items-center space-x-3">
                                <Bot className="text-cyan-400 glowing-icon" size={24} />
                                <h3 className="font-bold text-lg text-white">AI Support</h3>
                            </div>
                            <button onClick={() => setIsOpen(false)} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </header>

                        <main className="flex-grow p-4 space-y-2 overflow-y-auto">
                            {messages.map((msg, i) => (
                                <React.Fragment key={i}>
                                    <MessageBubble message={msg} />
                                    {msg.sender === 'ai' && msg.data.explain && !["Initial greeting.", "User input."].includes(msg.data.explain) && (
                                        <ExplainabilityChip text={msg.data.explain} />
                                    )}
                                </React.Fragment>
                            ))}
                            {isLoading && <div className="text-sm text-gray-400 italic pl-10">Neural Core is thinking...</div>}
                            <div ref={chatEndRef} />
                        </main>

                        <footer className="p-3 border-t border-white/10">
                            <form onSubmit={handleSend} className="relative">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder="Ask about your order..."
                                    className="w-full bg-white/5 border border-white/10 rounded-full py-2 pr-12 pl-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none"
                                />
                                <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-cyan-500 hover:bg-cyan-400 transition-colors">
                                    <Send size={18} className="text-black" />
                                </button>
                            </form>
                        </footer>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
