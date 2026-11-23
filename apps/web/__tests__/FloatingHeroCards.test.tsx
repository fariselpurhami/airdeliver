import React from 'react';
import { render } from '@testing-library/react';
import fs from 'fs';
import { FloatingHeroCards, HERO_STAGE_CLASSES } from '@/components/hero/FloatingHeroCards';
jest.mock('next/image',()=>({__esModule:true,default:({fill,...props}:any)=><img {...props}/>}));
it('renders one shared six-card layout with a protected center',()=>{
 const {container}=render(<FloatingHeroCards/>);
 expect(container.querySelectorAll('[data-hero-card]')).toHaveLength(6);
 expect(HERO_STAGE_CLASSES).toContain('min-h-[1000px]');
 for(const file of ['app/(main)/products/page.tsx','app/(main)/_components/LandingClient.tsx']){
  const source=fs.readFileSync(file,'utf8');
  expect(source).toContain('<FloatingHeroCards />');
  expect(source).toContain('HERO_STAGE_CLASSES');
 }
});

it('preserves the original eight-card mobile home distribution',()=>{
 const source=fs.readFileSync('app/(main)/_components/LandingClient.tsx','utf8');
 expect(source).toContain('MobileHomeHeroSection');
 expect(source).toContain('isMobile ? <MobileHomeHeroSection');
 expect(source).toContain('HERO_CARDS.map');
});

 it('copies the original mobile home configuration and gates the catalog replacement below desktop',()=>{
 const home=fs.readFileSync('app/(main)/_components/LandingClient.tsx','utf8');
 const mobile=fs.readFileSync('components/hero/MobileHomeFloatingCards.tsx','utf8');
 const config=(s:string)=>s.slice(s.indexOf('const HERO_CARDS:'),s.indexOf('const PRODUCTION_STEPS')>0?s.indexOf('const PRODUCTION_STEPS'):s.indexOf('const HeroFloatingCard = memo')).trim();
 expect(config(mobile)).toBe(config(home));
 const catalog=fs.readFileSync('app/(main)/products/page.tsx','utf8');
 expect(catalog).toContain('hidden lg:contents');
 expect(catalog).toContain('data-mobile-catalog-distribution');
 expect(catalog).toContain('<MobileHomeFloatingCards />');
 });
