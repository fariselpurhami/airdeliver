'use client';

import { useAIOrderingStore } from '@/hooks/useAIOrderingStore'; // تأكد من مسار الملف عندك
import { useUIStore } from '@/hooks/useUIStore'; // تأكد من مسار الملف عندك

import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Bot,
  Cpu,
  User,
  Loader2,
  CornerDownRight,
  Sparkles,
  BrainCircuit,
  ShieldCheck,
} from 'lucide-react';
import { useAISupportStore, type ChatMessage } from '@/hooks/useAISupportStore';
import { useBodyScrollLock } from '../../hooks/useBodyScrollLock';
interface ActionOption {
  title: string;
  payload: string;
}

const ExplainabilityChip = memo(({ text }: { text: string }) => (
  <motion.div
    initial={{ opacity: 0, height: 0, scale: 0.95 }}
    animate={{ opacity: 1, height: 'auto', scale: 1 }}
    style={{ willChange: 'transform, opacity, height' }}
    className="flex items-start gap-3 p-4 mt-4 bg-[#0A1116] border border-cyan-900/50 rounded-2xl max-w-lg relative overflow-hidden transform-gpu"
  >
    <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500" />
    <div className="absolute -right-4 -top-4 w-16 h-16 bg-cyan-500/10 blur-xl rounded-full pointer-events-none" />
    <div>
      <span className="block text-[10px] font-black text-cyan-300 tracking-widest mb-1">
        airdeliverOS
      </span>
      <p className="text-sm text-cyan-100/80 font-sans leading-relaxed">{text}</p>
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
      style={{ willChange: 'transform, opacity' }}
      className={`flex items-end gap-2 w-full mb-4 transform-gpu ${
        isUser ? 'justify-end' : 'justify-start'
      }`}
    >
      <div
        className={`w-fit max-w-[99%] px-4 py-3 ${
          isUser
            ? 'rounded-[32px] rounded-br-none bg-white/5 border border-white/10 text-white backdrop-blur-sm transform-gpu'
            : 'rounded-[32px] rounded-bl-none bg-[#050B14]/80 backdrop-blur-xl border border-white/5 text-gray-100 shadow-xl shadow-black/20 transform-gpu'
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-normal">
          {message.data.text}
        </p>

        {!isUser && action && action.action === 'present_options' && (
          <div className="flex flex-wrap gap-3 mt-4">
            {(action.payload.options as ActionOption[]).map((option, idx) => (
              <motion.button
                key={idx}
                onClick={() => onSend(option.payload)}
                whileHover={{ scale: 1.05, backgroundColor: 'rgba(6, 182, 212, 0.1)' }}
                whileTap={{ scale: 0.95 }}
                className="text-[10px] font-bold uppercase tracking-widest px-4 py-2.5 rounded-full border border-cyan-500/30 text-cyan-400 bg-cyan-950/20 hover:border-cyan-400 transition-all duration-300 shadow-[0_0_10px_rgba(6,182,212,0.1)]"
              >
                {option.title}
              </motion.button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
});
MessageBubble.displayName = 'MessageBubble';

const TypingIndicator = memo(() => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="flex items-end gap-2 w-full mb-4 justify-start"
  >
    <div className="rounded-[32px] rounded-bl-none bg-[#050B14]/80 backdrop-blur-xl border border-white/5 text-gray-100 shadow-xl shadow-black/20 px-4 py-3">
      <div className="flex items-center gap-2 text-cyan-300">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm leading-relaxed text-white/90 font-normal">
          Thinking...
        </span>
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wasTypingRef = useRef(isTyping);

  useEffect(() => {
    if (wasTypingRef.current === true && isTyping === false) {
      textareaRef.current?.focus();
    }
    wasTypingRef.current = isTyping;
  }, [isTyping]);

  const handleTriggerSend = useCallback(() => {
    if (!value.trim() || isTyping) return;
    onSend(value);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px';
    }
  }, [value, isTyping, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTriggerSend();
    }
  };

  const handleAutoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
      }
    });
  };

  return (
    <div className="p-6 border-t border-white/5 flex-shrink-0 bg-[#020617]/50 backdrop-blur-md relative z-20">
      <div className="relative group max-w-4xl mx-auto flex items-center gap-2">
        <div className="relative flex-grow">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleAutoResize}
            rows={1}
            onKeyDown={handleKeyDown}
            placeholder={isTyping ? 'Thinking...' : 'Ask air assistance...'}
            disabled={isTyping}
            className="w-full bg-gray-800 border border-gray-800 rounded-[28px] py-[14px] pr-16 pl-6 text-gray-100 placeholder-gray-400 focus:bg-gray-800 focus:border-none focus:outline-none transition-all duration-300 font-medium shadow-lg resize-none overflow-hidden no-scrollbar min-h-[52px] leading-relaxed"
            style={{
              overflowY:
                textareaRef.current && textareaRef.current.scrollHeight > 150 ? 'auto' : 'hidden',
            }}
          />
          <button
            disabled={isTyping || !value.trim()}
            onClick={handleTriggerSend}
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
    </div>
  );
});
ChatInput.displayName = 'ChatInput';

export default function Chatbot() {
  const { isOpen, setIsOpen, messages, sendMessage, isLoading } = useAISupportStore();
  const isOrderingOverlayOpen = useAIOrderingStore((state) => state.isOverlayVisible);
  const isProductOverlayOpen = useUIStore((state) => state.isProductOverlayVisible);

  // الشرط: لو أي واحد فيهم مفتوح، هنفعل الإخفاء
  const shouldHideOnMobile = isOrderingOverlayOpen || isProductOverlayOpen;

  const chatEndRef = useRef<HTMLDivElement>(null);
  useBodyScrollLock({ locked: isOpen });
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, isLoading, isOpen]);

  const handleSend = useCallback(
    (input: string) => {
      sendMessage(input);
    },
    [sendMessage]
  );

  return (
    <>
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-3 right-6 z-[60] p-0 rounded-full shadow-[0_0_72px_rgba(6,182,212,0.7)] focus:outline-none group transition-all duration-300 ${
          shouldHideOnMobile ? 'hidden md:block' : 'block'
        }`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {isOpen ? (
          <div className="w-14 h-14 rounded-full bg-[#020617] border border-white/10 flex items-center justify-center text-white">
            <X size={22} />
          </div>
        ) : (
          <div className="w-14 h-14 rounded-full bg-white flex items-center justify-center text-black">
            <Bot size={22} />
          </div>
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xl flex justify-center items-center p-4 overflow-hidden transform-gpu"
            style={{ colorScheme: 'dark', willChange: 'opacity', fontFamily: 'Montserrat, sans-serif' }}
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" />

            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 30 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 30 }}
              transition={{ duration: 0.35 }}
              onClick={(e) => e.stopPropagation()}
              style={{ willChange: 'transform, opacity' }}
              className="w-full h-full max-w-[460px] max-h-[1050px] md:max-w-7xl md:h-[93vh] md:max-h-none flex flex-col bg-[#020617]/55 backdrop-blur-3xl border border-white/10 rounded-[73px] shadow-[0_0_100px_rgba(6,182,212,0.1)] overflow-hidden relative transform-gpu"
            >
              <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-cyan-500/5 blur-[120px] pointer-events-none rounded-full" />
              <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/5 blur-[120px] pointer-events-none rounded-full" />

              <header className="px-8 py-6 flex items-center flex-shrink-0 relative z-10">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-full bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-300">
                    <Bot size={18} />
                  </div>
                  <div>
                    <h2 className="text-[11px] text-gray-400 flex items-center gap-1 mt-1">
                      <Cpu size={12} className="text-cyan-500" />
                      Real-time assistance
                    </h2>
                    <p className="text-[11px] text-gray-400 flex items-center gap-1 mt-1">
                      <ShieldCheck size={12} className="text-cyan-500" />
                      Secured
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setIsOpen(false)}
                  className="ml-auto p-3 rounded-full bg-white/5 border border-white/5 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20 transition-all duration-300"
                >
                  <X size={20} />
                </button>
              </header>

              <div className="flex-grow px-5 lg:px-12 py-8 space-y-8 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent relative z-10">
                <AnimatePresence initial={false}>
                  {messages.map((msg, idx) => (
                    <React.Fragment key={idx}>
                      <MessageBubble message={msg} onSend={handleSend} />
                      {msg.sender === 'ai' &&
                        msg.data.explain &&
                        !['Initial greeting.', 'User input.'].includes(msg.data.explain) && (
                          <div className="px-2">
                            <ExplainabilityChip text={msg.data.explain} />
                          </div>
                        )}
                    </React.Fragment>
                  ))}
                </AnimatePresence>

                {isLoading && <TypingIndicator />}

                <div ref={chatEndRef} />
              </div>

              <ChatInput onSend={handleSend} isTyping={isLoading} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
