import fs from 'fs';
import crypto from 'crypto';
import manifest from '@/lib/catalog/demo-images.json';
it('pins all reviewed candidate bytes and records provenance, without runtime activation',()=>{
 expect(manifest.runtime_enabled).toBe(false);
 for(const row of manifest.items){
  expect(row.asset).toMatch(/^\/images\/demo-v1\/[a-z-]+\.jpg$/);
  expect(crypto.createHash('sha256').update(fs.readFileSync(`public${row.asset}`)).digest('hex')).toBe(row.sha256);
  expect(row.source_url).toMatch(/^https:\/\/commons.wikimedia.org\/wiki\/File:/);
  expect(row.license_url).toBe('https://creativecommons.org/licenses/by-sa/4.0/');
  expect(row.author.length).toBeGreaterThan(0);
  expect(row.review_status).toBe('candidate');
  expect(row.match_kind).toBe('family_reference');
  expect(Number.isFinite(Date.parse(row.retrieved_at))).toBe(true);
 }
});
