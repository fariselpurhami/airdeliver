import { test, expect, beforeEach, afterEach } from '@jest/globals';
import { render, act } from '@testing-library/react';

const state = { reduced: false };
jest.mock('framer-motion', () => ({ useReducedMotion: () => state.reduced }));
import { TypewriterText } from '@/components/ui/TypewriterText';

beforeEach(() => { jest.useFakeTimers(); state.reduced = false; });
afterEach(() => { jest.useRealTimers(); });

const visible = (c: HTMLElement) => c.querySelector('[data-testid="typewriter-visible"]')?.textContent ?? '';

const step = (ms: number) => act(() => { jest.advanceTimersByTime(ms); });

test('types the text one character at a time, holds, erases and restarts', () => {
  const { container } = render(<TypewriterText text="abc" typeMs={10} eraseMs={10} holdMs={100} pauseMs={50} />);
  expect(visible(container)).toBe('');
  step(10); expect(visible(container)).toBe('a');
  step(10); step(10); expect(visible(container)).toBe('abc');
  step(99); expect(visible(container)).toBe('abc');
  step(1); step(10); expect(visible(container)).toBe('ab');
  step(10); step(10); expect(visible(container)).toBe('');
  step(50); step(10); expect(visible(container)).toBe('a');
});

test('keeps the full text for assistive tech and hides the animated copy', () => {
  const { container } = render(<TypewriterText text="hello" />);
  expect(container.querySelector('.sr-only')?.textContent).toBe('hello');
  expect(container.querySelector('[aria-hidden="true"]')).not.toBeNull();
});

test('prefers-reduced-motion shows the full text and starts no timers', () => {
  state.reduced = true;
  const { container } = render(<TypewriterText text="hello" />);
  expect(container.textContent).toBe('hello');
  expect(jest.getTimerCount()).toBe(0);
});

test('landing and products prompt bars use live typing plus camera and mic icons', () => {
  const fs = require('fs'); const path = require('path');
  const read = (p: string) => fs.readFileSync(path.join(process.cwd(), p), 'utf8');
  const home = read('src/app/(main)/_components/LandingClient.tsx');
  const products = read('src/app/(main)/products/page.tsx');
  expect(home.match(/<TypewriterText /g)).toHaveLength(2);
  expect(home.match(/<PromptMediaIcons \/>/g)).toHaveLength(2);
  expect(products.match(/<TypewriterText /g)).toHaveLength(1);
  expect(products.match(/<PromptMediaIcons \/>/g)).toHaveLength(1);
});
