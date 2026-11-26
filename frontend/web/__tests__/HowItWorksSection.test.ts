import { test, expect } from '@jest/globals';
import fs from 'fs';
import path from 'path';

const src = fs.readFileSync(path.join(process.cwd(), 'src/app/(main)/_components/LandingClient.tsx'), 'utf8');
const steps = src.slice(src.indexOf('const PRODUCTION_STEPS = ['), src.indexOf('] as const;', src.indexOf('const PRODUCTION_STEPS = [')));

test('How it works header is left aligned', () => {
  const header = src.slice(src.indexOf('id="how-it-works-heading"') - 1500, src.indexOf('id="how-it-works-heading"'));
  expect(header).toContain('items-start text-left');
  expect(header).not.toContain('text-center');
});

test('steps make no claim the code does not back', () => {
  for (const banned of ['neural', 'computer vision', 'milliseconds', 'reserving', 'one-tap', 'encrypted', 'autonomous', 'partner stores', 'local hubs', 'texture, brand']) {
    expect(steps.toLowerCase()).not.toContain(banned);
  }
  // Backed by: checkout/options (US, USD), image_hint_boundary (hint only, 6 MB, jpeg/png/webp/gif),
  // idempotent checkout confirm, and the unverified-price add-to-cart block.
  expect(steps).toContain('US only, in US dollars');
  expect(steps).toContain('a hint, not proof');
  expect(steps).toContain('up to 6 MB');
  expect(steps).toContain('never creates a second one');
});
