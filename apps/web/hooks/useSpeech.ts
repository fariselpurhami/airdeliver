import { useState, useEffect, useCallback } from 'react';

export const useSpeech = (onTranscript: (text: string) => void) => {
    const [isListening, setIsListening] = useState(false);
    const recognition = useRef<SpeechRecognition | null>(null);

    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error("Speech recognition not supported.");
            return;
        }
        
        recognition.current = new SpeechRecognition();
        recognition.current.continuous = false;
        recognition.current.lang = 'en-US';
        recognition.current.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            onTranscript(transcript);
            setIsListening(false);
        };
        recognition.current.onerror = () => setIsListening(false);
    }, [onTranscript]);

    const startListening = useCallback(() => {
        if (recognition.current && !isListening) {
            recognition.current.start();
            setIsListening(true);
        }
    }, [isListening]);
    
    const speak = useCallback((text: string) => {
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }, []);

    return { isListening, startListening, speak };
};
