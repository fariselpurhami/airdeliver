//** apps/web/components/ai/Chatbot.tsx **//

'use client';

import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bot, Cpu, User, Loader2, CornerDownRight, Sparkles, Terminal, ShieldCheck } from 'lucide-react';
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
            <span className="block text-[9px] font-bold text-cyan-500 uppercase tracking-widest mb-1">System Logic</span>
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
            className={`flex items-end gap-3 w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            
            <div className={`flex flex-col max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
                {/* Message Content */}
                <div className={`px-5 py-4 text-sm leading-relaxed backdrop-blur-sm ${
                    isUser 
                        ? 'rounded-[24px] rounded-br-none bg-white/5 border border-white/10 text-white' 
                        : 'rounded-[24px] rounded-bl-none bg-[#050B14]/80 border border-white/5 text-gray-100 shadow-xl shadow-black/20'
                }`}>
                    <p className="whitespace-pre-wrap font-medium">{message.data.text}</p>
                </div>

                {/* Action Options (Chips) */}
                {!isUser && action && action.action === 'present_options' && (
                    <motion.div
                        layout
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0, transition: { delay: 0.2 } }}
                        className="flex flex-wrap gap-2 mt-3 w-full"
                    >
                        {(action.payload.options as ActionOption[]).map((option, idx) => (
                            <motion.button
                                key={`${option.payload}-${idx}`}
                                onClick={() => onSend(option.payload)}
                                whileHover={{ scale: 1.05, backgroundColor: "rgba(6, 182, 212, 0.1)" }}
                                whileTap={{ scale: 0.95 }}
                                className="text-[10px] font-bold uppercase tracking-widest px-4 py-2.5 rounded-xl border border-cyan-500/30 text-cyan-400 bg-cyan-950/20 hover:border-cyan-400 transition-all duration-300"
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
      <form onSubmit={handleSubmit} className="p-5 border-t border-white/5 flex-shrink-0 bg-[#020617]/50 backdrop-blur-md relative z-20">
        <div className="relative group">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={isTyping ? "System processing..." : "Ask air intelligence..."}
            disabled={isTyping}
            className="w-full bg-[#0F172A] border border-white/10 rounded-full py-3.5 pr-14 pl-6 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500/40 focus:outline-none transition-all duration-300 font-medium text-sm shadow-inner"
          />
          <button
            type="submit"
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
      </form>
    );
});
ChatInput.displayName = 'ChatInput';

// --- Main Component ---

export default function Chatbot() {
    const { isOpen, setIsOpen, messages, sendMessage, isLoading } = useAISupportStore();
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const handleSend = useCallback((input: string) => {
        sendMessage(input);
    }, [sendMessage]);

    return (
        <>
            {/* Trigger Button */}
            <motion.button
                onClick={() => setIsOpen(!isOpen)}
                className="fixed bottom-6 right-6 z-[60] p-0 rounded-full shadow-[0_0_40px_rgba(6,182,212,0.4)] focus:outline-none group"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
            >
                <div className="relative w-16 h-16 rounded-full bg-black overflow-hidden flex items-center justify-center backdrop-blur-xl">
                    <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/10 to-transparent group-hover:opacity-100 transition-opacity duration-500" />
                    <motion.div
                        key={isOpen ? "close" : "open"}
                        initial={{ rotate: -90, opacity: 0 }}
                        animate={{ rotate: 0, opacity: 1 }}
                        exit={{ rotate: 90, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                         {isOpen ? (
                             <X size={26} className="text-gray-300 group-hover:text-red-400 transition-colors" />
                         ) : (
                             <div className="relative">
                                 <Sparkles size={26} className="text-white animate-pulse" />
                                
                             </div>
                         )}
                    </motion.div>
                </div>
            </motion.button>

            {/* Chat Window */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 40, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 40, scale: 0.95 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className="fixed bottom-24 right-6 z-50 w-[390px] h-[760px] max-h-[85vh] max-w-[90vw] flex flex-col bg-[#020617] border border-white/10 rounded-[40px] shadow-[0_0_60px_rgba(0,0,0,0.8)] overflow-hidden"
                    >
                        {/* Background Atmospherics */}
                        <div className="absolute top-0 left-0 w-40 h-40 bg-cyan-500/10 blur-[50px] pointer-events-none rounded-full" />
                        <div className="absolute bottom-0 right-0 w-40 h-40 bg-purple-500/10 blur-[50px] pointer-events-none rounded-full" />
                        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] pointer-events-none" />

                        {/* Header */}
                        <header className="px-6 py-5 border-b border-white/5 flex justify-between items-center flex-shrink-0 bg-black/20 backdrop-blur-md relative z-10">
                            <div>
                                <h3 className="font-bold text-lg tracking-tight flex items-center gap-2 text-white" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                               
                                    <motion.span
                                        className="text-transparent bg-clip-text bg-gradient-to-r text-white"
                                        animate={{ opacity: [0.8, 1, 0.8] }}
                                        transition={{ duration: 4, repeat: Infinity }}
                                    >
                                        air intelligence
                                    </motion.span>
                                </h3>
                                <div className="flex items-center gap-2 pl-7">
                                </div>
                            </div>
                            
                            <div className="flex items-center gap-2">
                                <div className="px-2 py-1 bg-white/5 rounded border border-white/5">
                                    <ShieldCheck size={14} className="text-gray-400" />
                                </div>
                            </div>
                        </header>

                        {/* Messages Area */}
                        <main className="flex-grow px-5 py-6 space-y-2 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent relative z-10">
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
                )}
            </AnimatePresence>
        </>
    );
}
