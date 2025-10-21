'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

// --- The Fix ---
// 1. We define an interface for the SpeechRecognition object itself.
//    This creates a global type named `SpeechRecognition`.
interface SpeechRecognition {
  continuous: boolean;
  lang: string;
  onresult: (event: any) => void;
  onerror: (event: any) => void;
  onend: () => void;
  start: () => void;
  stop: () => void;
}

// 2. We define a type for the constructor of the SpeechRecognition object.
type SpeechRecognitionConstructor = new () => SpeechRecognition;

// 3. We augment the global Window interface to tell TypeScript these constructors exist.
declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionConstructor;
    webkitSpeechRecognition: SpeechRecognitionConstructor;
  }
}

export const useSpeech = (onTranscript: (text: string) => void) => {
    const [isListening, setIsListening] = useState(false);
    // Now this works, because the 'SpeechRecognition' type is defined globally.
    const recognition = useRef<SpeechRecognition | null>(null);

    useEffect(() => {
        const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognitionAPI) {
            console.error("Speech recognition not supported.");
            return;
        }
        
        recognition.current = new SpeechRecognitionAPI();
        recognition.current.continuous = false;
        recognition.current.lang = 'en-US';
        
        recognition.current.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            onTranscript(transcript);
            setIsListening(false);
        };

        recognition.current.onerror = () => {
          setIsListening(false);
        };
        
        recognition.current.onend = () => {
          setIsListening(false);
        };

    }, [onTranscript]);

    const startListening = useCallback(() => {
        if (recognition.current && !isListening) {
            recognition.current.start();
            setIsListening(true);
        }
    }, [isListening]);
    
    const speak = useCallback((text: string) => {
        if (typeof window !== 'undefined' && window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    }, []);

    return { isListening, startListening, speak };
};
