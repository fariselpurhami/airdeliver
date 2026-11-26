/** Guards the two next/image dev warnings: logo aspect attributes and fill sizes. */
import fs from 'fs'
import path from 'path'

const root = path.resolve(__dirname, '..')
const read = (p: string) => fs.readFileSync(path.join(root, p), 'utf8')

test('logo width/height attributes match the real PNG aspect ratio', () => {
  const png = fs.readFileSync(path.join(root, 'public/logo.png'))
  const ratio = png.readUInt32BE(16) / png.readUInt32BE(20)
  for (const file of ['src/components/layout/Header.tsx', 'src/components/layout/Footer.tsx', 'src/components/home/MobileLandingView.tsx']) {
    const src = read(file)
    const blocks = src.split('<Image').slice(1).filter(b => b.includes('src="/logo.png"'))
    expect(blocks.length).toBeGreaterThan(0)
    for (const b of blocks) {
      const w = Number(/width=\{(\d+)\}/.exec(b)![1])
      const h = Number(/height=\{(\d+)\}/.exec(b)![1])
      expect(Math.abs(w / h - ratio) / ratio).toBeLessThan(0.02)
    }
  }
})

test('every fill CatalogImage on the products page declares sizes', () => {
  const src = read('src/app/(main)/products/page.tsx')
  for (const tag of src.match(/<CatalogImage[^>]*\bfill\b[^>]*>/g) ?? []) expect(tag).toContain('sizes=')
})
