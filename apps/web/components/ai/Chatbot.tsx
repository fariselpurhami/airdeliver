'use client'; 

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Loader2, MessageSquare, Send, X } from 'lucide-react';

type Message = {
  id: number;
  sender: 'user' | 'bot';
  text: string;
};

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to the latest message whenever messages change
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: Date.now(), sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // --- TODO: Call your REAL AI Support API endpoint here ---
      // This is a placeholder to simulate a bot response.
      await new Promise(resolve => setTimeout(resolve, 1500));
      const botMessage: Message = { 
        id: Date.now() + 1, 
        sender: 'bot', 
        text: "This is a simulated response. How can I help you with your order?" 
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = { 
        id: Date.now() + 1, 
        sender: 'bot', 
        text: "Sorry, I'm having trouble connecting right now." 
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <div className="fixed bottom-8 right-8 z-40">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setIsOpen(!isOpen)} 
          className="p-4 bg-primary text-primary-foreground rounded-full shadow-lg flex items-center justify-center h-16 w-16"
          aria-label="Toggle AI Support Chat"
        >
          <AnimatePresence initial={false} mode="wait">
            <motion.div
              key={isOpen ? 'x' : 'message'}
              initial={{ y: -20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {isOpen ? <X size={28} /> : <MessageSquare size={28} />}
            </motion.div>
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed bottom-28 right-8 w-[90vw] max-w-sm h-[70vh] max-h-[600px] bg-gray-900 text-white border border-white/10 rounded-2xl shadow-2xl flex flex-col z-50"
          >
            <header className="p-4 border-b border-white/10 flex justify-between items-center flex-shrink-0">
              <div className="flex items-center space-x-3">
                <Bot className="text-primary" size={24} />
                <h3 className="font-bold text-lg">AI Support</h3>
              </div>
              <button 
                onClick={() => setIsOpen(false)} 
                className="p-2 rounded-full text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
                aria-label="Close AI Support"
              >
                <X size={20} />
              </button>
            </header>

            <main className="flex-grow p-4 space-y-4 overflow-y-auto">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex w-full ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-xs px-4 py-3 rounded-2xl ${msg.sender === 'user' ? 'bg-primary text-primary-foreground rounded-br-none' : 'bg-gray-700 text-gray-200 rounded-bl-none'}`}>
                    <p className="text-sm">{msg.text}</p>
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex w-full justify-start"
                >
                   <div className="flex items-center space-x-1 p-3 bg-gray-700 rounded-2xl rounded-bl-none">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-75" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-150" />
                   </div>
                </motion.div>
              )}
              <div ref={chatEndRef} />
            </main>

            {/* This is the new, corrected footer section */}
            <footer className="p-4 border-t border-white/10 flex gap-3 items-center flex-shrink-0">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                placeholder="Ask about your order..."
                className="flex-grow p-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-primary focus:outline-none transition-all"
                disabled={isLoading}
              />
              <button onClick={handleSend} className="p-3 bg-primary text-primary-foreground rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-transform hover:scale-105" disabled={isLoading} aria-label="Send message">
                {isLoading ? <Loader2 size={24} className="animate-spin" /> : <Send size={24} />}
              </button>
            </footer>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
