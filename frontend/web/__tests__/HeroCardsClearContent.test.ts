/**
 * Layout-arithmetic contract (NOT a pixel test): at lg widths the desktop hero
 * cards must stay outside the centred content column (max-w-[48%]) and must not
 * overlap each other, using the Tailwind classes written in the component.
 * Rotation adds a few px of bounding box and is ignored, so this is a necessary
 * condition only. Real rendered measurement is still required.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, '../src/components/hero/FloatingHeroCards.tsx'), 'utf8');
const STAGE_H = 820;
type Box = { name: string; l: number; r: number; t: number; b: number };

function cards(vw: number): Box[] {
  const rows = [...src.matchAll(/sizeClasses="([^"]*lg:w-[^"]*)"[^>]*title="([^"]*)"/g)];
  return rows.map((row) => {
    const cls = row[1] ?? '';
    const name = row[2] ?? '';
    const g = (re: RegExp) => { const m = cls.match(re); return m && m[1] !== undefined ? parseFloat(m[1]) : NaN; };
    const w = g(/lg:w-(\d+)\b/) * 4, h = g(/lg:h-(\d+)\b/) * 4;
    const top = g(/lg:top-\[(\d+)%\]/), left = g(/lg:left-\[(\d+)%\]/), right = g(/lg:right-\[(\d+)%\]/);
    const l = Number.isNaN(left) ? vw - (vw * right) / 100 - w : (vw * left) / 100;
    const t = (STAGE_H * top) / 100;
    return { name, l, r: l + w, t, b: t + h };
  });
}

describe.each([1024, 1280, 1440, 1920])('desktop hero cards at %ipx', (vw) => {
  const list = cards(vw);
  it('parses all six cards', () => expect(list).toHaveLength(6));
  it('stays clear of the centred content column', () => {
    const colL = vw / 2 - (vw * 0.48) / 2, colR = vw / 2 + (vw * 0.48) / 2;
    for (const c of list) expect([c.name, c.r <= colL || c.l >= colR]).toEqual([c.name, true]);
  });
  it('stays inside the stage', () => {
    for (const c of list) expect([c.name, c.l >= 0 && c.r <= vw && c.b <= STAGE_H]).toEqual([c.name, true]);
  });
  it('does not overlap other cards', () => {
    for (const a of list) for (const b of list) if (a.name < b.name) {
      const hit = a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
      expect([a.name, b.name, hit]).toEqual([a.name, b.name, false]);
    }
  });
});
