import { readFileSync } from 'fs';
import { join } from 'path';
const read = (p: string) => readFileSync(join(__dirname, '..', p), 'utf8');

describe('prompt bar microphone', () => {
  it('sits in the same filled circle as the camera', () => {
    const src = read('src/components/ui/PromptMediaIcons.tsx');
    const circles = src.match(/rounded-full bg-white\/\[0\.08\]/g) ?? [];
    expect(circles).toHaveLength(2);
    expect(src).toContain('<Mic ');
  });
});

describe('floating card category label is never truncated', () => {
  const files = [
    'src/components/hero/FloatingHeroCards.tsx',
    'src/components/hero/MobileHomeFloatingCards.tsx',
    'src/app/(main)/_components/LandingClient.tsx',
    'src/app/(main)/login/page.tsx',
    'src/app/(main)/profile/page.tsx',
  ];
  it.each(files)('%s', (f) => {
    const spans = read(f).split('\n').filter((l) => l.includes('{category}</span>'));
    expect(spans.length).toBeGreaterThan(0);
    for (const l of spans) {
      expect(l).not.toMatch(/\btruncate\b|line-clamp-1|text-ellipsis/);
      // ELECTRONICS is 11 letters: the wide 0.3em tracking is desktop only
      expect(l).not.toMatch(/(?<![:\w-])tracking-\[0\.2em\]|tracking-widest/);
    }
  });
});
