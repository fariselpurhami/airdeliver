import {test,expect} from '@jest/globals';
import {render} from '@testing-library/react';
import {AirSparkles} from '@/components/ui/AirSparkles';
import fs from 'fs';
import path from 'path';

test('shopping mark has one large star and two small stars without changing assistant scope',()=>{
 const {container}=render(<AirSparkles className="text-purple-400" />);
 expect(container.querySelectorAll('svg path')).toHaveLength(3);
 expect(container.querySelector('svg')).toHaveAttribute('aria-hidden','true');
 const home=fs.readFileSync(path.join(process.cwd(),'src/app/(main)/_components/LandingClient.tsx'),'utf8');
 const products=fs.readFileSync(path.join(process.cwd(),'src/app/(main)/products/page.tsx'),'utf8');
 expect(home.match(/<AirSparkles /g)).toHaveLength(2);
 expect(products.match(/<AirSparkles /g)).toHaveLength(2);
 expect(products).not.toContain('<Bot ');
 const card=fs.readFileSync(path.join(process.cwd(),'src/components/products/ProductCard.tsx'),'utf8');
 expect(card).not.toContain('<Bot ');
 expect(card.match(/<AirSparkles /g)).toHaveLength(1);
});

test('no source file uses the old Bot glyph',()=>{
 const walk=(d:string):string[]=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):/\.tsx$/.test(e.name)?[path.join(d,e.name)]:[]);
 const offenders=walk(path.join(process.cwd(),'src')).filter(f=>/\bBot\b/.test(fs.readFileSync(f,'utf8').replace(/googleBot/g,'')));
 expect(offenders).toEqual([]);
});
