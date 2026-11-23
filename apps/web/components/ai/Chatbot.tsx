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
        className={`w-fit max-w-[95%] py-3.5 ${
          isUser
            ? 'px-4 rounded-[24px] rounded-br-sm bg-white/[0.09] text-white/95 backdrop-blur-2xl shadow-lg transform-gpu'
            : 'rounded-none bg-transparent text-white/90 transform-gpu'
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
                className="text-[12px] font-medium px-5 py-2.5 rounded-full text-white/85 bg-white/[0.08] backdrop-blur-2xl hover:bg-white/[0.15] transition-all duration-300 shadow-[0_8px_24px_rgba(0,0,0,0.25),inset_0_1px_1px_rgba(255,255,255,0.12)]"
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
    <div className="px-6 pt-4 pb-[max(28px,env(safe-area-inset-bottom))] flex-shrink-0 bg-transparent relative z-20">
      <div className="relative group w-full max-w-[340px] mx-auto flex items-center gap-2 rounded-full p-[1.5px] bg-gradient-to-r from-[#38BDF8]/45 via-white/25 to-[#818CF8]/45 shadow-[0_0_32px_rgba(56,189,248,0.22),0_12px_32px_rgba(0,0,0,0.65)]">
        <div className="relative flex-grow rounded-full bg-[#0E131F]/95 backdrop-blur-2xl">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleAutoResize}
            rows={1}
            onKeyDown={handleKeyDown}
            aria-label="Message Air Assistant"
            placeholder={isTyping ? 'Thinking...' : 'Ask Air Assistant...'}
            disabled={isTyping}
            className="w-full bg-transparent rounded-full py-3 pr-12 pl-5 text-[13px] text-white/95 placeholder-white/40 focus:outline-none transition-all duration-200 font-normal resize-none overflow-hidden no-scrollbar min-h-[44px] leading-snug"
            style={{
              overflowY:
                textareaRef.current && textareaRef.current.scrollHeight > 150 ? 'auto' : 'hidden',
            }}
          />
          <button
            aria-label="Send message"
            disabled={isTyping || !value.trim()}
            onClick={handleTriggerSend}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 flex items-center justify-center rounded-full text-[#38BDF8] hover:text-[#7DD3FC] disabled:text-[#38BDF8]/35 transition-all drop-shadow-[0_0_8px_rgba(56,189,248,0.45)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300"
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
        aria-label={isOpen ? "Close Air Assistant" : "Open Air Assistant"}
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-3 right-6 z-[60] p-0 rounded-full shadow-[0_0_72px_rgba(6,182,212,0.7)] focus:outline-none group transition-all duration-300 ${
          isOpen ? 'hidden' : shouldHideOnMobile ? 'hidden md:block' : 'block'
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
            className="fixed inset-0 z-50 bg-[#04070F]/95 backdrop-blur-3xl flex justify-center items-center p-0 sm:p-4 overflow-hidden transform-gpu"
            style={{ colorScheme: 'dark', willChange: 'opacity', fontFamily: 'Montserrat, sans-serif' }}
          >


            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 30 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 30 }}
              transition={{ duration: 0.35 }}
              role="dialog" aria-label="Air Assistant" aria-modal="true"
              onClick={(e) => e.stopPropagation()}
              style={{ willChange: 'transform, opacity' }}
              className="w-full h-[100dvh] sm:h-[92dvh] max-w-[460px] flex flex-col bg-transparent overflow-hidden relative transform-gpu"
            >
              <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-[380px] h-[260px] bg-[#38BDF8]/15 blur-[95px] pointer-events-none rounded-full" />
              <div className="absolute top-16 end-0 w-[260px] h-[260px] bg-indigo-500/12 blur-[100px] pointer-events-none rounded-full" />
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[360px] h-[180px] bg-[#38BDF8]/10 blur-[90px] pointer-events-none rounded-full" />
              <header className="px-6 pt-6 pb-3 flex items-center justify-between flex-shrink-0 relative z-10">
                <div className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-white/[0.08] backdrop-blur-2xl shadow-[0_8px_30px_rgba(0,0,0,0.35),inset_0_1px_1px_rgba(255,255,255,0.16)]">
                  <span className="w-2 h-2 rounded-full bg-[#7DD3FC] shadow-[0_0_8px_#7DD3FC]" />
                  <h2 className="text-[13px] font-medium text-white/95 tracking-tight">Air Assistant</h2>
                </div>
                <button aria-label="Close assistant panel" onClick={() => setIsOpen(false)} className="w-11 h-11 rounded-full bg-white/[0.08] backdrop-blur-2xl text-white/85 hover:bg-white/[0.15] hover:text-white transition-all flex items-center justify-center shadow-[0_8px_24px_rgba(0,0,0,0.35),inset_0_1px_1px_rgba(255,255,255,0.16)]">
                  <X size={18} strokeWidth={1.8} />
                </button>
              </header>

              <div className="flex-grow min-h-0 px-6 pt-4 pb-6 space-y-5 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/10 scrollbar-track-transparent relative z-10">
                <div className="pt-1 pb-2">
                  <h3 className="text-[23px] sm:text-[25px] font-semibold text-white tracking-[-0.02em] leading-snug">A little help. A lot of clarity.</h3>
                  <p className="text-[15px] sm:text-[20px] font-normal text-white/45 tracking-[-0.01em] leading-snug mt-0.5">Your Air Assistant, here to help.</p>
                </div>
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
