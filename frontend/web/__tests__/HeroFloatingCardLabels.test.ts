import { test, expect } from '@jest/globals';
import fs from 'fs';
import path from 'path';

const read = (p: string) => fs.readFileSync(path.join(process.cwd(), p), 'utf8');
const mobile = read('src/components/hero/MobileHomeFloatingCards.tsx');
const desktop = read('src/components/hero/FloatingHeroCards.tsx');

test('floating card category labels match what each product is', () => {
  expect(mobile).toMatch(/title: "PS5", category: "Gaming"/);
  expect(mobile).toMatch(/title: "Galaxy Buds", category: "Audio"/);
  expect(desktop).toContain('category="Audio" title="Galaxy Buds"');
  expect(mobile).not.toMatch(/category: "Wearables"/);
  expect(mobile + desktop).not.toContain('Neural Tech');
});

test('card titles wrap to two lines instead of truncating to an ellipsis', () => {
  for (const src of [mobile, desktop]) {
    expect(src).toContain('line-clamp-2 break-words');
  }
  expect(mobile).not.toMatch(/leading-tight truncate/);
});
