/**
 * Next reports the hero card photo (Galaxy Buds, bottom of the first screen) as the Largest
 * Contentful Paint image and asks for loading="eager". Next 16 deprecates `priority` in favour of
 * loading="eager" with fetchPriority. Every hero card <Image> must opt out of lazy loading.
 * This test is source-level: it does not prove the browser warning is gone on a device.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const FILES = [
  'src/components/hero/FloatingHeroCards.tsx',
  'src/components/hero/MobileHomeFloatingCards.tsx',
  'src/app/(main)/_components/LandingClient.tsx',
];

it.each(FILES)('%s hero card image loads eagerly', (file) => {
  const src = readFileSync(join(__dirname, '..', file), 'utf8');
  const tags = src.match(/<Image src=\{image\}[^>]*\/>/g) ?? [];
  expect(tags.length).toBe(1);
  expect(tags[0]).toContain('loading="eager"');
  expect(tags[0]).not.toContain('priority');
});
