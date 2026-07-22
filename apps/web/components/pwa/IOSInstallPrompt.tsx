'use client';

import React, { memo, useCallback, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { Share, PlusSquare, X, Rocket } from 'lucide-react';

type IOSInstallPromptProps = {
  isOpen: boolean;
  onClose: () => void;
};

const ROOT_FONT_FAMILY = "'Montserrat', sans-serif";
const MODAL_MAX_WIDTH_CLASS = 'max-w-sm';
const PANEL_TRANSITION = { type: 'spring', damping: 26, stiffness: 240, mass: 0.9 } as const;
const BACKDROP_TRANSITION = { duration: 0.16, ease: [0.16, 1, 0.3, 1] as const };

const STEPS = [
  {
    id: 'share',
    icon: Share,
    iconClassName: 'text-blue-400',
    text: (
      <>
        1. Tap <span className="font-bold text-white">Share</span> in Safari menu.
      </>
    ),
  },
  {
    id: 'home-screen',
    icon: PlusSquare,
    iconClassName: 'text-gray-300',
    text: (
      <>
        2. Tap <span className="font-bold text-white">Add to Home Screen</span>.
      </>
    ),
  },
] as const;

export const IOSInstallPrompt = memo(function IOSInstallPrompt({ isOpen, onClose }: IOSInstallPromptProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const prefersReducedMotion = useReducedMotion();

  const backdropMotion = useMemo(() => {
    if (prefersReducedMotion) {
      return {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0.01 },
      };
    }

    return {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
      transition: BACKDROP_TRANSITION,
    };
  }, [prefersReducedMotion]);

  const panelMotion = useMemo(() => {
    if (prefersReducedMotion) {
      return {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: 8 },
        transition: { duration: 0.01 },
      };
    }

    return {
      initial: { y: '100%', opacity: 0.98 },
      animate: { y: 0, opacity: 1 },
      exit: { y: '100%', opacity: 0.98 },
      transition: PANEL_TRANSITION,
    };
  }, [prefersReducedMotion]);

  const handleBackdropClick = useCallback(() => {
    onClose();
  }, [onClose]);

  const handleCloseClick = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!isOpen || typeof document === 'undefined') return;

    previouslyFocusedElementRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const focusFrame = window.requestAnimationFrame(() => {
      closeButtonRef.current?.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusableNodes = dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );

      if (focusableNodes.length === 0) return;

      const firstNode = focusableNodes[0];
      const lastNode = focusableNodes[focusableNodes.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey && activeElement === firstNode) {
        event.preventDefault();
        lastNode.focus();
      } else if (!event.shiftKey && activeElement === lastNode) {
        event.preventDefault();
        firstNode.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
      previouslyFocusedElementRef.current?.focus();
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence initial={false}>
      {isOpen ? (
        <div
          id="ios-install-prompt"
          className="pointer-events-none fixed inset-0 z-[100] flex items-end justify-center px-4 pb-8 sm:items-center sm:p-0"
          style={{ fontFamily: ROOT_FONT_FAMILY }}
        >
          <motion.button
            type="button"
            aria-label="Close install prompt"
            {...backdropMotion}
            onClick={handleBackdropClick}
            className="pointer-events-auto absolute inset-0 bg-black/60 backdrop-blur-sm"
          />

          <motion.div
            {...panelMotion}
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="ios-install-title"
            aria-describedby="ios-install-description"
            className={[
              'pointer-events-auto relative w-full',
              MODAL_MAX_WIDTH_CLASS,
              'rounded-3xl border border-white/10 bg-zinc-900 p-6 shadow-2xl',
              'transform-gpu [contain:layout_paint_style]',
            ].join(' ')}
          >
            <button
              ref={closeButtonRef}
              type="button"
              onClick={handleCloseClick}
              aria-label="Close install prompt"
              className="absolute right-4 top-4 rounded-full bg-zinc-800 p-1.5 text-gray-400 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900"
            >
              <X size={18} aria-hidden="true" />
            </button>

            <div className="mt-2 flex flex-col items-center text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-500 to-purple-500 shadow-lg shadow-cyan-500/20">
                <Rocket size={32} className="text-white" aria-hidden="true" />
              </div>

              <h3 id="ios-install-title" className="mb-2 font-sans text-xl font-bold tracking-tight text-white">
                Install airdeliver app
              </h3>

              <p id="ios-install-description" className="mb-6 text-sm font-light text-gray-400">
                Install our native app for the best ordering experience.
              </p>

              <div className="w-full space-y-4 rounded-2xl border border-white/5 bg-black/50 p-4 text-left">
                {STEPS.map((step, index) => {
                  const Icon = step.icon;
                  const showDivider = index < STEPS.length - 1;

                  return (
                    <React.Fragment key={step.id}>
                      <div className="flex items-center gap-4">
                        <div className={`rounded-xl bg-zinc-800 p-2 ${step.iconClassName}`}>
                          <Icon size={20} aria-hidden="true" />
                        </div>
                        <p className="text-sm text-gray-300">{step.text}</p>
                      </div>

                      {showDivider ? <div className="ml-6 h-4 w-px bg-white/10" aria-hidden="true" /> : null}
                    </React.Fragment>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={handleCloseClick}
                className="mt-6 w-full rounded-full bg-white/10 py-3 font-medium text-white transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900"
              >
                Got it
              </button>
            </div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>
  );
});
