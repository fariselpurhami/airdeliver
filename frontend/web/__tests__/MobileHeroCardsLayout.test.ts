/**
 * Layout arithmetic for the mobile hero cards (NOT a pixel test): the six lower cards sit in two
 * bottom-anchored rows of three, so they cannot reach the prompt bar or the subtitle that sit
 * above them, and no two cards in a row overlap horizontally at 360 and 390 px.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const FILES = ['src/components/hero/MobileHomeFloatingCards.tsx', 'src/app/(main)/_components/LandingClient.tsx'];
const W = (cls: string) => ({ 'w-20': 80, 'w-21': 84, 'w-22': 88 } as Record<string, number>)[cls] ?? NaN;

describe.each(FILES)('%s', (f) => {
  const src = readFileSync(join(__dirname, '..', f), 'utf8');
  const rows = [...src.matchAll(/\{ title: "([^"]+)",[^\n]*?positionClasses: "([^"]+)", sizeClasses: "(w-\d+) /g)];
  it('has eight cards', () => expect(rows).toHaveLength(8));
  it.each([360, 390])('lower cards are bottom-anchored and do not overlap at %ipx', (vw) => {
    const lower = rows.filter((r) => /\bbottom-\[/.test(r[2] ?? '') && !(r[2] ?? '').startsWith('top-'));
    expect(lower.map((r) => r[1]).sort()).toEqual(['Dyson', 'Galaxy Buds', 'Headphones', 'Iphone 17 pro max', 'Leather Handbag', 'Nike Air Max']);
    const byRow = new Map<string, { n: string; l: number; r: number }[]>();
    for (const [, n, pc, sc] of lower) {
      const cls = (pc ?? '').split(' ').filter((c) => !c.includes(':'));
      const bottom = cls.find((c) => c.startsWith('bottom-')) ?? '';
      const w = W(sc ?? '');
      const left = cls.find((c) => c.startsWith('left-[')), right = cls.find((c) => c.startsWith('right-['));
      const pct = (c: string) => parseFloat(c.replace(/\D*(\d+(?:\.\d+)?)%.*/, '$1')) / 100;
      const l = left ? vw * pct(left) : vw - vw * pct(right ?? 'right-[0%]') - w;
      byRow.set(bottom, [...(byRow.get(bottom) ?? []), { n: n ?? '', l, r: l + w }]);
    }
    expect([...byRow.keys()].sort()).toEqual(['bottom-[0%]', 'bottom-[132px]']);
    for (const cards of byRow.values()) {
      expect(cards).toHaveLength(3);
      for (const a of cards) {
        expect([a.n, a.l >= 0 && a.r <= vw]).toEqual([a.n, true]);
        for (const b of cards) if (a.n < b.n) expect([a.n, b.n, a.l < b.r && b.l < a.r]).toEqual([a.n, b.n, false]);
      }
    }
  });
  it('keeps the two top cards above the content', () => {
    for (const t of ['Apple Vision Pro', 'PS5']) expect(src).toMatch(new RegExp(`title: "${t}",[^\\n]*positionClasses: "top-\\[1%\\]`));
  });
});
