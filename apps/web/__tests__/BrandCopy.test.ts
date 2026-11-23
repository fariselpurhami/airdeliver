import fs from 'fs';
import path from 'path';

function files(root: string): string[] {
  return fs.readdirSync(root, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(root, entry.name);
    return entry.isDirectory() ? files(full) : /\.(tsx?|jsx?|html|svg)$/.test(entry.name) ? [full] : [];
  });
}

it('authored UI copy keeps the brand lowercase', () => {
  for (const root of ['app', 'components', 'hooks', 'lib', 'public']) {
    for (const file of files(path.join(process.cwd(), root))) {
      expect({ file, invalid: fs.readFileSync(file, 'utf8').match(/\b(?:AirDeliver|Airdeliver|AIRDELIVER)\b/g) }).toEqual({ file, invalid: null });
    }
  }
});

it('welcome and insight retain the requested brand spellings', () => {
  const store = fs.readFileSync('hooks/useAIOrderingStore.ts', 'utf8');
  const overlay = fs.readFileSync('components/ai/AIChatOverlay.tsx', 'utf8');
  expect(store).toContain('Welcome to airdeliver.');
  expect(overlay).toContain('airdeliverOS Insight');
  expect(overlay).toContain("'airdeliver SELECT'");
  expect(overlay).toContain("'normal-case'");
});
