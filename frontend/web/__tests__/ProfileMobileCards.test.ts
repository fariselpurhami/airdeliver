/**
 * Profile page, mobile (user request 1:11 PM): the six floating cards sit in a cluster above the
 * identity block (so all of them are above Shopping memory), text inside them is not truncated.
 * The scattered desktop/tablet layer is unchanged and only shown from sm up. Source-level test, not a
 * pixel check: real phone rendering is still unverified.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
const src = readFileSync(join(__dirname, '..', 'src/app/(main)/profile/page.tsx'), 'utf8');

it('renders a mobile-only cluster of all six cards before the avatar', () => {
  expect(src).toContain('data-testid="profile-mobile-card-cluster"');
  const idx = src.indexOf('data-testid="profile-mobile-card-cluster"');
  expect(src.indexOf('aria-label="Change profile picture"')).toBeGreaterThan(idx);
  expect(src.slice(idx - 200, idx + 200)).toContain('sm:hidden');
  expect(src).toContain('mobileClasses');
  expect((src.match(/mobileClasses: "/g) ?? []).length).toBe(6);
});
it('keeps the scattered layer for sm and up only', () => {
  expect(src).toMatch(/absolute inset-0 pointer-events-none z-0 hidden sm:flex/);
});
it('does not truncate card text', () => {
  const card = src.slice(src.indexOf('const ProfileFloatingProduct'), src.indexOf('ProfileFloatingProduct.displayName'));
  expect(card).not.toContain('truncate');
  expect(card).toContain('line-clamp-2');
});
it('desktop positions are unchanged', () => {
  const found = src.match(/positionClasses: "[^"]*"/g) ?? [];
  expect(found.length).toBe(6);
});
