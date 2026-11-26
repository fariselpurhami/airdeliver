import { test, expect } from '@jest/globals';
import fs from 'fs';
import path from 'path';

test('closed chatbot launcher keeps the Bot icon and sits on a barely visible glass disc', () => {
  const src = fs.readFileSync(path.join(process.cwd(), 'src/components/ai/Chatbot.tsx'), 'utf8');
  const glass = src.match(/data-testid="chatbot-launcher-glass" className="([^"]+)"/);
  expect(glass).not.toBeNull();
  expect(glass![1]).toContain('backdrop-blur');
  expect(glass![1]).toContain('rounded-full');
  expect(glass![1]).not.toContain('bg-transparent');
  expect(src).toContain('<Bot size={28} strokeWidth={1.6} aria-hidden="true" />');
});
