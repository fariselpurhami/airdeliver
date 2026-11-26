import fs from 'fs';
const source=fs.readFileSync('src/components/products/ProductCard.tsx','utf8');
it('order with air button uses the purple AI icon, not the shopping bag',()=>{
 expect(source).not.toMatch(/<ShoppingBag/);
 expect(source).not.toMatch(/ShoppingBag[,} ]/);
 const button=source.slice(source.indexOf('id={uniqueBtnId}'),source.indexOf('order with air</span>'));
 expect(button).toContain('<AirSparkles');
 expect(button).toContain('text-purple-400');
 expect(button).toContain('rounded-full');
 expect(button).not.toContain('bg-cyan-500/10');
});
it('price is a classic solid colour, not a cyan-blue gradient',()=>{
 const price=source.slice(source.indexOf('<span className="text-[10px] md:text-[10px] text-gray-600'),source.indexOf('<CatalogPrice'));
 expect(price).not.toContain('bg-clip-text');
 expect(price).not.toContain('from-cyan-300');
 expect(price).toContain('text-white');
});
