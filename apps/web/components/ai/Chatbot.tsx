'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Bot, Cpu, User, Loader2 } from 'lucide-react';
import { useAISupportStore, type ChatMessage } from '@/hooks/useAISupportStore';

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

const MessageBubble = ({ message }: { message: ChatMessage }) => {
    const isUser = message.sender === 'user';
    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex w-full items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            {!isUser && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/50">
                    <Bot size={16} className="text-cyan-400" />
                </div>
            )}
            <div className={`max-w-xs px-3 py-2 rounded-xl text-sm ${isUser ? 'bg-gradient-to-r from-blue-600 to-violet-600 text-white' : 'bg-black/20 border border-cyan-400/30 text-gray-200'}`}>
                <p className="whitespace-pre-wrap">{message.data.text}</p>
            </div>
            {isUser && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-500/20 flex items-center justify-center border border-gray-500/50">
                    <User size={16} className="text-gray-400" />
                </div>
            )}
        </motion.div>
    );
};

const TypingIndicator = () => (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-2"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/50">
        <Bot size={16} className="text-cyan-400" />
      </div>
      <div className="flex items-center gap-1.5 px-4 py-3 bg-black/20 rounded-lg">
        <motion.div
          className="w-2 h-2 bg-cyan-400 rounded-full"
          animate={{ y: [0, -3, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="w-2 h-2 bg-cyan-400 rounded-full"
          animate={{ y: [0, -3, 0] }}
          transition={{ duration: 0.8, delay: 0.1, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="w-2 h-2 bg-cyan-400 rounded-full"
          animate={{ y: [0, -3, 0] }}
          transition={{ duration: 0.8, delay: 0.2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
    </motion.div>
  );

const ChatInput = ({ onSend, isTyping }: { onSend: (text: string) => void; isTyping: boolean }) => {
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
            placeholder={isTyping ? "AI is thinking..." : "Ask for support..."}
            disabled={isTyping}
            className="w-full bg-white/5 backdrop-blur-md border border-white/10 rounded-full py-3 pr-12 pl-5 text-white placeholder-gray-500 focus:ring-2 focus:ring-cyan-400 focus:outline-none transition-all"
          />
          <button
            type="submit"
            disabled={isTyping}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-gray-600 transition-colors"
          >
            {isTyping ? (
              <Loader2 size={20} className="text-black animate-spin" />
            ) : (
              <Send size={18} className="text-black" />
            )}
          </button>
        </div>
      </form>
    );
  };

export default function Chatbot() {
    const { isOpen, setIsOpen, messages, sendMessage, isLoading } = useAISupportStore();
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const handleSend = (input: string) => {
        sendMessage(input);
    };

    return (
        <>
            <motion.button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 z-40 p-4 rounded-full 
                           bg-gradient-to-br from-cyan-500 to-purple-600 
                           text-white shadow-lg shadow-cyan-500/40 
                           flex items-center justify-center 
                           focus:outline-none focus:ring-4 focus:ring-cyan-400/50 
                           hover:scale-110 transition-all duration-300 ease-in-out group"
                whileHover={{ scale: 1.1, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ type: "spring", stiffness: 200, damping: 20 }}
                aria-label="Open AI Support Chat"
            >
                <motion.div
                    key={isOpen ? "close-icon" : "bot-icon"}
                    initial={{ scale: 0, rotate: -90 }}
                    animate={{ scale: 1, rotate: 0 }}
                    exit={{ scale: 0, rotate: 90 }}
                    transition={{ type: "spring", stiffness: 200, damping: 20 }}
                >
                    {isOpen ? (
                        <X size={28} className="text-white group-hover:rotate-180 transition-transform duration-300" />
                    ) : (
                        <Bot size={28} className="text-white group-hover:scale-110 transition-transform duration-300" />
                    )}
                </motion.div>
            </motion.button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 50, scale: 0.9 }}
                        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                        className="fixed bottom-24 right-2 z-50 w-[90vw] max-w-sm h-[70vh] max-h-[600px] flex flex-col bg-black/50 backdrop-blur-2xl border border-cyan-400/30 rounded-2xl shadow-2xl shadow-cyan-500/20 overflow-hidden"
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
                                AI Support
                            </motion.span>
                            </h3>
                            <button onClick={() => setIsOpen(false)} className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors">
                                <X size={20} />
                            </button>
                        </header>

                        <main className="flex-grow p-4 space-y-4 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-400/30 scrollbar-track-transparent">
                            <AnimatePresence>
                                {messages.map((msg) => (
                                    <React.Fragment key={msg.id}>
                                        <MessageBubble message={msg} />
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
