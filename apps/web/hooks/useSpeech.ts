'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface SpeechRecognition {
  continuous: boolean;
  lang: string;
  onresult: (event: any) => void;
  onerror: (event: any) => void;
  onend: () => void;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionConstructor;
    // another ambient declaration already types this as any; keep them in sync
    webkitSpeechRecognition: any;
  }
}

export const useSpeech = (onTranscript: (text: string) => void) => {
    const [isListening, setIsListening] = useState(false);
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
