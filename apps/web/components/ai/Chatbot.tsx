//** apps/web/components/ai/chatbot.tsx **//

'use client';

import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Bot, Cpu, User, Loader2, CornerDownRight, Sparkles } from 'lucide-react';
import { useAISupportStore, type ChatMessage } from '@/hooks/useAISupportStore';

interface ActionOption {
    title: string;
    payload: string;
}

interface ExplainabilityChipProps {
    text: string;
}

const ExplainabilityChip = memo(({ text }: ExplainabilityChipProps) => (
    <motion.div
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 self-start ml-12 -mt-1 mb-3 p-2 bg-cyan-900/10 border border-cyan-500/20 rounded-lg max-w-[85%]"
    >
        <Cpu size={12} className="text-cyan-400 flex-shrink-0 animate-pulse"/>
        <p className="text-[10px] text-cyan-200/80 font-mono leading-relaxed">{text}</p>
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
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className={`flex w-full flex-col items-start gap-1 ${isUser ? 'items-end' : 'items-start'}`}
        >
            <div className={`flex w-full items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                {!isUser && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-cyan-950/50 flex items-center justify-center border border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]">
                        <Bot size={16} className="text-cyan-400" />
                    </div>
                )}
                
                <div className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed rounded-2xl ${
                    isUser 
                        ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white shadow-lg shadow-purple-900/20 rounded-tr-none' 
                        : 'bg-black/40 backdrop-blur-md border border-white/10 text-gray-100 shadow-md rounded-tl-none'
                }`}>
                    <p className="whitespace-pre-wrap">{message.data.text}</p>
                </div>

                {isUser && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gray-800/50 flex items-center justify-center border border-gray-700">
                        <User size={16} className="text-gray-400" />
                    </div>
                )}
            </div>

            {!isUser && action && action.action === 'present_options' && (
                <motion.div
                    layout
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0, transition: { delay: 0.3 } }}
                    className="grid grid-cols-2 gap-2 ml-11 mt-2 w-fit"
                >
                    {(action.payload.options as ActionOption[]).map((option, idx) => (
                        <motion.button
                            key={`${option.payload}-${idx}`}
                            onClick={() => onSend(option.payload)}
                            className="text-[9px] font-bold uppercase tracking-widest bg-cyan-500/10 text-cyan-300 px-5 py-2 rounded-full border border-cyan-500/30 hover:bg-cyan-500 hover:text-black hover:scale-105 hover:shadow-[0_0_15px_rgba(6,182,212,0.4)] transition-all duration-300"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            {option.title}
                        </motion.button>
                    ))}
                </motion.div>
            )}
        </motion.div>
    );
});

MessageBubble.displayName = 'MessageBubble';

const TypingIndicator = memo(() => (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-3"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-cyan-950/50 flex items-center justify-center border border-cyan-500/30">
        <Bot size={16} className="text-cyan-400" />
      </div>
      <div className="flex items-center gap-1.5 px-4 py-3 bg-black/40 border border-white/5 rounded-[18px] rounded-tl-none">
        <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, repeat: Infinity }} />
        <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, delay: 0.2, repeat: Infinity }} />
        <motion.div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" animate={{ opacity: [0.2, 1, 0.2] }} transition={{ duration: 1, delay: 0.4, repeat: Infinity }} />
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
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/5 flex-shrink-0 bg-black/20 backdrop-blur-md">
        <div className="relative group">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={isTyping ? "AI is processing..." : "Ask air intelligence..."}
            disabled={isTyping}
            className="w-full bg-black/40 backdrop-blur-xl border border-white/10 rounded-full py-3 pr-12 pl-5 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/50 focus:outline-none transition-all duration-300 font-medium text-sm"
          />
          <button
            type="submit"
            disabled={isTyping}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-500 text-white shadow-lg transition-all hover:scale-105 active:scale-95"
          >
            {isTyping ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <CornerDownRight size={16} />
            )}
          </button>
        </div>
      </form>
    );
});

ChatInput.displayName = 'ChatInput';

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
            <motion.button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 z-40 p-0 rounded-full
                           shadow-[0_0_30px_rgba(6,182,212,0.3)]
                           focus:outline-none 
                           hover:scale-105 transition-all duration-500 ease-out group"
                whileHover={{ y: -5 }}
                whileTap={{ scale: 0.95 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ type: "spring", stiffness: 200, damping: 20 }}
                aria-label="Open AI Support Chat"
            >
                <div className="relative w-14 h-14 rounded-full bg-black/60 backdrop-blur-xl border border-white/10 overflow-hidden flex items-center justify-center">
                    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-purple-600/20 group-hover:opacity-100 transition-opacity duration-500" />
                    <motion.div
                        key={isOpen ? "close-icon" : "bot-icon"}
                        initial={{ scale: 0, rotate: -90 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0, rotate: 90 }}
                        transition={{ type: "spring", stiffness: 200, damping: 20 }}
                        className="relative z-10"
                    >
                        {isOpen ? (
                            <X size={24} className="text-white group-hover:rotate-90 transition-transform duration-300" />
                        ) : (
                            <Sparkles size={24} className="text-cyan-400 group-hover:text-white transition-colors duration-300" />
                        )}
                    </motion.div>
                </div>
            </motion.button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.9, filter: "blur(10px)" }}
                        animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
                        exit={{ opacity: 0, y: 50, scale: 0.9, filter: "blur(10px)" }}
                        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
       
                        className="fixed bottom-24 right-4 z-50 w-[95vw] max-w-sm h-[75vh] max-h-[700px] flex flex-col bg-black border border-white/10 rounded-[32px] shadow-[0_0_50px_rgba(0,198,255,0.15)] overflow-hidden"
                    >
                        <div className="absolute top-0 left-0 w-24 h-24 bg-cyan-500/10 blur-[40px] pointer-events-none" />
                        <div className="absolute bottom-0 right-0 w-24 h-24 bg-purple-500/10 blur-[40px] pointer-events-none" />

                        <header className="px-6 py-4 border-b border-white/5 flex justify-between items-center flex-shrink-0 bg-black/20 relative z-10">
                            <div className="flex flex-col">
                                <h3 className="font-bold text-base normal-case tracking-tight flex items-center gap-2" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                                    <Bot size={18} className="text-cyan-400" />
                                    <motion.span
                                        className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-purple-400"
                                        animate={{
                                            textShadow: [
                                                '0 0 10px rgba(6,182,212,0)',
                                                '0 0 15px rgba(6,182,212,0.2)',
                                                '0 0 10px rgba(6,182,212,0)'
                                            ]
                                        }}
                                        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                                    >
                                        air intelligence
                                    </motion.span>
                                </h3>
                                <span className="text-[10px] text-gray-500 font-mono tracking-widest pl-6">ONLINE // V2.0</span>
                            </div>
                            <button 
                                onClick={() => setIsOpen(false)} 
                                className="p-2 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/30 transition-all duration-300"
                            >
                                <X size={16} />
                            </button>
                        </header>

                        <main className="flex-grow p-4 space-y-4 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent relative z-10">
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

                       <ChatInput onSend={handleSend} isTyping={isLoading} />
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
