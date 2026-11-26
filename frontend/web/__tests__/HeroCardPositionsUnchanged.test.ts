/**
 * The user asked that floating cards keep exactly their original positions and sizes; only labels
 * and text may change. These digests are over every positionClasses/sizeClasses string as they were
 * at 05b95d32. A deliberate move needs the user's approval and a new digest.
 */
import { createHash } from 'crypto';
import { readFileSync } from 'fs';
import { join } from 'path';

const ORIGINAL: Record<string, string> = {
  'src/components/hero/FloatingHeroCards.tsx':
    '2d960f8ca787d1851a31d75de950ddc1b33afa2593340f70b7d4870ec8ea2fc3',
  'src/components/hero/MobileHomeFloatingCards.tsx':
    'c3da704d455a4399be2f39b7093ccbd6984990bf7c3e20d6df01d5525492c521',
  'src/app/(main)/_components/LandingClient.tsx':
    'c3da704d455a4399be2f39b7093ccbd6984990bf7c3e20d6df01d5525492c521',
};

it.each(Object.entries(ORIGINAL))('%s keeps its original card positions and sizes', (file, digest) => {
  const src = readFileSync(join(__dirname, '..', file), 'utf8');
  const found = src.match(/positionClasses: "[^"]*"|sizeClasses="[^"]*"/g) ?? [];
  expect(found.length).toBeGreaterThan(0);
  expect(createHash('sha256').update(found.join('\n')).digest('hex')).toBe(digest);
});
