//** apps/web/components/ai/Chatbot.tsx **//

'use client';

import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bot, Cpu, User, Loader2, CornerDownRight, Sparkles, BrainCircuit, ShieldCheck } from 'lucide-react';
import { useAISupportStore, type ChatMessage } from '@/hooks/useAISupportStore';

// --- Types ---
interface ActionOption {
    title: string;
    payload: string;
}

// --- Components ---

const ExplainabilityChip = memo(({ text }: { text: string }) => (
    <motion.div
        initial={{ opacity: 0, height: 0, scale: 0.95 }}
        animate={{ opacity: 1, height: 'auto', scale: 1 }}
        className="flex items-start gap-3 p-3 ml-2 mt-2 mb-4 bg-[#0A1116] border border-cyan-900/50 rounded-xl max-w-[90%] relative overflow-hidden"
    >
        <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500" />
        <Cpu size={14} className="text-cyan-400 flex-shrink-0 mt-0.5 animate-pulse"/>
        <div>
            <span className="block text-[9px] font-bold text-cyan-500 tracking-widest mb-1">air OS</span>
            <p className="text-[11px] text-cyan-100/70 font-mono leading-relaxed">{text}</p>
        </div>
    </motion.div>
));
ExplainabilityChip.displayName = 'ExplainabilityChip';

interface MessageBubbleProps {
    message: ChatMessage;
    onSend: (text: string) => void;
}

