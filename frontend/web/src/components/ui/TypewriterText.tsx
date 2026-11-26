'use client';

import { useEffect, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

interface TypewriterTextProps {
  readonly text: string;
  readonly className?: string;
  /** ms per typed character */
  readonly typeMs?: number;
  /** ms per erased character */
  readonly eraseMs?: number;
  /** ms the finished text stays on screen before it is erased */
  readonly holdMs?: number;
  /** ms the empty field stays before typing restarts */
  readonly pauseMs?: number;
}

/**
 * Live-typing placeholder: types the text, holds it, erases it, repeats.
 * With prefers-reduced-motion the full text is shown statically. The full text is
 * always available to assistive tech through a visually hidden copy; the animated
 * copy is aria-hidden so screen readers do not hear every keystroke.
 */
export function TypewriterText({ text, className, typeMs = 70, eraseMs = 35, holdMs = 1800, pauseMs = 500 }: TypewriterTextProps) {
  const reduced = useReducedMotion();
  const [count, setCount] = useState(0);
  const [erasing, setErasing] = useState(false);

  useEffect(() => {
    if (reduced) return;
    let delay: number;
    let next: () => void;
    if (!erasing && count < text.length) {
      delay = typeMs;
      next = () => setCount((c) => c + 1);
    } else if (!erasing) {
      delay = holdMs;
      next = () => setErasing(true);
    } else if (count > 0) {
      delay = eraseMs;
      next = () => setCount((c) => c - 1);
    } else {
      delay = pauseMs;
      next = () => setErasing(false);
    }
    const id = setTimeout(next, delay);
    return () => clearTimeout(id);
  }, [reduced, count, erasing, text, typeMs, eraseMs, holdMs, pauseMs]);

  if (reduced) return <span className={className}>{text}</span>;
  return (
    <span className={className}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" data-testid="typewriter-visible">
        {text.slice(0, count)}
        <span className="ml-px inline-block h-[1em] w-px translate-y-[0.15em] animate-pulse bg-current align-baseline" />
      </span>
    </span>
  );
}
