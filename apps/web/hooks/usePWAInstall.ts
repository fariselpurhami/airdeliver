'use client';

import { useState, useEffect, useCallback } from 'react';

// --- Types & Interfaces ---

/**
 * Standardized interface for the BeforeInstallPromptEvent.
 * @see https://developer.mozilla.org/en-US/docs/Web/API/BeforeInstallPromptEvent
 */
export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

/**
 * Extend the Navigator interface to support non-standard iOS properties.
 */
interface IOSNavigator extends Navigator {
  standalone?: boolean;
}

// --- Hooks ---

/**
 * Manages the PWA installation flow for Android/Windows and iOS.
 */
export const usePWAInstall = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isIOS, setIsIOS] = useState<boolean>(false);
  const [isIOSPromptVisible, setIOSPromptVisible] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // 1. Android/Windows Install Prompt
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // 2. iOS Detection
    const ua = window.navigator.userAgent;
    // 'MSStream' check avoids false positives on older Windows devices
    const isIOSDevice = /iPad|iPhone|iPod/.test(ua) && !('MSStream' in window);
    setIsIOS(isIOSDevice);

    // 3. Standalone Mode Detection
    const nav = window.navigator as IOSNavigator;
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || !!nav.standalone;
    
    if (isStandalone) {
      setDeferredPrompt(null);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const triggerInstall = useCallback(async () => {
    if (deferredPrompt) {
      try {
        await deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') {
          setDeferredPrompt(null);
        }
      } catch (error) {
        console.error('[PWA]: Install prompt failed or was blocked', error);
      }
    } else if (isIOS) {
      setIOSPromptVisible(true);
    } else {
      // Retaining original UI logic: alert fallback if already installed or unsupported
      alert('The app is already installed or not supported by this browser.');
    }
  }, [deferredPrompt, isIOS]);

  return { triggerInstall, isIOSPromptVisible, setIOSPromptVisible };
};

/**
 * Safely detects mobile viewports and PWA standalone mode without hydration errors.
 * Optimized to use matchMedia instead of expensive window resize listeners.
 */
export const useDeviceDetection = () => {
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [isStandalone, setIsStandalone] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    setMounted(true);
    
    // Utilize matchMedia for highly performant layout checking vs raw innerWidth + resize
    const mobileMediaQuery = window.matchMedia('(max-width: 1023px)');
    const standaloneMediaQuery = window.matchMedia('(display-mode: standalone)');
    const nav = window.navigator as IOSNavigator;

    // Initial state population
    setIsMobile(mobileMediaQuery.matches);
    setIsStandalone(standaloneMediaQuery.matches || !!nav.standalone);

    // Handlers
    const handleMobileChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    const handleStandaloneChange = (e: MediaQueryListEvent) => setIsStandalone(e.matches || !!nav.standalone);

    // Modern browsers support addEventListener on MediaQueryList; provide fallback for old Safari
    if (mobileMediaQuery.addEventListener) {
      mobileMediaQuery.addEventListener('change', handleMobileChange);
      standaloneMediaQuery.addEventListener('change', handleStandaloneChange);
    } else {
      mobileMediaQuery.addListener(handleMobileChange);
      standaloneMediaQuery.addListener(handleStandaloneChange);
    }

    return () => {
      if (mobileMediaQuery.removeEventListener) {
        mobileMediaQuery.removeEventListener('change', handleMobileChange);
        standaloneMediaQuery.removeEventListener('change', handleStandaloneChange);
      } else {
        mobileMediaQuery.removeListener(handleMobileChange);
        standaloneMediaQuery.removeListener(handleStandaloneChange);
      }
    };
  }, []);

  return { isMobile, isStandalone, mounted };
};