const MessageBubble = memo(({ message, onSend }: MessageBubbleProps) => {
    const isUser = message.sender === 'user';
    const action = message.data.action;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className={`flex items-end gap-3 w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            
            <div className={`flex flex-col max-w-[85%] md:max-w-2xl ${isUser ? 'items-end' : 'items-start'}`}>
                {/* Message Content */}
                <div className={`px-6 py-5 text-[15px] leading-7 backdrop-blur-sm ${
                    isUser 
                        ? 'rounded-[32px] rounded-br-none bg-white/5 border border-white/10 text-white' 
                        : 'rounded-[32px] rounded-bl-none bg-[#0A1116] border border-white/5 text-gray-100'
                }`}>
                    <p className="whitespace-pre-wrap font-medium">{message.data.text}</p>
                </div>

                {/* Action Options (Chips) */}
                {!isUser && action && action.action === 'present_options' && (
                    <motion.div
                        layout
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0, transition: { delay: 0.2 } }}
                        className="flex flex-wrap gap-2 mt-3 w-full pl-2"
                    >
                        {(action.payload.options as ActionOption[]).map((option, idx) => (
                            <motion.button
                                key={`${option.payload}-${idx}`}
                                onClick={() => onSend(option.payload)}
                                whileHover={{ scale: 1.05, backgroundColor: "rgba(6, 182, 212, 0.1)" }}
                                whileTap={{ scale: 0.95 }}
                                className="text-[10px] font-bold uppercase tracking-widest px-4 py-2.5 rounded-full border border-cyan-500/30 text-cyan-400 bg-cyan-950/20 hover:border-cyan-400 transition-all duration-300 shadow-[0_0_10px_rgba(6,182,212,0.1)]"
                            >
                                {option.title}
                            </motion.button>
                        ))}
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
});
MessageBubble.displayName = 'MessageBubble';

const TypingIndicator = memo(() => (
    <motion.div
        layout
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0 }}
        className="flex items-center gap-3 mb-4"
    >
      <div className="flex items-center gap-2 px-5 py-4 bg-black/40 border border-white/5 rounded-full rounded-tl-none">
        <div className="flex gap-1">
            <motion.div className="w-1 h-1 bg-cyan-400 rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 0.6, repeat: Infinity }} />
            <motion.div className="w-1 h-1 bg-cyan-400 rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 0.6, delay: 0.2, repeat: Infinity }} />
            <motion.div className="w-1 h-1 bg-cyan-400 rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 0.6, delay: 0.4, repeat: Infinity }} />
        </div>
      </div>
    </motion.div>
));
TypingIndicator.displayName = 'TypingIndicator';

interface ChatInputProps {
    onSend: (text: string) => void;
    isTyping: boolean;
}

const ChatInput = memo(({ onSend, isTyping }: ChatInputProps) => {
    const [value, setValue] = useState('');
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const wasTypingRef = useRef<boolean>(isTyping);

    useEffect(() => {
        if (wasTypingRef.current === true && isTyping === false) {
            inputRef.current?.focus();
        }
        wasTypingRef.current = isTyping;
    }, [isTyping]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim() && !isTyping) {
                onSend(value);
                setValue('');
            }
        }
    };

    const handleAutoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const target = e.target;
        setValue(target.value);
        target.style.height = 'auto';
        target.style.height = `${Math.min(target.scrollHeight, 150)}px`;
    };

    return (
      <div className="p-6 border-t border-white/5 flex-shrink-0 bg-[#050B14] relative z-20">
        <div className="relative group max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            value={value}
            onChange={handleAutoResize}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={isTyping ? "Thinking..." : "Ask air assistance..."}
            disabled={isTyping}
            className="w-full bg-gray-800 border border-gray-800 rounded-[28px] py-[14px] pr-16 pl-6 text-gray-100 placeholder-gray-400 focus:bg-gray-800 focus:border-cyan-500/30 focus:outline-none transition-all duration-300 font-medium shadow-lg resize-none no-scrollbar min-h-[52px] leading-relaxed"
            style={{
                overflowY: inputRef.current && inputRef.current.scrollHeight > 150 ? 'auto' : 'hidden'
            }}
          />
          <button
            onClick={() => {
                if (value.trim() && !isTyping) {
                    onSend(value);
                    setValue('');
                }
            }}
            disabled={isTyping || !value.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-transparent disabled:text-gray-600 text-white transition-all"
          >
            {isTyping ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <CornerDownRight size={18} />
            )}
          </button>
        </div>
      </div>
    );
});
ChatInput.displayName = 'ChatInput';

// --- Main Component ---

export default function Chatbot() {
    const { isOpen, setIsOpen, messages, sendMessage, isLoading } = useAISupportStore();
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isLoading, isOpen]);

    const handleSend = useCallback((input: string) => {
        sendMessage(input);
    }, [sendMessage]);

    return (
        <>
            {/* Trigger Button (FAB) */}
            <motion.button
                onClick={() => setIsOpen(!isOpen)}
                className="fixed bottom-6 right-6 z-[60] p-0 rounded-full shadow-[0_0_40px_rgba(6,182,212,0.4)] focus:outline-none group"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
            >
                <div className="relative w-16 h-16 rounded-full bg-black overflow-hidden flex items-center justify-center backdrop-blur-xl border border-white/10">
                    <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/10 to-transparent group-hover:opacity-100 transition-opacity duration-500" />
                    <motion.div
                        key={isOpen ? "close" : "open"}
                        initial={{ rotate: -90, opacity: 0 }}
                        animate={{ rotate: 0, opacity: 1 }}
                        exit={{ rotate: 90, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                         {isOpen ? (
                             <X size={26} className="text-gray-300 group-hover:text-white transition-colors" />
                         ) : (
                             <div className="relative">
                                 <Sparkles size={26} className="text-white animate-pulse" />
                             </div>
                         )}
                    </motion.div>
                </div>
            </motion.button>

            {/* Chat Overlay (Full Screen Modal) */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden"
                        onClick={() => setIsOpen(false)}
                    >
                        {/* Background Gradient Line */}
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" />

                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 30 }}
                            animate={{ scale: 1, opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } }}
                            exit={{ scale: 0.95, opacity: 0, y: 30, transition: { duration: 0.3 } }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-full max-w-7xl h-[93vh] flex flex-col bg-[#020617] border border-white/10 rounded-[73px] shadow-[0_0_100px_rgba(6,182,212,0.1)] overflow-hidden relative"
                        >
                            {/* Header */}
                            <header className="px-8 py-6 border-b border-white/5 flex justify-between items-center flex-shrink-0 relative z-10 bg-[#050B14]">
                                <div>
                                    <h3 className="font-bold text-2xl tracking-tight flex items-center gap-2 text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                        <motion.span
                                            className="text-transparent bg-clip-text bg-gradient-to-r text-white"
                                            animate={{
                                                textShadow: [
                                                    '0 0 10px rgba(6,182,212,0)',
                                                    '0 0 20px rgba(6,182,212,0.3)',
                                                    '0 0 10px rgba(6,182,212,0)'
                                                ]
                                            }}
                                            transition={{ duration: 4, repeat: Infinity }}
                                        >
                                            air assistance
                                        </motion.span>
                                    </h3>
                                </div>
                                
                                <button 
                                    onClick={() => setIsOpen(false)}
                                    className="p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white transition-all duration-300 hover:scale-110"
                                >
                                    <X size={20} />
                                </button>
                            </header>

                            {/* Messages Area */}
                            <main className="flex-grow px-4 lg:px-12 py-8 space-y-2 overflow-y-auto no-scrollbar relative z-10">
                                
                                {/* Empty State Hero */}
                                {messages.length === 0 && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center opacity-10 pointer-events-none select-none">
                                        <BrainCircuit size={120} strokeWidth={0.5} className="text-white mb-4" />
                                        <h2 className="text-2xl font-bold text-white tracking-[0.2em] font-orbitron">
                                            AIR INTELLIGENCE
                                        </h2>
                                    </div>
                                )}

                                <AnimatePresence initial={false}>
                                    {messages.map((msg) => (
                                        <React.Fragment key={msg.id}>
                                            <MessageBubble message={msg} onSend={handleSend} />
                                            {msg.sender === 'ai' && msg.data.explain && !["Initial greeting.", "User input."].includes(msg.data.explain) && (
                                                <ExplainabilityChip text={msg.data.explain} />
                                            )}
                                        </React.Fragment>
                                    ))}
                                </AnimatePresence>
                                {isLoading && <TypingIndicator />}
                                <div ref={chatEndRef} />
                            </main>

                            {/* Input Area */}
                            <ChatInput onSend={handleSend} isTyping={isLoading} />
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
