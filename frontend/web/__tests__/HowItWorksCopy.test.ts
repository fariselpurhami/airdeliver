/** Copy for HOW IT WORKS (user request 1:07 PM). Each claim maps to shipped behaviour: catalog price
 * and stock on every result, unverifiable price cannot be added to cart, one confirmation sends one
 * order and a retry never creates a second. Source-level test; not a pixel check. */
import { readFileSync } from 'fs';
import { join } from 'path';
const src = readFileSync(join(__dirname, '..', 'src/app/(main)/_components/LandingClient.tsx'), 'utf8');
it('uses the new pill, step title and subtitle; drops the old ones', () => {
  expect(src).not.toContain('FOUR STEPS');
  expect(src).not.toContain('Tell Air what you need');
  expect(src).not.toContain('in four steps.');
  expect(src).toContain('VERIFIED BEFORE YOU ORDER');
  expect(src).toContain('title: "Order with Air"');
  expect(src).toContain('Say it or snap it. Every price is checked against the catalog, and one confirmation places one order.');
});
it('stretches the word works with letter spacing', () => {
  const m = src.match(/bg-clip-text text-transparent[^"]*"\s*>\s*works/);
  expect(m).not.toBeNull();
  expect(m![0]).toMatch(/tracking-\[0\.0[4-9]em\]/);
});
