// In apps/web/components/ai/AIOrderingOverlay.tsx

"use client";

import { useAIOrderingStore } from '@/hooks/useAIOrdering';
import { Bot, Loader2, Send, ShoppingCart, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

// Message bubble component for displaying chat messages
const MessageBubble = ({ message }: { message: any }) => {
  const isUser = message.sender === 'user';
  
  const renderContent = () => {
    switch (message.contentType) {
      case 'text':
        return <p>{message.content}</p>;
      case 'cart':
        return (
          <div>
            <p className="font-semibold mb-2">I've prepared your cart:</p>
            <ul className="space-y-1 text-sm">
              {message.content.items.map((item: any) => (
                <li key={item.product_id} className="flex justify-between">
                  <span>{item.name} (x{item.quantity})</span>
                  <span>${(item.price * item.quantity).toFixed(2)}</span>
                </li>
              ))}
            </ul>
            <div className="flex justify-between font-bold mt-2 pt-2 border-t border-gray-600">
              <span>Total</span>
              <span>${message.content.total.toFixed(2)}</span>
            </div>
          </div>
        );
      case 'error':
        return <p className="text-red-400">{message.content}</p>;
      case 'typing':
        return <div className="flex items-center space-x-1 p-2"><div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" /><div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-75" /><div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-150" /></div>;
      default:
        return null;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-xs md:max-w-md px-4 py-3 rounded-2xl ${isUser ? 'bg-primary text-primary-foreground rounded-br-none' : 'bg-gray-700 text-gray-200 rounded-bl-none'}`}>
        {renderContent()}
      </div>
    </motion.div>
  );
};


export function AIOrderingOverlay() {
  const { isOverlayVisible, setOverlayVisible, messages, isLoading, sendMessage } = useAIOrderingStore();
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim()) {
      sendMessage(input);
      setInput('');
    }
  };

  return (
    <AnimatePresence>
      {isOverlayVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setOverlayVisible(false)} // Close on backdrop click
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="w-full max-w-2xl h-[80vh] max-h-[700px] bg-gray-900 text-white rounded-2xl shadow-2xl flex flex-col border border-white/10"
            onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
          >
            {/* Header */}
            <header className="p-4 border-b border-white/10 flex justify-between items-center flex-shrink-0">
              <div className="flex items-center space-x-3">
                <Bot className="text-primary" size={24} />
                <h3 className="font-bold text-lg">Order With AI</h3>
              </div>
              <button
                onClick={() => setOverlayVisible(false)}
                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                aria-label="Close AI ordering chat"
              >
                <X size={20} />
              </button>
            </header>

            {/* Chat Body */}
            <main className="flex-grow p-4 space-y-4 overflow-y-auto">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
                  <ShoppingCart size={48} className="mb-4" />
                  <p className="font-semibold">Welcome to AI Ordering</p>
                  <p className="text-sm">Describe what you'd like to buy in one sentence.</p>
                </div>
              )}
              {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
            </main>

            {/* Footer / Input Area */}
            <footer className="p-4 border-t border-white/10 flex gap-3 items-center flex-shrink-0">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                placeholder="e.g., 'I want an iPhone 17 and two cables...'"
                className="flex-grow p-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-primary focus:outline-none transition-all"
                disabled={isLoading}
              />
              <button onClick={handleSend} className="p-3 bg-primary text-primary-foreground rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-transform hover:scale-105" disabled={isLoading} aria-label="Send message">
                {isLoading ? <Loader2 size={24} className="animate-spin" /> : <Send size={24} />}
              </button>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
