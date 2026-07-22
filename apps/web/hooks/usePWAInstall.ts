'use client';
import { useState, useEffect } from 'react';

export const usePWAInstall = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isIOS, setIsIOS] = useState(false);
  const [isIOSPromptVisible, setIOSPromptVisible] = useState(false);

  useEffect(() => {
    // 1. Android/Windows
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // 2. iOS Detection
    const ua = window.navigator.userAgent;
    const isIOSDevice = /iPad|iPhone|iPod/.test(ua) && !(window as any).MSStream;
    setIsIOS(isIOSDevice);

    // 3. Check if already installed
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || (window.navigator as any).standalone;
    if (isStandalone) {
      setDeferredPrompt(null);
    }

    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  }, []);

  const triggerInstall = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') setDeferredPrompt(null);
    } else if (isIOS) {
      setIOSPromptVisible(true);
    } else {
      alert('The app is already installed or not supported by this browser.');
    }
  };

  return { triggerInstall, isIOSPromptVisible, setIOSPromptVisible };
};

// Hook لاكتشاف الموبايل بشكل آمن بدون Hydration Errors
// Hook لاكتشاف الموبايل وحالة التطبيق (Standalone)
export const useDeviceDetection = () => {
  const [isMobile, setIsMobile] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    const checkDevice = () => {
      // 1. هل الشاشة شاشة موبايل؟
      setIsMobile(window.innerWidth < 1024);
      
      // 2. هل التطبيق مفتوح كـ Native App (Standalone)؟
      const standalone = window.matchMedia('(display-mode: standalone)').matches || (window.navigator as any).standalone;
      setIsStandalone(standalone);
    };

    checkDevice();
    window.addEventListener('resize', checkDevice);
    
    // مستمع إضافي لو العميل غير حالة العرض فجأة
    const mediaQuery = window.matchMedia('(display-mode: standalone)');
    const handleDisplayModeChange = (e: MediaQueryListEvent) => setIsStandalone(e.matches);
    mediaQuery.addEventListener('change', handleDisplayModeChange);

    return () => {
      window.removeEventListener('resize', checkDevice);
      mediaQuery.removeEventListener('change', handleDisplayModeChange);
    };
  }, []);

  return { isMobile, isStandalone, mounted };
};
